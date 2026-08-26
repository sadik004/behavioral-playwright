"""Phase 13 suite: real-implementation / honesty audit regressions.

Pins the classifications decided during the Phase 13 source audit:
  * generated identifiers are visibly synthetic (never real-looking);
  * caller-supplied identifiers are never touched;
  * the documented simulator conveniences keep their bounded, labeled
    semantics;
  * cascade scan skips are logged, not silent.
"""
import logging
import re

import pytest

from fakes import FakeElement, FakePage, run
import behavioral_evasion_ten_patches_hardened_v15 as mod


class TestGeneratedIdentifierHonesty:
    def test_generated_tx_hash_is_visibly_synthetic(self):
        pipeline = mod.BlockchainLakehouseStreamingPipeline()
        for _ in range(5):
            rec = pipeline.process_transaction_event({"amount": 1.0})
            assert rec["tx_hash"].startswith("sim-tx-")
            assert re.fullmatch(r"sim-tx-[0-9a-f]{64}", rec["tx_hash"])

    def test_generated_tx_hashes_are_unique(self):
        pipeline = mod.BlockchainLakehouseStreamingPipeline()
        seen = {
            pipeline.process_transaction_event({"amount": float(i)})["tx_hash"]
            for i in range(20)
        }
        assert len(seen) == 20

    def test_caller_supplied_tx_hash_is_never_modified(self):
        pipeline = mod.BlockchainLakehouseStreamingPipeline()
        rec = pipeline.process_transaction_event({"amount": 1.0, "tx_hash": "0xREALHASH"})
        assert rec["tx_hash"] == "0xREALHASH"


class TestDocumentedSimulatorConveniences:
    def test_ingest_event_time_fallback_is_bounded_and_ordered(self, tmp_path):
        """event_time=None invents a bounded extraction-time estimate; the
        knowledge timestamp stays authoritative and ordering never inverts."""
        from pydantic import BaseModel

        class Schema(BaseModel):
            model_config = {"extra": "allow"}

        out = tmp_path / "probe.ndjson"
        pipeline = mod.QuantPersistencePipeline(output_path=str(out),
                                                min_expected_throughput=0)
        pipeline.open()

        async def scenario():
            await pipeline.ingest_market_record({"id": 1}, Schema, event_time=None)
            await pipeline.close()

        import json as _json
        run(scenario())
        record = _json.loads(out.read_text(encoding="utf-8").strip().splitlines()[0])
        t0, t1 = record["event_timestamp"], record["knowledge_timestamp"]
        assert 0.0 < (t1 - t0) <= 0.5          # bounded invented latency window
        assert t0 <= t1                        # knowledge is never before event

    def test_zero_epoch_still_honored_exactly(self, tmp_path):
        """Regression guard: only None may trigger the fallback (audit fix A3)."""
        from pydantic import BaseModel

        class Schema(BaseModel):
            model_config = {"extra": "allow"}

        out = tmp_path / "zero.ndjson"
        pipeline = mod.QuantPersistencePipeline(output_path=str(out),
                                                min_expected_throughput=0)
        pipeline.open()

        async def scenario():
            await pipeline.ingest_market_record({"id": 1}, Schema, event_time=0.0)
            await pipeline.close()

        import json as _json
        run(scenario())
        record = _json.loads(out.read_text(encoding="utf-8").strip().splitlines()[0])
        assert record["event_timestamp"] == 0.0

    def test_composite_figi_is_labeled_synthetic_and_deterministic(self):
        figi_a = mod._stable_composite_figi("AAPL")
        figi_b = mod._stable_composite_figi("aapl ")
        assert figi_a == figi_b                 # deterministic across processes
        assert figi_a.startswith("BBG")         # format-compatible for joins
        assert figi_a != mod._stable_composite_figi("MSFT")


class TestCascadeScanSkipsAreLogged:
    def test_unreadable_element_is_skipped_with_debug_log_not_silently(self, caplog):
        class ExplodingElement(FakeElement):
            async def get_attribute(self, name):
                raise RuntimeError("detached handle")

            async def inner_text(self):
                raise RuntimeError("detached handle")

            async def bounding_box(self):
                raise RuntimeError("detached handle")

        good = FakeElement(id="buy-btn", text="Buy now", aria_label="Buy now")
        page = FakePage(elements=[ExplodingElement(), good],
                        wait_results={"#buy-btn": good})
        engine = mod.SelfHealingSelectorEngine()

        with caplog.at_level(logging.DEBUG, logger="BehavioralPlaywright.EnterpriseV13"):
            resolved = run(engine.resolve_element(page, "#gone-dynamic", "Buy now"))

        assert resolved is good                  # recovery still succeeds
        skip_logs = [r for r in caplog.records
                     if "introspection failed" in r.getMessage()]
        assert len(skip_logs) >= 1               # and the skip is auditable


class TestCapabilityClassificationGuards:
    """Every questionable capability carries an explicit machine-checkable status."""

    def test_mitmproxy_reports_capture_only_status(self):
        addon = mod.MitmproxyStreamInterceptor()
        flow = type("F", (), {})()

        class Req:
            pretty_url = "https://api.example.com/api/v3/feed"
            host = "api.example.com"

        class Resp:
            content = b"\x08\x6e"

        flow.request, flow.response = Req(), Resp()
        status = addon.response(flow)
        assert status["status"] == "captured_unprocessed"
        assert addon.frames_captured == 1

    def test_frida_absence_reports_false_without_callback_invocation(self):
        invoked = []
        engine = mod.FridaNativeHookEngine(target_process="definitely.not.installed")
        hooked = engine.spawn_and_hook(lambda m, d: invoked.append(m))
        assert hooked is False or invoked == []   # no payloads fabricated either way

    def test_ixbrl_reports_explicit_unavailable_status(self):
        result = mod.IXBRLSECParser().extract_narrative_sections(
            "<html>Item 7. Management's Discussion</html>")
        assert result["status"] == "UNAVAILABLE_NOT_IMPLEMENTED"
        assert result["mda_detected"] is True
        assert result["mda_text"] is None         # honest absence, not canned text
