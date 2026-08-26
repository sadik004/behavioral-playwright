"""Phase 9 suite: verified lower-tier self-healing write-back.

A successful L1/L2/L3 recovery may feed SelectorHealMemory ONLY when the full
seven-condition safety contract holds (see
SelfHealingSelectorEngine._try_verified_write_back):

  C1  real element handle recovered
  C2  recovery confidence meets confidence_threshold
  C3  recovered element verifiable (expected_content honored when supplied)
  C4  stable selector extractable
  C5  selector non-empty
  C6  no transient/generated value relied upon
  C7  no overwrite of a strictly stronger existing memory entry

Any failed condition => NO write-back while the recovery result itself is
preserved. The blind L4 heuristic tier deliberately NEVER writes back.
"""
import os

import pytest

import fakes
from fakes import FakeElement, FakePage, run
import behavioral_evasion_ten_patches_hardened_v15 as mod


def button(id="", cls="", text="", aria_label="", title="", tag="button", box=None,
           attrs=None):
    return FakeElement(id=id, cls=cls, text=text, aria_label=aria_label,
                       title=title, tag=tag, box=box, attrs=attrs)


ARIA_SELECTOR = 'button[aria-label="Submit order"]'


def l2_page(candidate, **kw):
    """Page whose primary/cascade context lets ``candidate`` win via L2."""
    return FakePage(elements=[candidate], wait_results={ARIA_SELECTOR: candidate}, **kw)


