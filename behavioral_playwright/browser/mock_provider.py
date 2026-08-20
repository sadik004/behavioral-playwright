"""Mock in-memory BrowserProvider for fast, deterministic unit testing."""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from behavioral_playwright.browser.base import BrowserProvider
from behavioral_playwright.config.settings import BrowserConfig
from behavioral_playwright.exceptions import BrowserProviderError, NavigationError


@dataclass
class MockElementHandle:
    """Mock DOM element handle for unit tests."""
    tag: str
    attributes: Dict[str, str] = field(default_factory=dict)
    text: str = ""

    async def inner_text(self) -> str:
        return self.text

    async def get_attribute(self, name: str) -> Optional[str]:
        return self.attributes.get(name)

    async def click(self) -> None:
        pass

    async def fill(self, text: str) -> None:
        self.text = text


class MockPage:
    """Mock Page object representing an in-memory browser tab."""

    def __init__(self, title: str = "Mock Page", url: str = "https://mock.example.com") -> None:
        self._title = title
        self._url = url
        self._html_content = "<html><head><title>Mock Page</title></head><body></body></html>"
        self._elements: List[MockElementHandle] = []
        self._eval_handlers: Dict[str, Any] = {}
        self.clicks_recorded: List[str] = []
        self.types_recorded: List[Dict[str, str]] = []

    def set_content(self, html: str, title: Optional[str] = None, url: Optional[str] = None) -> None:
        self._html_content = html
        if title:
            self._title = title
        if url:
            self._url = url

    def register_eval_result(self, snippet: str, result: Any) -> None:
        self._eval_handlers[snippet] = result

    async def title(self) -> str:
        return self._title

    @property
    def url(self) -> str:
        return self._url

    async def content(self) -> str:
        return self._html_content

    async def goto(self, url: str, wait_until: str = "domcontentloaded", timeout: Optional[int] = None) -> None:
        if "fail" in url.lower():
            raise NavigationError(f"Simulated navigation failure for {url}")
        self._url = url

    async def screenshot(self, path: Optional[str] = None) -> bytes:
        return b"mock_png_bytes"

    async def evaluate(self, script: str, arg: Any = None) -> Any:
        for key, res in self._eval_handlers.items():
            if key in script:
                if callable(res):
                    return res(arg)
                return res
        return None

    async def query_selector(self, selector: str) -> Optional[MockElementHandle]:
        for el in self._elements:
            if selector.startswith("#") and el.attributes.get("id") == selector[1:]:
                return el
            if selector.startswith(".") and selector[1:] in el.attributes.get("class", "").split():
                return el
            if el.tag == selector:
                return el
        return None

    async def query_selector_all(self, selector: str) -> List[MockElementHandle]:
        matches = []
        for el in self._elements:
            if selector.startswith("#") and el.attributes.get("id") == selector[1:]:
                matches.append(el)
            elif selector.startswith(".") and selector[1:] in el.attributes.get("class", "").split():
                matches.append(el)
            elif el.tag == selector or selector == "*":
                matches.append(el)
        return matches

    async def click(self, selector: str) -> None:
        self.clicks_recorded.append(selector)

    async def fill(self, selector: str, text: str) -> None:
        self.types_recorded.append({"selector": selector, "text": text})

    async def close(self) -> None:
        pass


class MockBrowserProvider(BrowserProvider):
    """In-memory Mock BrowserProvider for testing without launching Chromium."""

    def __init__(self, config: Optional[BrowserConfig] = None) -> None:
        self.config = config or BrowserConfig()
        self.is_launched: bool = False
        self.active_page = MockPage()
        self.pages: List[MockPage] = []

    async def launch(self, config: Optional[BrowserConfig] = None) -> None:
        if config:
            self.config = config
        self.is_launched = True
        self.pages = [self.active_page]

    async def close(self) -> None:
        self.is_launched = False
        self.pages = []

    async def new_page(self) -> MockPage:
        if not self.is_launched:
            raise BrowserProviderError("Mock provider is not launched.")
        page = MockPage()
        self.pages.append(page)
        self.active_page = page
        return page

    async def goto(self, url: str, wait_until: str = "domcontentloaded", timeout_ms: Optional[int] = None) -> None:
        if not self.is_launched:
            raise BrowserProviderError("Mock provider is not launched.")
        await self.active_page.goto(url, wait_until=wait_until, timeout=timeout_ms)

    async def screenshot(self, path: Optional[str] = None) -> bytes:
        return await self.active_page.screenshot(path=path)

    async def get_title(self) -> str:
        return await self.active_page.title()

    async def get_url(self) -> str:
        return self.active_page.url

    async def evaluate(self, script: str, arg: Any = None) -> Any:
        return await self.active_page.evaluate(script, arg)

    async def query_selector(self, selector: str) -> Optional[Any]:
        return await self.active_page.query_selector(selector)

    async def query_selector_all(self, selector: str) -> List[Any]:
        return await self.active_page.query_selector_all(selector)

    async def click(self, selector: str) -> None:
        await self.active_page.click(selector)

    async def type(self, selector: str, text: str) -> None:
        await self.active_page.fill(selector, text)

    async def close_page(self, page: Any) -> None:
        if page in self.pages:
            self.pages.remove(page)
        if self.active_page == page:
            self.active_page = self.pages[0] if self.pages else MockPage()
