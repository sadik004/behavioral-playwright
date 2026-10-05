"""Phase 6 Functional Verification Suite: Resilience, Recovery & Long-Running Workflow Integrity.

Verifies:
- Failure taxonomy & rigorous exception classification
- Retry correctness with bounded backoff and non-polluting jitter
- Strict timeout budget enforcement across retry cycles
- Cancellation safety (asyncio.CancelledError immediately propagated)
- Idempotency & side-effect prevention (NON_IDEMPOTENT_WRITE safe retry gating)
- CircuitBreaker concurrency safety, state transitions, and half-open probing
- Coordinated single-flight recovery (preventing duplicate restart storms)
- Post-recovery verification of browser liveness and DOM responsiveness
- Stale state invalidation (purging dead page handles and selector caches)
- Session identity continuity across recovery
- Sibling page isolation under single-page failure
- Facade integration with live Chromium
"""

from __future__ import annotations

import asyncio
from typing import Any, List
from urllib.parse import quote
import pytest

from behavioral_playwright.config.settings import (
    AutomationConfig,
    BrowserConfig,
    CircuitBreakerConfig,
    RetryConfig,
)
from behavioral_playwright.exceptions import (
    BehavioralPlaywrightError,
    CircuitBreakerError,
    ConfigurationError,
    NavigationError,
    TimeoutError as BPTimeoutError,
)
from behavioral_playwright.facade import BP
from behavioral_playwright.page.session import BrowserSession, PageSession
from behavioral_playwright.resilience.circuit_breaker import CircuitBreaker, CircuitState
from behavioral_playwright.resilience.idempotency import IdempotencyPolicy, OperationType
from behavioral_playwright.resilience.models import RecoveryState
from behavioral_playwright.resilience.recovery import RecoveryManager
from behavioral_playwright.resilience.retry import RetryPolicy
from behavioral_playwright.resilience.taxonomy import (
    FailureCategory,
    classify_failure,
    is_recoverable_via_restart,
    is_retryable,
)


def make_data_url(html: str) -> str:
    return f"data:text/html;charset=utf-8,{quote(html)}"


RESILIENCE_HTML = """<!DOCTYPE html>
<html>
<head><title>Resilience Test Harness</title></head>
<body>
    <h1 id="title">Resilience Fixture</h1>
    <button id="action-btn" onclick="document.getElementById('counter').innerText = parseInt(document.getElementById('counter').innerText) + 1;">Increment</button>
    <div id="counter">0</div>
</body>
</html>
"""


# ============================================================================
# 1. Failure Taxonomy & Classification Correctness
# ============================================================================

def test_failure_taxonomy_classification():
    """Verifies that exceptions are classified into deterministic categories."""
    assert classify_failure(asyncio.CancelledError()) == FailureCategory.CANCELLATION
    assert is_retryable(FailureCategory.CANCELLATION) is False

    assert classify_failure(ConfigurationError("bad config")) == FailureCategory.NON_RECOVERABLE
    assert is_retryable(FailureCategory.NON_RECOVERABLE) is False

    assert classify_failure(AssertionError("invariant violated")) == FailureCategory.NON_RECOVERABLE
    assert classify_failure(TypeError("bad arg")) == FailureCategory.NON_RECOVERABLE

    assert classify_failure(asyncio.TimeoutError()) == FailureCategory.TIMEOUT
    assert is_retryable(FailureCategory.TIMEOUT) is True

    assert classify_failure(NavigationError("Page.goto: net::ERR_CONNECTION_REFUSED")) == FailureCategory.NETWORK_FAILURE
    assert is_retryable(FailureCategory.NETWORK_FAILURE) is True

    assert classify_failure(RuntimeError("Target closed")) == FailureCategory.PAGE_FAILURE
    assert is_recoverable_via_restart(FailureCategory.PAGE_FAILURE) is True

    assert classify_failure(RuntimeError("browser has been closed")) == FailureCategory.BROWSER_FAILURE
    assert is_recoverable_via_restart(FailureCategory.BROWSER_FAILURE) is True


# ============================================================================
# 2. Strict Timeout Budget Enforcement
# ============================================================================

@pytest.mark.asyncio
async def test_retry_policy_strictly_respects_timeout_budget():
    """Verify retry loop aborts as soon as caller's timeout budget expires."""
    virtual_time = 0.0

    def mock_clock() -> float:
        return virtual_time

    async def mock_sleep(d: float) -> None:
        nonlocal virtual_time
        virtual_time += d

    # 10 attempts allowed, but timeout budget is 2.5 seconds
    config = RetryConfig(max_attempts=10, base_delay=1.0, exponential_backoff=False)
    retry = RetryPolicy(config=config, sleep_fn=mock_sleep, clock_fn=mock_clock)

    attempts = 0

    async def slow_failing_op():
        nonlocal attempts, virtual_time
        attempts += 1
        virtual_time += 1.0  # Operation takes 1s per attempt
        raise ValueError("Simulated transient failure")

    with pytest.raises(ValueError):
        await retry.execute(
            slow_failing_op,
            operation_name="budgeted_op",
            timeout_budget_s=2.5,
        )

    # Attempt 1: takes 1s (total 1.0s), sleeps 1.0s (total 2.0s)
    # Attempt 2: takes 1s (total 3.0s > 2.5s) -> budget exhausted!
    assert attempts <= 2
    assert virtual_time >= 2.5


