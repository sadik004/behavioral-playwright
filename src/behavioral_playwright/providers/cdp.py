"""
Remote Chrome DevTools Protocol (CDP) Debugger Bridge provider.
"""

import asyncio
import logging
from typing import Any, Optional, Tuple, cast

from ..config.root import AutomationConfig
from ..exceptions import BrowserLaunchError
from ..utils.protocols import BrowserContextProtocol, BrowserProtocol

logger = logging.getLogger("BehavioralAutomation.Providers.CDP")


class CDPBrowserProvider:
    """Orchestrates remote debugging connection over CDP."""

    def __init__(self, config: AutomationConfig) -> None:
        self.cfg = config
        self.playwright_manager: Optional[Any] = None
        self.browser: Optional[BrowserProtocol] = None
        self.context: Optional[BrowserContextProtocol] = None

    async def launch_context(self) -> Tuple[BrowserContextProtocol, Optional[BrowserProtocol]]:
        logger.info(f"Connecting over CDP Debugger Bridge at: {self.cfg.browser.remote_cdp_url}...")
        try:
            from playwright.async_api import async_playwright
        except ImportError as ie:
            raise BrowserLaunchError("Playwright framework is not installed in current workspace.") from ie

        if not self.cfg.browser.remote_cdp_url:
            raise BrowserLaunchError("Remote CDP URL is not configured.")

        try:
            self.playwright_manager = await async_playwright().start()
            self.browser = await self.playwright_manager.chromium.connect_over_cdp(self.cfg.browser.remote_cdp_url)
            if not self.browser:
                raise BrowserLaunchError("Failed to connect over CDP.")
            contexts = getattr(self.browser, "contexts", [])
            self.context = cast(
                BrowserContextProtocol,
                contexts[0] if contexts else await self.browser.new_context(),
            )
            if not self.context:
                raise BrowserLaunchError("Failed to initialize CDP browser context.")
            return self.context, self.browser
        except Exception as ex:
            await self.shutdown()
            raise BrowserLaunchError(f"CDP remote-debugger handshake failed: {ex}") from ex

    async def shutdown(self) -> None:
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            finally:
                self.browser = None

        if self.playwright_manager:
            try:
                await self.playwright_manager.stop()
            except Exception:
                pass
            finally:
                self.playwright_manager = None

        await asyncio.sleep(0.05)
