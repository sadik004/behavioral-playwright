"""Deterministic CircuitBreaker for fault tolerance and failure isolation."""

from enum import Enum
import time
from typing import Any, Callable, Coroutine, Optional, TypeVar

from behavioral_playwright.config.settings import CircuitBreakerConfig
from behavioral_playwright.exceptions import CircuitBreakerError
from behavioral_playwright.logging import get_logger

logger = get_logger("resilience.circuit_breaker")

T = TypeVar("T")


class CircuitState(str, Enum):
    """Possible states for CircuitBreaker state machine."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    Finite State Machine CircuitBreaker isolating systemic failures.
    Accepts an injectable clock function for deterministic testing.
    """

    def __init__(
        self,
        config: Optional[CircuitBreakerConfig] = None,
        clock_fn: Optional[Callable[[], float]] = None
    ) -> None:
        self.config = config or CircuitBreakerConfig()
        self._clock_fn = clock_fn or time.time
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_state_change = self._clock_fn()
        self._half_open_successes = 0

    @property
    def state(self) -> CircuitState:
        """Returns the current state, evaluating automatic cooldown transitions."""
        current_time = self._clock_fn()
        if self._state == CircuitState.OPEN:
            elapsed = current_time - self._last_state_change
            if elapsed >= self.config.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def _transition_to(self, new_state: CircuitState) -> None:
        logger.info(f"[CircuitBreaker] Transition: {self._state.value} -> {new_state.value}")
        self._state = new_state
        self._last_state_change = self._clock_fn()
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._half_open_successes = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_successes = 0

    def record_success(self) -> None:
        """Records a successful operation call."""
        if self.state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= self.config.half_open_max_attempts:
                self._transition_to(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Records an operation failure."""
        self._failure_count += 1
        if self.state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
        elif self.state == CircuitState.CLOSED:
            if self._failure_count >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def reset(self) -> None:
        """Manually resets circuit breaker back to CLOSED state."""
        self._transition_to(CircuitState.CLOSED)

    async def execute(
        self,
        coro_fn: Callable[[], Coroutine[Any, Any, T]],
        operation_name: str = "operation"
    ) -> T:
        """Executes an operation protected by the circuit breaker."""
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(
                f"CircuitBreaker is OPEN for {operation_name}. Operation rejected."
            )

        try:
            result = await coro_fn()
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise e
