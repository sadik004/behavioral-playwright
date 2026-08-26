"""Phase 2/3 regression suite: correctness hardening of every component.

Covers the pure-logic surface of all 29 patches without requiring
playwright/curl_cffi/frida to be installed (quarantine paths included).
"""
import asyncio
import json
import logging
import math
import os
import random
import re
import sys
from typing import Optional

import pytest
from pydantic import BaseModel

import fakes
from fakes import (
    FakeBrowser,
    FakeContext,
    FakeElement,
    FakePage,
    PermissiveSchema,
    StrictIdSchema,
    run,
)

import behavioral_evasion_ten_patches_hardened_v15 as mod


# =====================================================================
# Logging / credential sanitization
# =====================================================================
class TestLogSanitization:
    def test_proxy_credentials_masked(self):
        formatter = mod.SanitizedLogFormatter("%(message)s")
        out = formatter.format(logging.LogRecord(
            "t", logging.INFO, "p", 1,
            "connecting via socks5://sec_user:secret_password_123@proxy-us-exit:9050",
            (), None))
        assert "secret_password_123" not in out
        assert "socks5://sec_user:******@" in out

    def test_bearer_token_masked(self):
        formatter = mod.SanitizedLogFormatter("%(message)s")
        out = formatter.format(logging.LogRecord(
            "t", logging.INFO, "p", 1, "Authorization: Bearer abc.def-ghi_jkl", (), None))
        assert "abc.def-ghi_jkl" not in out
        assert "Bearer *****" in out

    def test_benign_message_untouched(self):
        formatter = mod.SanitizedLogFormatter("%(message)s")
        msg = "plain log line with no secrets"
        out = formatter.format(logging.LogRecord("t", logging.INFO, "p", 1, msg, (), None))
        assert out == msg

    def test_framework_logging_is_opt_in_and_idempotent(self):
        root_handlers_before = list(logging.getLogger().handlers)
        h1 = mod.configure_framework_logging(level=logging.WARNING)
        h2 = mod.configure_framework_logging(level=logging.WARNING)
        fw = logging.getLogger("BehavioralPlaywright.EnterpriseV13")
        sanitized = [h for h in fw.handlers if getattr(h, "_behavioral_sanitized_handler", False)]
        assert len(sanitized) == 1 and sanitized[0] is h2
        assert list(logging.getLogger().handlers) == root_handlers_before
        assert fw.propagate is False

    def test_import_does_not_install_stdout_handler(self):
        # Import-time behaviour is checked in a fresh interpreter so pytest's
        # own LogCaptureHandlers cannot contaminate the assertion.
        import subprocess
        code = (
            "import logging, sys;"
            "import behavioral_evasion_ten_patches_hardened_v15 as m;"
            "fw = logging.getLogger('BehavioralPlaywright.EnterpriseV13');"
            "plain = [h for h in fw.handlers"
            " if isinstance(h, logging.StreamHandler)"
            " and not getattr(h, '_behavioral_sanitized_handler', False)];"
            "print('PLAIN:', plain)"
        )
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert proc.returncode == 0
        assert "PLAIN: []" in proc.stdout


# =====================================================================
# TLS/JA4 spoofer quarantine
# =====================================================================
class TestTLSJA4Spoofer:
    def test_missing_curl_cffi_fails_loudly(self):
        if mod.CURL_CFFI_AVAILABLE:
            pytest.skip("curl_cffi installed; fallback path unreachable")
        spoofer = mod.TLSJA4Spoofer()
        with pytest.raises(RuntimeError, match="curl_cffi"):
            spoofer.get_session()


# =====================================================================
# Biomechanical engine
# =====================================================================
class TestBiomechanicalInteractionEngine:
    def test_trajectory_reaches_target(self):
        eng = mod.BiomechanicalInteractionEngine()
        random.seed(7)
        pts = eng.generate_trajectory((0.0, 0.0), (300.0, 200.0), steps=35)
        assert pts
        dist_final = math.hypot(pts[-1][0] - 300.0, pts[-1][1] - 200.0)
        assert dist_final < 15.0

    def test_trajectory_step_count_is_load_bearing(self):
        eng = mod.BiomechanicalInteractionEngine()
        random.seed(11)
        coarse = eng.generate_trajectory((0.0, 0.0), (600.0, 0.0), steps=2)
        random.seed(11)
        fine = eng.generate_trajectory((0.0, 0.0), (600.0, 0.0), steps=400)
        # steps=2 seeds max_step=15 (capped); steps=400 seeds max_step=1.5.
        assert len(fine) > len(coarse) * 3

    def test_trajectory_rejects_bad_steps(self):
        eng = mod.BiomechanicalInteractionEngine()
        for bad in (0, -3, True, 2.5, "10", None):
            with pytest.raises(ValueError):
                eng.generate_trajectory((0, 0), (10, 10), steps=bad)

    def test_trajectory_same_point_returns_empty(self):
        eng = mod.BiomechanicalInteractionEngine()
        assert eng.generate_trajectory((5, 5), (5, 5)) == []

    def test_trajectory_capped_at_1000_points(self):
        eng = mod.BiomechanicalInteractionEngine()
        pts = eng.generate_trajectory((0.0, 0.0), (100000.0, 100000.0), steps=1)
        assert len(pts) <= 1000

    def test_smooth_scroll_zero_delta_is_noop(self):
        page = FakePage()
        run(mod.BiomechanicalInteractionEngine().smooth_scroll(page, 0))
        assert page.scroll_by == [] and page.scripts == []

    def test_smooth_scroll_total_matches_positive_delta(self):
        page = FakePage()
        run(mod.BiomechanicalInteractionEngine().smooth_scroll(page, 600))
        assert page.scroll_by
        assert sum(page.scroll_by) == 600

    def test_smooth_scroll_total_matches_negative_delta(self):
        page = FakePage()
        run(mod.BiomechanicalInteractionEngine().smooth_scroll(page, -250))
        assert sum(page.scroll_by) == -250
        assert all(v < 0 or v > 0 for v in page.scroll_by)

    def test_move_and_click_full_sequence(self):
        page = FakePage(wait_results={
            "#btn": FakeElement(box={"x": 180, "y": 140, "width": 80, "height": 30}),
        })
        eng = mod.BiomechanicalInteractionEngine()
        run(eng.move_and_click(page, "#btn"))
        assert page.mouse_moves, "expected trajectory moves"
        assert page.down_up == 2  # down + up
        end_x, end_y = eng.current_x, eng.current_y
        assert 180 <= end_x <= 260 and 140 <= end_y <= 170

    def test_move_and_click_falls_back_without_box(self):
        page = FakePage(wait_results={"#btn": FakeElement(box=None)})
        run(mod.BiomechanicalInteractionEngine().move_and_click(page, "#btn"))
        assert page.clicks == ["#btn"]
        assert page.down_up == 0


