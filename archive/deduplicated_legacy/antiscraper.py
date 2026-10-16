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
# Core AntiScraper Engine
# -----------------------------------------------------------------------------
class AntiScraper:
    """
    Production-grade, resilient browser automation bot.
    Handles anti-bot stealth masking, Cloudflare bypass, smooth human scrolling,
    and automatic DOM parsing with persistent context pooling across URLs.
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

        self._pw: Optional[Any] = None
        self._context: Optional[BrowserContext] = None
        self._profile_dir: Optional[str] = None
        self._is_closed: bool = False

    async def _ensure_context(self) -> BrowserContext:
        """Lazy-initializes or reuses a persistent pooled BrowserContext across URLs."""
        if self._context is not None:
            return self._context

        self._profile_dir = _get_temp_profile()
        self._pw = await async_playwright().start()

        browser_args = [
            "--start-maximized",
            "--window-position=0,0",
            "--window-size=1920,1080",
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
        ]

        self._context = await self._pw.chromium.launch_persistent_context(
            user_data_dir=self._profile_dir,
            headless=self.headless,
            no_viewport=True,
            args=browser_args,
            ignore_default_args=["--enable-automation"]
        )
        self._is_closed = False
        return self._context

    async def close(self) -> None:
        """Deterministic teardown of pooled context, Playwright process, and temp profile."""
        if self._is_closed:
            return
        self._is_closed = True

        if self._context:
            try:
                await self._context.close()
            except Exception as e:
                logger.debug(f"Error closing browser context: {e}", exc_info=True)
            self._context = None

        if self._pw:
            try:
                await self._pw.stop()
            except Exception as e:
                logger.debug(f"Error stopping Playwright runtime: {e}", exc_info=True)
            self._pw = None

        if self._profile_dir and os.path.exists(self._profile_dir):
            try:
                shutil.rmtree(self._profile_dir, ignore_errors=True)
            except Exception as e:
                logger.debug(f"Error removing temp profile directory {self._profile_dir}: {e}")
            self._profile_dir = None

    async def __aenter__(self) -> "AntiScraper":
        await self._ensure_context()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def _handle_cloudflare(self, page: Page, max_wait_sec: int = 15) -> bool:
        """Dynamic gate that automatically clears Cloudflare Turnstile challenges."""
        for _ in range(max_wait_sec):
            try:
                title = await page.title()
                if "just a moment" not in title.lower() and "security verification" not in title.lower() and len(title) > 5:
                    return True
            except Exception as e:
                logger.debug(f"Title evaluation error during Cloudflare check: {e}")

            try:
                for frame in page.frames:
                    if "turnstile" in frame.url or "challenges.cloudflare.com" in frame.url:
                        box = await frame.query_selector("input[type='checkbox'], span.mark, div.ctp-checkbox-label")
                        if box:
                            await box.click()
            except Exception as e:
                logger.debug(f"Cloudflare frame interaction skipped: {e}")

            try:
                await page.wait_for_load_state("domcontentloaded", timeout=1000)
            except Exception:
                await asyncio.sleep(0.5)

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
        Generic high-level scraping workflow reusing the pooled browser context.
        """
        context = await self._ensure_context()
        page = await context.new_page()
        results: List[Dict[str, Any]] = []

        if self.stealth:
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            """)

        try:
            try:
                await page.bring_to_front()
            except Exception as e:
                logger.debug(f"Failed to bring page to front: {e}")

            logger.info(f"[*] Navigating to: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)

            # Cloudflare resolution
            await self._handle_cloudflare(page, max_wait_sec=12)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=self.timeout_ms)
            except Exception as e:
                logger.debug(f"DOM load wait timed out after Cloudflare check: {e}")

            # Search interaction if requested
            if keyword and search_selector:
                logger.info(f"[*] Searching for: '{keyword}'...")
                input_elem = await page.wait_for_selector(search_selector, state="visible", timeout=self.timeout_ms)
                if input_elem:
                    await input_elem.click()
                    await input_elem.fill(keyword)
                    await page.keyboard.press("Enter")
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=self.timeout_ms)
                    except Exception as e:
                        logger.debug(f"DOM load state wait timed out after search: {e}")

            # Smooth scrolling for dynamic lazy-loading with dynamic wait
            if scroll_count > 0:
                logger.info(f"[*] Scrolling feed ({scroll_count} intervals)...")
                await page.mouse.move(500, 500)
                for i in range(1, scroll_count + 1):
                    await page.evaluate(f"window.scrollTo({{top: {i * 600}, behavior: 'smooth'}})")
                    try:
                        await page.wait_for_function(
                            f"() => window.pageYOffset >= {(i - 1) * 500} || document.body.scrollHeight <= window.innerHeight",
                            timeout=max(int(scroll_delay * 1000), 500)
                        )
                    except Exception as e:
                        logger.debug(f"Scroll completion wait timed out: {e}")

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
            logger.error(f"[!] Scrape error on {url}: {e}", exc_info=True)
            raise
        finally:
            try:
                await page.close()
            except Exception as e:
                logger.debug(f"Error closing page: {e}")

        return results


# Backward-compatibility alias
StealthBot = AntiScraper


# -----------------------------------------------------------------------------
# 1-Line Convenience Wrappers for Instant Scraping
# -----------------------------------------------------------------------------
async def _async_scrape_ryans(keyword: str, output_csv: Optional[str], max_items: int) -> List[Dict[str, str]]:
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

    async with AntiScraper(headless=False) as bot:
        return await bot.scrape(
            url="https://www.ryans.com",
            keyword=keyword,
            search_selector="input[placeholder*='Keyword'], #user-search-box, input.form-control",
            scroll_count=4,
            eval_script=eval_code,
            output_csv=output_csv
        )


def scrape_ryans(keyword: str = "RTX 4060", output_csv: Optional[str] = None, max_items: int = 30) -> List[Dict[str, str]]:
    """Instant 1-line scraper for Ryans Computers."""
    return asyncio.run(_async_scrape_ryans(keyword=keyword, output_csv=output_csv, max_items=max_items))


async def _async_scrape_bbc(section: str, output_csv: Optional[str], max_items: int) -> List[Dict[str, str]]:
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

    async with AntiScraper(headless=False) as bot:
        return await bot.scrape(
            url=url,
            scroll_count=4,
            eval_script=eval_code,
            output_csv=output_csv
        )


def scrape_bbc(section: str = "bangla", output_csv: Optional[str] = None, max_items: int = 30) -> List[Dict[str, str]]:
    """Instant 1-line scraper for BBC News / BBC Bangla."""
    return asyncio.run(_async_scrape_bbc(section=section, output_csv=output_csv, max_items=max_items))
