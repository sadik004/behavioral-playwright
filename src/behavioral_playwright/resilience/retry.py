"""Retry policy and decorator for resilient async operations with timeout budget and idempotency guards."""

from __future__ import annotations

import asyncio
import functools
import random
import time
from typing import Any, Callable, Coroutine, List, Optional, TypeVar

from behavioral_playwright.config.settings import RetryConfig
from behavioral_playwright.exceptions import TimeoutError as BPTimeoutError
from behavioral_playwright.logging import get_logger
from behavioral_playwright.resilience.idempotency import IdempotencyPolicy, OperationType
from behavioral_playwright.resilience.models import RetryAttemptRecord
from behavioral_playwright.resilience.taxonomy import classify_failure, is_retryable, FailureCategory

logger = get_logger("resilience.retry")

T = TypeVar("T")


class RetryPolicy:
    """Configurable retry policy with timeout budget enforcement, failure taxonomy, and idempotency protection."""

    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        sleep_fn: Optional[Callable[[float], Coroutine[Any, Any, None]]] = None,
        clock_fn: Optional[Callable[[], float]] = None,
        rng_seed: Optional[int] = None,
    ) -> None:
        self.config = config or RetryConfig()
        self._sleep_fn = sleep_fn or asyncio.sleep
        self._clock_fn = clock_fn or time.monotonic
        self._rng = random.Random(rng_seed) if rng_seed is not None else random.Random()
        self.attempts_history: List[RetryAttemptRecord] = []

    async def execute(
        self,
        coro_fn: Callable[[], Coroutine[Any, Any, T]],
        operation_name: str = "operation",
        operation_type: OperationType = OperationType.READ,
        timeout_budget_s: Optional[float] = None,
        explicit_idempotent: Optional[bool] = None,
        started_execution_cb: Optional[Callable[[], bool]] = None,
    ) -> T:
        """Executes coroutine function with configured retry policy.

        Invariants:
        1. Cancellation (asyncio.CancelledError) is NEVER retried or swallowed.
        2. Total duration across all retries strictly adheres to timeout_budget_s.
        3. Non-retryable failures (programming bugs, bad configs, circuit breaker rejections) fail immediately.
        4. Non-idempotent operations that initiated execution are NOT blindly repeated.
        """
        attempt = 0
        last_exception: Optional[Exception] = None
        start_time = self._clock_fn()
        deadline = (start_time + timeout_budget_s) if timeout_budget_s is not None else None

        while attempt < self.config.max_attempts:
            # 1. Budget verification before starting attempt
            now = self._clock_fn()
            if deadline is not None and now >= deadline:
                logger.warning(f"[RetryPolicy] Timeout budget ({timeout_budget_s}s) exhausted before attempt {attempt + 1} of {operation_name}.")
                if last_exception:
                    raise last_exception
                raise BPTimeoutError(f"Operation '{operation_name}' exceeded timeout budget of {timeout_budget_s}s.")

            attempt += 1
            try:
                return await coro_fn()
            except asyncio.CancelledError:
                logger.info(f"[RetryPolicy] Operation '{operation_name}' cancelled by parent task. Aborting retry loop.")
                raise
            except Exception as e:
                last_exception = e
                elapsed = self._clock_fn() - start_time
                category = classify_failure(e)
                retryable = is_retryable(category)

                # 2. Idempotency verification: is it safe to retry this operation?
                execution_initiated = started_execution_cb() if started_execution_cb else True
                safe_by_idempotency = IdempotencyPolicy.is_safe_to_retry(
                    op_type=operation_type,
                    attempt=attempt,
                    started_execution=execution_initiated,
                    explicit_idempotent=explicit_idempotent,
                )

                # Record attempt provenance
                self.attempts_history.append(
                    RetryAttemptRecord(
                        attempt=attempt,
                        timestamp=self._clock_fn(),
                        delay_s=0.0,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        failure_category=category,
                        is_retryable=retryable and safe_by_idempotency,
                        elapsed_budget_s=elapsed,
                    )
                )

                # 3. Check termination conditions
                if not retryable:
                    logger.warning(
                        f"[RetryPolicy] {operation_name} failed with non-retryable {category.value} ({e}). Failing immediately."
                    )
                    raise

                if not safe_by_idempotency:
                    logger.warning(
                        f"[RetryPolicy] {operation_name} is {operation_type.value} and unsafe to retry after execution initiation. Failing immediately to prevent duplicate side effects."
                    )
                    raise

                if attempt >= self.config.max_attempts:
                    logger.warning(
                        f"[RetryPolicy] {operation_name} failed permanently after {attempt} attempts: {e}"
                    )
                    raise

                # 4. Compute backoff and bounded jitter
                delay = self.config.base_delay
                if self.config.exponential_backoff:
                    delay = min(self.config.base_delay * (2 ** (attempt - 1)), self.config.max_delay)

                if self.config.jitter:
                    # Bounded jitter within [0.5 * delay, 1.0 * delay]
                    delay = delay * (0.5 + self._rng.random() * 0.5)

                # Clamp delay to remaining timeout budget
                if deadline is not None:
                    remaining_budget = deadline - self._clock_fn()
                    if remaining_budget <= 0.0:
                        logger.warning(
                            f"[RetryPolicy] Timeout budget ({timeout_budget_s}s) exhausted. Cannot sleep for next retry of {operation_name}."
                        )
                        raise last_exception
                    delay = min(delay, remaining_budget)

                if self.attempts_history:
                    self.attempts_history[-1].delay_s = delay

                logger.info(
                    f"[RetryPolicy] {operation_name} attempt {attempt} failed [{category.value}] ({e}). Retrying in {delay:.2f}s..."
                )
                await self._sleep_fn(delay)

        if last_exception:
            raise last_exception
        raise RuntimeError(f"Retry loop exited unexpectedly for {operation_name}")

    def __call__(
        self,
        func: Optional[Callable[..., Coroutine[Any, Any, T]]] = None,
        *,
        operation_type: OperationType = OperationType.READ,
        timeout_budget_s: Optional[float] = None,
        explicit_idempotent: Optional[bool] = None,
    ) -> Any:
        """Decorator wrapper for async functions."""
        def decorator(f: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
            @functools.wraps(f)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                return await self.execute(
                    lambda: f(*args, **kwargs),
                    operation_name=f.__name__,
                    operation_type=operation_type,
                    timeout_budget_s=timeout_budget_s,
                    explicit_idempotent=explicit_idempotent,
                )
            return wrapper

        if func is not None:
            return decorator(func)
        return decorator