# =====================================================================
# Write-back through the full resolve_element flow
# =====================================================================
class TestVerifiedLowerTierWriteBack:
    def test_l1_recovery_writes_stable_selector(self):
        candidate = button(id="btn-submit")
        page = FakePage(
            elements=[button(id="unrelated-zone"), candidate],
            wait_results={"#btn-submit": candidate},
        )
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()

        resolved = run(engine.resolve_element(
            page, "#btn-submt", logical_name="buy-button", heal_memory=mem))

        assert resolved is candidate
        assert engine.last_match_tier == "L1"
        assert mem.lookup("buy-button") == "#btn-submit"
        assert mem.stats()["tiers"] == {"L1": 1}
        assert engine.last_writeback == {
            "logical_name": "buy-button",
            "selector": "#btn-submit",
            "tier": "L1",
            "confidence": pytest.approx(engine.last_match_confidence),
        }

    def test_l2_recovery_writes_stable_selector(self):
        candidate = button(aria_label="Submit order")
        page = l2_page(candidate)
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()

        resolved = run(engine.resolve_element(
            page, "#gone", expected_content="submit order",
            logical_name="checkout", heal_memory=mem))

        assert resolved is candidate
        assert engine.last_match_tier == "L2"
        assert mem.lookup("checkout") == ARIA_SELECTOR
        assert mem.stats()["tiers"] == {"L2": 1}

    def test_l3_recovery_writes_stable_selector(self):
        candidate = button(
            text="Checkout now",
            id="checkout-btn",
            box={"x": 120, "y": 300, "width": 90, "height": 40},
        )
        page = FakePage(elements=[candidate], wait_results={"#checkout-btn": candidate})
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()

        resolved = run(engine.resolve_element(
            page, "#gone", expected_content="checkout",
            logical_name="checkout", heal_memory=mem))

        assert resolved is candidate
        assert engine.last_match_tier == "L3"
        assert mem.lookup("checkout") == "#checkout-btn"
        assert mem.stats()["tiers"] == {"L3": 1}

    def test_generated_id_is_never_persisted_recovery_preserved(self):
        candidate = button(id="btn-submit-1234")
        page = FakePage(elements=[candidate])
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()

        resolved = run(engine.resolve_element(
            page, "#btn-submt-1234", logical_name="buy-button", heal_memory=mem))

        assert resolved is candidate          # recovery result preserved
        assert engine.last_match_tier == "L1"
        assert mem.stats()["entries"] == 0    # unstable selector NOT persisted
        assert engine.last_writeback is None

    def test_empty_selector_is_never_persisted_recovery_preserved(self):
        candidate = button(text="Pay now invoice")   # no stable attributes at all
        page = FakePage(elements=[candidate])
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()

        resolved = run(engine.resolve_element(
            page, "#paynowinvoice", logical_name="pay", heal_memory=mem))

        assert resolved is candidate
        assert engine.last_match_tier == "L1"
        assert mem.stats()["entries"] == 0    # nothing invented, nothing stored
        assert engine.last_writeback is None

    def test_stronger_existing_memory_not_overwritten(self):
        mem = mod.SelectorHealMemory()
        mem.remember("buy-button", "#premium-stable", tier="PRIMARY", confidence=1.0)
        candidate = button(aria_label="Submit order")
        page = l2_page(candidate)
        engine = mod.SelfHealingSelectorEngine()

        resolved = run(engine.resolve_element(
            page, "#gone", expected_content="submit order",
            logical_name="buy-button", heal_memory=mem))

        assert resolved is candidate          # solve still succeeds
        assert engine.last_match_tier == "L2"
        assert mem.lookup("buy-button") == "#premium-stable"     # untouched
        assert mem.stats()["tiers"] == {"PRIMARY": 1}            # no downgrade
        assert engine.last_writeback is None

    def test_writeback_survives_new_instance(self, tmp_path):
        path = str(tmp_path / "heal.json")
        candidate = button(aria_label="Submit order")
        engine_a = mod.SelfHealingSelectorEngine()
        mem_a = mod.SelectorHealMemory(path=path)
        run(engine_a.resolve_element(
            l2_page(candidate), "#gone", expected_content="submit order",
            logical_name="checkout", heal_memory=mem_a))
        assert mem_a.save() is True

        mem_b = mod.SelectorHealMemory(path=path)
        assert mem_b.lookup("checkout") == ARIA_SELECTOR
        assert mem_b.entry("checkout")["tier"] == "L2"

        engine_b = mod.SelfHealingSelectorEngine()
        healed_again = button(aria_label="Submit order")
        page_b = FakePage(wait_results={ARIA_SELECTOR: healed_again})
        result = run(engine_b.resolve_element(
            page_b, "#irrelevant", logical_name="checkout", heal_memory=mem_b))
        assert result is healed_again
        assert engine_b.last_match_tier == "MEMORY"

    def test_second_solve_uses_memory_fast_path_cheaply(self):
        candidate = button(aria_label="Submit order")
        page_a = l2_page(candidate)
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()

        run(engine.resolve_element(
            page_a, "#gone", expected_content="submit order",
            logical_name="buy-button", heal_memory=mem))
        assert engine.last_match_tier == "L2"

        # Second page: cascade IMPOSSIBLE (no queryable elements); only the
        # remembered selector can succeed -- and does, with a single probe.
        healed_again = button(aria_label="Submit order")
        page_b = FakePage(wait_results={ARIA_SELECTOR: healed_again})
        result = run(engine.resolve_element(
            page_b, "#gone", logical_name="buy-button", heal_memory=mem))

        assert result is healed_again
        assert engine.last_match_tier == "MEMORY"
        assert engine.last_match_confidence == pytest.approx(0.90)
        assert page_b.wait_calls == [ARIA_SELECTOR]

    def test_expected_content_still_guards_memory_after_writeback(self):
        mem = mod.SelectorHealMemory()
        candidate = button(aria_label="Submit order")
        engine = mod.SelfHealingSelectorEngine()
        run(engine.resolve_element(
            l2_page(candidate), "#gone", expected_content="submit order",
            logical_name="buy-button", heal_memory=mem))

        # Page changed under the remembered selector: it now resolves the
        # WRONG element, so A2 must force a cascade fall-through...
        wrong = button(aria_label="Unrelated banner")
        right = button(aria_label="Refund policy")
        page_b = FakePage(
            elements=[wrong, right],
            wait_results={
                ARIA_SELECTOR: wrong,
                'button[aria-label="Refund policy"]': right,
            },
        )
        result = run(engine.resolve_element(
            page_b, "#original", expected_content="refund policy",
            logical_name="buy-button", heal_memory=mem))

        assert result is right
        assert engine.last_match_tier == "L2"      # fell through, re-healed
        # Equal-strength refresh is allowed (never a downgrade).
        assert mem.lookup("buy-button") == 'button[aria-label="Refund policy"]'
        assert mem.entry("buy-button")["confidence"] == pytest.approx(0.90)

    def test_derived_selector_must_revalidate_on_current_page(self):
        candidate = button(id="btn-submit")
        # No wait mapping for "#btn-submit": the derived selector cannot be
        # proven to re-resolve here -> write-back must be refused.
        page = FakePage(elements=[button(id="zzz-noise"), candidate])
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()

        resolved = run(engine.resolve_element(
            page, "#btn-submt", logical_name="buy-button", heal_memory=mem))

        assert resolved is candidate
        assert engine.last_match_tier == "L1"
        assert mem.stats()["entries"] == 0
        assert engine.last_writeback is None

    def test_corrupt_memory_quarantined_then_writeback_rebuilds(self, tmp_path):
        path = tmp_path / "heal.json"
        path.write_text("{not valid json!!", encoding="utf-8")
        mem = mod.SelectorHealMemory(path=str(path))
        assert mem.stats()["entries"] == 0                    # S3 quarantine
        assert os.path.exists(str(path) + ".corrupt")

        candidate = button(aria_label="Submit order")
        engine = mod.SelfHealingSelectorEngine()
        run(engine.resolve_element(
            l2_page(candidate), "#gone", expected_content="submit order",
            logical_name="checkout", heal_memory=mem))
        assert mem.save() is True

        revived = mod.SelectorHealMemory(path=str(path))
        assert revived.lookup("checkout") == ARIA_SELECTOR

    def test_l4_heuristic_never_writes_back(self):
        first_button = button(tag="button")
        page = FakePage(elements=[first_button])
        engine = mod.SelfHealingSelectorEngine(confidence_threshold=0.20)
        mem = mod.SelectorHealMemory()

        resolved = run(engine.resolve_element(
            page, "#nothing-matches", logical_name="whoever", heal_memory=mem))

        assert resolved is first_button
        assert engine.last_match_tier == "L4"
        assert mem.stats()["entries"] == 0
        assert engine.last_writeback is None

    def test_persistence_failure_does_not_create_fake_success(self, tmp_path):
        bogus = tmp_path / "missing-dir" / "heal.json"   # parent cannot hold it
        mem = mod.SelectorHealMemory(path=str(bogus))
        engine = mod.SelfHealingSelectorEngine()
        candidate = button(aria_label="Submit order")

        resolved = run(engine.resolve_element(
            l2_page(candidate), "#gone", expected_content="submit order",
            logical_name="checkout", heal_memory=mem))

        assert resolved is candidate                     # recovery preserved
        assert engine.last_match_tier == "L2"
        assert mem.lookup("checkout") == ARIA_SELECTOR   # honestly usable in RAM
        assert mem.save() is False                       # honest failure, no raise
        assert not bogus.exists()                        # nothing faked on disk


