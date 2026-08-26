"""Full-codebase-audit regression suite (AUDIT FIXES A1-A3).

Additive only -- existing suites are untouched. Each test pins one
correctness fix produced by the 2026-08 full codebase audit:

  A1  the MEMORY self-healing tier honors ``confidence_threshold``
      (a low-confidence remembered entry may no longer bypass the gate);
  A2  the MEMORY fast-path verifies ``expected_content`` before trusting
      a remembered selector (mismatch => stale => full cascade);
  A3  ``event_time=0.0`` is a valid epoch and is honored exactly instead
      of being silently replaced by an invented timestamp.
"""
import pytest

import fakes
from fakes import FakeElement, FakePage, run
import behavioral_evasion_ten_patches_hardened_v15 as mod
from pydantic import BaseModel


def button(id="", cls="", text="", aria_label="", title="", tag="button", box=None):
    return FakeElement(id=id, cls=cls, text=text, aria_label=aria_label,
                       title=title, tag=tag, box=box)


class AuditMarketData(BaseModel):
    id: int
    company: str
    rank: float
    event_timestamp: float
    knowledge_timestamp: float
    isin: str
    cusip: str
    figi: str
    ticker: str


# =====================================================================
# A1: MEMORY tier is gated by confidence_threshold
# =====================================================================
class TestMemoryTierThresholdGate:
    def test_low_confidence_memory_entry_cannot_bypass_threshold(self):
        """A remembered entry with confidence < threshold must NOT be
        returned via the fast-path even though its selector still resolves."""
        engine = mod.SelfHealingSelectorEngine()  # default threshold 0.80
        mem = mod.SelectorHealMemory()
        mem.remember("buy-button", "#remembered", tier="L3", confidence=0.50)

        healed = button()
        # The remembered selector WOULD resolve -- the gate must refuse it.
        page = FakePage(wait_results={"#remembered": healed})
        result = run(engine.resolve_element(
            page, "#original-selector", logical_name="buy-button",
            heal_memory=mem))

        assert result is None                      # fell through; nothing else matched
        assert engine.last_match_tier is None      # never accepted below threshold

    def test_low_confidence_memory_entry_falls_through_to_working_primary(self):
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()
        mem.remember("buy-button", "#stale-low-conf", tier="L3", confidence=0.40)

        primary_el = button()
        page = FakePage(wait_results={
            "#stale-low-conf": button(),           # old entry still resolves...
            "#current-stable": primary_el,         # ...but PRIMARY wins instead
        })
        result = run(engine.resolve_element(
            page, "#current-stable", logical_name="buy-button",
            heal_memory=mem))

        assert result is primary_el
        assert engine.last_match_tier == "PRIMARY"
        assert mem.lookup("buy-button") == "#current-stable"   # entry refreshed

    def test_memory_entry_at_exactly_the_threshold_is_accepted(self):
        engine = mod.SelfHealingSelectorEngine(confidence_threshold=0.85)
        mem = mod.SelectorHealMemory()
        mem.remember("buy-button", "#remembered", tier="L2", confidence=0.85)

        healed = button()
        page = FakePage(wait_results={"#remembered": healed})
        result = run(engine.resolve_element(
            page, "#original-selector", logical_name="buy-button",
            heal_memory=mem))

        assert result is healed                    # >= threshold boundary holds
        assert engine.last_match_tier == "MEMORY"
        assert engine.last_match_confidence == pytest.approx(0.85)

    def test_facade_propagates_gate_to_memory_hits(self, tmp_path):
        """End-to-end: solve() refuses a below-threshold memory fast-path."""
        async def scenario():
            bp = mod.BehavioralPlaywright(
                output_path=str(tmp_path / "bp.ndjson"),
                heal_memory_path=str(tmp_path / "heal.json"),
                confidence_threshold=0.95,
            )
            bp.heal_memory.remember("buy-btn", "#remembered", tier="L1",
                                    confidence=0.70)
            page = FakePage(wait_results={"#remembered": FakeElement()})
            try:
                await bp.solve("#anything-else", logical_name="buy-btn", page=page)
            except mod.ElementResolutionError:
                return "raised"
            return "returned"

        assert run(scenario()) == "raised"


