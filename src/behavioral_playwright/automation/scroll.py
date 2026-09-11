"""Deterministic ScrollController for page viewport scrolling."""

from typing import Any


class ScrollController:
    """Provides deterministic page scrolling automation."""

    def __init__(self, page: Any) -> None:
        self.page = page

    async def down(self, distance: int = 500, smooth: bool = True) -> None:
        """Scrolls the page down by distance in pixels."""
        behavior = "smooth" if smooth else "auto"
        await self.page.evaluate(f"window.scrollBy({{top: {distance}, behavior: '{behavior}'}})")

    async def up(self, distance: int = 500, smooth: bool = True) -> None:
        """Scrolls the page up by distance in pixels."""
        behavior = "smooth" if smooth else "auto"
        await self.page.evaluate(f"window.scrollBy({{top: -{distance}, behavior: '{behavior}'}})")

    async def to_bottom(self, smooth: bool = True) -> None:
        """Scrolls directly to the bottom of document body."""
        behavior = "smooth" if smooth else "auto"
        await self.page.evaluate(f"window.scrollTo({{top: document.body.scrollHeight, behavior: '{behavior}'}})")

    async def to_top(self, smooth: bool = True) -> None:
        """Scrolls directly to the top of document body."""
        behavior = "smooth" if smooth else "auto"
        await self.page.evaluate(f"window.scrollTo({{top: 0, behavior: '{behavior}'}})")

    async def to_element(self, selector: str) -> None:
        """Scrolls element into view."""
        await self.page.evaluate(f"""
            () => {{
                const el = document.querySelector('{selector}');
                if (el) el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            }}
        """)
