"""Resilience, fault tolerance, and recovery primitives."""

from behavioral_playwright.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
)
from behavioral_playwright.resilience.idempotency import (
    IdempotencyPolicy,
    OperationType,
)
from behavioral_playwright.resilience.models import (
    RecoveryRecord,
    RecoveryState,
    RetryAttemptRecord,
)
from behavioral_playwright.resilience.recovery import RecoveryManager
from behavioral_playwright.resilience.retry import RetryPolicy
from behavioral_playwright.resilience.state import PageStateEntry, StateTracker
from behavioral_playwright.resilience.taxonomy import (
    FailureCategory,
    classify_failure,
    is_recoverable_via_restart,
    is_retryable,
)

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "FailureCategory",
    "IdempotencyPolicy",
    "OperationType",
    "PageStateEntry",
    "RecoveryManager",
    "RecoveryRecord",
    "RecoveryState",
    "RetryAttemptRecord",
    "RetryPolicy",
    "StateTracker",
    "classify_failure",
    "is_recoverable_via_restart",
    "is_retryable",
]
