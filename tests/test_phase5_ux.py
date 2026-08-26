"""Phase 5 suite: BehavioralPlaywright facade (bp.run / bp.solve / bp.collect)."""
import json

import pytest
from pydantic import BaseModel

import fakes
from fakes import FakeBrowser, FakeContext, FakePage, PermissiveSchema, StrictIdSchema, run
import behavioral_evasion_ten_patches_hardened_v15 as mod


class MarketData(BaseModel):
    id: int
    company: str
    rank: float
    event_timestamp: float
    knowledge_timestamp: float
    isin: str
    cusip: str
    figi: str
    ticker: str


def make_bp(tmp_path, **kw):
    return mod.BehavioralPlaywright(
        output_path=str(tmp_path / "bp.ndjson"),
        heal_memory_path=str(tmp_path / "heal.json"),
        **kw,
    )


# =====================================================================
# Construction / wiring
# =====================================================================
class TestFacadeConstruction:
    def test_components_wired(self, tmp_path):
        bp = make_bp(tmp_path)
        assert isinstance(bp.geo_aligner, mod.DynamicUSGeoIPAligner)
        assert isinstance(bp.selector_engine, mod.SelfHealingSelectorEngine)
        assert isinstance(bp.heal_memory, mod.SelectorHealMemory)
        assert isinstance(bp.pipeline, mod.QuantPersistencePipeline)
        assert bp.sentinel is bp.pipeline.sentinel

    def test_region_propagates(self, tmp_path):
        bp = make_bp(tmp_path, region="us-west")
        assert bp.geo_aligner.region == "us-west"

    def test_confidence_threshold_propagates(self, tmp_path):
        bp = make_bp(tmp_path, confidence_threshold=0.95)
        assert bp.selector_engine.confidence_threshold == pytest.approx(0.95)


# =====================================================================
# collect()
# =====================================================================
class TestCollect:
    def test_collect_ingests_and_persists(self, tmp_path):
        async def scenario():
            bp = make_bp(tmp_path, min_expected_throughput=1)
            status = await bp.collect({"id": 1, "company": "Apple", "rank": 4.2}, MarketData)
            await bp.close()
            return status

        status = run(scenario())
        assert status["status"] == "ingested"
        assert status["records_processed"] == 1
        lines = (tmp_path / "bp.ndjson").read_text(encoding="utf-8").strip().splitlines()
        record = json.loads(lines[0])
        assert record["isin"] == "US0378331005"
        assert record["event_timestamp"] <= record["knowledge_timestamp"]

    def test_collect_contract_breach_is_loud(self, tmp_path):
        async def scenario():
            bp = make_bp(tmp_path)
            await bp.collect({"id": 1, "company": "Mystery LLC", "rank": 1.0}, MarketData)

        with pytest.raises(mod.EntityResolutionError):
            run(scenario())

    def test_close_enforces_throughput_contract(self, tmp_path):
        async def scenario():
            bp = make_bp(tmp_path, min_expected_throughput=2)
            await bp.collect({"id": 1, "company": "Apple", "rank": 1.0}, MarketData)
            with pytest.raises(RuntimeError, match="throughput"):
                await bp.close()

        run(scenario())


# =====================================================================
# solve()
# =====================================================================
class TestSolve:
    def test_solve_primary_success(self, tmp_path):
        el = fakes.FakeElement()
        page = FakePage(wait_results={"#btn": el})
        bp = make_bp(tmp_path)
        resolved = run(bp.solve("#btn", page=page))
        assert resolved is el
        assert bp.selector_engine.last_match_tier == "PRIMARY"

    def test_solve_failure_raises_never_gusses(self, tmp_path):
        bp = make_bp(tmp_path)
        page = FakePage()  # nothing resolvable
        with pytest.raises(mod.ElementResolutionError, match="confidence threshold"):
            run(bp.solve("#does-not-exist", page=page))

    def test_solve_uses_and_fills_heal_memory(self, tmp_path):
        el = fakes.FakeElement()
        bp = make_bp(tmp_path)
        page_a = FakePage(wait_results={"#stable": el})
        run(bp.solve("#stable", logical_name="buy-btn", page=page_a))
        assert bp.heal_memory.lookup("buy-btn") == "#stable"

        # Memory fast-path on a second solve.
        page_b = FakePage(wait_results={"#stable": el})
        result = run(bp.solve("#anything-else", logical_name="buy-btn", page=page_b))
        assert result is el
        assert bp.selector_engine.last_match_tier == "MEMORY"

    def test_heal_memory_survives_close_via_disk(self, tmp_path):
        el = fakes.FakeElement()

        async def scenario_one():
            bp = make_bp(tmp_path, min_expected_throughput=0)
            await bp.solve("#stable", logical_name="pay-btn", page=FakePage(wait_results={"#stable": el}))
            await bp.close()

        run(scenario_one())
        revived = mod.SelectorHealMemory(path=str(tmp_path / "heal.json"))
        assert revived.lookup("pay-btn") == "#stable"


# =====================================================================
# run()
# =====================================================================
class TestRun:
    def test_run_with_injected_page_applies_stealth_stack(self, tmp_path):
        seen_pages = []
        bp = make_bp(tmp_path)

        def action(page):
            seen_pages.append(page)
            return {"ok": True, "scripts": len(page.scripts)}

        result = run(bp.run(action, page=FakePage()))
        assert result["ok"] is True
        assert len(seen_pages) == 1
        # CDP shield + hardware spoofer both injected (2 scripts).
        assert result["scripts"] >= 2

    def test_run_accepts_coroutine_action(self, tmp_path):
        bp = make_bp(tmp_path)

        async def action(page):
            return "async-result"

        assert run(bp.run(action, page=FakePage())) == "async-result"

    def test_run_rejects_missing_action(self, tmp_path):
        bp = make_bp(tmp_path)
        with pytest.raises(ValueError, match="action"):
            run(bp.run(None, page=FakePage()))

    def test_run_without_browser_is_honest_error(self, tmp_path):
        bp = make_bp(tmp_path)
        with pytest.raises(RuntimeError, match="attach_browser"):
            run(bp.run(lambda page: "x"))

    def test_run_with_bound_browser_rotates_and_cleans_up(self, tmp_path):
        browser = FakeBrowser()
        bp = make_bp(tmp_path)

        async def scenario():
            bp.attach_browser(browser)
            result = await bp.run(lambda p: {"seen": type(p).__name__})
            return result

        result = run(scenario())
        assert result["seen"] == "FakePage"
        ctx = browser.created_contexts[0]
        # geo alignment ran against the acquired context
        assert ctx.geolocation is not None
        assert ctx.permissions == ["geolocation"]
        # the ephemeral page was closed after the action
        assert all(p.closed for p in ctx.pages)


# =====================================================================
# attach_browser / rotation integration
# =====================================================================
class TestAttachBrowser:
    def test_attach_returns_rotator_with_threshold(self, tmp_path):
        bp = make_bp(tmp_path)
        rotator = bp.attach_browser(FakeBrowser())
        assert isinstance(rotator, mod.ContextRotator)
        assert rotator.recycle_threshold >= 1

    def test_invalid_recycle_threshold_rejected_at_construction(self, tmp_path):
        with pytest.raises(ValueError):
            make_bp(tmp_path, recycle_threshold=0)
