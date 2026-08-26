"""Shared test doubles and helpers for the behavioral-evasion framework suite."""
import asyncio
import re
from typing import Any, Dict, List, Optional

_RAISE = object()


def run(coro):
    """Run a coroutine on a fresh event loop (no pytest-asyncio dependency)."""
    return asyncio.run(coro)


class FakeElement:
    def __init__(
        self,
        *,
        id: str = "",
        cls: str = "",
        text: str = "",
        aria_label: str = "",
        title: str = "",
        tag: str = "button",
        box: Optional[Dict[str, float]] = None,
    ) -> None:
        self._attrs = {"id": id, "class": cls, "aria-label": aria_label, "title": title}
        self._text = text
        self._tag = tag
        self._box = box

    async def get_attribute(self, name: str):
        return self._attrs.get(name)

    async def inner_text(self) -> str:
        return self._text

    async def bounding_box(self):
        return self._box

    async def evaluate(self, js: str) -> str:
        return self._tag.upper()


class FakeMouse:
    def __init__(self, page: "FakePage") -> None:
        self.page = page

    async def move(self, x: float, y: float) -> None:
        self.page.mouse_moves.append((x, y))

    async def down(self) -> None:
        self.page.down_up += 1

    async def up(self) -> None:
        self.page.down_up += 1


class FakePage:
    """Records every script/click; wait_for_selector is driven by a mapping.

    ``wait_results`` maps selector -> element to return, or the module-level
    _RAISE sentinel to force a timeout-style failure. Unmapped selectors raise.
    """

    def __init__(
        self,
        *,
        elements: Optional[List[FakeElement]] = None,
        wait_results: Optional[Dict[str, Any]] = None,
        evaluate_return: Any = None,
    ) -> None:
        self.elements = elements or []
        self.wait_results = dict(wait_results or {})
        self.evaluate_return = evaluate_return
        self.scripts: List[str] = []
        self.scroll_by: List[int] = []
        self.mouse_moves: List[tuple] = []
        self.clicks: List[str] = []
        self.down_up = 0
        self.closed = False
        self.mouse = FakeMouse(self)

    async def wait_for_selector(self, selector: str, timeout: Optional[int] = None):
        if selector in self.wait_results:
            el = self.wait_results[selector]
            if el is _RAISE:
                raise TimeoutError(f"simulated timeout for {selector!r}")
            return el
        raise TimeoutError(f"no wait mapping configured for {selector!r}")

    async def query_selector_all(self, selector: str) -> List[FakeElement]:
        return list(self.elements)

    async def evaluate(self, script: str):
        self.scripts.append(script)
        match = re.search(r"window\.scrollBy\(0,\s*(-?\d+)\)", script)
        if match:
            self.scroll_by.append(int(match.group(1)))
        if isinstance(self.evaluate_return, Exception):
            raise self.evaluate_return
        return self.evaluate_return

    async def click(self, selector: str) -> None:
        self.clicks.append(selector)

    async def close(self) -> None:
        self.closed = True


RAISE = _RAISE


class FakeContext:
    def __init__(self, storage_state: Optional[Dict[str, Any]] = None,
                 storage_error: Optional[Exception] = None) -> None:
        self.pages: List[FakePage] = []
        self.init_scripts: List[str] = []
        self.geolocation = None
        self.permissions = None
        self.closed = False
        self._storage_state = storage_state
        self._storage_error = storage_error

    async def new_page(self) -> FakePage:
        page = FakePage()
        self.pages.append(page)
        return page

    async def set_geolocation(self, geo: Dict[str, float]) -> None:
        self.geolocation = geo

    async def grant_permissions(self, permissions) -> None:
        self.permissions = list(permissions)

    async def add_init_script(self, script: str) -> None:
        self.init_scripts.append(script)

    async def storage_state(self) -> Dict[str, Any]:
        if self._storage_error is not None:
            raise self._storage_error
        if self._storage_state is None:
            raise RuntimeError("storage_state not supported by this context")
        return self._storage_state

    async def close(self) -> None:
        self.closed = True


class FakeBrowser:
    """Hands out a FRESH FakeContext per new_context() call, like Playwright."""

    def __init__(self) -> None:
        self.created_contexts = []
        self.context_kwargs = []
        self._pending_error = None

    def fail_next_new_context(self, exc: Exception) -> None:
        self._pending_error = exc

    async def new_context(self, **kwargs) -> FakeContext:
        if self._pending_error is not None:
            err, self._pending_error = self._pending_error, None
            raise err
        ctx = FakeContext()
        self.context_kwargs.append(kwargs)
        self.created_contexts.append(ctx)
        return ctx


from pydantic import BaseModel


class PermissiveSchema(BaseModel):
    """Accepts anything; used for pipeline happy paths."""
    model_config = {"extra": "allow"}


class StrictIdSchema(BaseModel):
    """Fails validation unless 'id' is an int."""
    id: int