# =====================================================================
# Stealth injectors (CDP shield / hardware / wasm / geo)
# =====================================================================
class TestStealthInjectors:
    def test_cdp_shield_injects_native_spoof(self):
        page = FakePage()
        run(mod.CDPEvasionShield(page).apply_cdp_stealth_binding())
        assert len(page.scripts) == 1
        assert "nativeRegistry" in page.scripts[0]
        assert "prepareStackTrace" in page.scripts[0]
        assert "/*NATIVE_SPOOF_JS*/" not in page.scripts[0]

    def test_hardware_spoofer_injects_webgl_override(self):
        page = FakePage()
        run(mod.HardwareOSSpoofer(page).inject_hardware_stealth())
        script = page.scripts[0]
        assert "37445" in script and "37446" in script  # UNMASKED_VENDOR/RENDERER params
        assert "navigator" in script
        assert "/*NATIVE_SPOOF_JS*/" not in script

    def test_wasm_interceptor_hooks_instantiate(self):
        page = FakePage()
        run(mod.WasmMemoryInterceptor().hook_page_wasm_module(page))
        assert "WebAssembly.instantiate" in page.scripts[0]

    def test_geo_aligner_configures_context(self):
        ctx = FakeContext()
        run(mod.DynamicUSGeoIPAligner("us-west").align_context(ctx))
        assert ctx.geolocation == {"latitude": 34.0522, "longitude": -118.2437}
        assert ctx.permissions == ["geolocation"]
        assert len(ctx.init_scripts) == 1
        assert "America/Los_Angeles" in ctx.init_scripts[0]
        assert "LOCALE_PLACEHOLDER" not in ctx.init_scripts[0]

    def test_geo_aligner_unknown_region_falls_back_east(self):
        ctx = FakeContext()
        run(mod.DynamicUSGeoIPAligner("us-nowhere").align_context(ctx))
        assert "America/New_York" in ctx.init_scripts[0]


# =====================================================================
# Context rotation lifecycle
# =====================================================================
class TestContextRotator:
    def test_invalid_threshold_rejected(self):
        with pytest.raises(ValueError, match="recycle_threshold"):
            mod.ContextRotator(FakeBrowser(), recycle_threshold=0)

    def test_initial_acquisition_creates_context(self):
        rotator = mod.ContextRotator(FakeBrowser(), recycle_threshold=50)
        ctx = run(rotator.get_healthy_context())
        assert ctx is not None and rotator.request_count == 0

    def test_rotation_at_threshold_new_before_old(self):
        browser = FakeBrowser()
        rotator = mod.ContextRotator(browser, recycle_threshold=2)
        first = run(rotator.get_healthy_context())    # initial acquisition
        second = run(rotator.get_healthy_context())   # count 1 < 2 -> same context
        assert second is first
        third = run(rotator.get_healthy_context())    # count 2 >= 2 -> rotate
        assert third is not None
        assert first.closed and not third.closed      # old torn down after swap
        assert rotator.current_context is third

    def test_manager_backed_replacement(self):
        class Manager:
            def __init__(self):
                self.created = []
            async def create_isolated_context(self):
                c = FakeContext()
                self.created.append(c)
                return c
        mgr = Manager()
        rotator = mod.ContextRotator(None, recycle_threshold=1)
        ctx = run(rotator.get_healthy_context(manager=mgr))
        assert ctx in mgr.created

    def test_failed_rotation_preserves_current_context(self):
        browser = FakeBrowser()
        rotator = mod.ContextRotator(browser, recycle_threshold=1)
        good = run(rotator.get_healthy_context())
        browser.fail_next_new_context(RuntimeError("renderer gone"))
        with pytest.raises(mod.ContextRotationError, match="left intact"):
            run(rotator.get_healthy_context())
        assert rotator.current_context is good
        assert not good.closed


# =====================================================================
# Session state vault
# =====================================================================
class TestSessionStateVault:
    def _valid_state(self):
        return {"cookies": [{"name": "sid"}], "origins": [{"origin": "https://x"}]}

    def test_save_atomic_roundtrip(self, tmp_path):
        vault = mod.SessionStateVault(str(tmp_path / "state.json"))
        ctx = FakeContext(storage_state=self._valid_state())
        run(vault.save_state(ctx))
        data = json.loads(open(vault.filepath, encoding="utf-8").read())
        assert data["cookies"] == [{"name": "sid"}]
        assert not os.path.exists(vault.filepath + ".tmp")

    def test_unsupported_context_never_clobbers_file(self, tmp_path):
        path = tmp_path / "state.json"
        path.write_text('{"previous": true}', encoding="utf-8")
        vault = mod.SessionStateVault(str(path))
        with pytest.raises(mod.SessionStateError, match="left untouched"):
            run(vault.save_state(None))
        assert json.loads(path.read_text(encoding="utf-8")) == {"previous": True}

    def test_export_failure_preserves_existing_file(self, tmp_path):
        path = tmp_path / "state.json"
        path.write_text('{"previous": true}', encoding="utf-8")
        vault = mod.SessionStateVault(str(path))
        ctx = FakeContext(storage_error=RuntimeError("target closed"))
        with pytest.raises(mod.SessionStateError, match="preserved"):
            run(vault.save_state(ctx))
        assert json.loads(path.read_text(encoding="utf-8")) == {"previous": True}

    def test_malformed_export_rejected(self, tmp_path):
        vault = mod.SessionStateVault(str(tmp_path / "state.json"))
        ctx = FakeContext(storage_state={"cookies": "not-a-list"})
        with pytest.raises(mod.SessionStateError, match="malformed"):
            run(vault.save_state(ctx))

    def test_write_failure_removes_tmp_and_preserves(self, tmp_path, monkeypatch):
        vault = mod.SessionStateVault(str(tmp_path / "state.json"))
        ctx = FakeContext(storage_state=self._valid_state())
        run(vault.save_state(ctx))  # seed a valid previous file

        def boom(*a, **kw):
            raise OSError("disk full")
        monkeypatch.setattr(vault, "_atomic_write", boom)
        with pytest.raises(mod.SessionStateError, match="atomic write failed"):
            run(vault.save_state(ctx))
        assert not os.path.exists(vault.filepath + ".tmp")
        # previous content still valid JSON
        json.loads(open(vault.filepath, encoding="utf-8").read())

    def test_load_state_includes_storage_when_present(self, tmp_path):
        path = tmp_path / "state.json"
        path.write_text('{"cookies": [], "origins": []}', encoding="utf-8")
        vault = mod.SessionStateVault(str(path))
        browser = FakeBrowser()
        run(vault.load_state(browser, proxy_config={"server": "http://p:1"}))
        kw = browser.context_kwargs[0]
        assert kw["storage_state"] == str(path)
        assert kw["proxy"] == {"server": "http://p:1"}

    def test_load_state_without_file_omits_storage(self, tmp_path):
        vault = mod.SessionStateVault(str(tmp_path / "missing.json"))
        browser = FakeBrowser()
        run(vault.load_state(browser))
        assert "storage_state" not in browser.context_kwargs[0]