# =====================================================================
# Direct contract-gate unit checks
# =====================================================================
class TestWriteBackSafetyContract:
    def test_low_confidence_recovery_refused(self):
        engine = mod.SelfHealingSelectorEngine()          # threshold 0.80
        mem = mod.SelectorHealMemory()
        el = button(id="stable-id")

        async def attempt():
            await engine._try_verified_write_back(
                page=FakePage(wait_results={"#stable-id": el}),
                element=el,
                tier="L2",
                confidence=0.60,                          # below threshold
                logical_name="x",
                heal_memory=mem,
            )

        run(attempt())
        assert mem.stats()["entries"] == 0
        assert engine.last_writeback is None

    def test_non_handle_elements_refused(self):
        engine = mod.SelfHealingSelectorEngine()
        mem = mod.SelectorHealMemory()

        async def attempt(element):
            await engine._try_verified_write_back(
                page=FakePage(), element=element, tier="L1",
                confidence=0.95, logical_name="x", heal_memory=mem,
            )

        run(attempt(None))
        run(attempt(object()))                            # no get_attribute API
        assert mem.stats()["entries"] == 0

    def test_no_memory_wiring_is_a_silent_noop(self):
        engine = mod.SelfHealingSelectorEngine()
        el = button(id="stable-id")

        async def attempt(**kw):
            await engine._try_verified_write_back(
                page=FakePage(wait_results={"#stable-id": el}),
                element=el, tier="L2", confidence=0.90, **kw,
            )

        run(attempt(logical_name=None, heal_memory=mod.SelectorHealMemory()))
        run(attempt(logical_name="   ", heal_memory=None))
        run(attempt(logical_name="x", heal_memory=None))
        assert engine.last_writeback is None


