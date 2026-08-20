"""High-level PageSession and BrowserSession abstractions."""

import asyncio
from types import TracebackType
from typing import Any, List, Optional, Type

from behavioral_playwright.automation.keyboard import KeyboardController
from behavioral_playwright.automation.mouse import MouseController
from behavioral_playwright.automation.scroll import ScrollController
from behavioral_playwright.browser.base import BrowserProvider
from behavioral_playwright.browser.playwright_provider import PlaywrightProvider
from behavioral_playwright.config.settings import AutomationConfig, BrowserConfig
from behavioral_playwright.extraction.dom import DOMExtractor
from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.results import ExtractionRecord, ResolutionResult
from behavioral_playwright.resilience.circuit_breaker import CircuitBreaker
from behavioral_playwright.resilience.retry import RetryPolicy
from behavioral_playwright.resilience.state import StateTracker
from behavioral_playwright.selectors.resolver import SelfHealingResolver

logger = get_logger("page.session")


class PageSession:
    """
    High-level facade over an active browser page.
    Binds SelfHealingResolver, automation controllers, resilience, and extraction.
    """

    def __init__(
        self,
        raw_page: Any,
        provider: BrowserProvider,
        config: AutomationConfig
    ) -> None:
        self.raw_page = raw_page
        self.provider = provider
        self.config = config

        # Automation Controllers
        self.mouse = MouseController(raw_page)
        self.keyboard = KeyboardController(raw_page)
        self.scroll = ScrollController(raw_page)

        # Extraction & Resolution
        self.resolver = SelfHealingResolver(config.resolver)
        self.extractor = DOMExtractor()

        # Resilience Primitives
        self.state_tracker = StateTracker()
        self.retry_policy = RetryPolicy(config.retry)
        self.circuit_breaker = CircuitBreaker(config.circuit_breaker)

    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """Navigates to URL and records the page state in StateTracker."""
        await self.provider.goto(url, wait_until=wait_until)
        title = await self.provider.get_title()
        self.state_tracker.record_state(url=url, title=title)

    async def get_title(self) -> str:
        """Returns active page title."""
        return await self.provider.get_title()

    async def get_url(self) -> str:
        """Returns active page URL."""
        return await self.provider.get_url()

    async def evaluate(self, script: str, arg: Any = None) -> Any:
        """Evaluates JavaScript expression."""
        return await self.provider.evaluate(script, arg)

    async def screenshot(self, path: Optional[str] = None) -> bytes:
        """Captures page screenshot."""
        return await self.provider.screenshot(path=path)

    async def resolve(self, target: str) -> ResolutionResult:
        """Resolves target element using SelfHealingResolver cascade."""
        return await self.resolver.resolve(self.raw_page, target)

    async def click_healed(self, target: str) -> ResolutionResult:
        """Resolves and clicks on target element using self-healing."""
        return await self.resolver.resolve_and_click(self.raw_page, target)

    async def type_healed(self, target: str, text: str) -> ResolutionResult:
        """Resolves and fills text into target element using self-healing."""
        return await self.resolver.resolve_and_type(self.raw_page, target, text)

    async def extract_links(self, container_selector: Optional[str] = None) -> List[ExtractionRecord]:
        """Extracts structured hyperlinks from page."""
        return await self.extractor.extract_links(self.raw_page, container_selector)

    async def extract_articles(self, container_selector: Optional[str] = None) -> List[ExtractionRecord]:
        """Extracts structured article blocks from page."""
        return await self.extractor.extract_articles(self.raw_page, container_selector)

    async def close(self) -> None:
        """Closes this page."""
        await self.provider.close_page(self.raw_page)


class BrowserSession:
    """
    High-level async context manager managing browser lifecycle.
    Example:
        async with BrowserSession() as session:
            page = await session.new_page()
            await page.goto("https://example.com")
    """

    def __init__(
        self,
        config: Optional[AutomationConfig] = None,
        provider: Optional[BrowserProvider] = None
    ) -> None:
        self.config = config or AutomationConfig()
        self.provider = provider or PlaywrightProvider(self.config.browser)
        self._is_active: bool = False

    async def __aenter__(self) -> "BrowserSession":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        await self.close()

    async def start(self) -> None:
        """Launches the underlying browser backend."""
        logger.info("[Session] Starting BrowserSession lifecycle...")
        await self.provider.launch(self.config.browser)
        self._is_active = True

    async def new_page(self) -> PageSession:
        """Spawns a new PageSession wrapped with self-healing and automation facade."""
        raw_page = await self.provider.new_page()
        return PageSession(
            raw_page=raw_page,
            provider=self.provider,
            config=self.config
        )

    async def close(self) -> None:
        """Terminates the browser session and releases all resources."""
        if self._is_active:
            logger.info("[Session] Closing BrowserSession...")
            await self.provider.close()
            self._is_active = False
