"""Deterministic MouseController for browser input automation."""

from typing import Any, Optional


class MouseController:
    """Provides deterministic mouse automation."""

    def __init__(self, page: Any) -> None:
        self.page = page

    async def move(self, x: float, y: float) -> None:
        """Moves mouse cursor to coordinate (x, y)."""
        if hasattr(self.page, "mouse") and hasattr(self.page.mouse, "move"):
            await self.page.mouse.move(x, y)

    async def click(self, selector_or_x: Any, y: Optional[float] = None) -> None:
        """Clicks on a CSS selector or at coordinates (x, y)."""
        if y is not None:
            if hasattr(self.page, "mouse") and hasattr(self.page.mouse, "click"):
                await self.page.mouse.click(float(selector_or_x), y)
        else:
            await self.page.click(str(selector_or_x))

    async def double_click(self, selector: str) -> None:
        """Double clicks on the specified element."""
        if hasattr(self.page, "dblclick"):
            await self.page.dblclick(selector)
        else:
            await self.page.click(selector)
            await self.page.click(selector)

    async def down(self) -> None:
        """Presses mouse button down."""
        if hasattr(self.page, "mouse") and hasattr(self.page.mouse, "down"):
            await self.page.mouse.down()

    async def up(self) -> None:
        """Releases mouse button up."""
        if hasattr(self.page, "mouse") and hasattr(self.page.mouse, "up"):
            await self.page.mouse.up()