# =====================================================================
# Stable-selector extraction rules
# =====================================================================
class TestStableSelectorExtraction:
    def test_generated_id_matrix(self):
        classify = mod.SelfHealingSelectorEngine._is_generated_id
        for unstable in [
            "ember123",                                   # Ember runtime id
            ":r5:",                                       # React useId runtime id
            "a1b2c3d4-e5f6-4789-a0b1-c2d3e4f5a6b7",       # UUID fragment
            "0123456789abcdef01",                         # opaque hex blob
            "btn-submit-1234",                            # auto-increment suffix
            "widget_987654",                              # long numeric tail
            "",                                           # empty
            "has space",                                  # unusable in CSS
        ]:
            assert classify(unstable) is True, unstable
        for stable in ["btn-submit", "checkout-btn", "main-header", "step-2"]:
            assert classify(stable) is False, stable

    def test_extraction_returns_empty_without_stable_attributes(self):
        engine = mod.SelfHealingSelectorEngine()
        assert run(engine._extract_stable_selector(None)) == ""
        assert run(engine._extract_stable_selector(button(text="Only text"))) == ""
        # Generated ids are refused too -- nothing else may be invented.
        assert run(engine._extract_stable_selector(button(id="ember1234"))) == ""

    def test_testid_preferred_over_aria_label(self):
        engine = mod.SelfHealingSelectorEngine()
        el = button(aria_label="Submit order", attrs={"data-testid": "submit-order"})
        assert run(engine._extract_stable_selector(el)) == \
            'button[data-testid="submit-order"]'

    def test_semantic_attribute_fallbacks(self):
        engine = mod.SelfHealingSelectorEngine()
        named = button(attrs={"name": "q"})
        titled = button(title="Open help center")
        assert run(engine._extract_stable_selector(named)) == 'button[name="q"]'
        assert run(engine._extract_stable_selector(titled)) == \
            'button[title="Open help center"]'


# =====================================================================
# Facade-level integration (bp.solve)
# =====================================================================
class TestFacadeWriteBackIntegration:
    def test_expensive_once_then_cheap_reuse_across_instances(self, tmp_path):
        async def scenario():
            bp = mod.BehavioralPlaywright(
                output_path=str(tmp_path / "bp.ndjson"),
                heal_memory_path=str(tmp_path / "heal.json"),
            )
            el = FakeElement(aria_label="Submit order")
            page_a = FakePage(
                elements=[el], wait_results={ARIA_SELECTOR: el})

            # FIRST solve: primary broken, expensive L2 recovery required.
            first = await bp.solve("#gone", "submit order",
                                   logical_name="buy-btn", page=page_a)
            await bp.close()

            # SECOND solve: brand-new instance, disk-revived memory, and a
            # page where the cascade is IMPOSSIBLE (no queryable elements).
            bp2 = mod.BehavioralPlaywright(
                output_path=str(tmp_path / "bp.ndjson"),
                heal_memory_path=str(tmp_path / "heal.json"),
            )
            el2 = FakeElement(aria_label="Submit order")
            page_b = FakePage(wait_results={ARIA_SELECTOR: el2})
            second = await bp2.solve("#gone", logical_name="buy-btn", page=page_b)
            outcome = (bp2.selector_engine.last_match_tier, len(page_b.wait_calls),
                       bp2.heal_memory.lookup("buy-btn"))
            await bp2.close()
            return first, second, outcome

        first, second, (tier, wait_count, remembered) = run(scenario())
        assert first is not None
        assert second is not None
        assert tier == "MEMORY"
        assert wait_count == 1                  # one cheap memory probe, no cascade
        assert remembered == ARIA_SELECTOR
