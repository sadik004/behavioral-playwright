"""
Linguistic & Biometric KeyboardController for Browser Keyboard Automation.
Integrated with Euclidean QWERTY Keyboard Distances and Weibull Latency Distributions.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional


class KeyboardController:
    """
    Provides human-mimetic keyboard automation with realistic keystroke cadences.
    """

    def __init__(self, page: Any, keystrokes: Optional[Any] = None) -> None:
        self.page = page
        self._keystrokes = keystrokes

    @property
    def keystrokes(self) -> Any:
        if self._keystrokes is None:
            from behavioral_playwright.powerplay.keystrokes import LinguisticKeystrokeDynamicsEngine
            self._keystrokes = LinguisticKeystrokeDynamicsEngine()
        return self._keystrokes

    async def type(
        self,
        text: str,
        delay_ms: float = 0.0,
        humanize: bool = True
    ) -> None:
        """
        Types text using the keyboard device.
        When humanize=True, generates authentic keystroke sequences modulated by
        QWERTY layout distances and Weibull flight times.
        """
        if humanize and hasattr(self.page, "keyboard") and hasattr(self.page.keyboard, "down"):
            sequence = self.keystrokes.generate_typing_sequence(text)
            for ev in sequence:
                key = ev.get("key", "")
                ev_type = ev.get("event")
                # Clamp latency between 5ms and 60ms to prevent bot detection and keep test execution fast
                delta_sec = min(0.06, max(0.005, float(ev.get("delta_ms", 25.0)) / 1000.0))

                if ev_type == "keydown":
                    await self.down(key)
                elif ev_type == "keyup":
                    await self.up(key)

                await asyncio.sleep(delta_sec)
        else:
            if hasattr(self.page, "keyboard") and hasattr(self.page.keyboard, "type"):
                await self.page.keyboard.type(text, delay=delay_ms)
            elif hasattr(self.page, "fill"):
                await self.page.fill("input", text)

    async def fill(self, selector: str, text: str) -> None:
        """Fills input element directly."""
        if hasattr(self.page, "fill"):
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
