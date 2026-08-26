"""Phase 11 suite: orchestration/UX consolidation (navigate verb, humanized
typing, session context manager) plus end-to-end workflow proofs."""
import asyncio

import pytest

import fakes
from fakes import (
    FakeBrowser,
    FakeContext,
    FakeElement,
    FakePage,
    PermissiveSchema,
    RAISE,
    run,
)
import behavioral_evasion_ten_patches_hardened_v15 as mod


class MarketData(fakes.PermissiveSchema):
    id: int


def make_bp(tmp_path, **kw):
    return mod.BehavioralPlaywright(
        output_path=str(tmp_path / "bp.ndjson"),
        heal_memory_path=str(tmp_path / "heal.json"),
        **kw,
    )


# =====================================================================
# navigate()
# =====================================================================
class TestNavigateVerb:
    def test_happy_path_reports_honest_status_and_applies_stealth(self, tmp_path):
        page = FakePage(goto_results={"https://shop.example.com": 200})
        bp = make_bp(tmp_path)
        result = run(bp.navigate("https://shop.example.com", page=page))
        assert result == {"url": "https://shop.example.com", "status": 200, "ok": True}
        # stealth stack applied before navigation
        assert len(page.scripts) >= 2
        # explicit timeout/wait_until forwarded to the driver
        assert page.goto_calls[0]["timeout"] == 30000
        assert page.goto_calls[0]["wait_until"] == "load"

    def test_explicit_timeout_and_wait_until_forwarded(self, tmp_path):
        page = FakePage()
        bp = make_bp(tmp_path)
        run(bp.navigate("https://x.example.com", page=page, timeout_ms=1234, wait_until="domcontentloaded"))
        assert page.goto_calls[0]["timeout"] == 1234
        assert page.goto_calls[0]["wait_until"] == "domcontentloaded"

    @pytest.mark.parametrize("bad_url", ["", "   ", None, "ftp://files.example.com", "javascript:alert(1)"])
    def test_malformed_urls_rejected_loudly_and_permanently(self, tmp_path, bad_url):
        bp = make_bp(tmp_path)
        sleeper_calls = []

        async def rec_sleep(delay):
            sleeper_calls.append(delay)

        bp.retry_policy = mod.RetryPolicy(max_attempts=4, base_delay=1.0, sleep_fn=rec_sleep)
        with pytest.raises(mod.NavigationError, match="navigate"):
            run(bp.navigate(bad_url, page=FakePage()))
        # Config errors are permanent: no retries burned.
        assert sleeper_calls == []
        assert not hasattr(bp, "_navigation_history") or list(bp._navigation_history) == []

    def test_about_blank_is_accepted(self, tmp_path):
        page = FakePage()
        bp = make_bp(tmp_path)
        result = run(bp.navigate("about:blank", page=page))
        assert result["ok"] is True and result["url"] == "about:blank"

    def test_failing_http_status_is_reported_not_raised(self, tmp_path):
        page = FakePage(goto_results={"https://waf.example.com": 403})
        bp = make_bp(tmp_path)
        result = run(bp.navigate("https://waf.example.com", page=page))
        assert result == {"url": "https://waf.example.com", "status": 403, "ok": False}

    def test_missing_response_object_is_reported_honestly(self, tmp_path):
        page = FakePage(goto_results={"https://odd.example.com": None})
        bp = make_bp(tmp_path)
        result = run(bp.navigate("https://odd.example.com", page=page))
        assert result["status"] is None
        assert result["ok"] is False

    def test_navigation_loop_guard_blocks_the_third_repeat(self, tmp_path):
        page = FakePage()
        bp = make_bp(tmp_path)
        url = "https://redirect-trap.example.com/loop"
        run(bp.navigate(url, page=page))
        run(bp.navigate(url, page=page))
        with pytest.raises(mod.NavigationLoopError, match="loop"):
            run(bp.navigate(url, page=page))
        # Only the two completed navigations are on record.
        assert list(bp._navigation_history).count(url) == 2

    def test_history_is_bounded_and_interleaved_urls_are_unaffected(self, tmp_path):
        page = FakePage()
        bp = make_bp(tmp_path)
        for i in range(10):
            run(bp.navigate(f"https://pages.example.com/{i}", page=page))
        assert len(bp._navigation_history) <= 8
        # Old targets fell out of the window: navigating again is legal.
        run(bp.navigate("https://pages.example.com/0", page=page))

    class FlakyGotoPage(FakePage):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.goto_failures_left = 1

        async def goto(self, url, timeout=None, wait_until=None):
            if self.goto_failures_left > 0:
                self.goto_failures_left -= 1
                raise TimeoutError("net split")
            return await super().goto(url, timeout=timeout, wait_until=wait_until)

    def test_transient_navigation_failure_retries_under_policy(self, tmp_path):
        page = self.FlakyGotoPage()
        events = []
        bp = make_bp(tmp_path)
        bp.retry_policy = mod.RetryPolicy(
            max_attempts=3, base_delay=0.0, jitter=False, on_event=events.append
        )
        result = run(bp.navigate("https://flaky.example.com", page=page))
        assert result["ok"] is True
        assert [e["event"] for e in events] == ["retry"]

    def test_open_breaker_fast_fails_navigation_without_touching_the_page(self, tmp_path):
        page = FakePage()
        bp = make_bp(tmp_path)
        breaker = mod.CircuitBreaker(failure_threshold=1, recovery_timeout=999.0)
        breaker.record_failure()               # force OPEN directly
        assert breaker.state == mod.CircuitState.OPEN
        bp.circuit_breaker = breaker
        with pytest.raises(mod.CircuitBreakerOpenError):
            run(bp.navigate("https://blocked.example.com", page=page))
        assert page.goto_calls == []

    def test_owned_page_is_cleaned_up_after_navigation(self, tmp_path):
        browser = FakeBrowser()
        bp = make_bp(tmp_path)

        async def scenario():
            bp.attach_browser(browser)
            return await bp.navigate("https://owned.example.com")

        result = run(scenario())
        assert result["ok"] is True
        ctx = browser.created_contexts[0]
        assert ctx.geolocation is not None          # geo-aligned
        assert all(p.closed for p in ctx.pages)     # ephemeral page closed

    def test_page_without_goto_is_an_honest_error(self, tmp_path):
        bp = make_bp(tmp_path)
        with pytest.raises(mod.NavigationError, match="goto"):
            run(bp.navigate("https://nope.example.com", page=object()))


