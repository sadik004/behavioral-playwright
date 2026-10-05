"""Search engine abstraction providing resilient query execution and structured result extraction."""

from __future__ import annotations

from typing import List, Optional
from behavioral_playwright.exceptions import SearchError
from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.results import ExtractionRecord
from behavioral_playwright.page.session import PageSession

logger = get_logger("search.engine")


class SearchEngine:
    """High-level search operation abstraction with behavioral typing and result deduplication."""

    def __init__(self, page: PageSession) -> None:
        self.page = page

    async def search(
        self,
        query: str,
        search_input_selector: str = "input[type='search'], input[name='q']",
        submit_selector: str = "button[type='submit']",
        results_container_selector: Optional[str] = None,
    ) -> List[ExtractionRecord]:
        """
        Submits a search query and extracts the results.
        Validates query non-emptiness, executes behavioral typing, handles submission,
        and returns deduplicated, provenance-tagged results in deterministic DOM order.
        """
        if not query or not query.strip():
            raise ValueError("Search query must not be empty or whitespace.")

        query_clean = query.strip()
        logger.info(f"Executing search for query: {query_clean}")

        async def _perform_search() -> List[ExtractionRecord]:
            # 1. Behavioral typing into search input
            await self.page.type_healed(search_input_selector, query_clean)

            # 2. Submit search query
            try:
                await self.page.click_healed(submit_selector)
            except Exception as click_err:
                logger.warning(f"Submit button click failed ({click_err}), falling back to Enter key")
                try:
                    if hasattr(self.page, "keyboard") and hasattr(self.page.keyboard, "press"):
                        await self.page.keyboard.press("Enter")
                    elif hasattr(self.page.raw_page, "keyboard"):
                        await self.page.raw_page.keyboard.press("Enter")
                except Exception as key_err:
                    logger.error(f"Keyboard Enter fallback failed: {key_err}")
                    raise SearchError(f"Failed to submit search: {key_err}") from key_err

            # 3. Wait for navigation/results state
            try:
                if hasattr(self.page.raw_page, "wait_for_load_state"):
                    await self.page.raw_page.wait_for_load_state("domcontentloaded")
            except Exception as load_err:
                logger.debug(f"Search navigation wait notice: {load_err}")

            # 4. Extract links from target container or page
            raw_links = await self.page.extract_links(results_container_selector)

            # 5. Deterministic deduplication by URL preserving order
            seen_urls = set()
            deduped_results: List[ExtractionRecord] = []
            position = 1

            for link in raw_links:
                url_key = link.href or link.url or link.get("url")
                if not url_key or url_key in seen_urls:
                    continue
                seen_urls.add(url_key)

                # Attach search provenance metadata
                link.metadata["search_query"] = query_clean
                link.metadata["search_position"] = position
                position += 1
                deduped_results.append(link)

            return deduped_results

        # Execute wrapped with resilience primitives
        return await self.page.circuit_breaker.execute(
            lambda: self.page.retry_policy.execute(_perform_search),
            operation_name=f"search_{query_clean}"
        )
