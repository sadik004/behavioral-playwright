"""Phase 10 suite: resilience subsystem (retry / backoff / jitter / circuit breaker).

Deterministic by construction: every test injects a recording sleeper / fake
clock / seeded RNG -- nothing ever really waits.
"""
import asyncio
import random

import pytest

import fakes
from fakes import FakePage, run
import behavioral_evasion_ten_patches_hardened_v15 as mod


class SleepRecorder:
    """Async sleep stand-in that records requested delays instead of waiting."""

    def __init__(self):
        self.delays = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


class FakeClock:
    """Monotonic clock under explicit test control."""

    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def flaky(fail_times: int, exc_factory=lambda n: TimeoutError(f"transient-{n}")):
    """Returns (call_count_holder, op) failing ``fail_times`` times then succeeding."""
    calls = {"n": 0}

    async def op():
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise exc_factory(calls["n"])
        return f"ok-after-{calls['n']}"

    return calls, op


# =====================================================================
# RetryPolicy
# =====================================================================
class TestRetryPolicyBasics:
    def test_first_try_success_consumes_no_retries(self):
        sleeper = SleepRecorder()
        calls, op = flaky(0)
        result = run(mod.RetryPolicy(sleep_fn=sleeper).execute(op))
        assert result == "ok-after-1"
        assert calls["n"] == 1
        assert sleeper.delays == []

    def test_transient_failure_then_success(self):
        sleeper = SleepRecorder()
        calls, op = flaky(1)
        policy = mod.RetryPolicy(max_attempts=3, base_delay=0.5, jitter=False, sleep_fn=sleeper)
        result = run(policy.execute(op))
        assert result == "ok-after-2"
        assert calls["n"] == 2
        assert sleeper.delays == [0.5]

    def test_exhaustion_reraises_the_original_exception_instance(self):
        sleeper = SleepRecorder()
        original = TimeoutError("the-real-failure")
        calls, op = flaky(99, exc_factory=lambda n: original)
        policy = mod.RetryPolicy(max_attempts=3, base_delay=0.0, jitter=False, sleep_fn=sleeper)
        with pytest.raises(TimeoutError) as info:
            run(policy.execute(op, operation_name="fetch"))
        assert info.value is original          # honesty: the real error surfaces
        assert calls["n"] == 3                 # bounded attempts honored
        assert len(sleeper.delays) == 2        # no sleep after the final attempt

    def test_backoff_is_exponential_and_capped(self):
        sleeper = SleepRecorder()
        calls, op = flaky(99)
        policy = mod.RetryPolicy(
            max_attempts=6, base_delay=1.0, multiplier=2.0, max_delay=4.0,
            jitter=False, sleep_fn=sleeper,
        )
        with pytest.raises(TimeoutError):
            run(policy.execute(op))
        assert sleeper.delays == [1.0, 2.0, 4.0, 4.0, 4.0]

    def test_jitter_stays_within_bounds_under_seeded_rng(self):
        sleeper = SleepRecorder()
        calls, op = flaky(3)
        policy = mod.RetryPolicy(
            max_attempts=4, base_delay=2.0, jitter=True, jitter_ratio=0.5,
            sleep_fn=sleeper, rng=random.Random(1234),
        )
        run(policy.execute(op))
        assert len(sleeper.delays) == 3
        for effective, expected_cap in zip(sleeper.delays, [2.0, 4.0, 8.0]):
            assert expected_cap * 0.5 <= effective < expected_cap

    def test_zero_base_delay_permits_immediate_retries(self):
        sleeper = SleepRecorder()
        calls, op = flaky(1)
        policy = mod.RetryPolicy(base_delay=0.0, jitter=False, sleep_fn=sleeper)
        assert run(policy.execute(op)) == "ok-after-2"
        assert sleeper.delays == [0.0]


