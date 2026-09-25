"""
Single-Browser Multi-Context Pooling & Resource Management Engine.
Enforces process pooling, ephemeral contexts, and route-level asset abortion.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional
from urllib.parse import urlparse

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Route,
    async_playwright,
)

from behavioral_playwright.config.settings import BrowserConfig
from behavioral_playwright.exceptions import BrowserProviderError
from behavioral_playwright.logging import get_logger

logger = get_logger("browser.pool")

# Asset & tracking patterns blocked to preserve bandwidth and heap memory
IMAGE_FONT_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg",
    ".woff", ".woff2", ".ttf", ".otf", ".eot"
)

TRACKING_DOMAINS = (
    "google-analytics.com",
    "googletagmanager.com",
    "connect.facebook.net",
    "hotjar.com",
    "doubleclick.net",
    "scorecardresearch.com",
    "quantserve.com",
    "criteo.net",
    "adnxs.com",
)


class BrowserPoolManager:
    """
    Centralized Single-Browser Multi-Context Pooling Engine.
    Launches one shared Chromium process and dispenses ephemeral, isolated contexts.
    """

    def __init__(
        self,
        config: Optional[BrowserConfig] = None,
        max_concurrent_pages: int = 8,
    ) -> None:
        self.config = config or BrowserConfig()
        self.max_concurrency = max_concurrent_pages
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._active_contexts: int = 0
        self._initialized: bool = False
        self._lock = asyncio.Lock()

    @property
    def is_initialized(self) -> bool:
        return self._initialized and self._browser is not None and self._browser.is_connected()

    @property
    def active_contexts(self) -> int:
        return self._active_contexts

    async def initialize(self) -> None:
        """Initializes the long-running master browser process once."""
        async with self._lock:
            if self.is_initialized:
                return

            try:
                self._semaphore = asyncio.Semaphore(self.max_concurrency)
                self._playwright = await async_playwright().start()

                args = list(self.config.args)
                default_args = [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    f"--window-size={self.config.width},{self.config.height}",
                    "--no-first-run",
                    "--no-default-browser-check",
                ]
                for arg in default_args:
                    if arg not in args:
                        args.append(arg)

                browser_type = getattr(self._playwright, self.config.browser_type, self._playwright.chromium)
                self._browser = await browser_type.launch(
                    headless=self.config.headless,
                    args=args,
                    slow_mo=self.config.slow_mo,
                )
                self._initialized = True
                logger.info("[BrowserPoolManager] Master browser process initialized successfully.")
            except Exception as exc:
                logger.error(f"[BrowserPoolManager] Failed to initialize master browser: {exc}")
                await self.shutdown()
                raise BrowserProviderError(f"BrowserPool initialization failed: {exc}") from exc

    async def _setup_route_interception(self, context: BrowserContext, allow_media: bool) -> None:
        """Attaches route-level resource abortion to preserve bandwidth and heap memory."""
        async def _handle_route(route: Route) -> None:
            req_url = route.request.url.lower()
            parsed = urlparse(req_url)
            path = parsed.path

            # 1. Block tracking beacons & ad analytics unconditionally
            if any(tracker in parsed.netloc for tracker in TRACKING_DOMAINS):
                await route.abort()
                return

            # 2. Block heavy media and font formats unless allow_media is True
            if not allow_media:
                if any(path.endswith(ext) for ext in IMAGE_FONT_EXTENSIONS):
                    await route.abort()
                    return
                # Check resource type header if available
                res_type = route.request.resource_type
                if res_type in ("image", "font", "media"):
                    await route.abort()
                    return

            try:
                await route.continue_()
            except Exception:
                pass

        await context.route("**/*", _handle_route)

    @asynccontextmanager
    async def get_context(
        self,
        allow_media: Optional[bool] = None,
        viewport: Optional[Dict[str, int]] = None,
        extra_http_headers: Optional[Dict[str, str]] = None,
        **context_kwargs: Any,
    ) -> AsyncGenerator[BrowserContext, None]:
        """
        Dispenses a lightweight ephemeral BrowserContext taking <10ms and <10MB RAM.
        Guarantees deterministic teardown in finally: while keeping master browser warm.
        """
        if not self.is_initialized:
            await self.initialize()

        if not self._browser or not self._semaphore:
            raise BrowserProviderError("Browser pool is not initialized.")

        await self._semaphore.acquire()
        context: Optional[BrowserContext] = None
        media_allowed = self.config.allow_media if allow_media is None else allow_media

        try:
            vp = viewport or {"width": self.config.width, "height": self.config.height}
            context = await self._browser.new_context(
                viewport=vp,
                extra_http_headers=extra_http_headers,
                **context_kwargs,
            )
            self._active_contexts += 1

            # Attach route interception to context
            await self._setup_route_interception(context, allow_media=media_allowed)

            yield context
        finally:
            if context:
                try:
                    await context.close()
                except Exception as exc:
                    logger.debug(f"[BrowserPoolManager] Non-fatal error closing ephemeral context: {exc}")
                self._active_contexts = max(0, self._active_contexts - 1)
            self._semaphore.release()

    @asynccontextmanager
    async def get_page(
        self,
        allow_media: Optional[bool] = None,
        **context_kwargs: Any,
    ) -> AsyncGenerator[Page, None]:
        """
        Dispenses an ephemeral Page within a managed ephemeral context.
        Guarantees complete page and context teardown on exit.
        """
        async with self.get_context(allow_media=allow_media, **context_kwargs) as ctx:
            page = await ctx.new_page()
            try:
                yield page
            finally:
                if not page.is_closed():
                    try:
                        await page.close()
                    except Exception:
                        pass

    async def shutdown(self) -> None:
        """Gracefully terminates master browser and Playwright process."""
        async with self._lock:
            try:
                if self._browser:
                    await self._browser.close()
                if self._playwright:
                    await self._playwright.stop()
                logger.info("[BrowserPoolManager] Browser pool shut down cleanly.")
            except Exception as exc:
                logger.warning(f"[BrowserPoolManager] Error during pool shutdown: {exc}")
            finally:
                self._browser = None
                self._playwright = None
                self._initialized = False
                self._active_contexts = 0

    async def __aenter__(self) -> "BrowserPoolManager":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.shutdown()


__all__ = ["BrowserPoolManager", "IMAGE_FONT_EXTENSIONS", "TRACKING_DOMAINS"]
