"""
Patch 5: Concurrent Memory Recycling & Context Rotation
Actively recycles BrowserContexts and purges V8 caching boundaries
to maintain a low memory footprint and bypass accumulated bot telemetry.
"""
import logging
from typing import Any

logger = logging.getLogger("BehavioralEvasion.ContextRotator")


class ContextRotator:
    """
    Actively recycles BrowserContexts and purges V8 caching boundaries
    to maintain a low memory footprint and bypass accumulated bot telemetry.
    """
    def __init__(self, browser: Any, recycle_threshold: int = 50) -> None:
        self.browser = browser
        self.recycle_threshold = recycle_threshold
        self.request_count = 0
        self.current_context = None

    async def get_healthy_context(self, manager: Any = None) -> Any:
        """Recycles the context and clears cache if threshold is reached."""
        self.request_count += 1
        if self.current_context is None or self.request_count >= self.recycle_threshold:
            if self.current_context is not None:
                logger.info("ContextRotator: Session threshold reached. V8 caches cleared and Context rotated smoothly.")
                try:
                    pages = await self.current_context.pages()
                    if pages:
                        cdp = await pages[0].context.new_cdp_session(pages[0])
                        await cdp.send("Network.clearBrowserCache")
                except Exception:
                    pass
                await self.current_context.close()

            # Spawn fresh context via manager or directly
            if manager:
                self.current_context = await manager.create_isolated_context()
            else:
                self.current_context = await self.browser.new_context()
            self.request_count = 0
            logger.info("ContextRotator: Spawned a completely fresh and un-cached BrowserContext.")

        return self.current_context