class TestRetryClassification:
    def test_definitive_error_fails_immediately_without_more_attempts(self):
        calls, op = flaky(99, exc_factory=lambda n: ValueError("permanent"))
        policy = mod.RetryPolicy(max_attempts=5, base_delay=0.0)
        with pytest.raises(ValueError, match="permanent"):
            run(policy.execute(op))
        assert calls["n"] == 1                 # never retried

    def test_connection_errors_are_transient_by_default(self):
        sleeper = SleepRecorder()
        calls, op = flaky(2, exc_factory=lambda n: ConnectionResetError("reset"))
        policy = mod.RetryPolicy(max_attempts=3, base_delay=0.0, jitter=False, sleep_fn=sleeper)
        assert run(policy.execute(op)) == "ok-after-3"

    def test_nonretryable_marker_overrides_default_transient_family(self):
        calls, op = flaky(
            99, exc_factory=lambda n: mod.NonRetryableError("stop", wrapped=TimeoutError("x"))
        )
        policy = mod.RetryPolicy(max_attempts=4, base_delay=0.0)
        with pytest.raises(mod.NonRetryableError):
            run(policy.execute(op))
        assert calls["n"] == 1

    def test_custom_predicate_can_expand_retryability(self):
        calls, op = flaky(1, exc_factory=lambda n: ValueError("custom-transient"))
        policy = mod.RetryPolicy(retryable=lambda e: isinstance(e, ValueError), base_delay=0.0)
        assert run(policy.execute(op)) == "ok-after-2"

    def test_custom_predicate_can_narrow_retryability(self):
        calls, op = flaky(1)  # TimeoutError would be transient by default
        policy = mod.RetryPolicy(retryable=lambda e: False, base_delay=0.0)
        with pytest.raises(TimeoutError):
            run(policy.execute(op))
        assert calls["n"] == 1

    def test_predicate_crash_is_treated_as_non_retryable_not_fatal_to_flow(self):
        def bad_predicate(exc):
            raise RuntimeError("predicate bug")

        calls, op = flaky(1)
        policy = mod.RetryPolicy(retryable=bad_predicate, base_delay=0.0)
        with pytest.raises(TimeoutError):      # the ORIGINAL error surfaces
            run(policy.execute(op))
        assert calls["n"] == 1


class TestRetryTimeoutAndCancellation:
    def test_per_attempt_timeout_is_classified_transient_and_retried(self):
        sleeper = SleepRecorder()
        calls = {"n": 0}

        async def hanging_then_ok():
            calls["n"] += 1
            if calls["n"] == 1:
                await asyncio.sleep(5.0)       # will be cut off by wait_for
                return "unreachable"
            return "recovered"

        policy = mod.RetryPolicy(
            max_attempts=2, per_attempt_timeout=0.01, base_delay=0.0,
            jitter=False, sleep_fn=sleeper,
        )
        assert run(policy.execute(hanging_then_ok)) == "recovered"
        assert calls["n"] == 2

    def test_cancellederror_inside_operation_is_never_swallowed_or_retried(self):
        calls, op = flaky(99, exc_factory=lambda n: asyncio.CancelledError())
        policy = mod.RetryPolicy(max_attempts=3, base_delay=0.0)
        with pytest.raises(asyncio.CancelledError):
            run(policy.execute(op))
        assert calls["n"] == 1                 # cancellation propagates immediately

    def test_cancellation_while_backing_off_aborts_the_loop(self):
        started = asyncio.Event()

        async def slow_sleep(delay):
            started.set()
            await asyncio.sleep(30)

        calls, op = flaky(99)

        async def scenario():
            policy = mod.RetryPolicy(max_attempts=3, base_delay=1.0, sleep_fn=slow_sleep)
            task = asyncio.ensure_future(policy.execute(op))
            await asyncio.wait_for(started.wait(), timeout=1.0)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                return "cancelled-cleanly"
            return "not-cancelled"

        assert run(scenario()) == "cancelled-cleanly"


