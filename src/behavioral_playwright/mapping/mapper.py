"""Mapping module."""

from typing import Dict, Any
from behavioral_playwright.page.session import PageSession
from behavioral_playwright.logging import get_logger

logger = get_logger("mapping.mapper")

class SiteMapper:
    """Discovers useful page/link structure using DOM extraction."""

    def __init__(self, page: PageSession) -> None:
        self.page = page

    async def map(self, url: str) -> Dict[str, Any]:
        """Maps out the structural links and articles of a page."""
        logger.info(f"Mapping structural layout for: {url}")
        
        async def _perform_map():
            await self.page.goto(url)
            
            links = await self.page.extract_links()
            articles = await self.page.extract_articles()
            
            # Categorize links for basic site structure mapping
            internal_links = []
            external_links = []
            
            for link in links:
                href = link.metadata.get("url", "")
                if isinstance(href, str):
                    if href.startswith("http") and not href.startswith(url):
                        external_links.append(link)
                    else:
                        internal_links.append(link)
                        
            return {
                "url": url,
                "title": await self.page.get_title(),
                "internal_links_count": len(internal_links),
                "external_links_count": len(external_links),
                "articles_count": len(articles),
                "internal_links": internal_links,
                "external_links": external_links,
                "articles": articles
            }

        # Call using resilience primitives
        return await self.page.circuit_breaker.execute(
            lambda: self.page.retry_policy.execute(_perform_map),
            operation_name=f"map_{url}"
        )
