"""Crawling module."""

from typing import List, Set
from behavioral_playwright.page.session import PageSession
from behavioral_playwright.models.results import ExtractionRecord
from behavioral_playwright.logging import get_logger

logger = get_logger("crawling.crawler")

class Crawler:
    """A basic crawler built on top of the 10.1.0a1 architecture."""

    def __init__(self, page: PageSession) -> None:
        self.page = page

    async def crawl(self, start_url: str, max_pages: int = 5) -> List[ExtractionRecord]:
        """Crawls starting from a URL and extracts links/articles."""
        visited: Set[str] = set()
        queue: List[str] = [start_url]
        results: List[ExtractionRecord] = []

        while queue and len(visited) < max_pages:
            current_url = queue.pop(0)
            if current_url in visited:
                continue

            logger.info(f"Crawling: {current_url}")
            try:
                # Wrap with CircuitBreaker and RetryPolicy
                async def _crawl_page():
                    await self.page.goto(current_url)
                    visited.add(current_url)
                    return await self.page.extract_links()

                # Call using resilience primitives
                page_links = await self.page.circuit_breaker.execute(
                    lambda: self.page.retry_policy.execute(_crawl_page),
                    operation_name=f"crawl_{current_url}"
                )
                
                if page_links:
                    results.extend(page_links)
                    
                    # Add new links to queue
                    for link_record in page_links:
                        url = link_record.metadata.get("url")
                        if url and isinstance(url, str) and url.startswith("http") and url not in visited:
                            queue.append(url)
            except Exception as e:
                logger.error(f"Failed to crawl {current_url}: {e}")

        return results
