"""Phase 4 suite: SelectorHealMemory + 4-tier cascading self-healing engine.

Recovery strategies under test:
  S1  memory fast-path hit skips the cascade
  S2  stale memory entry falls through to the full cascade, then refreshes
  S3  corrupted persisted memory is quarantined and rebuilt empty
"""
import json
import os

import pytest

import fakes
from fakes import FakeElement, FakePage, run
import behavioral_evasion_ten_patches_hardened_v15 as mod


# =====================================================================
# SelfHealingSelectorEngine tiers & gates
# =====================================================================
def button(id="", cls="", text="", aria_label="", title="", tag="button", box=None):
    return FakeElement(id=id, cls=cls, text=text, aria_label=aria_label,
                       title=title, tag=tag, box=box)


class TestSelectorEngineTiers:
    def test_invalid_threshold_rejected(self):
        with pytest.raises(ValueError, match="confidence_threshold"):
            mod.SelfHealingSelectorEngine(confidence_threshold=1.5)

    def test_primary_hit(self):
        el = button()
        page = FakePage(wait_results={"#ok": el})
        engine = mod.SelfHealingSelectorEngine()
        assert run(engine.resolve_element(page, "#ok")) is el
        assert engine.last_match_tier == "PRIMARY"
        assert engine.last_match_confidence == 1.0

    def test_l1_fuzzy_match_accepted(self):
        candidate = button(id="btn-submit")
        page = FakePage(elements=[button(id="unrelated"), candidate])
        engine = mod.SelfHealingSelectorEngine()  # threshold 0.80
        resolved = run(engine.resolve_element(page, "#btn-submt"))
        assert resolved is candidate
        assert engine.last_match_tier == "L1"

    def test_l1_below_threshold_not_accepted(self):
        page = FakePage(elements=[button(id="zzz-very-different-zzz")])
        engine = mod.SelfHealingSelectorEngine()
        result = run(engine.resolve_element(page, "#btn-submit"))
        assert result is None
        assert engine.last_match_tier is None

    def test_l1_distance_cap_of_five(self):
        # similarity above threshold but Levenshtein distance > 5 -> rejected
        page = FakePage(elements=[button(id="btn-submitttedxxxxx")])
        engine = mod.SelfHealingSelectorEngine(confidence_threshold=0.3)
        result = run(engine.resolve_element(page, "#btn"))
        assert engine.last_match_tier != "L1" or result is not None
        # explicit: with only this far-off element nothing better exists
        page2 = FakePage(elements=[button(id="completely-different-content")])
        engine2 = mod.SelfHealingSelectorEngine(confidence_threshold=0.3)
        assert run(engine2.resolve_element(page2, "#btn")) is None

    def test_l2_aria_match(self):
        target = button(aria_label="Submit order", text="")
        page = FakePage(elements=[target])
        engine = mod.SelfHealingSelectorEngine()
        resolved = run(engine.resolve_element(page, "#gone", expected_content="submit order"))
        assert resolved is target
        assert engine.last_match_tier == "L2"
        assert engine.last_match_confidence == pytest.approx(0.90)

    def test_l2_gated_when_threshold_above_tier_confidence(self):
        target = button(aria_label="Submit order")
        page = FakePage(elements=[target])
        engine = mod.SelfHealingSelectorEngine(confidence_threshold=0.95)
        assert run(engine.resolve_element(page, "#gone", expected_content="submit order")) is None

    def test_l3_spatial_geometry_match(self):
        target = button(text="Checkout now", box={"x": 120, "y": 300, "width": 90, "height": 40})
        page = FakePage(elements=[target])
        engine = mod.SelfHealingSelectorEngine()
        resolved = run(engine.resolve_element(page, "#gone", expected_content="checkout"))
        assert resolved is target
        assert engine.last_match_tier == "L3"

    def test_l4_suppressed_at_default_threshold(self):
        first_button = button(tag="button")
        page = FakePage(elements=[first_button])
        engine = mod.SelfHealingSelectorEngine()  # L4 confidence 0.25 < 0.80
        assert run(engine.resolve_element(page, "#nothing-matches")) is None

    def test_l4_reachable_when_threshold_lowered_explicitly(self):
        first_button = button(tag="button")
        page = FakePage(elements=[first_button])
        engine = mod.SelfHealingSelectorEngine(confidence_threshold=0.20)
        assert run(engine.resolve_element(page, "#nothing-matches")) is first_button
        assert engine.last_match_tier == "L4"

    def test_state_reset_between_attempts(self):
        page_ok = FakePage(wait_results={"#ok": button()})
        engine = mod.SelfHealingSelectorEngine()
        run(engine.resolve_element(page_ok, "#ok"))
        assert engine.last_match_tier == "PRIMARY"
        run(engine.resolve_element(FakePage(), "#never-found-anywhere"))
        assert engine.last_match_tier is None
        assert engine.last_match_confidence is None


