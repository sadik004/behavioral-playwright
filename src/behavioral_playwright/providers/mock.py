"""
Zero-dependency mock provider for offline testing.
"""

import logging
from typing import Optional, Tuple

from ..utils.mocks import MockBrowserContext
from ..utils.protocols import BrowserContextProtocol, BrowserProtocol

logger = logging.getLogger("BehavioralAutomation.Providers.Mock")


class MockBrowserProvider:
    """Zero-dependency mock provider for clean standalone testing and local container execution."""

    def __init__(self) -> None:
        self.context: Optional[MockBrowserContext] = None

    async def launch_context(self) -> Tuple[BrowserContextProtocol, Optional[BrowserProtocol]]:
        logger.info("Deploying Mock Container Provider for clean standalone testing.")
        self.context = MockBrowserContext()
        return self.context, None

    async def shutdown(self) -> None:
        pass