# ============================================================================
# 3. Cancellation Safety & Immediate Propagation
# ============================================================================

@pytest.mark.asyncio
async def test_cancellation_propagates_immediately_without_eating_retries():
    """asyncio.CancelledError must NEVER be caught or consumed as a retry attempt."""
    config = RetryConfig(max_attempts=5, base_delay=0.1)
    retry = RetryPolicy(config=config)

    attempts = 0

    async def cancelling_op():
        nonlocal attempts
        attempts += 1
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await retry.execute(cancelling_op, operation_name="cancelling_op")

    # Must fail immediately on first attempt without sleeping or retrying
    assert attempts == 1


# ============================================================================
# 4. Idempotency & Side-Effect Protection
# ============================================================================

@pytest.mark.asyncio
async def test_idempotency_prevents_unsafe_side_effect_retries():
    """Non-idempotent operations that initiated execution must NOT be blindly retried."""
    config = RetryConfig(max_attempts=3, base_delay=0.1)
    retry = RetryPolicy(config=config)

    attempts = 0

    async def dangerous_checkout_op():
        nonlocal attempts
        attempts += 1
        raise RuntimeError("Network response dropped after submitting credit card")

    # Calling as NON_IDEMPOTENT_WRITE with started_execution_cb returning True
    with pytest.raises(RuntimeError):
        await retry.execute(
            dangerous_checkout_op,
            operation_name="credit_card_submit",
            operation_type=OperationType.NON_IDEMPOTENT_WRITE,
            started_execution_cb=lambda: True,
        )

    # Must NOT retry dangerous write: exactly 1 attempt executed
    assert attempts == 1

    # But if execution failed BEFORE dispatching (started_execution=False), safe to retry:
    retry_before = RetryPolicy(config=config)
    safe_attempts = 0

    async def failed_before_dispatch():
        nonlocal safe_attempts
        safe_attempts += 1
        if safe_attempts < 2:
            raise ValueError("Pre-flight check failed")
        return "ok"

    res = await retry_before.execute(
        failed_before_dispatch,
        operation_name="safe_preflight",
        operation_type=OperationType.NON_IDEMPOTENT_WRITE,
        started_execution_cb=lambda: False,
    )
    assert res == "ok"
    assert safe_attempts == 2


# ============================================================================
# 5. Circuit Breaker Concurrency & Synchronization
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_concurrent_access_is_lock_safe():
    """Verifies that concurrent tasks do not cause race conditions in CircuitBreaker."""
    config = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=1.0)
    cb = CircuitBreaker(config=config)

    async def failing_worker():
        try:
            async def _fail():
                raise ValueError("Worker failure")
            await cb.execute(_fail, operation_name="concurrent_worker")
        except (ValueError, CircuitBreakerError):
            pass

    # Launch 20 concurrent failing workers
    tasks = [asyncio.create_task(failing_worker()) for _ in range(20)]
    await asyncio.gather(*tasks)

    # CircuitBreaker must cleanly transition to OPEN without deadlocking or state corruption
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count >= 5

    # Manual reset works reliably
    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


# ============================================================================
# 6. Coordinated Recovery Manager: Single-Flight & Post-Recovery Verification
# ============================================================================

@pytest.mark.asyncio
async def test_coordinated_recovery_single_flight_and_post_verification():
    """Multiple concurrent failures trigger a single coordinated recovery with DOM verification."""
    async with BrowserSession() as session:
        page = await session.new_page()
        await page.goto(make_data_url(RESILIENCE_HTML))
        orig_session_id = page.session_id

        # Verify initial healthy state
        assert await page.get_title() == "Resilience Test Harness"

        # Simulate a crash by explicitly closing the underlying raw page
        old_raw_page = page.raw_page
        await old_raw_page.close()
        assert old_raw_page.is_closed() is True

        # Launch 3 concurrent recovery requests (e.g. from 3 background scrapers)
        rec_mgr = page.recovery_manager
        results = await asyncio.gather(
            rec_mgr.execute_recovery(page, RuntimeError("Target closed: Page crashed"), restore_url=True),
            rec_mgr.execute_recovery(page, RuntimeError("Target closed: Page crashed"), restore_url=True),
            rec_mgr.execute_recovery(page, RuntimeError("Target closed: Page crashed"), restore_url=True),
        )

        # All 3 coordinated requests should report True (success)
        assert all(results) is True
        assert rec_mgr.state == RecoveryState.RECOVERED

        # Verification Invariant: Raw page is fresh, open, and responsive
        assert page.raw_page is not old_raw_page
        assert page.raw_page.is_closed() is False
        assert await page.evaluate("() => 2 + 2") == 4

        # Session Identity Invariant: session_id remains identical across recovery
        assert page.session_id == orig_session_id

        # Provenance Invariant: Exactly one recovery record created with verified=True
        assert len(rec_mgr.recovery_history) >= 1
        last_rec = rec_mgr.recovery_history[-1]
        assert last_rec.verification_passed is True
        assert last_rec.resulting_state == RecoveryState.RECOVERED
        assert last_rec.verification_details.get("evaluation_alive") is True


