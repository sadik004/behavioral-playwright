"""
Comprehensive Test Suite for the PowerPlay Subsystem and BP Framework Bridge.

Covers:
1. Import & package structure
2. Public API & Bpp orchestrator
3. Mathematical & trajectory behavior (BiomechanicalTremorEngine)
4. Timing & keystroke jitter behavior (LinguisticKeystrokeDynamicsEngine)
5. State & memory behavior (StatefulEvasionTracker & Memory PID)
6. CAPTCHA loop detector & Poisson risk modeling
7. Schema integrity & O(N) Shannon entropy
8. Spatial action guard (Normalized GIoU & centroid healing)
9. Framework bridge integration (bp.powerplay namespace)
10. Simulation/stub honesty tests & edge cases
"""

import asyncio
import math
import os
import pytest
import numpy as np

# ---------------------------------------------------------------------------
# 1. Import & Package Structure Tests
# ---------------------------------------------------------------------------

def test_powerplay_direct_package_imports():
    import behavioral_playwright.powerplay as pp

    expected_classes = [
        "Bpp",
        "StatefulEvasionTracker",
        "VirtualDisplayManager",
        "OSLevelInputBridge",
        "OSLevelDisplayInputBridge",
        "BiomechanicalTremorEngine",
        "LinguisticKeystrokeDynamicsEngine",
        "TCPTTLMTUAligner",
        "ResolvedCAPTCHAInfiniteLoopDetector",
        "ResolvedSchemaIntegrityGuard",
        "UltimateVisionLanguageActionGuard",
        "ResolvedChromiumMemoryPIDController",
    ]
    for cls_name in expected_classes:
        assert hasattr(pp, cls_name), f"Missing class {cls_name} in powerplay package"
        assert cls_name in pp.__all__, f"{cls_name} not listed in __all__"


def test_powerplay_top_level_package_exports():
    from behavioral_playwright import BP, Bpp, powerplay
    assert BP is not None
    assert Bpp is not None
    assert powerplay is not None
    assert hasattr(powerplay, "Bpp")


def test_powerplay_submodules_isolated_imports():
    from behavioral_playwright.powerplay.tracking import StatefulEvasionTracker
    from behavioral_playwright.powerplay.os_bridge import (
        VirtualDisplayManager,
        OSLevelInputBridge,
        OSLevelDisplayInputBridge,
    )
    from behavioral_playwright.powerplay.biomechanics import BiomechanicalTremorEngine
    from behavioral_playwright.powerplay.keystrokes import LinguisticKeystrokeDynamicsEngine
    from behavioral_playwright.powerplay.network_l4 import TCPTTLMTUAligner
    from behavioral_playwright.powerplay.captcha import ResolvedCAPTCHAInfiniteLoopDetector
    from behavioral_playwright.powerplay.schema_guard import ResolvedSchemaIntegrityGuard
    from behavioral_playwright.powerplay.vision_guard import UltimateVisionLanguageActionGuard
    from behavioral_playwright.powerplay.memory_pid import ResolvedChromiumMemoryPIDController
    from behavioral_playwright.powerplay.orchestrator import Bpp

    assert StatefulEvasionTracker is not None
    assert VirtualDisplayManager is not None
    assert OSLevelInputBridge is not None
    assert OSLevelDisplayInputBridge is not None
    assert BiomechanicalTremorEngine is not None
    assert LinguisticKeystrokeDynamicsEngine is not None
    assert TCPTTLMTUAligner is not None
    assert ResolvedCAPTCHAInfiniteLoopDetector is not None
    assert ResolvedSchemaIntegrityGuard is not None
    assert UltimateVisionLanguageActionGuard is not None
    assert ResolvedChromiumMemoryPIDController is not None
    assert Bpp is not None


# ---------------------------------------------------------------------------
# 2. Public API & Bpp Orchestrator Tests
# ---------------------------------------------------------------------------

