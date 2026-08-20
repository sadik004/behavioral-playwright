"""
Circuit Breaker State Machine coordinating CLOSED -> OPEN -> HALF_OPEN transitions.
"""

import logging
from enum import Enum
from typing import Optional

from ..utils.clock_rng import SystemClock
from ..utils.protocols import Clock

logger = logging.getLogger("BehavioralAutomation.Navigation.CircuitBreaker")


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    Implements a strict, time-coherence Circuit Breaker state machine
    coordinating CLOSED -> OPEN -> HALF_OPEN -> CLOSED transitions.
    """

    def __init__(
        self,
        failure_threshold: int = 2,
        recovery_cooldown: float = 1.0,
        clock: Clock = SystemClock(),
        custom_logger: Optional[logging.Logger] = None,
    ) -> None:
        self.state = CircuitState.CLOSED
        self.failure_threshold = failure_threshold
        self.recovery_cooldown = recovery_cooldown
        self.clock = clock
        self.logger = custom_logger or logger
        self.consecutive_failures = 0
        self.last_failure_timestamp = 0.0

    def record_success(self) -> None:
        """Resets failure counts and transitions the circuit cleanly to CLOSED."""
        if self.state != CircuitState.CLOSED:
            self.logger.info("Circuit Breaker transitioned to CLOSED state (System healthy).")
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        """Increments failures and triggers transition to OPEN on exceeding thresholds."""
        self.consecutive_failures += 1
        self.last_failure_timestamp = self.clock.time()

        if self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning(
                f"Circuit Breaker transitioned to OPEN (failures: {self.consecutive_failures}). "
                f"Cooldown: {self.recovery_cooldown}s."
            )

    def allow_request(self) -> bool:
        """Determines if requests are permitted, executing auto-recovery checks dynamically."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            time_since_failure = self.clock.time() - self.last_failure_timestamp
            if time_since_failure >= self.recovery_cooldown:
                self.state = CircuitState.HALF_OPEN
                self.logger.info("Circuit Breaker transitioned to HALF_OPEN. Permitting test probe request.")
                return True
            return False

        return self.state == CircuitState.HALF_OPEN
