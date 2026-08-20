"""
Unit tests for Circuit Breaker State Machine, Markov Loop Detector, and NavigationManager.
"""

import pytest

from behavioral_playwright import (
    AutomationConfig,
    CircuitBreaker,
    CircuitState,
    MarkovLoopDetector,
    MockPage,
    NavigationManager,
    NetworkConfig,
    VirtualTestClock,
)


def test_markov_loop_detector() -> None:
    detector = MarkovLoopDetector(history_limit=8, entropy_threshold=1.15)
    for i in range(5):
        detector.record_transition(f"https://target.com/page/{i}")
    assert not detector.is_loop_detected()
    assert detector.calculate_transition_entropy() > 0.8

    for _ in range(6):
        detector.record_transition("https://target.com/page/loop-a")
        detector.record_transition("https://target.com/page/loop-b")

    assert detector.is_loop_detected()


def test_markov_loop_detector_small_window_and_boundaries() -> None:
    detector = MarkovLoopDetector(history_limit=8, entropy_threshold=1.10)

    # 1. Empty state history
    assert detector.calculate_transition_entropy() == 0.0
    assert not detector.is_loop_detected()

    # 2. History < 4 returns False without false-positive loop detection
    detector.record_transition("https://target.com/login")
    assert detector.calculate_transition_entropy() == 0.0
    assert not detector.is_loop_detected()

    detector.record_transition("https://target.com/home")
    assert abs(detector.calculate_transition_entropy() - 1.0) < 1e-6
    assert not detector.is_loop_detected()

    # 3. 4-step stuck loop on same page (entropy = 0.0) -> loop detected
    stuck_detector = MarkovLoopDetector(history_limit=8, entropy_threshold=1.10)
    for _ in range(4):
        stuck_detector.record_transition("https://target.com/error")
    assert stuck_detector.calculate_transition_entropy() == 0.0
    assert stuck_detector.is_loop_detected()

    # 4. 4-step unique pages (entropy = 2.0) -> no loop
    unique_detector = MarkovLoopDetector(history_limit=8, entropy_threshold=1.10)
    for i in range(4):
        unique_detector.record_transition(f"https://target.com/step/{i}")
    assert abs(unique_detector.calculate_transition_entropy() - 2.0) < 1e-6
    assert not unique_detector.is_loop_detected()


@pytest.mark.asyncio
async def test_circuit_breaker_transitions(mock_page: MockPage, test_clock: VirtualTestClock) -> None:
    cb = CircuitBreaker(failure_threshold=2, recovery_cooldown=1.0, clock=test_clock)
    nav_cfg = AutomationConfig(network=NetworkConfig(initial_delay=0.001, backoff_factor=1.0))
    manager = NavigationManager(nav_cfg, cb)

    # 1. Closed state
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True

    # 2. Trigger failures -> OPEN
    mock_page.should_fail_goto = True
    await manager.safe_goto(mock_page, "invalid_protocol_url")
    await manager.safe_goto(mock_page, "invalid_protocol_url")

    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False

    success = await manager.safe_goto(mock_page, "https://example.com")
    assert success is False

    # 3. Advance clock past cooldown -> HALF_OPEN
    await test_clock.sleep(1.2)
    assert cb.allow_request() is True
    assert cb.state == CircuitState.HALF_OPEN

    # 4. Probe success -> CLOSED
    mock_page.should_fail_goto = False
    success = await manager.safe_goto(mock_page, "https://valid-url.com")
    assert success is True
    assert cb.state == CircuitState.CLOSED
