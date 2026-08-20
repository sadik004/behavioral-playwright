"""
BrowserProviderFactory with cascading fallback launch chain and BrowserLifecycleManager context manager.
"""

import logging
from typing import Any, List, Optional, Tuple

from ..config.root import AutomationConfig
from ..exceptions import ProviderError
from ..utils.protocols import BrowserContextProtocol, BrowserProvider
from .cdp import CDPBrowserProvider
from .cloak import CloakBrowserProvider
from .mock import MockBrowserProvider
from .playwright import PlaywrightProvider

logger = logging.getLogger("BehavioralAutomation.Providers.Factory")


class BrowserProviderFactory:
    """
    Implements a robust Cascading Fallback Launch chain:
    CDPBrowserProvider -> CloakBrowser -> Playwright -> MockBrowserProvider.
    """

    @staticmethod
    def get_provider(config: AutomationConfig) -> BrowserProvider:
        if config.browser.remote_cdp_url:
            return CDPBrowserProvider(config)

        if config.browser.license_key:
            return CloakBrowserProvider(config)

        try:
            import playwright  # noqa: F401

            return PlaywrightProvider(config)
        except ImportError:
            return MockBrowserProvider()

    @classmethod
    async def launch_stabilized_lifecycle(
        cls, config: AutomationConfig
    ) -> Tuple[BrowserContextProtocol, BrowserProvider]:
        """Runs cascade launch chain, catching failures and transitioning smoothly to healthy alternatives."""
        providers_to_try: List[Tuple[str, BrowserProvider]] = []

        if config.browser.remote_cdp_url:
            providers_to_try.append(("CDPBrowserProvider", CDPBrowserProvider(config)))

        if config.browser.license_key:
            providers_to_try.append(("CloakBrowserProvider", CloakBrowserProvider(config)))

        providers_to_try.append(("PlaywrightProvider", PlaywrightProvider(config)))
        providers_to_try.append(("MockBrowserProvider", MockBrowserProvider()))

        for name, provider in providers_to_try:
            try:
                logger.info(f"Attempting to launch browser context using: {name}")
                context, _ = await provider.launch_context()
                logger.info(f"Successful launch achieved with provider: {name}!")
                return context, provider
            except Exception as e:
                logger.warning(f"Launch attempt failed for provider {name}: {e}. Activating fallback...")

        raise ProviderError("All cascading browser providers failed to boot.")


class BrowserLifecycleManager:
    """Async context manager wrapper for browser lifecycles."""

    def __init__(
        self,
        provider: BrowserProvider,
        context: Optional[BrowserContextProtocol] = None,
    ) -> None:
        self.provider = provider
        self.context: Optional[BrowserContextProtocol] = context

    async def __aenter__(self) -> "BrowserLifecycleManager":
        if self.context is None:
            self.context, _ = await self.provider.launch_context()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        logger.info("Starting graceful shutdown of browser context...")
        await self.provider.shutdown()
        self.context = None
        logger.info("Browser Provider shutdown successfully executed.")