def test_bpp_orchestrator_initialization():
    from behavioral_playwright.powerplay import Bpp

    bot = Bpp()
    assert hasattr(bot, "tracker")
    assert hasattr(bot, "os_bridge")
    assert hasattr(bot, "biomechanics")
    assert hasattr(bot, "keystrokes")
    assert hasattr(bot, "tcp_tuner")
    assert hasattr(bot, "vision_guard")
    assert hasattr(bot, "loop_detector")
    assert hasattr(bot, "schema_guard")
    assert hasattr(bot, "memory_pid")


def test_bpp_os_bridge_composite_methods():
    from behavioral_playwright.powerplay import Bpp

    bot = Bpp()
    # 1. Virtual framebuffer initialization
    fb_res = bot.os_bridge.initialize_virtual_framebuffer()
    assert isinstance(fb_res, dict)
    assert fb_res["display"] == ":99"
    assert "status" in fb_res
    assert os.environ.get("DISPLAY") == ":99"

    # 2. OS mouse click simulation
    click_res = bot.os_bridge.dispatch_os_mouse_click(250, 400)
    assert isinstance(click_res, dict)
    assert click_res["coordinates"] == (250, 400)
    assert click_res["device"] == "uinput_kernel_virtual_mouse"
    assert click_res["isTrusted_forced"] is True

    # 3. OS keystroke simulation
    key_res = bot.os_bridge.dispatch_os_keystrokes("test_payload")
    assert isinstance(key_res, dict)
    assert key_res["payload_length"] == 12
    assert key_res["device"] == "uinput_kernel_virtual_keyboard"


# ---------------------------------------------------------------------------
# 3. Mathematical & Trajectory Behavior (BiomechanicalTremorEngine)
# ---------------------------------------------------------------------------

def test_biomechanical_bezier_trajectory_length_and_structure():
    from behavioral_playwright.powerplay import BiomechanicalTremorEngine

    engine = BiomechanicalTremorEngine(tremor_amp=0.5, sdn_k=0.03)
    start = (100.0, 100.0)
    target = (500.0, 400.0)
    steps = 25

    points = engine.generate_bezier_trajectory(start, target, steps=steps)
    assert len(points) == steps
    for pt in points:
        assert isinstance(pt, tuple)
        assert len(pt) == 2
        assert not math.isnan(pt[0]) and not math.isnan(pt[1])
        assert not math.isinf(pt[0]) and not math.isinf(pt[1])

    # Starting point should be close to start (within tremor offset)
    assert math.hypot(points[0][0] - start[0], points[0][1] - start[1]) < 10.0
    # Final point should be close to target (within tremor noise)
    assert math.hypot(points[-1][0] - target[0], points[-1][1] - target[1]) < 10.0


def test_biomechanical_zero_distance_safety():
    from behavioral_playwright.powerplay import BiomechanicalTremorEngine

    engine = BiomechanicalTremorEngine()
    pos = (200.0, 200.0)
    # Zero distance move: must not produce NaN or ZeroDivisionError
    points = engine.generate_bezier_trajectory(pos, pos, steps=10)
    assert len(points) == 10
    for x, y in points:
        assert not math.isnan(x) and not math.isnan(y)


def test_biomechanical_saccadic_overshoot():
    from behavioral_playwright.powerplay import BiomechanicalTremorEngine

    engine = BiomechanicalTremorEngine()
    start = (0.0, 0.0)
    target = (100.0, 0.0)
    overshoot = engine.apply_saccadic_overshoot(start, target)
    assert isinstance(overshoot, tuple)
    # X coordinate should be in overshoot/undershoot range [92, 108]
    assert 90.0 <= overshoot[0] <= 110.0
    assert abs(overshoot[1]) < 1.0


def test_click_micro_slip_bounds():
    from behavioral_playwright.powerplay import BiomechanicalTremorEngine

    engine = BiomechanicalTremorEngine()
    pos = (150.0, 150.0)
    down, up, dwell = engine.simulate_click_micro_slip(pos)
    assert isinstance(down, tuple)
    assert isinstance(up, tuple)
    assert 0.06 <= dwell <= 0.14
    # Slip distance should be in 1-2px range
    slip = math.hypot(up[0] - down[0], up[1] - down[1])
    assert 0.9 <= slip <= 2.1


