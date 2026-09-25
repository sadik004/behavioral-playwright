"""Search engine module."""

from typing import List
from behavioral_playwright.page.session import PageSession
from behavioral_playwright.models.results import ExtractionRecord
from behavioral_playwright.logging import get_logger

logger = get_logger("search.engine")

class SearchEngine:
    """High-level search operation abstraction."""

    def __init__(self, page: PageSession) -> None:
        self.page = page

    async def search(self, query: str, search_input_selector: str = "input[type='search'], input[name='q']", submit_selector: str = "button[type='submit']") -> List[ExtractionRecord]:
        """Submits a search query and extracts the results."""
        logger.info(f"Executing search for query: {query}")
        
        async def _perform_search():
            # Self-healing typing
            await self.page.type_healed(search_input_selector, query)
            
            # Self-healing click to submit
            try:
                await self.page.click_healed(submit_selector)
            except Exception as click_err:
                # Fallback to Enter key if submit button fails
                logger.warning(f"Submit button click failed ({click_err}), falling back to Enter key")
                try:
                    await self.page.raw_page.keyboard.press("Enter")
                except Exception as key_err:
                    logger.error(f"Keyboard Enter fallback failed: {key_err}")
                    raise

            # Wait for navigation/results
            try:
                await self.page.raw_page.wait_for_load_state("domcontentloaded")
            except Exception as load_err:
                logger.debug(f"Search navigation wait warning: {load_err}")

            # Extract links as results
            return await self.page.extract_links()

        # Call using resilience primitives
        return await self.page.circuit_breaker.execute(
            lambda: self.page.retry_policy.execute(_perform_search),
            operation_name=f"search_{query}"
        )