class TestRetryObservabilityAndValidation:
    def test_observability_events_describe_every_decision(self):
        events = []
        sleeper = SleepRecorder()
        calls, op = flaky(2)
        policy = mod.RetryPolicy(
            max_attempts=3, base_delay=1.0, jitter=False,
            sleep_fn=sleeper, on_event=events.append,
        )
        run(policy.execute(op, operation_name="probe"))
        kinds = [e["event"] for e in events]
        assert kinds == ["retry", "retry"]
        assert events[0]["operation"] == "probe"
        assert events[0]["attempt"] == 1
        assert events[0]["delay"] == 1.0
        assert "transient-1" in events[0]["error"]

        # Exhaustion emits the terminal event before re-raising.
        events.clear()
        calls2, op2 = flaky(99)
        policy2 = mod.RetryPolicy(
            max_attempts=2, base_delay=0.0, sleep_fn=sleeper, on_event=events.append
        )
        with pytest.raises(TimeoutError):
            run(policy2.execute(op2, operation_name="probe"))
        assert [e["event"] for e in events] == ["retry", "retries_exhausted"]
        assert events[-1]["attempts"] == 2

    def test_hook_failure_never_breaks_the_operation(self):
        sleeper = SleepRecorder()
        calls, op = flaky(1)

        def bad_hook(event):
            raise RuntimeError("hook exploded")

        policy = mod.RetryPolicy(
            max_attempts=2, base_delay=0.0, sleep_fn=sleeper, on_event=bad_hook
        )
        assert run(policy.execute(op)) == "ok-after-2"

    @pytest.mark.parametrize("bad_kwargs", [
        {"max_attempts": 0},
        {"base_delay": -0.1},
        {"max_delay": -1},
        {"multiplier": 0.5},
        {"jitter_ratio": 1.5},
        {"per_attempt_timeout": 0},
    ])
    def test_invalid_configuration_rejected_eagerly(self, bad_kwargs):
        with pytest.raises(ValueError):
            mod.RetryPolicy(**bad_kwargs)

    def test_operation_must_be_callable(self):
        policy = mod.RetryPolicy()
        with pytest.raises(TypeError):
            run(policy.execute("not-callable"))

    def test_decorator_style_usage_via_lambda_free_closure(self):
        sleeper = SleepRecorder()

        async def fetch():
            return 42

        policy = mod.RetryPolicy(sleep_fn=sleeper)
        assert run(policy.execute(fetch)) == 42