# =====================================================================
# BiomechanicalInteractionEngine.type_like_human
# =====================================================================
class SleepRecorder:
    def __init__(self):
        self.delays = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


class TestHumanizedTyping:
    def make_engine_page(self):
        return mod.BiomechanicalInteractionEngine(), FakePage()

    def test_types_every_character_in_order_after_focus_click(self):
        engine, page = self.make_engine_page()
        typed = run(engine.type_like_human(page, "AAPL", selector="#search",
                                           sleep_fn=SleepRecorder()))
        assert typed == 4
        assert "".join(page.keyboard.typed) == "AAPL"
        assert page.clicks == ["#search"]

    def test_zero_sigma_gives_exact_uniform_pacing(self):
        engine, page = self.make_engine_page()
        sleeper = SleepRecorder()
        run(engine.type_like_human(page, "abc", base_delay=0.2, sigma=0.0,
                                   hesitation_probability=0.0, sleep_fn=sleeper))
        assert sleeper.delays == [0.2, 0.2, 0.2]

    def test_certain_hesitation_adds_bounded_extra_pause(self):
        engine, page = self.make_engine_page()
        sleeper = SleepRecorder()
        run(engine.type_like_human(page, "xy", base_delay=0.1, sigma=0.0,
                                   hesitation_probability=1.0, sleep_fn=sleeper))
        for extra_delay in sleeper.delays:
            assert 0.35 <= extra_delay <= 0.75      # base + uniform(0.25, 0.65)

    def test_missing_keyboard_is_a_loud_non_fallback_error(self):
        engine = mod.BiomechanicalInteractionEngine()

        class NoKeyboardPage:
            pass

        with pytest.raises(RuntimeError, match="keyboard"):
            run(engine.type_like_human(NoKeyboardPage(), "text"))

    def test_invalid_inputs_rejected_eagerly(self):
        engine, page = self.make_engine_page()
        with pytest.raises(TypeError):
            run(engine.type_like_human(page, 123, sleep_fn=SleepRecorder()))
        with pytest.raises(ValueError):
            run(engine.type_like_human(page, "x", base_delay=-1))
        with pytest.raises(ValueError):
            run(engine.type_like_human(page, "x", sigma=-0.5))
        with pytest.raises(ValueError):
            run(engine.type_like_human(page, "x", hesitation_probability=2.0))