# ---------------------------------------------------------------------------
# 4. Timing & Keystroke Jitter (LinguisticKeystrokeDynamicsEngine)
# ---------------------------------------------------------------------------

def test_qwerty_distance_calculation():
    from behavioral_playwright.powerplay import LinguisticKeystrokeDynamicsEngine

    engine = LinguisticKeystrokeDynamicsEngine()
    # 'q' to 'w' is adjacent (distance 1.0)
    d_qw = engine.get_qwerty_distance("q", "w")
    assert abs(d_qw - 1.0) < 1e-4

    # 'q' to 'p' spans across keyboard (distance 9.0)
    d_qp = engine.get_qwerty_distance("q", "p")
    assert abs(d_qp - 9.0) < 1e-4

    # Unmapped character returns default standard distance (1.8)
    assert engine.get_qwerty_distance("@", "!") == 1.8


def test_keystroke_sequence_chronology_and_clamping():
    from behavioral_playwright.powerplay import LinguisticKeystrokeDynamicsEngine

    engine = LinguisticKeystrokeDynamicsEngine()
    text = "Playwright"
    events = engine.generate_typing_sequence(text)

    # 2 events per character (keydown, keyup)
    assert len(events) == len(text) * 2

    # Verify chronological ordering and minimum boundary clamping
    prev_time = 0
    for i in range(0, len(events), 2):
        keydown = events[i]
        keyup = events[i + 1]

        assert keydown["event"] == "keydown"
        assert keyup["event"] == "keyup"
        assert keydown["key"] == keyup["key"]

        # Flight time to keydown >= 20ms
        flight = keydown["timestamp_ms"] - prev_time
        assert flight >= 20

        # Dwell time between keydown and keyup >= 15ms
        dwell = keyup["timestamp_ms"] - keydown["timestamp_ms"]
        assert dwell >= 15

        prev_time = keyup["timestamp_ms"]


def test_keystroke_sequence_empty_text():
    from behavioral_playwright.powerplay import LinguisticKeystrokeDynamicsEngine

    engine = LinguisticKeystrokeDynamicsEngine()
    events = engine.generate_typing_sequence("")
    assert events == []


# ---------------------------------------------------------------------------
# 5. State & Memory Tracking (StatefulEvasionTracker & PID Controller)
# ---------------------------------------------------------------------------

def test_stateful_evasion_tracker_sliding_window():
    from behavioral_playwright.powerplay import StatefulEvasionTracker

    tracker = StatefulEvasionTracker(history_window_size=5)
    for _ in range(8):
        tracker.record_request()
    assert len(tracker.request_timestamps) == 5

    rpm, jitter = tracker.calculate_rolling_request_rate()
    assert rpm >= 0.0
    assert jitter >= 0.0


def test_stateful_evasion_tracker_reputation_and_threat_score():
    from behavioral_playwright.powerplay import StatefulEvasionTracker

    tracker = StatefulEvasionTracker()
    assert tracker.ip_reputation == 1.0

    # CAPTCHA encounter decays reputation
    tracker.register_captcha()
    assert tracker.ip_reputation == 0.75
    assert tracker.captcha_encounters == 1

    # Shadow ban strike decays reputation faster
    tracker.register_shadow_ban()
    assert tracker.ip_reputation == 0.375

    threat_idx = tracker.compute_adaptive_threat_index()
    assert 0.0 <= threat_idx <= 100.0


def test_stateful_tracker_memory_averaging():
    from behavioral_playwright.powerplay import StatefulEvasionTracker

    tracker = StatefulEvasionTracker(history_window_size=3)
    tracker.record_memory(100.0)
    tracker.record_memory(200.0)
    tracker.record_memory(300.0)
    assert tracker.get_sliding_average_ram() == 200.0

    tracker.record_memory(400.0)
    assert tracker.get_sliding_average_ram() == 300.0


