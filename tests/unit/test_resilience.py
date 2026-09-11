"""Unit tests for resilience modules: CircuitBreaker, RetryPolicy, and StateTracker."""

import pytest
from behavioral_playwright.config.settings import CircuitBreakerConfig, RetryConfig
from behavioral_playwright.exceptions import CircuitBreakerError
from behavioral_playwright.resilience.circuit_breaker import CircuitBreaker, CircuitState
from behavioral_playwright.resilience.retry import RetryPolicy
from behavioral_playwright.resilience.state import StateTracker


# -----------------------------------------------------------------------------
# CircuitBreaker Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_circuit_breaker_transitions():
    current_time = 1000.0

    def mock_clock():
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

    # Operation rejected in OPEN state
    with pytest.raises(CircuitBreakerError):
        async def sample_op():
            return "ok"
        await cb.execute(sample_op)

    # Advance time past recovery timeout -> transitions to HALF_OPEN
    current_time += 11.0
    assert cb.state == CircuitState.HALF_OPEN

    # 2 consecutive successes in HALF_OPEN -> transitions to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


# -----------------------------------------------------------------------------
# RetryPolicy Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retry_policy_success_after_retries():
    sleep_calls = []

    async def mock_sleep(d: float):
        sleep_calls.append(d)

    config = RetryConfig(max_attempts=3, base_delay=1.0, exponential_backoff=True)
    retry = RetryPolicy(config=config, sleep_fn=mock_sleep)

    attempts = 0

    async def flaky_operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError(f"Temporary failure {attempts}")
        return "success"

    res = await retry.execute(flaky_operation, operation_name="flaky")
    assert res == "success"
    assert attempts == 3
    assert len(sleep_calls) == 2


@pytest.mark.asyncio
async def test_retry_policy_exhaustion():
    async def mock_sleep(d: float):
        pass

    config = RetryConfig(max_attempts=2, base_delay=0.1)
    retry = RetryPolicy(config=config, sleep_fn=mock_sleep)

    async def permanent_failure():
        raise RuntimeError("Fatal error")

    with pytest.raises(RuntimeError):
        await retry.execute(permanent_failure)


# -----------------------------------------------------------------------------
# StateTracker Tests
# -----------------------------------------------------------------------------
def test_state_tracker_history_and_loop_detection():
    tracker = StateTracker()
    assert tracker.transition_count == 0

    tracker.record_state(url="https://site.com/home", title="Home")
    tracker.record_state(url="https://site.com/login", title="Login")
    tracker.record_state(url="https://site.com/redirect", title="Redirect")

    assert tracker.transition_count == 3
    assert tracker.current_state.url == "https://site.com/redirect"
    assert tracker.is_in_loop() is False

    # Simulate loop
    tracker.record_state(url="https://site.com/redirect", title="Redirect")
    tracker.record_state(url="https://site.com/redirect", title="Redirect")

    assert tracker.is_in_loop(window_size=4, max_repeats=3) is True
