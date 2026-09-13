"""
Patch 8: Status-Granular Circuit Breaker with Cooldown Jitter
Handles cooldowns and dynamic delays based on block taxonomy with Gaussian Jitter.
"""
import time
import random
import logging
from typing import List, Tuple

logger = logging.getLogger("BehavioralEvasion.CircuitBreaker")


class StatusGranularCircuitBreaker:
    """Handles cooldowns and dynamic delays based on block taxonomy with Gaussian Jitter."""
    def __init__(self, threshold: int = 3, cooldown_window: float = 5.0) -> None:
        self.threshold = threshold
        self.cooldown_window = cooldown_window
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failures: List[Tuple[float, str]] = []

    def register_failure(self, error_type: str) -> None:
        now = time.time()
        self.failures.append((now, error_type))
        recent_failures = [f for f in self.failures if now - f[0] < 60.0]

        if len(recent_failures) >= self.threshold:
            self.state = "OPEN"
            jitter = random.gauss(0.0, 3.5)
            if error_type == "ip_ban_429_403":
                self.cooldown_window = 120.0 + abs(jitter)
                logger.error(f"CircuitBreaker: OPENED (IP ban). Dynamic Cooldown: {self.cooldown_window:.2f}s. Triggering Proxy Rotation.")
            elif error_type == "schema_drift_validation":
                self.cooldown_window = 10.0 + abs(jitter)
                logger.error(f"CircuitBreaker: OPENED (Schema drift). Cooldown: {self.cooldown_window:.2f}s. Halting execution.")
            else:
                self.cooldown_window = 15.0 + abs(jitter)
                logger.error(f"CircuitBreaker: OPENED (Transient Timeout). Cooldown: {self.cooldown_window:.2f}s. Retrying softly.")

    def allow_request(self) -> bool:
        if self.state == "CLOSED":
            return True
        now = time.time()
        last_fail_time = self.failures[-1][0] if self.failures else 0
        if self.state == "OPEN":
            if now - last_fail_time > self.cooldown_window:
                self.state = "HALF_OPEN"
                logger.info("CircuitBreaker: Moving to HALF_OPEN state. Testing connection viability.")
                return True
            return False
        return True