def test_pid_memory_controller_anti_windup_and_kick_prevention():
    from behavioral_playwright.powerplay import ResolvedChromiumMemoryPIDController

    pid = ResolvedChromiumMemoryPIDController(target_mb=500.0, kp=0.5, ki=0.1, kd=0.05)

    # First run: derivative kick must be 0.0
    res1 = pid.compute_correction(600.0, dt=1.0)
    assert res1["derivative"] == 0.0
    assert res1["error_mb"] == 100.0
    assert 0.0 <= res1["correction_intensity_pct"] <= 100.0

    # Consecutive large errors: integral must clamp at 100.0
    for _ in range(20):
        pid.compute_correction(1500.0, dt=1.0)
    assert pid.integral <= 100.0
    assert pid.integral >= -100.0


# ---------------------------------------------------------------------------
# 6. CAPTCHA Loop Risk Evaluator (ResolvedCAPTCHAInfiniteLoopDetector)
# ---------------------------------------------------------------------------

def test_captcha_loop_detector_zero_challenges():
    from behavioral_playwright.powerplay import ResolvedCAPTCHAInfiniteLoopDetector

    detector = ResolvedCAPTCHAInfiniteLoopDetector()
    res = detector.evaluate_loop_risk(0)
    assert res["decision"] == "PASS"
    assert res["cumulative_loop_risk"] == "0.0%"


def test_captcha_loop_detector_escalation():
    from behavioral_playwright.powerplay import ResolvedCAPTCHAInfiniteLoopDetector

    detector = ResolvedCAPTCHAInfiniteLoopDetector()
    # 3+ challenges trigger PROACTIVE_ROTATE
    res = detector.evaluate_loop_risk(3)
    assert res["decision"] == "PROACTIVE_ROTATE"
    assert "PROACTIVE SOFT ROTATION" in res["action"]


# ---------------------------------------------------------------------------
# 7. Schema Integrity & Shannon Entropy (ResolvedSchemaIntegrityGuard)
# ---------------------------------------------------------------------------

def test_shannon_entropy_calculation():
    from behavioral_playwright.powerplay import ResolvedSchemaIntegrityGuard

    guard = ResolvedSchemaIntegrityGuard()
    # Empty string
    assert guard.calculate_shannon_entropy("") == 0.0

    # Single repeated char has 0 entropy
    assert guard.calculate_shannon_entropy("aaaaaaa") == 0.0

    # 4 equally probable characters: H = - 4 * (0.25 * log2(0.25)) = 2.0
    h = guard.calculate_shannon_entropy("abcd" * 10)
    assert abs(h - 2.0) < 1e-4


def test_schema_audit_short_text_bypass():
    from behavioral_playwright.powerplay import ResolvedSchemaIntegrityGuard

    guard = ResolvedSchemaIntegrityGuard()
    res = guard.audit_page_text("Too short")
    assert res["decision"] == "PASS_BYPASS"
    assert "N=9 < 50" in res["action"]


def test_schema_audit_profile_detection():
    from behavioral_playwright.powerplay import ResolvedSchemaIntegrityGuard

    guard = ResolvedSchemaIntegrityGuard()
    assert guard.detect_content_profile('{"status": "ok", "count": 42}') == "json_api"
    assert guard.detect_content_profile("<!DOCTYPE html><html><body>Normal text</body></html>") == "english_html"


# ---------------------------------------------------------------------------
# 8. Spatial Action Guard (UltimateVisionLanguageActionGuard)
# ---------------------------------------------------------------------------

def test_vision_guard_cosine_similarity():
    from behavioral_playwright.powerplay import UltimateVisionLanguageActionGuard

    guard = UltimateVisionLanguageActionGuard()
    vec_a = np.array([1.0, 0.0, 0.0])
    vec_b = np.array([1.0, 0.0, 0.0])
    vec_c = np.array([0.0, 1.0, 0.0])

    assert abs(guard.calculate_cosine_similarity(vec_a, vec_b) - 1.0) < 1e-4
    assert abs(guard.calculate_cosine_similarity(vec_a, vec_c) - 0.0) < 1e-4
    assert guard.calculate_cosine_similarity(np.zeros(3), vec_a) == 0.0