# =====================================================================
# DOM -> Markdown simplifier
# =====================================================================
class TestDOMToMarkdownSimplifier:
    def test_default_noise_selectors_serialized(self):
        page = FakePage(evaluate_return="# Title\n\nbody text")
        simplifier = mod.DOMToMarkdownSimplifier()
        md = run(simplifier.simplify(page))
        assert '"header"' in page.scripts[0] and '".ads"' in page.scripts[0]
        assert md == "# Title\n\nbody text"

    def test_custom_selectors_drive_cleanup_script(self):
        page = FakePage(evaluate_return="clean")
        simplifier = mod.DOMToMarkdownSimplifier(noise_selectors=[".promo", ".promo", "", "  ", ".banner"])
        run(simplifier.simplify(page))
        payload = json.loads(re.search(r"\[.*?\]", page.scripts[0]).group(0))
        assert payload == [".promo", ".banner"]  # deduped, blanks dropped, order kept

    def test_page_without_evaluate_raises_not_fabricates(self):
        with pytest.raises(RuntimeError, match="evaluate"):
            run(mod.DOMToMarkdownSimplifier().simplify(object()))

    def test_non_string_evaluate_result_raises(self):
        page = FakePage(evaluate_return={"oops": True})
        with pytest.raises(RuntimeError, match="instead of markdown"):
            run(mod.DOMToMarkdownSimplifier().simplify(page))


# =====================================================================
# Quality sentinel (honeypot + schema drift)
# =====================================================================
class TestQualitySentinel:
    def test_display_none_is_honeypot(self):
        s = mod.QualitySentinel()
        assert s.check_honeypots({"style": {"display": "none"}}) is True

    def test_numeric_opacity_variants(self):
        s = mod.QualitySentinel()
        assert s.check_honeypots({"style": {"opacity": 0}}) is True
        assert s.check_honeypots({"style": {"opacity": "0.0"}}) is True
        assert s.check_honeypots({"style": {"opacity": "0.5"}}) is False

    def test_out_of_range_opacity_ignored_not_clamped(self):
        s = mod.QualitySentinel()
        assert s.check_honeypots({"style": {"opacity": 7}}) is False

    def test_unparseable_signals_ignored(self):
        s = mod.QualitySentinel()
        meta = {
            "style": {"opacity": "invisible", "display": None},
            "boundingBox": {"height": "tall", "width": None},
        }
        assert s.check_honeypots(meta) is False

    def test_nan_and_bool_metrics_rejected(self):
        s = mod.QualitySentinel()
        assert s.check_honeypots({"style": {"opacity": float("nan")}}) is False
        assert s.check_honeypots({"style": {"opacity": False}}) is False

    def test_collapsed_dimensions_are_honeypot(self):
        s = mod.QualitySentinel()
        assert s.check_honeypots({"boundingBox": {"height": 0, "width": 40}}) is True
        assert s.check_honeypots({"boundingBox": {"height": 30, "width": -1}}) is True
        assert s.check_honeypots({"boundingBox": {"height": 30, "width": 12}}) is False

    def test_malformed_metadata_is_visible(self):
        for bad in (None, "style-string", ["list"], 42):
            assert mod.QualitySentinel().check_honeypots(bad) is False

    def test_blank_payload_counts_as_failure(self):
        s = mod.QualitySentinel(window_size=2)
        assert s.monitor_data_quality("u", {}, StrictIdSchema) is False

    def test_schema_drift_detected_then_halts(self):
        s = mod.QualitySentinel(max_allowed_failure_ratio=0.5, window_size=3)
        assert s.monitor_data_quality("u", {"id": 1}, StrictIdSchema) is True    # [T]
        assert s.monitor_data_quality("u", {"id": "bad"}, StrictIdSchema) is False   # window <3
        assert s.monitor_data_quality("u", {"id": 2}, StrictIdSchema) is True    # [T,F,T] = 1/3
        with pytest.raises(RuntimeError, match="Pipeline halted"):
            s.monitor_data_quality("u", {"id": "worse"}, StrictIdSchema)          # [F,T,F] = 2/3


# =====================================================================
# Passive OS tuner (platform-dependent)
# =====================================================================
class TestPassiveOSFingerprintTuner:
    def test_non_linux_skips_kernel_tuning(self):
        if sys.platform.startswith("linux"):
            pytest.skip("only meaningful on non-Linux hosts")
        assert mod.PassiveOSFingerprintTuner().tune_kernel_tcp_stack() is False


# =====================================================================
# VM/AST deobfuscator
# =====================================================================
OBF_CODE = (
    "var _0x5a1b = ['\\x68\\x65\\x6c\\x6c\\x6f', '\\x77\\x6f\\x72\\x6c\\x64'];\n"
    "var _0x3f2d = function(_0xa) { return _0x5a1b[_0xa]; };\n"
    "var greeting = _0x3f2d(0x0);\n"
    "var place = _0x3f2d(0x1);\n"
)