# =====================================================================
# CircuitBreaker
# =====================================================================
class TestCircuitBreakerFSM:
    def test_starts_closed(self):
        cb = mod.CircuitBreaker()
        assert cb.state == mod.CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_opens_after_consecutive_failure_threshold_and_fast_fails(self):
        clock = FakeClock()
        cb = mod.CircuitBreaker(failure_threshold=3, recovery_timeout=60.0, clock_fn=clock)
        calls = {"n": 0}

        async def failing():
            calls["n"] += 1
            raise TimeoutError("boom")

        for _ in range(3):
            with pytest.raises(TimeoutError):
                run(cb.execute(failing))
        assert cb.state == mod.CircuitState.OPEN

        # While OPEN the operation must NOT be executed at all.
        with pytest.raises(mod.CircuitBreakerOpenError, match="OPEN"):
            run(cb.execute(failing))
        assert calls["n"] == 3

    def test_success_while_closed_resets_the_consecutive_counter(self):
        cb = mod.CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

        async def fail():
            raise TimeoutError("x")

        async def ok():
            return 1

        for _ in range(2):
            with pytest.raises(TimeoutError):
                run(cb.execute(fail))
        assert cb.failure_count == 2
        run(cb.execute(ok))
        assert cb.failure_count == 0           # consecutive, not cumulative
        assert cb.state == mod.CircuitState.CLOSED

    def test_recovery_timeout_promotes_open_to_half_open(self):
        clock = FakeClock()
        cb = mod.CircuitBreaker(failure_threshold=1, recovery_timeout=10.0, clock_fn=clock)

        async def fail():
            raise TimeoutError("trip")

        with pytest.raises(TimeoutError):
            run(cb.execute(fail))
        assert cb.state == mod.CircuitState.OPEN

        clock.advance(9.999)
        assert cb.state == mod.CircuitState.OPEN   # cooldown not elapsed
        clock.advance(0.001)
        assert cb.state == mod.CircuitState.HALF_OPEN

    def test_half_open_requires_consecutive_probing_successes_to_close(self):
        clock = FakeClock()
        cb = mod.CircuitBreaker(
            failure_threshold=1, recovery_timeout=0.0, half_open_max_successes=2,
            clock_fn=clock,
        )

        async def fail():
            raise TimeoutError("trip")

        async def ok():
            return "fine"

        with pytest.raises(TimeoutError):
            run(cb.execute(fail))
        assert cb.state == mod.CircuitState.HALF_OPEN  # zero cooldown

        run(cb.execute(ok))
        assert cb.state == mod.CircuitState.HALF_OPEN  # one probe is not enough
        run(cb.execute(ok))
        assert cb.state == mod.CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_any_half_open_failure_retrips_open_immediately(self):
        clock = FakeClock()
        cb = mod.CircuitBreaker(failure_threshold=1, recovery_timeout=100.0, clock_fn=clock)

        async def fail():
            raise TimeoutError("x")

        with pytest.raises(TimeoutError):
            run(cb.execute(fail))
        clock.advance(100.0)                   # cooldown elapses -> HALF_OPEN
        assert cb.state == mod.CircuitState.HALF_OPEN
        with pytest.raises(TimeoutError):
            run(cb.execute(fail))
        assert cb.state == mod.CircuitState.OPEN   # re-tripped despite long timeout
        # And it stays OPEN while the new cooldown runs.
        clock.advance(99.999)
        assert cb.state == mod.CircuitState.OPEN

    def test_reset_forces_closed(self):
        cb = mod.CircuitBreaker(failure_threshold=1, recovery_timeout=100.0)

        async def fail():
            raise TimeoutError("x")

        with pytest.raises(TimeoutError):
            run(cb.execute(fail))
        assert cb.state == mod.CircuitState.OPEN
        cb.reset()
        assert cb.state == mod.CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_transition_events_are_emitted(self):
        events = []
        cb = mod.CircuitBreaker(
            failure_threshold=1, recovery_timeout=0.0, on_event=events.append
        )

        async def fail():
            raise TimeoutError("x")

        with pytest.raises(TimeoutError):
            run(cb.execute(fail))
        transitions = [e for e in events if e["event"] == "circuit_transition"]
        assert transitions == [{"event": "circuit_transition", "from": "CLOSED", "to": "OPEN"}]
        # Lazy HALF_OPEN promotion also reports.
        assert cb.state == mod.CircuitState.HALF_OPEN
        transitions2 = [e for e in events if e["event"] == "circuit_transition"]
        assert transitions2[-1] == {"event": "circuit_transition", "from": "OPEN", "to": "HALF_OPEN"}

    def test_hook_failure_does_not_corrupt_state_machine(self):
        def bad_hook(event):
            raise RuntimeError("hook down")

        cb = mod.CircuitBreaker(failure_threshold=1, recovery_timeout=0.0, on_event=bad_hook)

        async def fail():
            raise TimeoutError("x")

        with pytest.raises(TimeoutError):
            run(cb.execute(fail))
        assert cb.state == mod.CircuitState.HALF_OPEN

    @pytest.mark.parametrize("bad_kwargs", [
        {"failure_threshold": 0},
        {"recovery_timeout": -1},
        {"half_open_max_successes": 0},
    ])
    def test_invalid_configuration_rejected_eagerly(self, bad_kwargs):
        with pytest.raises(ValueError):
            mod.CircuitBreaker(**bad_kwargs)