# =====================================================================
# Session context manager
# =====================================================================
class TestSessionContextManager:
    def test_exit_flushes_pipeline_and_persists_heal_memory(self, tmp_path):
        async def scenario():
            async with make_bp(tmp_path, min_expected_throughput=1) as bp:
                await bp.collect({"id": 7}, MarketData)
                bp.heal_memory.remember("btn", "#ok")
            # After exit both durability effects must be visible.
            lines = (tmp_path / "bp.ndjson").read_text(encoding="utf-8").strip().splitlines()
            assert len(lines) == 1
            revived = mod.SelectorHealMemory(path=str(tmp_path / "heal.json"))
            assert revived.lookup("btn") == "#ok"

        run(scenario())

    def test_close_failure_inside_exit_propagates_when_body_clean(self, tmp_path):
        async def scenario():
            async with make_bp(tmp_path, min_expected_throughput=2) as bp:
                await bp.collect({"id": 1}, MarketData)   # throughput contract needs 2
            # aexit re-raises the sentinel's loud breach

        with pytest.raises(RuntimeError, match="throughput"):
            run(scenario())

    def test_body_exception_is_never_masked_by_close_failure(self, tmp_path):
        async def scenario():
            async with make_bp(tmp_path, min_expected_throughput=99) as bp:
                raise ValueError("the-real-bug")

        with pytest.raises(ValueError, match="the-real-bug"):
            run(scenario())

    def test_aenter_returns_self_for_inline_use(self, tmp_path):
        async def scenario():
            async with make_bp(tmp_path) as bp:
                assert isinstance(bp, mod.BehavioralPlaywright)

        run(scenario())


# =====================================================================
# End-to-end workflow proofs (user-written-code reduction)
# =====================================================================
class TestCommonWorkflows:
    def test_research_workflow_navigate_solve_type_collect_in_six_lines(self, tmp_path):
        """The whole common workflow -- previously ~20+ lines of acquire /
        geo-align / stealth / cleanup / flush boilerplate -- in six statements."""
        buy_btn = FakeElement(id="buy-btn", text="Buy now", aria_label="Buy now")
        page = FakePage(elements=[buy_btn], wait_results={"#buy-btn": buy_btn})

        async def workflow():
            async with make_bp(tmp_path, min_expected_throughput=1) as bp:      # 1
                nav = await bp.navigate("https://shop.example.com", page=page)   # 2
                btn = await bp.solve("#broken-dynamic-id", "Buy now",             # 3
                                     logical_name="buy-btn", page=page)
                typed = await mod.BiomechanicalInteractionEngine().type_like_human(  # 4
                    page, "AAPL", selector="#ticker-input",
                    base_delay=0.01, sigma=0.0, hesitation_probability=0.0,
                    sleep_fn=SleepRecorder())
                got = await bp.collect({"id": 1}, MarketData)                     # 5
                return nav, btn, typed, got                                       # 6

        nav, btn, typed, got = run(workflow())
        assert nav["ok"] is True
        assert btn is not None
        assert typed == 4
        assert "".join(page.keyboard.typed) == "AAPL"
        assert got["status"] == "ingested"
        # Healing remembered the recovered element for next run.
        assert (tmp_path / "heal.json").exists()

    def test_resilient_read_workflow_with_one_configuration_line(self, tmp_path):
        """Retry/breaker protection is one constructor argument, zero call-site code."""
        browser = FakeBrowser()

        async def workflow():
            bp = make_bp(tmp_path)                                               # 1
            bp.retry_policy = mod.RetryPolicy(max_attempts=3, base_delay=0.0)     # 2 <- only line
            bp.attach_browser(browser)
            return await bp.run(lambda p: {"visited": True})

        result = run(workflow())
        assert result == {"visited": True}