class TestVMASTDeobfuscator:
    def test_constant_folding(self):
        out = mod.VMASTDeobfuscator().deobfuscate_obfuscated_tag("var x = !![]; var y = ![];")
        assert "true" in out and "false" in out
        assert "!![]" not in out and "![]" not in out

    def test_proxy_array_substitution_and_dce(self):
        out = mod.VMASTDeobfuscator().deobfuscate_obfuscated_tag(OBF_CODE)
        assert '"hello"' in out and '"world"' in out
        assert "_0x3f2d(0x0)" not in out and "_0x3f2d(0x1)" not in out
        assert "_0x5a1b" not in out.replace("_0x5a1b[_0xa]", "")  # array definition eliminated

    def test_unparseable_array_raises_instead_of_fabricating(self):
        # Array regex MATCHES but the content is not valid JSON once quotes
        # are normalized -- must raise, never fall back to placeholder strings.
        bad = "var _0xbbbb = ['a\"b', 'c'];\nvar v = _0xf(0x0);"
        with pytest.raises(ValueError, match="could not be parsed"):
            mod.VMASTDeobfuscator().deobfuscate_obfuscated_tag(bad)

    def test_out_of_range_index_left_alone(self):
        code = ("var _0xcccc = ['only'];\n"
                "var _0xdddd = function(_0xa) { return _0xcccc[_0xa]; };\n"
                "var v = _0xdddd(0x9);")
        out = mod.VMASTDeobfuscator().deobfuscate_obfuscated_tag(code)
        assert "_0xdddd(0x9)" in out  # untouched, never invented

    def test_decimal_indices_supported(self):
        code = ("var _0xeeee = ['alpha', 'beta'];\n"
                "var _0xffff = function(_0xb) { return _0xeeee[_0xb]; };\n"
                "var v = _0xffff(1);")
        out = mod.VMASTDeobfuscator().deobfuscate_obfuscated_tag(code)
        assert '"beta"' in out


# =====================================================================
# Microtask timing aligner (quarantined by default)
# =====================================================================
class TestMicrotaskTimingAligner:
    def test_disabled_default_is_explicit_noop(self):
        page = FakePage()
        result = run(mod.MicrotaskTimingAligner().inject_timing_jitter(page))
        assert result is False
        assert page.scripts == []

    def test_forced_enable_injects_and_reports_true(self):
        page = FakePage()
        result = run(mod.MicrotaskTimingAligner(enabled=True).inject_timing_jitter(page))
        assert result is True
        assert "Promise.prototype.then" in page.scripts[0]

    def test_enabled_without_evaluate_reports_false(self):
        result = run(mod.MicrotaskTimingAligner(enabled=True).inject_timing_jitter(object()))
        assert result is False


# =====================================================================
# Persistence pipeline + OS guard + strict context manager
# =====================================================================
class TestBasePersistencePipeline:
    def test_flush_at_threshold_and_close(self, tmp_path):
        path = tmp_path / "out.ndjson"
        pipe = mod.BasePersistencePipeline(str(path))

        async def scenario():
            pipe.open()
            for i in range(4):
                await pipe.append_record({"i": i})
            assert path.exists() is False          # buffered
            await pipe.append_record({"i": 4})     # crosses threshold of 5
            await pipe.close()                     # empty flush no-op safe

        run(scenario())
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 5
        assert [json.loads(l)["i"] for l in lines] == [0, 1, 2, 3, 4]


