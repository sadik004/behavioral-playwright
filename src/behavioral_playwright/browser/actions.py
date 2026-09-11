"""Humanized browser action namespace.

Delegates to a booted humanizer when it exposes the specialized
``execute_safe_*`` methods, otherwise falls back to raw Playwright page
methods. All stateful actions raise ``ProviderUnavailableError`` before
``bp.boot()`` has installed a humanizer.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Optional

from behavioral_playwright.exceptions import ProviderUnavailableError

logger = logging.getLogger(__name__)

_GUARD_MSG = ("Facade humanizer is not booted. Call bp.boot() first.")


class BrowserActionNamespace:
    """Humanized browser interactions exposed as ``bp.browser``."""

    def __init__(self, bp: Any) -> None:
        self._bp = bp
        self._typing_mu = 0.085
        self._typing_sigma = 0.18

    # -- internal helpers ---------------------------------------------------
    def _humanizer(self) -> Any:
        humanizer = getattr(self._bp, "_humanizer", None)
        if humanizer is None:
            raise ProviderUnavailableError(_GUARD_MSG)
        return humanizer

    def _page(self) -> Any:
        return getattr(self._bp, "_page", None)

    async def _focus_blur(self, selector: str) -> None:
        """Best-effort strict focus/blur cycle (non-blocking on failure)."""
        page = self._page()
        if page is None:
            return
        try:
            await page.evaluate(
                "sel => { if (document.activeElement) document.activeElement.blur(); }",
                selector)
            el = await page.query_selector(selector)
            if el is not None:
                await el.focus()
        except Exception:
            logger.debug("focus/blur cycle failed for %s", selector)

    async def _delegate_or_fallback(self, humanizer_method: str,
                                    page_method: str, *args: Any) -> bool:
        humanizer = self._humanizer()
        await self._focus_blur(args[0] if args else "")
        fn = getattr(humanizer, humanizer_method, None)
        if callable(fn):
            return await fn(*args)
        page = self._page()
        if page is None:
            raise ProviderUnavailableError(_GUARD_MSG)
        await getattr(page, page_method)(*args)
        return True

    def _get_keystroke_hold_delay(self) -> float:
        return max(0.01, random.gauss(self._typing_mu, self._typing_sigma))

    # -- public actions -----------------------------------------------------
    async def hover(self, selector: str) -> bool:
        return await self._delegate_or_fallback(
            "execute_safe_hover", "hover", selector)

    async def drag_and_drop(self, source_selector: str,
                            target_selector: str) -> bool:
        return await self._delegate_or_fallback(
            "execute_safe_drag_and_drop", "drag_and_drop",
            source_selector, target_selector)

    async def check_checkbox(self, selector: str, checked: bool = True) -> bool:
        humanizer = self._humanizer()
        await self._focus_blur(selector)
        fn = getattr(humanizer, "execute_safe_check", None)
        if callable(fn):
            return await fn(selector, checked)
        page = self._page()
        if page is None:
            raise ProviderUnavailableError(_GUARD_MSG)
        if checked:
            await page.check(selector)
        else:
            await page.uncheck(selector)
        return True

    async def select_option(self, selector: str, value: str) -> bool:
        return await self._delegate_or_fallback(
            "execute_safe_select_option", "select_option", selector, value)

    async def keyboard_press(self, selector: str, key: str) -> bool:
        return await self._delegate_or_fallback(
            "execute_safe_keyboard_press", "press", selector, key)

    async def type(self, selector: str, text: str,
                   expected_text: Optional[str] = None) -> bool:
        """Types character-by-character with humanized keystroke rhythm."""
        humanizer = self._humanizer()
        await self._focus_blur(selector)
        fn = getattr(humanizer, "execute_safe_type", None)
        if not callable(fn):
            raise ProviderUnavailableError(
                "Humanizer typing is unavailable in this configuration.")
        for char in text:
            await fn(selector, char, expected_text=None)
            await asyncio.sleep(self._get_keystroke_hold_delay())
        return True

    async def scroll(self, distance_y: float) -> None:
        """Scrolls in 5 inertial steps with optical reading pauses."""
        humanizer = self._humanizer()
        human_scroll = getattr(humanizer, "human_scroll", None)
        if not callable(human_scroll):
            raise ProviderUnavailableError(
                "Humanizer scrolling is unavailable in this configuration.")
        delta = distance_y / 5.0
        for _ in range(5):
            await human_scroll(delta)
            await asyncio.sleep(random.uniform(0.05, 0.15))

    # -- aliases ------------------------------------------------------------
    async def check(self, selector: str) -> bool:
        return await self.check_checkbox(selector, True)

    async def uncheck(self, selector: str) -> bool:
        return await self.check_checkbox(selector, False)

    async def press(self, selector: str, key: str) -> bool:
        return await self.keyboard_press(selector, key)

    async def fill(self, selector: str, value: str,
                   expected_text: Optional[str] = None) -> bool:
        return await self.type(selector, value, expected_text)

    async def click(self, selector: str,
                    expected_text: Optional[str] = None) -> bool:
        humanizer = self._humanizer()
        await self._focus_blur(selector)
        fn = getattr(humanizer, "execute_safe_click", None)
        if callable(fn):
            return await fn(selector, expected_text=expected_text)
        page = self._page()
        if page is None:
            raise ProviderUnavailableError(_GUARD_MSG)
        await page.click(selector)
        return True


__all__ = ["BrowserActionNamespace"]
