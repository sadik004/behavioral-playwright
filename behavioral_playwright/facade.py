"""
Unified Public API Facade (BP Class) for the Behavioral Playwright Framework.
Provides a thin, elegant interface over the 10.1.0a1 architecture.
"""

from typing import Any, List, Optional, Dict
from behavioral_playwright.config.settings import AutomationConfig
from behavioral_playwright.page.session import BrowserSession, PageSession
from behavioral_playwright.models.results import ExtractionRecord


class BP:
    """
    Unified high-level facade orchestrating the Behavioral Playwright framework.
    Provides a simplified public API while maintaining structural integrity.
    """

    def __init__(self, config: Optional[AutomationConfig] = None) -> None:
        self.config = config or AutomationConfig()
        self.session: Optional[BrowserSession] = None
        self.page: Optional[PageSession] = None

    async def boot(self) -> "BP":
        """Starts the browser session and initializes the first page."""
        if not self.session:
            self.session = BrowserSession(config=self.config)
            await self.session.start()
        
        if not self.page:
            self.page = await self.session.new_page()
            
        return self

    async def open(self, url: str) -> None:
        """Navigates to the specified URL."""
        if not self.page:
            await self.boot()
        await self.page.goto(url)

    async def goto(self, url: str) -> None:
        """Alias for open()."""
        await self.open(url)

    async def click(self, selector: str) -> Any:
        """Executes a self-healing click on the target selector."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        return await self.page.click_healed(selector)

    async def type(self, selector: str, text: str) -> Any:
        """Executes a self-healing type into the target selector."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        return await self.page.type_healed(selector, text)

    async def fill(self, selector: str, text: str) -> Any:
        """Alias for type()."""
        return await self.type(selector, text)

    async def scroll(self, distance_y: float = 500) -> None:
        """Scrolls the page down by the specified distance."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        await self.page.scroll.down(distance=int(distance_y))

    async def screenshot(self, path: Optional[str] = None) -> bytes:
        """Captures a screenshot of the current page."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        return await self.page.screenshot(path=path)

    async def extract(self, target: str = "links", container_selector: Optional[str] = None) -> List[ExtractionRecord]:
        """Extracts structured data from the DOM."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        
        if target == "links":
            return await self.page.extract_links(container_selector)
        elif target == "articles":
            return await self.page.extract_articles(container_selector)
        else:
            raise ValueError(f"Extraction target '{target}' is not supported by DOMExtractor.")

    async def crawl(self, start_url: str, max_pages: int = 5) -> List[ExtractionRecord]:
        """Crawls starting from a URL and extracts data."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        from behavioral_playwright.crawling.crawler import Crawler
        crawler = Crawler(self.page)
        return await crawler.crawl(start_url, max_pages)

    async def search(self, query: str, search_input_selector: str = "input[type='search'], input[name='q']", submit_selector: str = "button[type='submit']") -> List[ExtractionRecord]:
        """Submits a search query and extracts the results."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        from behavioral_playwright.search.engine import SearchEngine
        engine = SearchEngine(self.page)
        return await engine.search(query, search_input_selector, submit_selector)

    async def map(self, url: str) -> Dict[str, Any]:
        """Maps out the structural links and articles of a page."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        from behavioral_playwright.mapping.mapper import SiteMapper
        mapper = SiteMapper(self.page)
        return await mapper.map(url)

    async def handoff(self, context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Exports or injects the current context state for handoff."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        from behavioral_playwright.handoff.session_handoff import SessionHandoff
        handoff_manager = SessionHandoff(self.page)
        return await handoff_manager.handoff(context_data)

    async def verify(self, 
                     state_before: Optional[Dict[str, Any]] = None, 
                     expected_title: Optional[str] = None,
                     expected_url: Optional[str] = None,
                     expected_element_selector: Optional[str] = None,
                     expected_text: Optional[str] = None) -> Dict[str, Any]:
        """Validates the current DOM/page state against expectations."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        from behavioral_playwright.verification.verifier import StateVerifier
        verifier = StateVerifier(self.page)
        return await verifier.verify(state_before, expected_title, expected_url, expected_element_selector, expected_text)

    async def close(self) -> None:
        """Gracefully closes the page and browser session."""
        if self.page:
            await self.page.close()
            self.page = None
        if self.session:
            await self.session.close()
            self.session = None

    async def __aenter__(self) -> "BP":
        await self.boot()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
