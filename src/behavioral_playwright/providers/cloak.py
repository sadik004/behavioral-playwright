"""
CloakBrowser integration provider.
"""

import asyncio
import logging
from typing import Optional, Tuple

from ..config.root import AutomationConfig
from ..exceptions import BrowserLaunchError
from ..utils.protocols import BrowserContextProtocol, BrowserProtocol

logger = logging.getLogger("BehavioralAutomation.Providers.Cloak")


class CloakBrowserProvider:
    """Orchestrates CloakBrowser C++ source-level integration client."""

    def __init__(self, config: AutomationConfig) -> None:
        self.cfg = config
        self.context: Optional[BrowserContextProtocol] = None

    async def launch_context(self) -> Tuple[BrowserContextProtocol, Optional[BrowserProtocol]]:
        logger.info("Initializing C++ Source-Level CloakBrowser provider...")
        try:
            from cloakbrowser import launch_persistent_context_async
        except ImportError as ie:
            raise BrowserLaunchError("CloakBrowser Python bindings are absent in current workspace.") from ie

        try:
            self.context = await launch_persistent_context_async(
                self.cfg.browser.user_data_dir,
                headless=self.cfg.browser.headless,
                proxy=self.cfg.network.proxy_url,
                license_key=self.cfg.browser.license_key,
                timezone=self.cfg.locale.timezone_id,
                locale=self.cfg.locale.locale,
                geoip=True if self.cfg.network.proxy_url else False,
                user_agent=self.cfg.locale.user_agent,
                viewport={"width": self.cfg.browser.width, "height": self.cfg.browser.height},
                args=[f"--fingerprint-storage-quota={self.cfg.rendering.storage_quota_mb}"]
                if self.cfg.rendering.storage_quota_mb > 0
                else [],
            )
            return self.context, None
        except Exception as ex:
            raise BrowserLaunchError(f"CloakBrowser native C++ launch failed: {ex}") from ex

    async def shutdown(self) -> None:
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            finally:
                self.context = None

        await asyncio.sleep(0.05)