# =====================================================================
# A2: MEMORY fast-path verifies expected_content
# =====================================================================
class TestMemoryContentVerification:
    def test_matching_expected_content_still_fast_paths(self):
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()
        mem.remember("buy-button", "#remembered")

        healed = button(text="Submit order")
        page = FakePage(wait_results={"#remembered": healed})
        result = run(engine.resolve_element(
            page, "#original-selector", expected_content="submit order",
            logical_name="buy-button", heal_memory=mem))

        assert result is healed
        assert engine.last_match_tier == "MEMORY"

    def test_mismatching_expected_content_falls_through_to_cascade(self):
        """The page changed under the remembered selector: the old selector
        now resolves a DIFFERENT element. It must not be trusted."""
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()
        mem.remember("buy-button", "#remembered")

        wrong_element = button(text="Totally unrelated label")
        right_element = button(aria_label="Checkout order")
        page = FakePage(elements=[wrong_element, right_element])
        page.wait_results["#remembered"] = wrong_element   # resolves, but wrong

        result = run(engine.resolve_element(
            page, "#original-selector", expected_content="checkout",
            logical_name="buy-button", heal_memory=mem))

        assert result is right_element
        assert engine.last_match_tier == "L2"      # recovered via cascade
        assert engine.last_match_confidence == pytest.approx(0.90)

    def test_unverifiable_element_keeps_memory_hit(self):
        """If content cannot be inspected, the memory hit stands rather than
        inventing a verification failure."""
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()
        mem.remember("buy-button", "#remembered")

        class NoTextElement(FakeElement):
            async def inner_text(self):
                raise RuntimeError("inner_text unavailable on this handle")

        healed = NoTextElement()
        page = FakePage(wait_results={"#remembered": healed})
        result = run(engine.resolve_element(
            page, "#original-selector", expected_content="anything",
            logical_name="buy-button", heal_memory=mem))

        assert result is healed
        assert engine.last_match_tier == "MEMORY"


# =====================================================================
# A3: event_time=0.0 honored exactly
# =====================================================================
class TestEventTimeZeroHonored:
    def test_zero_epoch_is_not_replaced_by_invented_timestamp(self, tmp_path):
        async def scenario():
            out = str(tmp_path / "zero.ndjson")
            pipeline = mod.QuantPersistencePipeline(output_path=out,
                                                    min_expected_throughput=0)
            await pipeline.ingest_market_record(
                {"id": 1, "company": "Apple", "rank": 1.0},
                AuditMarketData,
                event_time=0.0,
            )
            await pipeline.close()
            return out

        import json as _json
        out = run(scenario())
        record = _json.loads(open(out, encoding="utf-8").read().splitlines()[0])
        assert record["event_timestamp"] == 0.0
        assert record["knowledge_timestamp"] > 0.0

    def test_none_still_gets_extraction_time_fallback(self, tmp_path):
        async def scenario():
            out = str(tmp_path / "none.ndjson")
            pipeline = mod.QuantPersistencePipeline(output_path=out,
                                                    min_expected_throughput=0)
            await pipeline.ingest_market_record(
                {"id": 2, "company": "Microsoft", "rank": 2.0},
                AuditMarketData,
                event_time=None,
            )
            await pipeline.close()
            return out

        import json as _json
        out = run(scenario())
        record = _json.loads(open(out, encoding="utf-8").read().splitlines()[0])
        # Fallback: extraction time minus bounded latency jitter (< 1s).
        assert record["knowledge_timestamp"] - 1.0 <= record["event_timestamp"] \
            <= record["knowledge_timestamp"]

    def test_collect_passes_zero_epoch_through_facade(self, tmp_path):
        import json as _json

        async def scenario():
            bp = mod.BehavioralPlaywright(
                output_path=str(tmp_path / "bp.ndjson"),
                min_expected_throughput=1,
            )
            status = await bp.collect(
                {"id": 3, "company": "Tesla", "rank": 3.0},
                AuditMarketData,
                event_time=0.0,
            )
            await bp.close()
            return status

        run(scenario())
        lines = (tmp_path / "bp.ndjson").read_text(encoding="utf-8").splitlines()
        record = _json.loads(lines[0])
        assert record["event_timestamp"] == 0.0
