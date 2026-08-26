"""Phase 18 suite: final self-healing lifecycle audit.

Walks the complete healing chain -- MEMORY -> PRIMARY -> L1 -> L2 -> L3 -> L4 --
across engine instances and on-disk persistence, pinning every contract the
final release depends on:

  first solve = recovery, subsequent solve = cheap memory fast-path,
  confidence gating everywhere (incl. MEMORY), expected_content verification,
  verified lower-tier write-back, stable-selector extraction/revalidation,
  stronger-entry preservation, L4 never persists, corruption quarantine,
  bounded eviction, atomic persistence, and failure honesty.
"""
import json
import os

import pytest

import fakes
from fakes import FakeElement, FakePage, RAISE, run
import behavioral_evasion_ten_patches_hardened_v15 as mod


def button(id="", cls="", text="", aria_label="", title="", tag="button",
           box=None, attrs=None):
    return FakeElement(id=id, cls=cls, text=text, aria_label=aria_label,
                       title=title, tag=tag, box=box, attrs=attrs)


HEAL_PATH = "lifecycle-heal.json"


class TestCompleteHealingLifecycle:
    def test_first_solve_recovers_via_l2_and_writes_back(self, tmp_path):
        heal = mod.SelectorHealMemory(path=str(tmp_path / HEAL_PATH))
        engine = mod.SelfHealingSelectorEngine()
        target = button(id="checkout-buy", text="Buy now", aria_label="Buy now")
        page = FakePage(
            elements=[target],
            wait_results={"#checkout-buy": target},   # stable id resolves too
        )
        resolved = run(engine.resolve_element(
            page, "#btn-dynamic-4815162342", "Buy now",
            logical_name="buy", heal_memory=heal))
        assert resolved is target
        assert engine.last_match_tier == "L2"
        # Verified write-back persisted the STABLE selector found via the id.
        entry = heal.entry("buy")
        assert entry["selector"] == "#checkout-buy"
        assert entry["tier"] == "L2"
        assert entry["confidence"] == pytest.approx(0.90)

    def test_second_solve_is_a_single_probe_memory_hit_across_instances(self, tmp_path):
        heal_file = str(tmp_path / HEAL_PATH)

        el = button(id="checkout-buy", text="Buy now", aria_label="Buy now")

        async def stage_one():
            heal = mod.SelectorHealMemory(path=heal_file)
            engine = mod.SelfHealingSelectorEngine()
            page = FakePage(elements=[el], wait_results={"#checkout-buy": el})
            await engine.resolve_element(page, "#broken-x", "Buy now",
                                         logical_name="buy", heal_memory=heal)
            assert engine.last_match_tier != "MEMORY"
            heal.save()

        run(stage_one())

        async def stage_two():
            revived = mod.SelectorHealMemory(path=heal_file)
            assert revived.lookup("buy") == "#checkout-buy"
            engine = mod.SelfHealingSelectorEngine()
            page = FakePage(wait_results={"#checkout-buy": el})
            resolved = await engine.resolve_element(page, "#whatever-else", "Buy now",
                                                    logical_name="buy", heal_memory=revived)
            return resolved, page, engine

        resolved, page, engine = run(stage_two())
        assert resolved is el
        assert engine.last_match_tier == "MEMORY"
        assert page.wait_calls == ["#checkout-buy"]      # EXACTLY one probe;
        # the cascade (PRIMARY/L1/L2/L3 scans) never ran: expensive once, cheap forever.

    def test_stale_memory_falls_through_to_cascade_then_recovers(self, tmp_path):
        heal = mod.SelectorHealMemory()
        heal.remember("buy", "#old-stale-selector", tier="PRIMARY", confidence=1.0)
        engine = mod.SelfHealingSelectorEngine()
        fresh = button(id="fresh-btn", aria_label="Buy now", text="Buy now")
        page = FakePage(elements=[fresh],
                        wait_results={
                            "#old-stale-selector": RAISE,     # stale selector gone
                            "#fresh-btn": fresh,
                        })
        resolved = run(engine.resolve_element(page, "#gone-primary", "Buy now",
                                              logical_name="buy", heal_memory=heal))
        assert resolved is fresh
        assert engine.last_match_tier == "L2"                 # cascade recovered (S2)
        # Documented Phase 9 contract: a strictly stronger stored entry is NEVER
        # overwritten by a lower-tier recovery (C7), even when its selector went
        # stale on the current page; a later PRIMARY-resolution refreshes it.
        # The cost is one wasted probe per solve until that happens -- accepted,
        # deliberate trade-off (pinned since Phase 9).
        assert heal.lookup("buy") == "#old-stale-selector"
        assert engine.last_writeback is None

    def test_expected_content_mismatch_treats_memory_as_stale(self, tmp_path):
        heal = mod.SelectorHealMemory()
        wrong = button(id="other", text="Totally different")
        right = button(id="right", aria_label="Buy now", text="Buy now")
        heal.remember("buy", "#other", tier="PRIMARY", confidence=1.0)
        engine = mod.SelfHealingSelectorEngine()
        page = FakePage(elements=[wrong, right],
                        wait_results={"#other": wrong, "#right": right})
        resolved = run(engine.resolve_element(page, "#gone", "Buy now",
                                              logical_name="buy", heal_memory=heal))
        assert resolved is right                              # A2: wrong hit refused

    def test_low_confidence_memory_entry_cannot_bypass_the_gate(self, tmp_path):
        heal = mod.SelectorHealMemory()
        heal._entries["buy"] = {                               # simulate legacy file
            "selector": "#weak", "tier": "UNKNOWN",
            "confidence": 0.10, "updated": "2020-01-01T00:00:00+00:00",
        }
        engine = mod.SelfHealingSelectorEngine(confidence_threshold=0.80)
        good = button(id="strong-btn", aria_label="Buy now", text="Buy now")
        page = FakePage(elements=[good], wait_results={"#weak": None, "#strong-btn": good})
        resolved = run(engine.resolve_element(page, "#gone", "Buy now",
                                              logical_name="buy", heal_memory=heal))
        assert engine.last_match_tier != "MEMORY"              # A1: gate honored

    def test_stronger_existing_entry_is_never_downgraded(self, tmp_path):
        heal = mod.SelectorHealMemory()
        heal.remember("buy", "#primary-truth", tier="PRIMARY", confidence=1.0)
        engine = mod.SelfHealingSelectorEngine(confidence_threshold=0.80)
        el = button(aria_label="Buy now", text="Buy now")      # NO id: L2 recovery
        page = FakePage(elements=[el], wait_results={})        # nothing re-resolves
        run(engine.resolve_element(page, "#gone", "Buy now",
                                   logical_name="buy", heal_memory=heal))
        assert heal.lookup("buy") == "#primary-truth"          # C7 preserved

    def test_l4_never_writes_back_even_when_explicitly_enabled(self, tmp_path):
        heal = mod.SelectorHealMemory()
        engine = mod.SelfHealingSelectorEngine(confidence_threshold=0.20)
        btn = button(tag="button", id="some-button", text="whatever")
        page = FakePage(elements=[btn], wait_results={"#some-button": btn})
        run(engine.resolve_element(page, "#no-match-possible", None,
                                   logical_name="first-thing", heal_memory=heal))
        assert engine.last_match_tier == "L4"
        assert heal.lookup("first-thing") is None              # heuristic never persists

    def test_corrupt_memory_file_is_quarantined_and_rebuilt(self, tmp_path):
        heal_file = tmp_path / HEAL_PATH
        heal_file.write_text("{ this is not json", encoding="utf-8")
        heal = mod.SelectorHealMemory(path=str(heal_file))
        assert heal.stats()["entries"] == 0                    # rebuilt empty
        assert os.path.exists(str(heal_file) + ".corrupt")     # quarantined
        heal.remember("k", "#v")
        assert heal.save() is True                             # and usable again
        assert not os.path.exists(str(heal_file) + ".tmp")     # atomic: no tmp litter

    def test_eviction_keeps_highest_value_entries_under_capacity(self, tmp_path):
        heal = mod.SelectorHealMemory(max_entries=3)
        for i, conf in enumerate([0.95, 0.55, 0.85]):
            heal.remember(f"k{i}", f"#s{i}", confidence=conf)
        heal.remember("k3", "#s3", confidence=0.75)            # evicts k1 (0.55)
        assert sorted(heal._entries) == ["k0", "k2", "k3"]

    def test_unresolvable_everything_raises_instead_of_guessing(self, tmp_path):
        bp = mod.BehavioralPlaywright(output_path=str(tmp_path / "o.ndjson"))
        page = FakePage()                                      # empty DOM
        with pytest.raises(mod.ElementResolutionError, match="confidence"):
            run(bp.solve("#nothing-at-all", "Buy now", page=page))

    def test_persistence_failure_reports_false_never_fake_success(self, tmp_path):
        heal = mod.SelectorHealMemory(path=str(tmp_path / "dir-does-not-exist" / HEAL_PATH))
        heal.remember("k", "#v")
        assert heal.save() is False                            # honest False
