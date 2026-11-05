"""Reddit Behavioral Automation and Client Lead Mining Client.

Integrates Reddit Shreddit extraction, high-intent hiring lead discovery,
algorithmic budget extraction, and custom technical pitch generation.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional
from playwright.async_api import async_playwright

from behavioral_playwright.browser.pool import BrowserPoolManager
from behavioral_playwright.config.settings import BrowserConfig
from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.reddit_dtos import (
    RedditAuthStatusDTO,
    RedditLeadAuditDTO,
    RedditLeadDTO,
)

logger = get_logger("reddit")

DEFAULT_SUBREDDITS = ["forhire", "webscraping", "freelance_forhire", "jobbit"]
DEFAULT_INTENT_KEYWORDS = [
    "[hiring]",
    "hiring",
    "python",
    "scraper",
    "scraping",
    "playwright",
    "selenium",
    "crawler",
    "crawl",
    "bot",
    "bypass",
    "cloudflare",
    "datadome",
    "automation",
    "api",
    "budget",
]

BUDGET_REGEX = re.compile(
    r"(\$\s*\d+[\d,]*(?:\.\d{2})?(?:\s*-\s*\$\s*\d+[\d,]*(?:\.\d{2})?)?(?:\s*/\s*(?:hr|hour|project|month|k))?)",
    re.IGNORECASE,
)


class RedditAutomationClient:
    """Production client for Reddit client acquisition, post intelligence, and session management."""

    def __init__(
        self,
        pool: Optional[BrowserPoolManager] = None,
        default_storage_state: str = "reddit_state.json",
    ) -> None:
        self.default_storage_state = default_storage_state
        self._pool = pool
        self._owns_pool = pool is None

    async def _get_pool(self) -> BrowserPoolManager:
        if self._pool is None:
            config = BrowserConfig(headless=True, allow_media=False)
            self._pool = BrowserPoolManager(config=config)
            await self._pool.initialize()
        elif not self._pool.is_initialized:
            await self._pool.initialize()
        return self._pool

    async def close(self) -> None:
        """Closes browser pool if owned."""
        if self._owns_pool and self._pool is not None and self._pool.is_initialized:
            await self._pool.shutdown()

    @staticmethod
    def _fetch_subreddit_json(subreddit: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Zero-latency HTTP fetching of subreddit posts with realistic User-Agent."""
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                children = data.get("data", {}).get("children", [])
                return [c.get("data", {}) for c in children if isinstance(c, dict)]
        except Exception as exc:
            logger.debug(f"[RedditClient] Subreddit JSON endpoint notice for r/{subreddit}: {exc}")
            return []

    async def _scrape_subreddit_dom(self, subreddit: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Fallback Shreddit DOM parser via BrowserPoolManager when HTTP endpoint is throttled."""
        pool = await self._get_pool()
        url = f"https://www.reddit.com/r/{subreddit}/new/"
        results: List[Dict[str, Any]] = []

        try:
            async with pool.get_page(allow_media=False) as page:
                await page.goto(url, wait_until="domcontentloaded")
                posts_locator = page.locator("shreddit-post, div[data-testid='post-container']")
                count = await posts_locator.count()

                for i in range(min(count, limit)):
                    post = posts_locator.nth(i)
                    title = await post.get_attribute("post-title") or ""
                    author = await post.get_attribute("author") or ""
                    post_id = await post.get_attribute("id") or f"dom_{i}"
                    permalink = await post.get_attribute("permalink") or ""
                    full_url = f"https://www.reddit.com{permalink}" if permalink else url

                    if title:
                        results.append({
                            "id": post_id,
                            "title": title,
                            "author": author,
                            "url": full_url,
                            "selftext": "",
                            "created_utc": 0.0,
                        })
        except Exception as exc:
            logger.error(f"[RedditClient] Fallback DOM scraper failed for r/{subreddit}: {exc}")

        return results

    async def mine_hiring_leads(
        self,
        subreddits: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        limit_per_sub: int = 25,
    ) -> List[RedditLeadDTO]:
        """
        Discovers and ranks high-intent paying client leads across technical hiring subreddits.
        Filters by intent keywords (e.g. Python, scraping, bot, playwright, bypass) and extracts budget hints.
        """
        targets = subreddits or DEFAULT_SUBREDDITS
        kw_list = [k.lower() for k in (keywords or DEFAULT_INTENT_KEYWORDS)]
        discovered_leads: List[RedditLeadDTO] = []
        seen_ids = set()

        for sub in targets:
            raw_posts = self._fetch_subreddit_json(sub, limit=limit_per_sub)
            if not raw_posts:
                raw_posts = await self._scrape_subreddit_dom(sub, limit=limit_per_sub)

            for p in raw_posts:
                post_id = str(p.get("id", ""))
                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)

                title = str(p.get("title", ""))
                selftext = str(p.get("selftext", ""))
                combined_text = f"{title} {selftext}".lower()

                # In r/forhire, only match posts tagged [Hiring]
                if sub.lower() in ("forhire", "freelance_forhire") and "[for hire]" in combined_text:
                    continue

                matched = [kw for kw in kw_list if kw in combined_text]
                if not matched:
                    continue

                # Extract budget hint
                budget_match = BUDGET_REGEX.search(f"{title} {selftext}")
                budget_str = budget_match.group(1).strip() if budget_match else None

                permalink = p.get("permalink", "")
                post_url = f"https://www.reddit.com{permalink}" if permalink and not permalink.startswith("http") else p.get("url", f"https://www.reddit.com/r/{sub}")

                lead = RedditLeadDTO(
                    id=post_id,
                    title=title.strip(),
                    subreddit=sub,
                    author=str(p.get("author", "")),
                    url=post_url,
                    created_utc=float(p.get("created_utc", 0.0)),
                    budget_hint=budget_str,
                    matched_keywords=matched,
                    selftext_snippet=selftext[:250].strip() if selftext else "",
                )
                discovered_leads.append(lead)

        # Sort descending by recency
        discovered_leads.sort(key=lambda x: x.created_utc, reverse=True)
        return discovered_leads

    def analyze_lead_and_generate_pitch(self, lead: RedditLeadDTO) -> RedditLeadAuditDTO:
        """
        Analyzes a client lead and formulates an elite, high-converting technical proposal.
        Highlights clean architecture, Playwright anti-bot bypass, and verifiable repo artifacts.
        """
        title_lower = lead.title.lower()
        snippet_lower = lead.selftext_snippet.lower()
        combined = f"{title_lower} {snippet_lower}"

        # Diagnose specific client technical problem
        if any(term in combined for term in ("cloudflare", "datadome", "captcha", "block", "bypass", "forbidden")):
            assessment = "Client is encountering Layer-7 WAF/anti-bot interstitial challenges (Cloudflare Turnstile, DataDome, or IP fingerprint blocking)."
            solution = "Deploy BehavioralPlaywright with Costello Bézier saccadic trajectories, Harris-Wolpert tremor noise, and single-browser ephemeral context pooling."
            angle = "anti-bot evasion & stealth scraping"
        elif any(term in combined for term in ("api", "fastapi", "backend", "database", "pipeline")):
            assessment = "Client requires high-throughput data extraction integrated into a clean backend/database pipeline with typed DTO validation."
            solution = "Implement 3-tier clean architecture (FastAPI/Postgres), O(1) in-memory lookups, and AWS full-jitter exponential backoff resilience."
            angle = "production backend architecture"
        else:
            assessment = "Client needs robust, automated data extraction without fragile CSS selectors breaking over time."
            solution = "Build self-healing multi-tier selector resolver with automatic Next.js/Nuxt hydration metadata extraction."
            angle = "resilient web automation"

        author_salutation = f"u/{lead.author}" if lead.author else "there"

        pitch = (
            f"Hi {author_salutation},\n\n"
            f"I came across your post regarding: \"{lead.title}\".\n\n"
            f"Based on your requirements, the core challenge is {assessment.lower()}\n\n"
            f"Here is how I would engineer this for you:\n"
            f"1. **{solution}**\n"
            f"2. **Zero Fragility:** Enforce semantic locators and route-level asset blocking so the scraper is lightning-fast and never crashes on DOM updates.\n"
            f"3. **Production Data Quality:** All extracted records are typed and validated via Pydantic schemas before export (CSV/JSON/Database).\n\n"
            f"I have built an open-source enterprise stealth framework solving exactly this: https://github.com/sadik004/behavioral-playwright (KS-test verified human biometric movement & Level-5 stealth).\n\n"
            f"Happy to jump on a quick chat or share a live demo script for your target site. What is the best way to connect?"
        )

        return RedditLeadAuditDTO(
            lead=lead,
            intent_level="HIGH" if ("[hiring]" in title_lower or lead.budget_hint) else "MEDIUM",
            technical_assessment=assessment,
            recommended_solution=solution,
            pitch_draft=pitch,
        )

    async def check_auth_status(
        self,
        storage_state_path: Optional[str] = None,
    ) -> RedditAuthStatusDTO:
        """Verifies if the saved Reddit storage state provides an active authenticated session."""
        path = storage_state_path or self.default_storage_state
        if not os.path.exists(path):
            return RedditAuthStatusDTO(
                authenticated=False,
                message=f"Session file '{path}' not found. Run export_reddit_session.py to login once.",
            )

        pool = await self._get_pool()
        try:
            async with pool.get_page(storage_state=path, allow_media=False) as page:
                await page.goto("https://www.reddit.com/", wait_until="domcontentloaded")
                user_button = page.locator("shreddit-async-loader[bundlename='user_drawer'], button[id*='USER_DROPDOWN_ID']").first

                if await user_button.count() > 0:
                    return RedditAuthStatusDTO(
                        authenticated=True,
                        message="Reddit session is active and authenticated.",
                    )
                return RedditAuthStatusDTO(
                    authenticated=False,
                    message="Session expired or anonymous profile detected.",
                )
        except Exception as exc:
            return RedditAuthStatusDTO(
                authenticated=False,
                message=f"Error checking session: {exc}",
            )

    @staticmethod
    async def export_session_interactive(
        output_path: str = "reddit_state.json",
        timeout_seconds: int = 180,
    ) -> RedditAuthStatusDTO:
        """Opens headful browser allowing user to log in to Reddit once and dump storage_state.json."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            logger.info("[RedditClient] Opening interactive Reddit login window...")
            await page.goto("https://www.reddit.com/login/")

            try:
                # Wait until redirected to home feed or profile
                await page.wait_for_url(lambda u: "login" not in u.lower(), timeout=timeout_seconds * 1000)
                await context.storage_state(path=output_path)
                logger.info(f"[RedditClient] Successfully saved Reddit session to: {output_path}")
                await browser.close()
                return RedditAuthStatusDTO(
                    authenticated=True,
                    message=f"Interactive login succeeded. State saved to '{output_path}'.",
                )
            except Exception as exc:
                await browser.close()
                return RedditAuthStatusDTO(
                    authenticated=False,
                    message=f"Interactive login timed out or closed: {exc}",
                )