class TestOSResourceGuard:
    def test_small_concurrency_passes_through(self):
        assert mod.OSResourceGuard().check_os_limits(concurrency_estimate=5) == 5

    def test_extreme_concurrency_clamped_to_safe_max(self):
        clamped = mod.OSResourceGuard().check_os_limits(concurrency_estimate=10**9)
        try:
            import resource
            soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        except ImportError:
            soft = 8192
        assert clamped == max(1, soft // 20)


class TestStrictContextManager:
    def test_proxy_forwarded_and_no_webrtc_shim(self):
        browser = FakeBrowser()

        async def scenario():
            mgr = mod.StrictContextManager(browser)
            return await mgr.create_isolated_context(proxy_config={"server": "socks5://x"})

        ctx = run(scenario())
        assert browser.context_kwargs[0]["proxy"] == {"server": "socks5://x"}
        assert ctx.init_scripts == []  # honest: nothing injected# =====================================================================
# ITCH parser / LOB
# =====================================================================
class TestITCHParserLOB:
    def make_book(self):
        r = mod.ITCHParserLOBReconstructor()
        r.parse_itch_message("A", {"isin": "X", "price": 99.0, "shares": 100, "order_id": "b1", "side": "B"})
        r.parse_itch_message("A", {"isin": "X", "price": 100.0, "shares": 200, "order_id": "b2", "side": "B"})
        r.parse_itch_message("A", {"isin": "X", "price": 101.0, "shares": 150, "order_id": "s1", "side": "S"})
        return r

    def test_book_sorted_sides(self):
        snap = self.make_book().get_order_book_snapshot("X")
        assert snap["bids"][0]["price"] == 100.0
        assert snap["asks"][0]["price"] == 101.0

    def test_partial_execution_keeps_residual(self):
        r = self.make_book()
        r.parse_itch_message("E", {"isin": "X", "order_id": "b2", "shares": 50})
        snap = r.get_order_book_snapshot("X")
        assert snap["bids"][0]["shares"] == 150

    def test_full_execution_removes_order(self):
        r = self.make_book()
        r.parse_itch_message("E", {"isin": "X", "order_id": "b2", "shares": 200})
        snap = r.get_order_book_snapshot("X")
        assert [o["order_id"] for o in snap["bids"]] == ["b1"]

    def test_over_execution_removes_order(self):
        r = self.make_book()
        r.parse_itch_message("E", {"isin": "X", "order_id": "b2", "shares": 500})
        assert all(o["order_id"] != "b2" for o in r.get_order_book_snapshot("X")["bids"])

    def test_cancel_removes_order_both_sides(self):
        r = self.make_book()
        r.parse_itch_message("C", {"isin": "X", "order_id": "s1"})
        assert r.get_order_book_snapshot("X")["asks"] == []
        r.parse_itch_message("C", {"isin": "X", "order_id": "b1"})
        assert [o["order_id"] for o in r.get_order_book_snapshot("X")["bids"]] == ["b2"]

    def test_depth_parameter_slices_snapshot(self):
        r = self.make_book()
        r.parse_itch_message("A", {"isin": "X", "price": 98.0, "shares": 10, "order_id": "b0", "side": "B"})
        assert len(r.get_order_book_snapshot("X", depth=2)["bids"]) == 2

    def test_unknown_isin_empty_book(self):
        assert self.make_book().get_order_book_snapshot("NOPE") == {"bids": [], "asks": []}

    def test_dollar_bar_math(self):
        trades = [
            {"price": 185.50, "shares": 200},   # 37,100
            {"price": 185.55, "shares": 150},   # cumulative 64,932.5 >= 50k
            {"price": 186.00, "shares": 100},   # leftover below threshold
        ]
        bars = mod.ITCHParserLOBReconstructor().generate_dollar_bars(trades, dollar_threshold=50000.0)
        assert len(bars) == 1
        bar = bars[0]
        assert bar["open"] == 185.50 and bar["high"] == 185.55
        assert bar["low"] == 185.50 and bar["close"] == 185.55
        assert bar["volume"] == 350
        assert bar["dollar_value"] == pytest.approx(64932.5)


# =====================================================================
# EDGAR PiT aligner
# =====================================================================
class TestEDGARPiTAligner:
    def test_alignment_outputs_dual_timestamps(self):
        aligned = mod.EDGARPiTAligner().align_filing_metadata({
            "cik": "0000320193",
            "period_of_report_epoch": 1787630000,
            "sec_dissemination_epoch": 1787630500,
        })
        assert aligned["event_timestamp"] == 1787630000
        assert aligned["knowledge_timestamp"] == 1787630500

    def test_numeric_string_epochs_coerced(self):
        aligned = mod.EDGARPiTAligner().align_filing_metadata({
            "period_of_report_epoch": "1000", "sec_dissemination_epoch": "2000",
        })
        assert aligned["knowledge_timestamp"] == 2000.0

    @pytest.mark.parametrize("payload", [
        {},
        {"sec_dissemination_epoch": 5},
        {"period_of_report_epoch": None, "sec_dissemination_epoch": 5},
    ])
    def test_missing_timestamps_refused(self, payload):
        with pytest.raises(mod.FilingTimestampError, match="missing"):
            mod.EDGARPiTAligner().align_filing_metadata(payload)

    def test_malformed_timestamps_refused(self):
        with pytest.raises(mod.FilingTimestampError, match="numeric epoch"):
            mod.EDGARPiTAligner().align_filing_metadata({
                "period_of_report_epoch": "not-a-number", "sec_dissemination_epoch": 5})

    def test_nan_inf_refused(self):
        with pytest.raises(mod.FilingTimestampError, match="NaN"):
            mod.EDGARPiTAligner().align_filing_metadata({
                "period_of_report_epoch": float("nan"), "sec_dissemination_epoch": 5})

    def test_lookahead_breach_raises(self):
        with pytest.raises(ValueError, match="Temporal Contract Breach"):
            mod.EDGARPiTAligner().align_filing_metadata({
                "period_of_report_epoch": 5000, "sec_dissemination_epoch": 4000})


# =====================================================================
# Synthetic market generator
# =====================================================================
class TestMarketSyntheticGenerator:
    def test_short_seed_rejected(self):
        with pytest.raises(ValueError, match="Insufficient seed"):
            mod.MarketSyntheticGenerator().generate_synthetic_series([1.0, 2.0])

    def test_output_shape_and_positivity(self):
        gen = mod.MarketSyntheticGenerator(sequence_length=12)
        series = gen.generate_synthetic_series([185.0, 185.2, 185.1, 185.3, 185.5])
        assert len(series) == 13
        assert series[0] == 185.0
        assert all(p > 0 for p in series)

    def test_seeded_reproducibility(self):
        random.seed(42)
        a = mod.MarketSyntheticGenerator(5).generate_synthetic_series([10.0] * 6)
        random.seed(42)
        b = mod.MarketSyntheticGenerator(5).generate_synthetic_series([10.0] * 6)
        assert a == b


# =====================================================================
# Entity resolver (fabrication removed + boundary matching)
# =====================================================================
class TestCapitalMarketEntityResolver:
    def test_known_entity_resolved(self):
        ids = mod.CapitalMarketEntityResolver().resolve("Apple Inc.")
        assert ids["isin"] == "US0378331005" and ids["ticker"] == "AAPL US"

    def test_case_insensitive_embedded_match(self):
        ids = mod.CapitalMarketEntityResolver().resolve("the MICROSOFT corporation")
        assert ids["cusip"] == "594918104"

    def test_substring_false_positive_blocked(self):
        with pytest.raises(mod.EntityResolutionError, match="no verified mapping"):
            mod.CapitalMarketEntityResolver().resolve("Pineapple Corp")

    def test_unknown_entity_raises_never_fabricates(self):
        with pytest.raises(mod.EntityResolutionError, match="Fabricated"):
            mod.CapitalMarketEntityResolver().resolve("Unknown Startup Inc")

    def test_empty_or_non_string_rejected(self):
        resolver = mod.CapitalMarketEntityResolver()
        for bad in ("", "   ", None, 123):
            with pytest.raises(mod.EntityResolutionError):
                resolver.resolve(bad)

    def test_registry_extension_enables_resolution(self):
        resolver = mod.CapitalMarketEntityResolver()
        resolver.registry["acme"] = {"isin": "US0000000001", "cusip": "000000001",
                                     "figi": "BBG000000001", "ticker": "ACME US"}
        assert resolver.resolve("Acme Ltd")["isin"] == "US0000000001"


# =====================================================================
# Data contract sentinel
# =====================================================================
class PitSchema(BaseModel):
    value: float
    event_timestamp: float
    knowledge_timestamp: float


class NullableValueSchema(BaseModel):
    value: Optional[float] = None
    event_timestamp: float
    knowledge_timestamp: float


def pit_record(value=1.0, **over):
    base = {"value": value, "event_timestamp": 1.0, "knowledge_timestamp": 2.0}
    base.update(over)
    return base


class TestQuantDataContractSentinel:
    def test_negative_throughput_config_rejected(self):
        with pytest.raises(ValueError):
            mod.QuantDataContractSentinel(min_expected_throughput=-1)

    def test_pit_dual_timestamps_mandatory(self):
        s = mod.QuantDataContractSentinel(min_expected_throughput=0)
        with pytest.raises(ValueError, match="PIT timestamps"):
            s.validate_data_contract({"value": 1.0}, PitSchema)

    def test_schema_drift_halts_loudly(self):
        s = mod.QuantDataContractSentinel(min_expected_throughput=0)
        with pytest.raises(RuntimeError, match="Schema drift"):
            s.validate_data_contract(pit_record(value="NaN!"), PitSchema)

    def test_null_spike_breaker(self):
        s = mod.QuantDataContractSentinel(min_expected_throughput=0, max_null_ratio=0.15)
        s.validate_data_contract(pit_record(value=None), NullableValueSchema)  # ratio 1.0 but n<5
        for _ in range(3):
            s.validate_data_contract(pit_record(), NullableValueSchema)
        with pytest.raises(RuntimeError, match="Null-value contract breach"):
            s.validate_data_contract(pit_record(), NullableValueSchema)  # n=5, ratio 0.2

    def test_throughput_breach_detected(self):
        s = mod.QuantDataContractSentinel(min_expected_throughput=3)
        s.validate_data_contract(pit_record(), PitSchema)
        with pytest.raises(RuntimeError, match="throughput contract breach"):
            s.check_throughput()

    def test_throughput_override_and_success_return(self):
        s = mod.QuantDataContractSentinel(min_expected_throughput=5)
        s.validate_data_contract(pit_record(), PitSchema)
        assert s.check_throughput(min_records=1) == 1
        with pytest.raises(ValueError):
            s.check_throughput(min_records=-2)


# =====================================================================
# Quant persistence pipeline
# =====================================================================
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


class TestQuantPersistencePipeline:
    def test_ingest_resolves_entity_and_writes_ndjson(self, tmp_path):
        path = tmp_path / "pit.ndjson"
        pipe = mod.QuantPersistencePipeline(str(path), min_expected_throughput=1)

        async def scenario():
            pipe.open()
            await pipe.ingest_market_record({"id": 1, "company": "Apple Inc.", "rank": 4.9}, MarketData)
            await pipe.close()

        run(scenario())
        rec = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        assert rec["isin"] == "US0378331005"
        assert rec["event_timestamp"] < rec["knowledge_timestamp"]

    def test_close_enforces_minimum_throughput(self, tmp_path):
        pipe = mod.QuantPersistencePipeline(str(tmp_path / "x.ndjson"), min_expected_throughput=1)

        async def scenario():
            pipe.open()
            with pytest.raises(RuntimeError, match="throughput contract breach"):
                await pipe.close()

        run(scenario())

    def test_unknown_company_blocks_ingestion(self, tmp_path):
        pipe = mod.QuantPersistencePipeline(str(tmp_path / "x.ndjson"), min_expected_throughput=0)

        async def scenario():
            pipe.open()
            with pytest.raises(mod.EntityResolutionError):
                await pipe.ingest_market_record({"id": 1, "company": "Mystery LLC", "rank": 1.0}, MarketData)

        run(scenario())

    def test_event_time_override_respected(self, tmp_path):
        pipe = mod.QuantPersistencePipeline(str(tmp_path / "x.ndjson"), min_expected_throughput=0)

        async def scenario():
            pipe.open()
            await pipe.ingest_market_record(
                {"id": 1, "company": "Tesla", "rank": 2.0}, MarketData, event_time=1000.0)
            await pipe.close()

        run(scenario())
        rec = json.loads((tmp_path / "x.ndjson").read_text(encoding="utf-8").splitlines()[0])
        assert rec["event_timestamp"] == 1000.0


# =====================================================================
# Frida engine (quarantine when unavailable)
# =====================================================================
class TestFridaNativeHookEngine:
    def test_hook_script_contains_ssl_write(self):
        script = mod.FridaNativeHookEngine().generate_native_ssl_hook_script()
        assert "SSL_write" in script and "Interceptor.attach" in script

    def test_unavailable_frida_returns_false_no_callback(self):
        try:
            import frida  # noqa: F401
        except ImportError:
            fired = []
            result = mod.FridaNativeHookEngine().spawn_and_hook(fired.append)
            assert result is False
            assert fired == []
        else:
            pytest.skip("frida installed; quarantine path unreachable")


# =====================================================================
# Mitmproxy interceptor
# =====================================================================
class MockRequest:
    pretty_url = "https://host/api/v3/market-depth"
    host = "host"


class MockFlowOffNamespace:
    class request:
        pretty_url = "https://host/other/path"
        host = "host"


class MockFlow:
    def __init__(self, content=b"\x08\x6e\x12\x04data"):
        self.request = MockRequest()
        self.response = type("R", (), {"content": content})()


class TestMitmproxyStreamInterceptor:
    def test_off_namespace_ignored(self):
        addon = mod.MitmproxyStreamInterceptor()
        assert addon.response(MockFlowOffNamespace())["status"] == "ignored"

    def test_capture_retains_raw_bytes_never_decodes(self):
        addon = mod.MitmproxyStreamInterceptor(retain_last=3)
        status = addon.response(MockFlow(content=b"raw-bytes"))
        assert status == {"status": "captured_unprocessed", "bytes": 9}
        assert addon.captured_frames[-1] == b"raw-bytes"
        assert addon.frames_captured == 1

    def test_retain_window_bounded(self):
        addon = mod.MitmproxyStreamInterceptor(retain_last=2)
        for _ in range(5):
            addon.response(MockFlow())
        assert len(addon.captured_frames) == 2

    def test_processing_error_counted_not_swallowed(self):
        addon = mod.MitmproxyStreamInterceptor()
        status = addon.response(object())  # no .request attr
        assert status["status"] == "error"
        assert addon.dispatch_failures == 1

    def test_submit_unconfigured(self):
        assert mod.MitmproxyStreamInterceptor().submit_ingestion({}) == {"status": "unconfigured"}

    def test_submit_completed_on_fresh_loop(self, tmp_path):
        pipe = mod.QuantPersistencePipeline(str(tmp_path / "m.ndjson"), min_expected_throughput=0)
        pipe.open()
        addon = mod.MitmproxyStreamInterceptor(quant_pipeline=pipe, schema_class=PitSchema)
        record = {"value": 1.0}
        result = addon.submit_ingestion(record)
        assert result["status"] == "completed"

        async def finish():
            await pipe.close()
        run(finish())
        lines = (tmp_path / "m.ndjson").read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

    def test_submit_scheduled_on_running_loop(self, tmp_path):
        pipe = mod.QuantPersistencePipeline(str(tmp_path / "m.ndjson"), min_expected_throughput=0)
        pipe.open()
        addon = mod.MitmproxyStreamInterceptor(quant_pipeline=pipe, schema_class=PitSchema)

        async def scenario():
            result = addon.submit_ingestion({"value": 2.0})
            assert result["status"] == "scheduled"
            await asyncio.sleep(0.05)
            await result["task"]
            await pipe.close()

        run(scenario())

    def test_submit_failure_counted(self):
        pipe = object()  # has no ingest_market_record -> AttributeError inside coroutine
        addon = mod.MitmproxyStreamInterceptor(quant_pipeline=pipe, schema_class=PitSchema)
        result = addon.submit_ingestion({"v": 1})
        assert result["status"] == "failed"
        assert addon.dispatch_failures == 1


# =====================================================================
# WebSocket sentiment streamer + blockchain lakehouse
# =====================================================================
class TestWebSocketDataflowStreamer:
    def test_sentiment_scores_and_entities(self):
        result = mod.WebSocketDataflowStreamer().analyze_news_sentiment(
            "Bullish surge for AAPL; bankrupt rival MSFT will drop!")
        # bullish +0.9, surge +0.8, bankrupt -1.0, drop -0.7 -> ~0.0
        assert result["sentiment_score"] == pytest.approx(0.0)
        assert set(result["detected_entities"]) >= {"AAPL", "MSFT"}
        assert result["payload_length"] > 0
        assert isinstance(result["stream_timestamp"], float)

    def test_negative_sentiment_dominates(self):
        result = mod.WebSocketDataflowStreamer().analyze_news_sentiment("bankrupt drop loss")
        assert result["sentiment_score"] == round(-1.0 - 0.7 - 0.5, 2)

    def test_neutral_text_scores_zero(self):
        result = mod.WebSocketDataflowStreamer().analyze_news_sentiment("nothing happens")
        assert result["sentiment_score"] == 0.0

    def test_custom_lexicon(self):
        streamer = mod.WebSocketDataflowStreamer(sentiment_lexicon={"moon": 5.0})
        assert streamer.analyze_news_sentiment("to the moon!")["sentiment_score"] == 5.0


class TestBlockchainLakehouseStreamingPipeline:
    def test_warmup_records_not_flagged(self):
        p = mod.BlockchainLakehouseStreamingPipeline(window_size=20)
        for i in range(2):
            rec = p.process_transaction_event({"amount": 100.0 + i, "tx_hash": f"0x{i}"})
            assert rec["is_anomaly"] is False and rec["z_score"] == 0.0  # n < 3
        third = p.process_transaction_event({"amount": 102.0, "tx_hash": "0x2"})
        assert third["is_anomaly"] is False          # z small, not anomalous
        assert third["z_score"] != 0.0               # but z-score now computed

    def test_anomaly_detection_and_window_eviction(self):
        p = mod.BlockchainLakehouseStreamingPipeline(window_size=5)
        for amount in (80.0, 90.0, 100.0, 110.0, 120.0):
            p.process_transaction_event({"amount": amount, "tx_hash": "0xsame"})
        rec = p.process_transaction_event({"amount": 10000.0, "tx_hash": "0xbig"})
        assert rec["is_anomaly"] is True
        assert abs(rec["z_score"]) > 2.5

    def test_window_eviction_bounds_history(self):
        p = mod.BlockchainLakehouseStreamingPipeline(window_size=5)
        for i in range(50):
            p.process_transaction_event({"amount": float(i)})
        assert len(p.transaction_history) == 5

    def test_generated_hash_is_visibly_synthetic_when_absent(self):
        # PHASE 13 honesty decision: generated ids must be visibly synthetic
        # ('sim-tx-' prefix) -- a bare 0x+64hex was indistinguishable from a
        # real chain transaction hash.
        rec = mod.BlockchainLakehouseStreamingPipeline().process_transaction_event({"amount": 1.0})
        assert re.fullmatch(r"sim-tx-[0-9a-f]{64}", rec["tx_hash"])

    def test_partition_date_format(self):
        rec = mod.BlockchainLakehouseStreamingPipeline().process_transaction_event({"amount": 1.0})
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", rec["lakehouse_partition"])


# =====================================================================
# Quarantined SEC/binary parsers (explicit unavailability)
# =====================================================================
class TestQuarantinedExtractors:
    def test_ixbrl_header_detection(self):
        res = mod.IXBRLSECParser().extract_narrative_sections(
            "<html>Item 1A. Risk Factors ... Item 7. Management's Discussion</html>")
        assert res["mda_detected"] is True and res["risk_factors_detected"] is True
        assert res["mda_text"] is None and res["risk_factors"] is None
        assert res["status"] == "UNAVAILABLE_NOT_IMPLEMENTED"

    def test_ixbrl_no_headers(self):
        res = mod.IXBRLSECParser().extract_narrative_sections("<html>nothing</html>")
        assert res["mda_detected"] is False and res["risk_factors_detected"] is False

    def test_ixbrl_non_string_rejected(self):
        with pytest.raises(ValueError, match="string"):
            mod.IXBRLSECParser().extract_narrative_sections(b"bytes")

    def test_balance_sheet_parser_quarantined(self):
        with pytest.raises(NotImplementedError, match="Phase 2"):
            mod.EDGARBalanceSheetParser().parse_balance_sheet("{}")

    def test_form4_parser_quarantined(self):
        with pytest.raises(NotImplementedError, match="Form 4"):
            mod.SECForm4InsiderTracker().parse_insider_transactions("<xml>")

    def test_risk_drift_extremes(self):
        tracker = mod.SECForm4InsiderTracker()
        same = "risk factors unchanged across filings"
        assert tracker.compute_risk_shifts_dask(same, same) == 0.0
        assert tracker.compute_risk_shifts_dask("alpha beta", "gamma delta") == 1.0
        mid = tracker.compute_risk_shifts_dask("alpha beta gamma", "beta gamma delta")
        assert 0.0 < mid < 1.0

    def test_risk_drift_empty_inputs_safe(self):
        assert mod.SECForm4InsiderTracker().compute_risk_shifts_dask("", "") == 0.0

    def test_pyarmor_unpacker_quarantined(self):
        unpacker = mod.PyarmorCPythonUnpacker(target_module="custom_mod")
        with pytest.raises(NotImplementedError, match="custom_mod"):
            unpacker.inject_pyeval_hooks()

    def test_ole2_valid_magic_and_sector_accounting(self):
        data = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * (512 * 3 - 8)
        res = mod.BinaryOLE2REDecoder().parse_ole2_container(data)
        assert res["ole2_magic_valid"] is True
        assert res["sectors_parsed"] == 3
        assert res["decompressed_payload"] is None
        assert res["status"] == "UNAVAILABLE_NOT_IMPLEMENTED"

    def test_ole2_invalid_magic_refuses_deep_parse(self):
        res = mod.BinaryOLE2REDecoder().parse_ole2_container(b"NOTOLE2!" + b"\x00" * 504)
        assert res["ole2_magic_valid"] is False

    def test_ole2_type_validation(self):
        with pytest.raises(ValueError, match="bytes-like"):
            mod.BinaryOLE2REDecoder().parse_ole2_container("string-not-bytes")


# =====================================================================
# PIT timestamp parsing + quant engine
# =====================================================================
class TestParsePITTimestamp:
    def test_naive_datetime_treated_as_utc(self):
        dt = mod.parse_pit_timestamp("2026-08-25 03:50:00", "f")
        assert dt.tzinfo is not None and dt.utcoffset().total_seconds() == 0

    def test_aware_datetime_preserved(self):
        from datetime import datetime, timezone as tz
        original = datetime(2026, 8, 25, 12, 0, tzinfo=tz.utc)
        assert mod.parse_pit_timestamp(original, "f") is original

    def test_epoch_numbers(self):
        dt = mod.parse_pit_timestamp(1756080000.5, "f")
        assert dt.timestamp() == pytest.approx(1756080000.5)

    def test_iso_with_offset_and_z(self):
        dt = mod.parse_pit_timestamp("2026-08-25 03:50:00+05:00", "f")
        assert dt.utcoffset().total_seconds() == 5 * 3600
        dt_z = mod.parse_pit_timestamp("2026-08-25T03:50:00Z", "f")
        assert dt_z.utcoffset().total_seconds() == 0

    def test_rejected_values(self):
        for bad in (None, True, [], {}, object()):
            with pytest.raises(mod.PITimestampError):
                mod.parse_pit_timestamp(bad, "f")

    def test_garbage_string_named_in_error(self):
        with pytest.raises(mod.PITimestampError, match="as_of_date"):
            mod.parse_pit_timestamp("yesterday-ish", "as_of_date")

    def test_out_of_range_epoch(self):
        with pytest.raises(mod.PITimestampError, match="range"):
            mod.parse_pit_timestamp(10**20, "f")


EVENTS = [
    {"ticker": "AAPL", "event_time": "2026-08-25 03:00:00", "knowledge_time": "2026-08-25 03:05:00", "metric_value": 182.5},
    {"ticker": "AAPL", "event_time": "2026-08-25 03:30:00", "knowledge_time": "2026-08-25 04:05:00", "metric_value": 184.2},
    {"ticker": "MSFT", "event_time": "2026-08-25 03:10:00", "knowledge_time": "2026-08-25 03:15:00", "metric_value": 415.6},
]
CUTOFF = "2026-08-25 03:50:00"


class TestPITQuantEngine:
    def test_cutoff_filter_and_latest_row_selection(self):
        feed = mod.PITQuantEngine().generate_quant_ready_feed(EVENTS, CUTOFF)
        tickers = {r["ticker"]: r for r in feed.to_dict("records")}
        assert set(tickers) == {"AAPL", "MSFT"}
        assert tickers["AAPL"]["metric_value"] == 182.5  # later row excluded by cutoff

    def test_composite_figi_deterministic_within_process(self):
        eng = mod.PITQuantEngine()
        figi_a = eng.generate_quant_ready_feed(EVENTS, CUTOFF).to_dict("records")[0]["composite_figi"]
        figi_b = mod.PITQuantEngine().generate_quant_ready_feed(EVENTS, CUTOFF).to_dict("records")[0]["composite_figi"]
        assert figi_a == figi_b == mod._stable_composite_figi("AAPL")

    def test_stable_figi_differs_across_tickers(self):
        assert mod._stable_composite_figi("AAPL") != mod._stable_composite_figi("MSFT")

    def test_whole_row_consistency_no_frankenstein_stitching(self):
        events = EVENTS[:2] + [
            {"ticker": "AAPL", "event_time": "2026-08-25 02:00:00",
             "knowledge_time": "2026-08-25 02:30:00", "metric_value": 999.0},
        ]
        rows = mod.PITQuantEngine().generate_quant_ready_feed(events, CUTOFF).to_dict("records")
        aapl = [r for r in rows if r["ticker"] == "AAPL"][0]
        assert aapl["metric_value"] == 182.5  # latest REAL row, not column-stitched

    def test_missing_required_columns_raise_descriptively(self):
        broken = [{"ticker": "AAPL", "knowledge_time": "2026-08-25 03:00:00", "metric_value": 1.0}]
        with pytest.raises(mod.PITimestampError, match="event_time"):
            mod.PITQuantEngine().generate_quant_ready_feed(broken, CUTOFF)

    def test_empty_events_yield_empty_frame(self):
        feed = mod.PITQuantEngine().generate_quant_ready_feed([], CUTOFF)
        assert hasattr(feed, "empty") and feed.empty

    def test_all_events_after_cutoff_empty(self):
        feed = mod.PITQuantEngine().generate_quant_ready_feed(
            [{"ticker": "T", "event_time": "2027-01-01 00:00:00",
              "knowledge_time": "2027-01-01 01:00:00", "metric_value": 1.0}], CUTOFF)
        assert feed.empty

    def test_fallback_path_without_pandas(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "pandas", None)
        feed = mod.PITQuantEngine().generate_quant_ready_feed(EVENTS, CUTOFF)
        assert isinstance(feed, list)
        by_ticker = {r["ticker"]: r for r in feed}
        assert by_ticker["AAPL"]["metric_value"] == 182.5
        assert by_ticker["AAPL"]["composite_figi"] == mod._stable_composite_figi("AAPL")

    def test_fallback_missing_ticker_descriptive(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "pandas", None)
        with pytest.raises(mod.PITimestampError, match="'ticker'"):
            mod.PITQuantEngine().generate_quant_ready_feed(
                [{"event_time": "2026-08-25 03:00:00",
                  "knowledge_time": "2026-08-25 03:05:00", "metric_value": 1.0}], CUTOFF)

    def test_fallback_malformed_knowledge_time_raises(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "pandas", None)
        with pytest.raises(mod.PITimestampError, match="knowledge_time"):
            mod.PITQuantEngine().generate_quant_ready_feed(
                [{"ticker": "AAPL", "event_time": "2026-08-25 03:00:00",
                  "knowledge_time": "not-a-date", "metric_value": 1.0}], CUTOFF)
