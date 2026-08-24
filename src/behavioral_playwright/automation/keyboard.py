"""Deterministic KeyboardController for browser keyboard automation."""

from typing import Any


class KeyboardController:
    """Provides deterministic keyboard automation."""

    def __init__(self, page: Any) -> None:
        self.page = page

    async def type(self, text: str, delay_ms: float = 0.0) -> None:
        """Types text using the keyboard device."""
        if hasattr(self.page, "keyboard") and hasattr(self.page.keyboard, "type"):
            await self.page.keyboard.type(text, delay=delay_ms)

    async def fill(self, selector: str, text: str) -> None:
        """Fills input element directly."""
        await self.page.fill(selector, text)

    async def press(self, key: str) -> None:
        """Presses a single key (e.g. 'Enter', 'Escape', 'Tab')."""
        if hasattr(self.page, "keyboard") and hasattr(self.page.keyboard, "press"):
            await self.page.keyboard.press(key)

    async def down(self, key: str) -> None:
        """Holds a key down."""
        if hasattr(self.page, "keyboard") and hasattr(self.page.keyboard, "down"):
            await self.page.keyboard.down(key)

    async def up(self, key: str) -> None:
        """Releases a key up."""
        if hasattr(self.page, "keyboard") and hasattr(self.page.keyboard, "up"):
            await self.page.keyboard.up(key)