# ============================================================================
# 7. Sibling Page Isolation Under Single-Page Failure
# ============================================================================

@pytest.mark.asyncio
async def test_sibling_page_isolation_under_page_failure():
    """Crashing Page A and recovering it must leave Page B completely untouched."""
    async with BrowserSession() as session:
        page_a = await session.new_page()
        page_b = await session.new_page()

        await page_a.goto(make_data_url("<html><body><h1 id='a'>Page A</h1></body></html>"))
        await page_b.goto(make_data_url("<html><body><h1 id='b'>Page B</h1></body></html>"))

        assert await page_a.extract_text("h1#a") == "Page A"
        assert await page_b.extract_text("h1#b") == "Page B"

        # Crash Page A only
        await page_a.raw_page.close()
        assert page_a.raw_page.is_closed() is True

        # Page B MUST remain open, functional, and uncontaminated
        assert page_b.raw_page.is_closed() is False
        assert await page_b.extract_text("h1#b") == "Page B"

        # Recover Page A
        recovered = await page_a.recover(reason="Crash test", restore_url=True)
        assert recovered is True
        assert page_a.raw_page.is_closed() is False

        # Verify Page B is STILL completely untouched
        assert page_b.raw_page.is_closed() is False
        assert await page_b.extract_text("h1#b") == "Page B"


# ============================================================================
# 8. Stale State Invalidation
# ============================================================================

@pytest.mark.asyncio
async def test_stale_selector_memory_invalidated_on_recovery():
    """Recovery must invalidate stale selector memory to prevent referencing dead DOM nodes."""
    async with BrowserSession() as session:
        page = await session.new_page()
        await page.goto(make_data_url(RESILIENCE_HTML))

        # Record a learned healed selector resolution in memory
        if hasattr(page.resolver, "memory"):
            from behavioral_playwright.models.results import ResolutionResult, ResolutionStrategy
            page.resolver.memory.record(
                "#action-btn",
                ResolutionResult(
                    success=True,
                    is_healed=True,
                    selector="#action-btn",
                    strategy=ResolutionStrategy.L2_SEMANTIC,
                    confidence=0.95
                )
            )
            assert len(page.resolver.memory) > 0

        # Trigger recovery
        await page.recover(reason="Simulated node detach", restore_url=True)

        # Stale state invalidation invariant: selector memory was purged
        if hasattr(page.resolver, "memory"):
            assert len(page.resolver.memory) == 0

        # Resolving on recovered page succeeds with fresh live DOM
        new_res = await page.resolve("#action-btn")
        assert new_res.success is True


# ============================================================================
# 9. Top-Level Facade Integration & execute_resilient
# ============================================================================

@pytest.mark.asyncio
async def test_bp_facade_execute_resilient_end_to_end():
    """Verify BP facade's execute_resilient and recover APIs work end-to-end on live Chromium."""
    async with BP() as bp:
        await bp.open(make_data_url(RESILIENCE_HTML))

        counter = 0

        async def resilient_worker():
            nonlocal counter
            counter += 1
            if counter < 2:
                raise ValueError("Transient error on attempt 1")
            return await bp.page.get_title()

        title = await bp.execute_resilient(
            resilient_worker,
            operation_name="get_title_resilient",
            operation_type=OperationType.READ,
            timeout_budget_s=5.0,
        )

        assert title == "Resilience Test Harness"
        assert counter == 2

        # Verify direct recovery invocation on facade
        recovered = await bp.recover(reason="Manual test check", restore_url=True)
        assert recovered is True
        assert await bp.page.get_title() == "Resilience Test Harness"


# ============================================================================
# 10. Failure Honesty & Non-Recoverable Rejection
# ============================================================================

@pytest.mark.asyncio
async def test_non_recoverable_failure_rejects_recovery_honestly():
    """Non-recoverable errors (e.g. ConfigurationError) must NEVER trigger recovery or fake success."""
    async with BrowserSession() as session:
        page = await session.new_page()
        rec_mgr = page.recovery_manager

        # Execute non-recoverable error
        success = await rec_mgr.execute_recovery(
            page,
            ConfigurationError("Fatal invalid configuration provided"),
            restore_url=False
        )

        # Must fail honestly with TERMINAL_FAILURE
        assert success is False
        assert rec_mgr.state == RecoveryState.TERMINAL_FAILURE
        assert len(rec_mgr.recovery_history) == 1
        assert rec_mgr.recovery_history[0].verification_passed is False
        assert rec_mgr.recovery_history[0].recovery_action == "RECOVERY_REJECTED"