def test_vision_guard_normalized_giou_and_centroid():
    from behavioral_playwright.powerplay import UltimateVisionLanguageActionGuard

    guard = UltimateVisionLanguageActionGuard()
    box_a = [10, 10, 100, 100]
    box_b = [10, 10, 100, 100]

    spatial_score, giou, norm_giou, centroid_score = guard.calculate_giou_and_centroid_score(box_a, box_b)
    # Perfect overlap: IoU=1, GIoU=1, norm_giou=1.0, centroid_score=1.0
    assert abs(giou - 1.0) < 1e-4
    assert abs(norm_giou - 1.0) < 1e-4
    assert abs(centroid_score - 1.0) < 1e-4
    assert abs(spatial_score - 1.0) < 1e-4
    # Must be normalized in [0, 1]
    assert 0.0 <= norm_giou <= 1.0


def test_vision_guard_click_healing_decision():
    from behavioral_playwright.powerplay import UltimateVisionLanguageActionGuard

    guard = UltimateVisionLanguageActionGuard(min_safe_probability=0.75)
    vec = np.array([1.0, 0.5, 0.2])
    box_int = [50, 50, 150, 150]
    box_scan = [52, 48, 148, 152]

    # Close spatial match + identical semantics -> PASS
    pass_res = guard.evaluate_and_heal_click(vec, vec, box_int, box_scan)
    assert pass_res["decision"] == "PASS"
    assert pass_res["resolved_coords"] == (100, 100)

    # Completely disjoint boxes and orthogonal vectors -> BLOCK
    box_far = [1000, 1000, 1100, 1100]
    vec_ortho = np.array([-0.5, 1.0, 0.0])
    block_res = guard.evaluate_and_heal_click(vec, vec_ortho, box_int, box_far)
    assert block_res["decision"] == "BLOCK"


# ---------------------------------------------------------------------------
# 9. Framework Bridge Integration (bp.powerplay namespace)
# ---------------------------------------------------------------------------

def test_bp_powerplay_namespace_attachment():
    from behavioral_playwright import BP

    bp = BP()
    assert hasattr(bp, "powerplay"), "BP instance lacks powerplay namespace"
    assert bp.powerplay is not None


def test_bp_powerplay_properties_lazy_instantiation():
    from behavioral_playwright import BP

    bp = BP()
    pp = bp.powerplay
    assert pp.tracker is not None
    assert pp.biomechanics is not None
    assert pp.keystrokes is not None
    assert pp.vision_guard is not None
    assert pp.schema_guard is not None
    assert pp.memory_pid is not None
    assert pp.loop_detector is not None
    assert pp.tcp_tuner is not None
    assert pp.os_bridge is not None


def test_bp_powerplay_helpers_without_booted_browser():
    from behavioral_playwright import BP

    bp = BP()
    # 1. Trajectory generation
    traj = bp.powerplay.generate_mouse_trajectory((10, 10), (100, 100), steps=8)
    assert len(traj) == 8

    # 2. Keystroke generation
    seq = bp.powerplay.generate_keystroke_sequence("abc")
    assert len(seq) == 6

    # 3. Entropy audit
    audit = bp.powerplay.audit_content_entropy("Hello World")
    assert "decision" in audit

    # 4. Async helpers executed when no page is booted (must safely return points/seq)
    async def run_async():
        pts = await bp.powerplay.move_mouse_humanized((0, 0), (50, 50), steps=5, step_delay=0)
        assert len(pts) == 5
        keys = await bp.powerplay.type_humanized("hi", delay_multiplier=0)
        assert len(keys) == 4

    asyncio.run(run_async())


def test_bp_powerplay_create_orchestrator():
    from behavioral_playwright import BP
    from behavioral_playwright.powerplay import Bpp

    bp = BP()
    bot = bp.powerplay.create_orchestrator()
    assert isinstance(bot, Bpp)