# =====================================================================
# Composition + facade wiring
# =====================================================================
class TestCompositionAndFacadeWiring:
    def test_breaker_outer_policy_inner_composition(self):
        clock = FakeClock()
        breaker = mod.CircuitBreaker(failure_threshold=2, recovery_timeout=100.0, clock_fn=clock)
        policy = mod.RetryPolicy(max_attempts=2, base_delay=0.0, jitter=False)

        calls = {"n": 0}

        async def failing():
            calls["n"] += 1
            raise TimeoutError("always")

        async def scenario():
            for _ in range(2):
                with pytest.raises(TimeoutError):
                    # outer breaker wraps inner retrying policy
                    await breaker.execute(
                        lambda: policy.execute(failing, operation_name="nav")
                    )

        run(scenario())
        # Each logical operation consumed BOTH policy attempts...
        assert calls["n"] == 4
        # ...and the breaker tripped afterwards.
        assert breaker.state == mod.CircuitState.OPEN
        with pytest.raises(mod.CircuitBreakerOpenError):
            run(breaker.execute(lambda: policy.execute(failing)))

    def make_bp(self, tmp_path, **kw):
        return mod.BehavioralPlaywright(
            output_path=str(tmp_path / "bp.ndjson"),
            heal_memory_path=str(tmp_path / "heal.json"),
            **kw,
        )

    def test_facade_defaults_keep_behavior_identical(self, tmp_path):
        bp = self.make_bp(tmp_path)
        assert bp.retry_policy is None
        assert bp.circuit_breaker is None
        el = fakes.FakeElement()
        page = FakePage(wait_results={"#btn": el})
        resolved = run(bp.solve("#btn", page=page))
        assert resolved is el
        assert bp.selector_engine.last_match_tier == "PRIMARY"

    def test_facade_solve_retries_transient_engine_failures(self, tmp_path):
        bp = self.make_bp(tmp_path)
        events = []
        bp.retry_policy = mod.RetryPolicy(
            max_attempts=3, base_delay=0.0, jitter=False, on_event=events.append
        )
        real_resolve = bp.selector_engine.resolve_element
        calls = {"n": 0}
        el = fakes.FakeElement()

        async def flaky_resolve(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise TimeoutError("page froze")
            return await real_resolve(*args, **kwargs)

        bp.selector_engine.resolve_element = flaky_resolve
        page = FakePage(wait_results={"#btn": el})
        resolved = run(bp.solve("#btn", page=page))
        assert resolved is el
        assert calls["n"] == 2
        assert [e["event"] for e in events] == ["retry"]

    def test_facade_solve_never_retries_a_definitive_negative(self, tmp_path):
        bp = self.make_bp(tmp_path)
        bp.retry_policy = mod.RetryPolicy(max_attempts=5, base_delay=0.0)
        calls = {"n": 0}

        async def negative_resolve(*args, **kwargs):
            calls["n"] += 1
            return None

        bp.selector_engine.resolve_element = negative_resolve
        page = FakePage()
        with pytest.raises(mod.ElementResolutionError):
            run(bp.solve("#nothing", page=page))
        assert calls["n"] == 1                 # None == definite answer, not retried

    def test_facade_solve_open_breaker_rejects_before_touching_the_page(self, tmp_path):
        bp = self.make_bp(tmp_path)
        breaker = mod.CircuitBreaker(failure_threshold=1, recovery_timeout=999.0)
        bp.circuit_breaker = breaker

        async def fail_once(*args, **kwargs):
            raise TimeoutError("trip the breaker")

        bp.selector_engine.resolve_element = fail_once
        with pytest.raises(TimeoutError):
            run(bp.solve("#x", page=FakePage()))
        assert breaker.state == mod.CircuitState.OPEN

        calls = {"n": 0}

        async def must_not_run(*args, **kwargs):
            calls["n"] += 1
            return None

        bp.selector_engine.resolve_element = must_not_run
        with pytest.raises(mod.CircuitBreakerOpenError):
            run(bp.solve("#x", page=FakePage()))
        assert calls["n"] == 0                 # fast-failed, page untouched

    def test_collect_writes_are_never_protected_by_the_breaker(self, tmp_path):
        """Safety contract: persistence writes stay outside the retry/breaker stack."""
        bp = self.make_bp(tmp_path, min_expected_throughput=1)
        breaker = mod.CircuitBreaker(failure_threshold=1, recovery_timeout=999.0)
        breaker.record_failure()               # force OPEN without touching ops
        assert breaker.state == mod.CircuitState.OPEN
        bp.circuit_breaker = breaker
        status = run(bp.collect({"id": 1, "company": "Apple", "rank": 1.0},
                                fakes.PermissiveSchema))
        assert status["status"] == "ingested"  # writes bypass the breaker entirely
