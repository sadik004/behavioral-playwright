"""Failure taxonomy and classification engine for behavioral-playwright resilience."""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any, Optional, Set

from behavioral_playwright.exceptions import (
    BehavioralPlaywrightError,
    BrowserProviderError,
    CircuitBreakerError,
    ConfigurationError,
    ElementResolutionError,
    ExtractionError,
    MappingError,
    NavigationError,
    ProviderError,
    ProviderUnavailableError,
    SearchError,
    TimeoutError as BPTimeoutError,
)


class FailureCategory(str, Enum):
    """Rigorous classification of runtime failures to guide recovery and retry decisions."""
    TRANSIENT = "TRANSIENT"
    RECOVERABLE = "RECOVERABLE"
    NON_RECOVERABLE = "NON_RECOVERABLE"
    STATE_CORRUPTION = "STATE_CORRUPTION"
    TIMEOUT = "TIMEOUT"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    BROWSER_FAILURE = "BROWSER_FAILURE"
    PAGE_FAILURE = "PAGE_FAILURE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    NAVIGATION_FAILURE = "NAVIGATION_FAILURE"
    DETACHED_TARGET = "DETACHED_TARGET"
    CANCELLATION = "CANCELLATION"
    UNKNOWN = "UNKNOWN"


# Non-retryable categories that must fail immediately without consuming retry attempts
NON_RETRYABLE_CATEGORIES: Set[FailureCategory] = {
    FailureCategory.CANCELLATION,
    FailureCategory.NON_RECOVERABLE,
    FailureCategory.STATE_CORRUPTION,
    FailureCategory.BROWSER_FAILURE,   # Requires coordinated browser recovery, not simple function retry
    FailureCategory.PAGE_FAILURE,      # Requires page recreation, not simple function retry
}

# Categories where an in-place retry (with backoff/jitter) is valid and safe
RETRYABLE_CATEGORIES: Set[FailureCategory] = {
    FailureCategory.TRANSIENT,
    FailureCategory.RECOVERABLE,
    FailureCategory.TIMEOUT,
    FailureCategory.NETWORK_FAILURE,
    FailureCategory.DETACHED_TARGET,
}

# Categories that can trigger session / page / browser recovery state machine
RECOVERABLE_RESTART_CATEGORIES: Set[FailureCategory] = {
    FailureCategory.BROWSER_FAILURE,
    FailureCategory.PAGE_FAILURE,
    FailureCategory.PROVIDER_FAILURE,
    FailureCategory.STATE_CORRUPTION,
}


def classify_failure(exc: BaseException) -> FailureCategory:
    """Classifies an exception into an authoritative FailureCategory.

    Invariants:
    1. Cancellation is NEVER classified as transient or retryable.
    2. Code bugs, assertion errors, and configuration flaws are NON_RECOVERABLE.
    3. Browser process / context / target closures are classified as BROWSER_FAILURE or PAGE_FAILURE.
    4. Network connection drops and timeouts are strictly differentiated.
    """
    # 1. Cancellation must be detected first and respected unconditionally
    if isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt)):
        return FailureCategory.CANCELLATION

    # 2. Configuration, assertion, type, and programming errors
    if isinstance(exc, (ConfigurationError, AssertionError, TypeError, KeyError, SyntaxError, AttributeError)):
        return FailureCategory.NON_RECOVERABLE

    # 3. CircuitBreaker open error is non-recoverable at function level
    if isinstance(exc, CircuitBreakerError):
        return FailureCategory.NON_RECOVERABLE

    # 4. Provider missing or uninstalled (Phase 2 invariant)
    if isinstance(exc, ProviderUnavailableError):
        return FailureCategory.NON_RECOVERABLE

    # 5. Network, socket, and connection errors
    if isinstance(exc, (ConnectionError, ConnectionResetError, ConnectionRefusedError, BrokenPipeError)):
        return FailureCategory.NETWORK_FAILURE

    # 6. Timeout errors
    if isinstance(exc, (asyncio.TimeoutError, BPTimeoutError, TimeoutError)):
        return FailureCategory.TIMEOUT

    # 7. DOM element resolution or detached target errors
    if isinstance(exc, ElementResolutionError):
        return FailureCategory.DETACHED_TARGET

    # 8. Navigation errors
    if isinstance(exc, NavigationError):
        msg = str(exc).lower()
        if any(term in msg for term in ("net::err_", "econnrefused", "connection_failed", "dns_", "reset by peer")):
            return FailureCategory.NETWORK_FAILURE
        return FailureCategory.NAVIGATION_FAILURE

    # 8. Schema mapping or ambiguity errors
    if isinstance(exc, MappingError):
        return FailureCategory.NON_RECOVERABLE

    # 9. Search errors
    if isinstance(exc, SearchError):
        return FailureCategory.RECOVERABLE

    # 10. String inspection for underlying Playwright / OS process errors
    exc_str = str(exc).lower()
    exc_type = type(exc).__name__.lower()

    if any(term in exc_str or term in exc_type for term in (
        "browser has been closed",
        "browser closed",
        "target closed",
        "connection closed",
        "closed pipe",
        "broken pipe",
        "process died",
        "crash",
    )):
        if "target" in exc_str or "page" in exc_str:
            return FailureCategory.PAGE_FAILURE
        return FailureCategory.BROWSER_FAILURE

    if any(term in exc_str for term in ("connection refused", "network error", "err_connection")):
        return FailureCategory.NETWORK_FAILURE

    if "execution context was destroyed" in exc_str:
        return FailureCategory.PAGE_FAILURE

    if isinstance(exc, BrowserProviderError):
        return FailureCategory.PROVIDER_FAILURE

    if isinstance(exc, ValueError):
        return FailureCategory.TRANSIENT

    if isinstance(exc, NotImplementedError):
        return FailureCategory.NON_RECOVERABLE

    return FailureCategory.UNKNOWN


def is_retryable(category: FailureCategory) -> bool:
    """Returns True if the failure category represents a transient condition safe for in-place retry."""
    return category in RETRYABLE_CATEGORIES


def is_recoverable_via_restart(category: FailureCategory) -> bool:
    """Returns True if the failure warrants triggering an architectural page or browser recovery."""
    return category in RECOVERABLE_RESTART_CATEGORIES
