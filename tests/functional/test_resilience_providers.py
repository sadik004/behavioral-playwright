"""Functional Validation: Resilience Primitives & Provider Lifecycle.
Tests CircuitBreaker state machine, RetryPolicy, provider matrix honesty, and ProviderUnavailableError.
"""

from __future__ import annotations

import pytest

from behavioral_playwright.config.settings import CircuitBreakerConfig, RetryConfig
from behavioral_playwright.exceptions import CircuitBreakerError, ProviderUnavailableError
from behavioral_playwright.providers import create_browser_provider, provider_matrix
from behavioral_playwright.resilience.circuit_breaker import CircuitBreaker, CircuitState
from behavioral_playwright.resilience.retry import RetryPolicy


@pytest.mark.asyncio
async def test_circuit_breaker_full_lifecycle_and_rejection():
    """Verify CircuitBreaker transitions CLOSED -> OPEN -> HALF_OPEN -> CLOSED and rejects calls in OPEN state."""
    current_time = 100.0

    def mock_clock() -> float:
        return current_time

    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=10.0,
        half_open_max_attempts=2
    )
    cb = CircuitBreaker(config=config, clock_fn=mock_clock)

    assert cb.state == CircuitState.CLOSED

    # Record 2 failures -> remains CLOSED
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 2

    # 3rd failure reaches threshold -> transitions to OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    # Operation rejected in OPEN state with CircuitBreakerError
    async def op():
        return "should not run"

    with pytest.raises(CircuitBreakerError) as exc_info:
        await cb.execute(op)
    assert "CircuitBreaker is OPEN" in str(exc_info.value)

    # Fast forward past recovery timeout -> transitions to HALF_OPEN
    current_time += 15.0
    assert cb.state == CircuitState.HALF_OPEN

    # Successful call in HALF_OPEN resets to CLOSED
    async def healthy_op():
        return "healed"

    # Needs half_open_max_attempts (2) successes to close
    res1 = await cb.execute(healthy_op)
    assert res1 == "healed"
    res2 = await cb.execute(healthy_op)
    assert res2 == "healed"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


@pytest.mark.asyncio
async def test_retry_policy_eventual_success_and_exhaustion():
    """Verify RetryPolicy retries transient failures and raises when exhausted."""
    # 1. Transient failure recovering on attempt 3
    config = RetryConfig(max_attempts=3, base_delay=0.01, max_delay=0.05)
    retryer = RetryPolicy(config=config)

    attempts = 0

    async def flaky_op():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionResetError("Transient network failure")
        return "success_recovered"

    result = await retryer.execute(flaky_op)
    assert result == "success_recovered"
    assert attempts == 3

    # 2. Permanent failure exhausting retries
    perm_attempts = 0

    async def perm_fail():
        nonlocal perm_attempts
        perm_attempts += 1
        raise ValueError("Permanent configuration error")

    with pytest.raises(ValueError) as exc_info:
        await retryer.execute(perm_fail)
    assert "Permanent configuration error" in str(exc_info.value)
    assert perm_attempts == 3  # max_attempts = 3


def test_provider_matrix_honesty_and_gating():
    """Verify provider_matrix truthfully reflects installed libraries without false claims."""
    matrix = provider_matrix()
    
    # Playwright is installed in this runtime
    assert "browser/playwright" in matrix
    assert matrix["browser/playwright"].installed is True
    assert matrix["browser/playwright"].error is None
    
    # Patchright is uninstalled in this runtime
    assert "browser/patchright" in matrix
    assert matrix["browser/patchright"].installed is False
    assert "No module named" in str(matrix["browser/patchright"].error)


def test_provider_instantiation_and_unavailable_error():
    """Verify create_browser_provider returns active instance for installed provider and raises ProviderUnavailableError on launch/require."""
    # 1. Installed provider succeeds
    provider = create_browser_provider("playwright")
    assert provider is not None
    assert hasattr(provider, "launch")

    # 2. Uninstalled provider raises ProviderUnavailableError upon require_available or launch
    patchright_provider = create_browser_provider("patchright")
    assert patchright_provider is not None
    with pytest.raises(ProviderUnavailableError) as exc_info:
        patchright_provider.launch()
    assert "patchright" in str(exc_info.value).lower()
