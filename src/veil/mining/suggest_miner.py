"""
Google Suggest Wildcard & Alphabet Mining Engine.
Extracts search query autocomplete hierarchies, wildcard completions, and A-Z alphabet drilldowns.
"""

from __future__ import annotations

import asyncio
import json
import re
import string
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.seo_dtos import SuggestResult

logger = get_logger("mining.suggest")

try:
    from curl_cffi.requests import AsyncSession  # type: ignore
    _HAS_CURL_CFFI = True
except ImportError:
    _HAS_CURL_CFFI = False


class GoogleSuggestMiner:
    """
    Mines search autocomplete predictions and keyword expansions from Google Suggest.
    Supports wildcard query pattern matching and recursive A-Z alphabet soup drilldowns.
    """

    GOOGLE_SUGGEST_URL = "https://suggestqueries.google.com/complete/search"

    def __init__(self, default_lang: str = "en", default_country: str = "us") -> None:
        self.default_lang = default_lang
        self.default_country = default_country

    @staticmethod
    def _clean_suggestion(raw_text: str) -> str:
        """Strips HTML bolding tags, non-breaking spaces, and leading/trailing whitespace."""
        if not raw_text:
            return ""
        cleaned = re.sub(r"<[^>]+>", "", raw_text)
        cleaned = cleaned.replace("\xa0", " ").strip()
        return cleaned

    def parse_response_json(self, raw_data: Any) -> List[str]:
        """
        Parses Google Suggest JSON responses (Chrome/Firefox client formats)
        into a clean, deduplicated list of search suggestions.
        """
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except Exception:
                return []

        suggestions: List[str] = []
        if isinstance(raw_data, list) and len(raw_data) >= 2:
            second_item = raw_data[1]
            if isinstance(second_item, list):
                for item in second_item:
                    if isinstance(item, str):
                        cleaned = self._clean_suggestion(item)
                        if cleaned and cleaned not in suggestions:
                            suggestions.append(cleaned)
                    elif isinstance(item, list) and item and isinstance(item[0], str):
                        cleaned = self._clean_suggestion(item[0])
                        if cleaned and cleaned not in suggestions:
                            suggestions.append(cleaned)
        return suggestions

    async def fetch_suggestions(
        self,
        query: str,
        lang: Optional[str] = None,
        country: Optional[str] = None,
        client: str = "chrome",
        timeout: float = 8.0,
    ) -> List[str]:
        """
        Fetches autocomplete suggestions for a single query using stealth HTTP impersonation.
        Falls back to standard urllib if curl_cffi is unavailable or fails.
        """
        if not query or not query.strip():
            return []

        target_lang = lang or self.default_lang
        target_country = country or self.default_country
        url = (
            f"{self.GOOGLE_SUGGEST_URL}?client={client}&q={quote_plus(query.strip())}"
            f"&hl={target_lang}&gl={target_country}"
        )

        # 1. Primary: curl_cffi stealth browser impersonation
        if _HAS_CURL_CFFI:
            try:
                async with AsyncSession(impersonate="chrome120") as session:
                    resp = await session.get(url, timeout=timeout)
                    if resp.status_code == 200:
                        try:
                            return self.parse_response_json(resp.json())
                        except Exception:
                            return self.parse_response_json(resp.text)
            except Exception as exc:
                logger.debug(f"[SuggestMiner] curl_cffi request failed for '{query}': {exc}")

        # 2. Resilient fallback: urllib via asyncio executor
        try:
            import urllib.request

            def _urllib_fetch() -> str:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return response.read().decode("utf-8", errors="ignore")

            raw_body = await asyncio.to_thread(_urllib_fetch)
            return self.parse_response_json(raw_body)
        except Exception as fallback_exc:
            logger.warning(f"[SuggestMiner] Fallback fetch failed for '{query}': {fallback_exc}")
            return []

    async def mine(
        self,
        query: str,
        alphabet: bool = False,
        lang: Optional[str] = None,
        country: Optional[str] = None,
        concurrency: int = 5,
    ) -> SuggestResult:
        """
        Runs autocomplete mining for a query. If alphabet=True, executes an A-Z
        alphabetical drilldown expansion and merges results with O(1) deduplication.
        """
        clean_query = query.strip()
        target_lang = lang or self.default_lang
        target_country = country or self.default_country

        # 1. Fetch base query suggestions
        base_suggestions = await self.fetch_suggestions(
            clean_query, lang=target_lang, country=target_country
        )

        all_suggestions: List[str] = list(base_suggestions)
        seen_queries = set(s.lower() for s in all_suggestions)
        alphabet_tree: Dict[str, List[str]] = {}

        # 2. Alphabet soup drilldown (A through Z)
        if alphabet:
            sem = asyncio.Semaphore(max(1, concurrency))

            async def _fetch_letter(char: str) -> tuple[str, List[str]]:
                # Wildcard pattern replacement if query contains '*' or '_'
                if "*" in clean_query:
                    drill_query = clean_query.replace("*", char, 1)
                elif "_" in clean_query:
                    drill_query = clean_query.replace("_", char, 1)
                else:
                    drill_query = f"{clean_query} {char}"

                async with sem:
                    results = await self.fetch_suggestions(
                        drill_query, lang=target_lang, country=target_country
                    )
                    return char, results

            tasks = [_fetch_letter(char) for char in string.ascii_lowercase]
            letter_results = await asyncio.gather(*tasks, return_exceptions=False)

            for char, results in letter_results:
                alphabet_tree[char] = results
                for item in results:
                    lowered = item.lower()
                    if lowered not in seen_queries:
                        seen_queries.add(lowered)
                        all_suggestions.append(item)

        return SuggestResult(
            query=clean_query,
            suggestions=all_suggestions,
            alphabet_tree=alphabet_tree,
            total_unique=len(all_suggestions),
        )

    def mine_sync(
        self,
        query: str,
        alphabet: bool = False,
        lang: Optional[str] = None,
        country: Optional[str] = None,
    ) -> SuggestResult:
        """Synchronous wrapper for mine()."""
        return asyncio.run(
            self.mine(query=query, alphabet=alphabet, lang=lang, country=country)
        )


SuggestMiner = GoogleSuggestMiner

__all__ = ["GoogleSuggestMiner", "SuggestMiner"]
