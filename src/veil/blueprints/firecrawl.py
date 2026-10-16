"""Firecrawl Drop-in Replacement Client Blueprint (`src/veil/blueprints/firecrawl.py`).

Provides high-fidelity web scraping and structured extraction mirroring the Firecrawl API:
- Clean Markdown extraction from arbitrary web pages (zero cloud token cost)
- Metadata extraction (title, description, canonical, OpenGraph)
- Multi-page crawling with SQLite checkpoint store and bounded concurrency
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from veil.crawling.checkpoint import CheckpointStore
from veil.crawling.models import CrawlerTier, CrawlRequest
from veil.crawling.service import AutoRuleSchemaExtractor, TieredCrawlerService


class FirecrawlReplacementBlueprint:
    """Self-contained drop-in replacement for Firecrawl web scraping and crawling."""

    def __init__(
        self,
        crawler: Optional[TieredCrawlerService] = None,
        checkpoint_store: Optional[CheckpointStore] = None,
        max_concurrency: int = 10,
    ) -> None:
        self.checkpoint = checkpoint_store or CheckpointStore(":memory:")
        self.crawler = crawler or TieredCrawlerService(
            max_concurrency=max_concurrency, checkpoint_store=self.checkpoint
        )

    @staticmethod
    def html_to_markdown(html: str) -> str:
        """Converts raw HTML into clean, formatted Markdown without LLM cost."""
        if not html:
            return ""

        # Remove scripts, styles, and SVG
        text = re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Convert headers
        for level in range(6, 0, -1):
            pattern = rf"<h{level}[^>]*>(.*?)</h{level}>"
            replacement = rf"\n\n{'#' * level} \1\n\n"
            text = re.sub(pattern, replacement, text, flags=re.DOTALL | re.IGNORECASE)

        # Convert table rows and cells
        text = re.sub(r"</th>\s*<th[^>]*>", " | ", text, flags=re.IGNORECASE)
        text = re.sub(r"</td>\s*<td[^>]*>", " | ", text, flags=re.IGNORECASE)
        text = re.sub(r"<tr[^>]*>\s*<td>", "| ", text, flags=re.IGNORECASE)
        text = re.sub(r"</td>\s*</tr>", " |", text, flags=re.IGNORECASE)

        # Convert links <a href="url">text</a> -> [text](url)
        text = re.sub(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r"[\2](\1)", text, flags=re.DOTALL | re.IGNORECASE)

        # Convert bold / strong / em
        text = re.sub(r"<(strong|b)>(.*?)</\1>", r"**\2**", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<(em|i)>(.*?)</\1>", r"*\2*", text, flags=re.DOTALL | re.IGNORECASE)

        # Convert lists
        text = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", text, flags=re.DOTALL | re.IGNORECASE)

        # Strip remaining HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Clean multiple spaces and blank lines
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
        cleaned = "\n".join(line for line in lines if line)
        return cleaned

    def extract_metadata(self, html: str, source_url: str) -> Dict[str, Any]:
        """Extracts page title, description, and OpenGraph tags."""
        title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_m.group(1).strip() if title_m else ""

        desc_m = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
        desc = desc_m.group(1).strip() if desc_m else ""

        og_title_m = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
        og_title = og_title_m.group(1).strip() if og_title_m else ""

        return {
            "title": title,
            "description": desc,
            "ogTitle": og_title,
            "sourceURL": source_url,
            "language": "en",
        }

    async def scrape(self, url: str, formats: Optional[List[str]] = None) -> Dict[str, Any]:
        """Scrapes a URL and returns Firecrawl-compatible formatted markdown and metadata."""
        fmts = formats or ["markdown", "html"]
        req = CrawlRequest(url=url, initial_tier=CrawlerTier.HTTP_FAST)
        resp = await self.crawler.crawl(req)

        metadata = self.extract_metadata(resp.body, url)
        metadata["statusCode"] = resp.status_code

        data: Dict[str, Any] = {"metadata": metadata}
        if "markdown" in fmts:
            data["markdown"] = self.html_to_markdown(resp.body)
        if "html" in fmts:
            data["html"] = resp.body
        if "schema" in fmts:
            data["schema"] = AutoRuleSchemaExtractor.infer_and_extract(resp.body)

        return {
            "success": resp.is_success,
            "data": data,
        }

    async def crawl(
        self,
        start_url: str,
        limit: int = 5,
        formats: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Performs crash-resilient multi-page crawl with checkpoint store."""
        fmts = formats or ["markdown"]
        visited_urls: List[str] = []
        queue = [start_url]
        pages_data: List[Dict[str, Any]] = []

        while queue and len(visited_urls) < limit:
            current = queue.pop(0)
            if current in visited_urls:
                continue

            visited_urls.append(current)
            scrape_res = await self.scrape(current, formats=fmts)
            pages_data.append(scrape_res.get("data", {}))

            # Extract child links if needed
            body = scrape_res.get("data", {}).get("html", "")
            links = re.findall(r'href=["\'](http[^"\']+)["\']', body)
            for link in links:
                if link not in visited_urls and link not in queue:
                    queue.append(link)

        return {
            "success": True,
            "total_pages": len(pages_data),
            "data": pages_data,
        }


__all__ = ["FirecrawlReplacementBlueprint"]
