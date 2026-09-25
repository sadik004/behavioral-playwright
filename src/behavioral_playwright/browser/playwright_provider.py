"""Playwright implementation of BrowserProvider."""

import os
import shutil
import tempfile
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, List, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from behavioral_playwright.browser.base import BrowserProvider
from behavioral_playwright.config.settings import BrowserConfig
from behavioral_playwright.exceptions import BrowserProviderError, NavigationError
from behavioral_playwright.logging import get_logger

logger = get_logger("browser.playwright")


class PlaywrightProvider(BrowserProvider):
    """Production Playwright concrete provider."""

    def __init__(self, config: Optional[BrowserConfig] = None) -> None:
        self.config = config or BrowserConfig()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._current_page: Optional[Page] = None
        self._temp_dir: Optional[str] = None

    async def launch(self, config: Optional[BrowserConfig] = None) -> None:
        if config:
            self.config = config

        try:
            self._playwright = await async_playwright().start()

            user_data_dir = self.config.user_data_dir
            if not user_data_dir:
                self._temp_dir = os.path.join(
                    tempfile.gettempdir(),
                    f"bpw_profile_{int(time.time() * 1000)}"
                )
                os.makedirs(self._temp_dir, exist_ok=True)
                user_data_dir = self._temp_dir

            args = list(self.config.args)
            if "--start-maximized" not in args:
                args.extend([
                    f"--window-size={self.config.width},{self.config.height}",
                    "--no-first-run",
                    "--no-default-browser-check",
                ])

            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=self.config.headless,
                no_viewport=True if self.config.headless is False else False,
                viewport={"width": self.config.width, "height": self.config.height} if self.config.headless else None,
                args=args,
                slow_mo=self.config.slow_mo,
            )

            pages = self._context.pages
            self._current_page = pages[0] if pages else await self._context.new_page()

            # Attach route interception to abort heavy assets and trackers by default
            await self._setup_route_interception(self._context, allow_media=self.config.allow_media)

            logger.info("[Provider] Playwright browser context launched successfully.")
        except Exception as e:
            logger.error(f"[Provider] Failed to launch Playwright browser: {e}")
            raise BrowserProviderError(f"Playwright launch failed: {e}") from e

    @staticmethod
    async def _setup_route_interception(context: BrowserContext, allow_media: bool = False) -> None:
        """Aborts images, fonts, and trackers by default to preserve bandwidth and heap memory."""
        from urllib.parse import urlparse
        from behavioral_playwright.browser.pool import IMAGE_FONT_EXTENSIONS, TRACKING_DOMAINS

        async def _handle_route(route: Any) -> None:
            req_url = route.request.url.lower()
            parsed = urlparse(req_url)
            path = parsed.path

            if any(tracker in parsed.netloc for tracker in TRACKING_DOMAINS):
                await route.abort()
                return

            if not allow_media:
                if any(path.endswith(ext) for ext in IMAGE_FONT_EXTENSIONS):
                    await route.abort()
                    return
                if route.request.resource_type in ("image", "font", "media"):
                    await route.abort()
                    return

            try:
                await route.continue_()
            except Exception:
                pass

        await context.route("**/*", _handle_route)

    async def close(self) -> None:
        try:
            if self._context:
                await self._context.close()
            if self._playwright:
                await self._playwright.stop()
            if self._temp_dir and os.path.exists(self._temp_dir):
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            logger.info("[Provider] Playwright browser context closed.")
        except Exception as e:
            logger.warning(f"[Provider] Error during Playwright shutdown: {e}")
        finally:
            self._context = None
            self._playwright = None
            self._current_page = None

    async def new_page(self) -> Page:
        if not self._context:
            raise BrowserProviderError("Browser context is not initialized. Call launch() first.")
        self._current_page = await self._context.new_page()
        return self._current_page

    @property
    def page(self) -> Page:
        if not self._current_page:
            raise BrowserProviderError("No active page available. Call launch() or new_page().")
        return self._current_page

    async def goto(self, url: str, wait_until: str = "domcontentloaded", timeout_ms: Optional[int] = None) -> None:
        to = timeout_ms if timeout_ms is not None else self.config.timeout_ms
        try:
            await self.page.goto(url, wait_until=wait_until, timeout=to)
        except Exception as e:
            raise NavigationError(f"Failed to navigate to '{url}': {e}") from e

    async def screenshot(self, path: Optional[str] = None) -> bytes:
        return await self.page.screenshot(path=path)

    async def get_title(self) -> str:
        return await self.page.title()

    async def get_url(self) -> str:
        return self.page.url

    async def evaluate(self, script: str, arg: Any = None) -> Any:
        return await self.page.evaluate(script, arg)

    async def query_selector(self, selector: str) -> Optional[Any]:
        return await self.page.query_selector(selector)

    async def query_selector_all(self, selector: str) -> List[Any]:
        return await self.page.query_selector_all(selector)

    async def click(self, selector: str) -> None:
        await self.page.click(selector)

    async def type(self, selector: str, text: str) -> None:
        await self.page.fill(selector, text)

    async def close_page(self, page: Any) -> None:
        await page.close()
        if self._current_page == page:
            pages = self._context.pages if self._context else []
            self._current_page = pages[0] if pages else None

    @asynccontextmanager
    async def ephemeral_context(
        self,
        allow_media: Optional[bool] = None,
        **context_kwargs: Any,
    ) -> AsyncGenerator[BrowserContext, None]:
        """
        Dispenses an ephemeral, lightweight BrowserContext with route-level asset abortion.
        Ensures context is closed on exit while preserving the master process.
        """
        if not self._context:
            await self.launch()
        assert self._context is not None

        media_allowed = self.config.allow_media if allow_media is None else allow_media

        if self._browser and self._browser.is_connected():
            ctx = await self._browser.new_context(**context_kwargs)
            await self._setup_route_interception(ctx, allow_media=media_allowed)
            try:
                yield ctx
            finally:
                await ctx.close()
        else:
            # Fallback to persistent context with configured route abortion
            yield self._context

    @asynccontextmanager
    async def ephemeral_page(
        self,
        allow_media: Optional[bool] = None,
        **context_kwargs: Any,
    ) -> AsyncGenerator[Page, None]:
        """Dispenses an ephemeral Page with guaranteed cleanup on exit."""
        async with self.ephemeral_context(allow_media=allow_media, **context_kwargs) as ctx:
            page = await ctx.new_page()
            try:
                yield page
            finally:
                if not page.is_closed():
                    try:
                        await page.close()
                    except Exception:
                        pass