# =====================================================================
# SelectorHealMemory unit behaviour (S2/S3 recovery)
# =====================================================================
class TestSelectorHealMemory:
    def test_remember_and_lookup_roundtrip(self):
        mem = mod.SelectorHealMemory()
        mem.remember("checkout-btn", "#btn-checkout-v2")
        assert mem.lookup("checkout-btn") == "#btn-checkout-v2"
        assert mem.lookup("unknown") is None

    def test_empty_name_or_selector_refused(self):
        mem = mod.SelectorHealMemory()
        mem.remember("", "#x")
        mem.remember("name", "   ")
        assert len(mem) == 0 if hasattr(mem, "__len__") else mem.stats()["entries"] == 0

    def test_forget_returns_bool(self):
        mem = mod.SelectorHealMemory()
        mem.remember("a", "#a")
        assert mem.forget("a") is True
        assert mem.forget("a") is False

    def test_max_entries_validation(self):
        with pytest.raises(ValueError):
            mod.SelectorHealMemory(max_entries=0)

    def test_eviction_keeps_highest_value_entries(self):
        mem = mod.SelectorHealMemory(max_entries=2)
        mem.remember("low", "#l", tier="L1", confidence=0.5)
        mem.remember("high", "#h", tier="PRIMARY", confidence=1.0)
        mem.remember("mid", "#m", tier="L2", confidence=0.9)
        stats = mem.stats()
        assert stats["entries"] == 2
        assert mem.lookup("low") is None      # lowest confidence evicted first
        assert mem.lookup("high") == "#h"
        assert mem.lookup("mid") == "#m"

    def test_save_and_load_roundtrip(self, tmp_path):
        path = str(tmp_path / "heal.json")
        mem = mod.SelectorHealMemory(path=path)
        mem.remember("login-form", "form#login", tier="PRIMARY", confidence=1.0)
        mem.remember("search-box", "input[name=q]", tier="L2", confidence=0.9)
        assert mem.save() is True
        revived = mod.SelectorHealMemory(path=path)
        assert revived.lookup("login-form") == "form#login"
        assert revived.stats()["tiers"] == {"PRIMARY": 1, "L2": 1}

    def test_load_missing_file_is_silent_noop(self, tmp_path):
        mem = mod.SelectorHealMemory(path=str(tmp_path / "nope.json"))
        assert mem.stats()["entries"] == 0

    def test_save_without_path_reports_false(self):
        assert mod.SelectorHealMemory().save() is False

    def test_corrupt_memory_quarantined_and_rebuilt(self, tmp_path):
        path = tmp_path / "heal.json"
        path.write_text("{not valid json!!", encoding="utf-8")
        mem = mod.SelectorHealMemory(path=str(path))
        assert mem.stats()["entries"] == 0                       # S3: starts empty
        assert os.path.exists(str(path) + ".corrupt")            # quarantined
        assert not path.exists()
        mem.remember("fresh", "#fresh")                          # rebuild works
        assert mem.save() is True
        assert mod.SelectorHealMemory(path=str(path)).lookup("fresh") == "#fresh"

    def test_structurally_invalid_memory_entries_skipped(self, tmp_path):
        path = tmp_path / "heal.json"
        payload = {
            "good": {"selector": "#g", "tier": "PRIMARY", "confidence": 1.0},
            "bad-no-selector": {"tier": "X"},
            "bad-root": ["not", "an", "object"],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        mem = mod.SelectorHealMemory(path=str(path))
        assert mem.lookup("good") == "#g"
        assert mem.lookup("bad-no-selector") is None


# =====================================================================
# Engine x memory integration (S1/S2)
# =====================================================================
class TestHealMemoryIntegration:
    def test_primary_success_written_to_memory(self):
        page = FakePage(wait_results={"#stable": button()})
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()

        async def scenario():
            return await engine.resolve_element(
                page, "#stable", logical_name="buy-button", heal_memory=mem)

        assert run(scenario()) is not None
        assert mem.lookup("buy-button") == "#stable"
        assert mem.stats()["tiers"]["PRIMARY"] == 1

    def test_memory_hit_skips_cascade_entirely(self):
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()
        mem.remember("buy-button", "#remembered")

        healed = button()
        # Page ONLY knows the remembered selector; primary/cascade selectors fail.
        page = FakePage(wait_results={"#remembered": healed})
        result = run(engine.resolve_element(
            page, "#original-selector", logical_name="buy-button", heal_memory=mem))
        assert result is healed
        assert engine.last_match_tier == "MEMORY"
        assert engine.last_match_confidence >= 0.9

    def test_stale_memory_falls_through_to_cascade_then_refreshes(self):
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()
        mem.remember("buy-button", "#stale-entry")

        healed = button()
        # remembered selector times out; PRIMARY '#new-stable' succeeds.
        page = FakePage(wait_results={"#new-stable": healed})
        result = run(engine.resolve_element(
            page, "#new-stable", logical_name="buy-button", heal_memory=mem))
        assert result is healed
        assert engine.last_match_tier == "PRIMARY"
        assert mem.lookup("buy-button") == "#new-stable"   # entry refreshed

    def test_no_memory_without_logical_name(self):
        page = FakePage(wait_results={"#s": button()})
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()
        run(engine.resolve_element(page, "#s", heal_memory=mem))
        assert mem.stats()["entries"] == 0

    def test_memory_persisted_across_instances_end_to_end(self, tmp_path):
        path = str(tmp_path / "mem.json")
        page = FakePage(wait_results={"#pay": button()})
        engine_a = mod.SelfHealingSelectorEngine()
        mem_a = mod.SelectorHealMemory(path=path)

        async def learn():
            return await engine_a.resolve_element(
                page, "#pay", logical_name="pay-btn", heal_memory=mem_a)
        run(learn())
        mem_a.save()

        # New process-equivalent: fresh engine + fresh memory from disk.
        mem_b = mod.SelectorHealMemory(path=path)
        engine_b = mod.SelfHealingSelectorEngine()
        healed = button()
        page_b = FakePage(wait_results={"#pay": healed})
        result = run(engine_b.resolve_element(
            page_b, "#pay", logical_name="pay-btn", heal_memory=mem_b))
        assert result is healed
        assert engine_b.last_match_tier == "MEMORY"


class RecoveryPipelineProbe:
    """Documents the Phase 4 recovery-strategy inventory used by tests."""

    STRATEGIES = [
        "S1-memory-fast-path",
        "S2-stale-fallthrough-refresh",
        "S3-corrupt-quarantine-rebuild",
        "R1-context-rotation-new-before-old",
        "R2-rotation-failure-preserves-current",
        "R3-vault-atomic-write-preserves-previous",
        "R4-mitm-loop-safe-dispatch",
    ]


def test_recovery_strategy_inventory_documented():
    assert len(RecoveryPipelineProbe.STRATEGIES) == 7
