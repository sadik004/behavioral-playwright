"""Abstract base class and protocols for Browser Providers."""

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from behavioral_playwright.config.settings import BrowserConfig


class BrowserProvider(ABC):
    """
    Pluggable abstraction layer for browser automation backends.
    Allows testing with mocks and future expansion without altering application logic.
    """

    @abstractmethod
    async def launch(self, config: Optional[BrowserConfig] = None) -> None:
        """Launches the underlying browser context."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Closes all pages and terminates the browser backend."""
        pass

    @abstractmethod
    async def new_page(self) -> Any:
        """Creates and returns a new page instance."""
        pass

    @abstractmethod
    async def goto(self, url: str, wait_until: str = "domcontentloaded", timeout_ms: Optional[int] = None) -> None:
        """Navigates the active page to the given URL."""
        pass

    @abstractmethod
    async def screenshot(self, path: Optional[str] = None) -> bytes:
        """Captures a screenshot of the active page."""
        pass

    @abstractmethod
    async def get_title(self) -> str:
        """Returns the current page title."""
        pass

    @abstractmethod
    async def get_url(self) -> str:
        """Returns the current page URL."""
        pass

    @abstractmethod
    async def evaluate(self, script: str, arg: Any = None) -> Any:
        """Evaluates a JavaScript expression in the page context."""
        pass

    @abstractmethod
    async def query_selector(self, selector: str) -> Optional[Any]:
        """Finds the first element matching selector, or None."""
        pass

    @abstractmethod
    async def query_selector_all(self, selector: str) -> List[Any]:
        """Finds all elements matching selector."""
        pass

    @abstractmethod
    async def click(self, selector: str) -> None:
        """Clicks on the element matching selector."""
        pass

    @abstractmethod
    async def type(self, selector: str, text: str) -> None:
        """Types text into the element matching selector."""
        pass

    @abstractmethod
    async def close_page(self, page: Any) -> None:
        """Closes a specific page instance."""
        pass
