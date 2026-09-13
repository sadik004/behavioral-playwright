"""
Patch 9 Support: Bounded Backpressure Async Queue
Prevents concurrent memory bloating by restricting task queues with strict bounds.
"""
import asyncio
import logging
from typing import Any

logger = logging.getLogger("BehavioralEvasion.BackpressureQueue")


class BackpressureQueue:
    """Prevents concurrent memory bloating by restricting task queues with strict bounds."""
    def __init__(self, maxsize: int = 50) -> None:
        self.queue = asyncio.Queue(maxsize=maxsize)
        logger.info(f"BackpressureQueue: Initialized with a strict buffer limit of {maxsize} concurrent items.")

    async def push_item(self, item: Any) -> None:
        await self.queue.put(item)

    async def get_item(self) -> Any:
        item = await self.queue.get()
        self.queue.task_done()
        return item
