"""Site mapping and structural hierarchy discovery module."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from behavioral_playwright.exceptions import NavigationError
from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.results import ExtractionRecord
from behavioral_playwright.page.session import PageSession

logger = get_logger("mapping.mapper")


class SiteMapper:
    """Discovers useful page, link, and structural heading hierarchies using live DOM extraction."""

    def __init__(self, page: PageSession) -> None:
        self.page = page

    async def map(self, url: str) -> Dict[str, Any]:
        """Maps out the structural links, articles, and heading hierarchies of a page."""
        logger.info(f"Mapping structural layout for: {url}")

        async def _perform_map() -> Dict[str, Any]:
            await self.page.goto(url)

            links: List[ExtractionRecord] = await self.page.extract_links()
            articles: List[ExtractionRecord] = await self.page.extract_articles()

            # Accurate internal vs external link classification using domain netloc comparison
            base_parsed = urlparse(url)
            base_netloc = base_parsed.netloc.lower()

            internal_links: List[ExtractionRecord] = []
            external_links: List[ExtractionRecord] = []

            for link in links:
                href = link.href or link.url or link.get("url")
                if not href or not isinstance(href, str):
                    continue
                parsed = urlparse(href)
                # If relative or matching domain -> internal link; otherwise external
                if not parsed.netloc or parsed.netloc.lower() == base_netloc:
                    internal_links.append(link)
                else:
                    external_links.append(link)

            # Discover structural heading hierarchy
            script = """
            () => {
                const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
                return headings.map(h => ({
                    level: h.tagName.toLowerCase(),
                    text: (h.innerText || h.textContent || '').trim()
                })).filter(h => h.text.length > 0);
            }
            """
            headings = []
            try:
                raw_headings = await self.page.evaluate(script)
                if isinstance(raw_headings, list):
                    headings = raw_headings
            except Exception as e:
                logger.debug(f"Heading hierarchy scan skipped: {e}")

            return {
                "url": url,
                "title": await self.page.get_title(),
                "headings": headings,
                "headings_count": len(headings),
                "internal_links_count": len(internal_links),
                "external_links_count": len(external_links),
                "articles_count": len(articles),
                "internal_links": internal_links,
                "external_links": external_links,
                "articles": articles,
            }

        # Call using resilience primitives
        return await self.page.circuit_breaker.execute(
            lambda: self.page.retry_policy.execute(_perform_map),
            operation_name=f"map_{url}"
        )
