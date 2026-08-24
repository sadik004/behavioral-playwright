"""Retry policy and decorator for resilient async operations."""

import asyncio
import functools
import random
from typing import Any, Callable, Coroutine, Optional, TypeVar

from behavioral_playwright.config.settings import RetryConfig
from behavioral_playwright.logging import get_logger

logger = get_logger("resilience.retry")

T = TypeVar("T")


class RetryPolicy:
    """Configurable retry policy with injectable sleep handler for deterministic testing."""

    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        sleep_fn: Optional[Callable[[float], Coroutine[Any, Any, None]]] = None
    ) -> None:
        self.config = config or RetryConfig()
        self._sleep_fn = sleep_fn or asyncio.sleep

    async def execute(
        self,
        coro_fn: Callable[[], Coroutine[Any, Any, T]],
        operation_name: str = "operation"
    ) -> T:
        """Executes coroutine function with configured retry policy."""
        attempt = 0
        last_exception: Optional[Exception] = None

        while attempt < self.config.max_attempts:
            attempt += 1
            try:
                return await coro_fn()
            except Exception as e:
                last_exception = e
                if attempt >= self.config.max_attempts:
                    logger.warning(
                        f"[RetryPolicy] {operation_name} failed permanently after {attempt} attempts: {e}"
                    )
                    raise

                delay = self.config.base_delay
                if self.config.exponential_backoff:
                    delay = min(self.config.base_delay * (2 ** (attempt - 1)), self.config.max_delay)

                if self.config.jitter:
                    delay = delay * (0.5 + random.random() * 0.5)

                logger.info(
                    f"[RetryPolicy] {operation_name} attempt {attempt} failed ({e}). Retrying in {delay:.2f}s..."
                )
                await self._sleep_fn(delay)

        if last_exception:
            raise last_exception
        raise RuntimeError(f"Retry loop exited unexpectedly for {operation_name}")

    def __call__(self, func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        """Decorator wrapper for async functions."""
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await self.execute(lambda: func(*args, **kwargs), operation_name=func.__name__)
        return wrapper