# ---------------------------------------------------------------------------
# 10. Simulation / Stub Honesty Tests
# ---------------------------------------------------------------------------

def test_virtual_display_manager_simulation_honesty():
    from behavioral_playwright.powerplay import VirtualDisplayManager

    mgr = VirtualDisplayManager(width=1280, height=720, color_depth=16)
    report = mgr.initialize_virtual_framebuffer()
    assert isinstance(report, dict)
    assert report["resolution"] == "1280x720x16"
    assert report["display"] == ":99"


def test_tcp_ttl_mtu_aligner_report():
    from behavioral_playwright.powerplay import TCPTTLMTUAligner

    aligner = TCPTTLMTUAligner()
    params = aligner.align_socket_parameters()
    assert params["socket_ttl"] == 128
    assert params["socket_mtu"] == 1500
    assert params["socket_mss"] == 1460
    assert params["window_size"] == 64240


def test_os_level_input_bridge_stub():
    from behavioral_playwright.powerplay import OSLevelInputBridge

    bridge = OSLevelInputBridge()
    click = bridge.dispatch_os_mouse_click(10, 20)
    assert click["device"] == "uinput_kernel_virtual_mouse"
    assert click["coordinates"] == (10, 20)

    keys = bridge.dispatch_os_keystrokes("hello")
    assert keys["payload_length"] == 5
    assert keys["rollover_typing_active"] is True


# ---------------------------------------------------------------------------
# 11. Additional Failure & Edge-Case Behavior Tests
# ---------------------------------------------------------------------------

def test_schema_audit_shadow_ban_detection_on_repetitive_text():
    from behavioral_playwright.powerplay import ResolvedSchemaIntegrityGuard

    guard = ResolvedSchemaIntegrityGuard()
    # High length (N >= 50) but extremely low entropy (repeated char) -> z_score < -2.5
    repetitive_text = "a" * 100
    res = guard.audit_page_text(repetitive_text)
    assert res["decision"] == "SHADOW_BAN_DETECTED"
    assert res["shannon_entropy"] == 0.0
    assert res["z_score"] < -2.5


def test_schema_audit_unicode_profile_detection():
    from behavioral_playwright.powerplay import ResolvedSchemaIntegrityGuard

    guard = ResolvedSchemaIntegrityGuard()
    # Bengali unicode string
    bengali_text = "\u0986\u09ae\u09be\u09b0 \u09b8\u09cb\u09a8\u09be\u09b0 \u09ac\u09be\u0982\u09b2\u09be " * 5
    res = guard.audit_page_text(bengali_text)
    assert res["content_profile"] == "unicode_bengali"
    assert res["decision"] == "PASS"


def test_stateful_evasion_tracker_high_rpm_low_jitter():
    from behavioral_playwright.powerplay import StatefulEvasionTracker

    tracker = StatefulEvasionTracker(history_window_size=20)
    # Simulate high RPM (> 15) and very low jitter (< 0.1)
    base = 1000.0
    for i in range(15):
        tracker.request_timestamps.append(base + i * 1.0)  # interval = 1.0s, rpm = 60, jitter = 0
    rpm, jitter = tracker.calculate_rolling_request_rate()
    assert rpm == 60.0
    assert jitter == 0.0
    threat = tracker.compute_adaptive_threat_index()
    # regularity factor should trigger (+25)
    assert threat >= 25.0


def test_memory_pid_bounds_on_extreme_inputs():
    from behavioral_playwright.powerplay import ResolvedChromiumMemoryPIDController

    pid = ResolvedChromiumMemoryPIDController(target_mb=512.0)
    # Very high usage: 5000 MB
    res = pid.compute_correction(5000.0)
    assert res["correction_intensity_pct"] == 100.0
    assert "PROACTIVE RECLAIM" in res["action"]

    # Usage below target: 200 MB
    res_low = pid.compute_correction(200.0)
    assert res_low["correction_intensity_pct"] == 0.0
    assert "SAFE" in res_low["action"]
