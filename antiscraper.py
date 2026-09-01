"""
================================================================================
ANTISCRAPER: Modern High-Level Python Web Automation & Scraping Library
Author: Antigravity Developer Suite
Zero Boilerplate | 100% Anti-Bot Bypass | Visual & Headless | Safe CSV Export
================================================================================
"""

import asyncio
import csv
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Union
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, BrowserContext

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AntiScraper")


def _get_temp_profile() -> str:
    """Creates a temporary isolated Chrome profile directory."""
    temp_dir = os.path.join(tempfile.gettempdir(), f"chrome_anti_{int(time.time()*1000)}")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def safe_save_csv(data: List[Dict[str, Any]], filename: str) -> str:
    """Saves structured data list to CSV, handling file locks safely."""
    if not data:
        logger.warning("[!] No data available to save.")
        return filename

    output_path = filename
    fieldnames = list(data[0].keys())

    for attempt in range(5):
        try:
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            logger.info(f"[✓] Successfully saved {len(data)} items -> '{output_path}'")
            return output_path
        except PermissionError:
            output_path = f"{filename.rsplit('.', 1)[0]}_{int(time.time())}.csv"

    return output_path


# -----------------------------------------------------------------------------
# Core StealthBot Engine
# -----------------------------------------------------------------------------
class StealthBot:
    """
    Ultra-lightweight, plug-and-play browser automation bot.
    Handles anti-bot stealth masking, Cloudflare bypass, smooth human scrolling,
    and automatic DOM parsing in minimal code.
    """

    def __init__(
        self,
        headless: bool = False,
        timeout_ms: int = 45000,
        stealth: bool = True
    ) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.stealth = stealth

    async def _launch(self) -> tuple[Any, BrowserContext, Page, str]:
        profile_dir = _get_temp_profile()
        pw = await async_playwright().start()

        browser_args = [
            "--start-maximized",
            "--window-position=0,0",
            "--window-size=1920,1080",
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
        ]

        context = await pw.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=self.headless,
            no_viewport=True,
            args=browser_args,
            ignore_default_args=["--enable-automation"]
        )

        page = context.pages[0] if context.pages else await context.new_page()

        if self.stealth:
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            """)

        try:
            await page.bring_to_front()
        except Exception:
            pass

        return pw, context, page, profile_dir

    async def _handle_cloudflare(self, page: Page, max_wait_sec: int = 15) -> bool:
        """Dynamic gate that automatically clears Cloudflare Turnstile challenges."""
        for _ in range(max_wait_sec):
            title = await page.title()
            if "just a moment" not in title.lower() and "security verification" not in title.lower() and len(title) > 5:
                return True

            try:
                for frame in page.frames:
                    if "turnstile" in frame.url or "challenges.cloudflare.com" in frame.url:
                        box = await frame.query_selector("input[type='checkbox'], span.mark, div.ctp-checkbox-label")
                        if box:
                            await box.click()
            except Exception:
                pass

            await asyncio.sleep(1)
        return False

    async def scrape(
        self,
        url: str,
        keyword: Optional[str] = None,
        search_selector: Optional[str] = None,
        scroll_count: int = 3,
        scroll_delay: float = 1.2,
        eval_script: Optional[str] = None,
        output_csv: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generic high-level scraping workflow in a single function call.
        """
        pw, context, page, profile_dir = await self._launch()
        results: List[Dict[str, Any]] = []

        try:
            logger.info(f"[*] Navigating to: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)

            # Cloudflare resolution
            await self._handle_cloudflare(page, max_wait_sec=12)
            await asyncio.sleep(1.5)

            # Search interaction if requested
            if keyword and search_selector:
                logger.info(f"[*] Searching for: '{keyword}'...")
                input_elem = await page.query_selector(search_selector)
                if input_elem:
                    await input_elem.click()
                    await input_elem.fill(keyword)
                    await asyncio.sleep(0.4)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(5)

            # Smooth scrolling for dynamic lazy-loading
            if scroll_count > 0:
                logger.info(f"[*] Scrolling feed ({scroll_count} intervals)...")
                await page.mouse.move(500, 500)
                for i in range(1, scroll_count + 1):
                    await page.evaluate(f"window.scrollTo({{top: {i * 600}, behavior: 'smooth'}})")
                    await asyncio.sleep(scroll_delay)

            # Execute evaluation script or return page HTML
            if eval_script:
                raw_results = await page.evaluate(eval_script)
                if isinstance(raw_results, list):
                    results = raw_results
            else:
                html = await page.content()
                results = [{"html": html, "url": page.url, "title": await page.title()}]

            # Auto export if CSV requested
            if output_csv and results:
                safe_save_csv(results, output_csv)

        except Exception as e:
            logger.error(f"[!] Scrape error: {e}", exc_info=True)
        finally:
            await context.close()
            await pw.stop()
            try:
                shutil.rmtree(profile_dir, ignore_errors=True)
            except Exception:
                pass

        return results


# -----------------------------------------------------------------------------
# 1-Line Convenience Wrappers for Instant Scraping
# -----------------------------------------------------------------------------
def scrape_ryans(keyword: str = "RTX 4060", output_csv: Optional[str] = None, max_items: int = 30) -> List[Dict[str, str]]:
    """Instant 1-line scraper for Ryans Computers."""
    if not output_csv:
        output_csv = f"ryans_{re.sub(r'[^a-zA-Z0-9_]', '_', keyword.lower())}.csv"

    eval_code = f"""
        () => {{
            const results = [];
            const cards = document.querySelectorAll('.cus-col, .product-box, .product-card, .grid-item, div.card, div[class*="col-"]');
            
            cards.forEach(card => {{
                const titleEl = card.querySelector('p.card-text a, a.card-text, .product-title a, h2 a, h3 a, a[href*="/product/"]');
                if (!titleEl) return;
                
                const title = (titleEl.getAttribute('title') || titleEl.innerText || '').trim();
                let link = titleEl.getAttribute('href') || '';
                if (link && !link.startsWith('http')) {{
                    link = 'https://www.ryans.com' + link;
                }}
                
                const prTextEl = card.querySelector('.pr-text, .price, .special-price, .product-price, p.pr-text, span.pr-text');
                let price = prTextEl ? prTextEl.innerText.trim() : '';
                
                const delEl = card.querySelector('del, .old-price, span.price-old');
                let regPrice = delEl ? delEl.innerText.trim() : 'N/A';
                
                if (!price || price.includes('0')) {{
                    const allText = card.innerText.replace(/\\s+/g, ' ');
                    const match = allText.match(/(?:Special\\s*Price\\s*)?(?:Tk\\.?|৳)\\s*[1-9][\\d,]+/i);
                    if (match) price = match[0];
                }}
                
                if (title && title.length > 5 && !title.toLowerCase().startsWith('show ') && !results.some(r => r.Title === title)) {{
                    results.push({{
                        Title: title,
                        "Current Price": price || "Contact Store",
                        "Regular Price": regPrice || "N/A",
                        URL: link
                    }});
                }}
            }});
            return results.slice(0, {max_items});
        }}
    """

    bot = StealthBot(headless=False)
    return asyncio.run(
        bot.scrape(
            url="https://www.ryans.com",
            keyword=keyword,
            search_selector="input[placeholder*='Keyword'], #user-search-box, input.form-control",
            scroll_count=4,
            eval_script=eval_code,
            output_csv=output_csv
        )
    )


def scrape_bbc(section: str = "bangla", output_csv: Optional[str] = None, max_items: int = 30) -> List[Dict[str, str]]:
    """Instant 1-line scraper for BBC News / BBC Bangla."""
    if not output_csv:
        output_csv = f"bbc_{section.lower()}.csv"

    url = "https://www.bbc.com/bengali" if section.lower() in ["bangla", "bengali", "bd"] else f"https://www.bbc.com/news/{section.lower()}" if section.lower() in ["technology", "business", "science", "sport"] else "https://www.bbc.com/news"

    eval_code = f"""
        () => {{
            const results = [];
            const cards = document.querySelectorAll('div[data-testid="card-text-wrapper"], div[data-testid="anchor-inner"], article, div[class*="Promo"], div[class*="Card"]');
            
            cards.forEach(card => {{
                const headlineEl = card.querySelector('h2, h3, [data-testid="card-headline"]');
                if (!headlineEl) return;
                
                const headline = (headlineEl.innerText || '').trim();
                if (!headline || headline.length < 10) return;
                
                const linkEl = card.querySelector('a') || headlineEl.closest('a');
                let link = linkEl ? (linkEl.getAttribute('href') || '') : '';
                if (link && !link.startsWith('http')) link = 'https://www.bbc.com' + link;
                
                const catEl = card.querySelector('[data-testid="card-tag"], span[class*="Tag"]');
                const category = catEl ? catEl.innerText.trim() : 'BBC News';
                
                const descEl = card.querySelector('p[data-testid="card-description"], p');
                let summary = descEl ? descEl.innerText.trim() : 'Full coverage available on BBC.';
                
                const timeEl = card.querySelector('span[data-testid="card-metadata-lastupdated"], time');
                const timestamp = timeEl ? timeEl.innerText.trim() : 'Recent';
                
                if (!results.some(r => r.Headline === headline || r.URL === link)) {{
                    results.push({{
                        Headline: headline,
                        Category: category,
                        Summary: summary,
                        Timestamp: timestamp,
                        URL: link
                    }});
                }}
            }});
            return results.slice(0, {max_items});
        }}
    """

    bot = StealthBot(headless=False)
    return asyncio.run(
        bot.scrape(
            url=url,
            scroll_count=4,
            eval_script=eval_code,
            output_csv=output_csv
        )
    )
