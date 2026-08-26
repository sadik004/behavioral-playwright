"""Phase 12 suite: historical capability reconciliation.

Restores (and pins) the capabilities judged genuinely valuable from the
historical generations; documents-by-test what was deliberately NOT restored.
"""
import sqlite3

import pytest

import fakes
from fakes import FakePage, run
import behavioral_evasion_ten_patches_hardened_v15 as mod


class TestObservabilitySQLiteSink:
    def test_record_and_recent_roundtrip(self, tmp_path):
        with mod.ObservabilitySQLiteSink(str(tmp_path / "obs.db")) as sink:
            sink.record({"event": "retry", "attempt": 1})
            sink.record({"event": "circuit_transition", "to": "OPEN"})
            events = sink.recent(10)
        assert len(events) == 2
        # newest first
        assert events[0]["event"] == "circuit_transition"
        assert events[0]["to"] == "OPEN"
        assert events[-1]["attempt"] == 1
        assert events[-1]["_recorded_at"] > 0

    def test_count_total_and_by_kind(self, tmp_path):
        with mod.ObservabilitySQLiteSink(str(tmp_path / "obs.db")) as sink:
            for i in range(3):
                sink.record({"event": "retry", "attempt": i})
            sink.record({"event": "retries_exhausted"})
            assert sink.count() == 4
            assert sink.count("retry") == 3
            assert sink.count("retries_exhausted") == 1

    def test_schema_created_on_demand_and_persists_across_instances(self, tmp_path):
        db = str(tmp_path / "obs.db")
        sink_a = mod.ObservabilitySQLiteSink(db)
        sink_a.record({"event": "retry"})
        sink_a.close()
        sink_b = mod.ObservabilitySQLiteSink(db)   # fresh connection, same file
        assert sink_b.count() == 1
        sink_b.close()

    def test_invalid_events_raise_loudly(self, tmp_path):
        with mod.ObservabilitySQLiteSink(str(tmp_path / "obs.db")) as sink:
            with pytest.raises(ValueError, match="dict"):
                sink.record("not-a-dict")
            with pytest.raises(ValueError, match="event"):
                sink.record({"no_kind_key": True})

    def test_non_json_payload_values_survive_via_repr_fallback(self, tmp_path):
        with mod.ObservabilitySQLiteSink(str(tmp_path / "obs.db")) as sink:
            sink.record({"event": "custom", "conn": object()})
            back = sink.recent(1)[0]
            assert isinstance(back["conn"], str)   # repr'd, never silently dropped

    def test_limit_validation(self, tmp_path):
        with mod.ObservabilitySQLiteSink(str(tmp_path / "obs.db")) as sink:
            with pytest.raises(ValueError):
                sink.recent(-1)

    def test_close_is_idempotent(self, tmp_path):
        sink = mod.ObservabilitySQLiteSink(str(tmp_path / "obs.db"))
        sink.close()
        sink.close()                                # no raise

    def test_wiring_to_resilience_hooks_end_to_end(self, tmp_path):
        """The documented integration: point on_event at sink.record."""
        db = str(tmp_path / "runs.db")
        sink = mod.ObservabilitySQLiteSink(db)

        calls = {"n": 0}

        async def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise TimeoutError("transient")
            return "done"

        policy = mod.RetryPolicy(
            max_attempts=5, base_delay=0.0, jitter=False, on_event=sink.record
        )
        try:
            result = run(policy.execute(flaky, operation_name="probe"))
            breaker_events_before = sink.count("circuit_transition")
            assert result == "done"
            assert sink.count("retry") == 2
            assert breaker_events_before == 0

            cb = mod.CircuitBreaker(failure_threshold=1, recovery_timeout=0.0,
                                    on_event=sink.record)

            async def fail():
                raise TimeoutError("trip")

            with pytest.raises(TimeoutError):
                run(cb.execute(fail))
            assert sink.count("circuit_transition") == 1
        finally:
            sink.close()

        # Data is durable on disk in a real SQLite database.
        conn = sqlite3.connect(db)
        try:
            rows = conn.execute("SELECT kind FROM events").fetchall()
        finally:
            conn.close()
        kinds = sorted(r[0] for r in rows)
        assert kinds == ["circuit_transition", "retry", "retry"]


# =====================================================================
# Reconciliation decisions pinned by tests (restored vs intentionally lost)
# =====================================================================
class TestReconciliationDecisions:
    def test_restored_resilience_surface_exists(self):
        for name in ("RetryPolicy", "CircuitBreaker", "CircuitState",
                     "CircuitBreakerOpenError", "NonRetryableError",
                     "is_retryable_exception", "ObservabilitySQLiteSink"):
            assert hasattr(mod, name), name

    def test_restored_navigation_and_typing_surface_exists(self):
        bp_methods = ("navigate", "close", "__aenter__", "__aexit__")
        for name in bp_methods:
            assert hasattr(mod.BehavioralPlaywright, name), name
        engine = mod.BiomechanicalInteractionEngine()
        for name in ("type_like_human", "move_and_click", "smooth_scroll"):
            assert hasattr(engine, name), name
        for name in ("NavigationError", "NavigationLoopError"):
            assert hasattr(mod, name), name

    def test_preserved_self_healing_stack_untouched(self):
        engine = mod.SelfHealingSelectorEngine()
        assert [engine.TIER_CONFIDENCE_L2, engine.TIER_CONFIDENCE_L3,
                engine.TIER_CONFIDENCE_L4] == [0.90, 0.85, 0.25]
        memory = mod.SelectorHealMemory()
        assert callable(memory.remember) and callable(memory.lookup)
        assert callable(engine._try_verified_write_back)

    def test_deliberately_absent_capabilities_are_still_absent(self):
        """Guard against silent reintroduction of Gen1/Gen2 mock theater."""
        for forbidden in ("MockBrowserProvider", "ExploitPoCExporter",
                          "EbpfTcpSpoofBridge"):
            assert not hasattr(mod, forbidden), forbidden
        engine = mod.BehavioralPlaywright.__dict__
        for forbidden_verb in ("crawl", "search", "map", "handoff", "boot",
                               "goto", "click", "type", "fill", "scroll",
                               "screenshot", "extract", "verify"):
            assert forbidden_verb not in engine, forbidden_verb

    def test_quarantined_capabilities_remain_honestly_unavailable(self):
        with pytest.raises(NotImplementedError):
            mod.EDGARBalanceSheetParser().parse_balance_sheet("{}")
        with pytest.raises(NotImplementedError):
            mod.SECForm4InsiderTracker().parse_insider_transactions("<x/>")
        with pytest.raises(NotImplementedError):
            mod.PyarmorCPythonUnpacker().inject_pyeval_hooks()
        ole2 = mod.BinaryOLE2REDecoder().parse_ole2_container(b"\x00" * 8)
        assert ole2["status"] == "UNAVAILABLE_NOT_IMPLEMENTED"
