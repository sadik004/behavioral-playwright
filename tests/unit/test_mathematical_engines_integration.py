"""
Unit test suite verifying tight architectural integration of the 5 core mathematical engines
across the Behavioral Playwright framework.
"""

from behavioral_playwright import (
    BP,
    BiomechanicalTremorEngine,
    BiometricDistributionValidator,
    LinguisticKeystrokeDynamicsEngine,
    ResolvedCAPTCHAInfiniteLoopDetector,
    ResolvedChromiumMemoryPIDController,
    ResolvedSchemaIntegrityGuard,
    UltimateVisionLanguageActionGuard,
)
import behavioral_playwright.powerplay as powerplay


def test_top_level_package_exports_all_seven_engines():
    """Confirms all 7 engines are exported at the root behavioral_playwright package level."""
    assert issubclass(BiomechanicalTremorEngine, object)
    assert issubclass(LinguisticKeystrokeDynamicsEngine, object)
    assert issubclass(ResolvedChromiumMemoryPIDController, object)
    assert issubclass(ResolvedSchemaIntegrityGuard, object)
    assert issubclass(UltimateVisionLanguageActionGuard, object)
    assert issubclass(ResolvedCAPTCHAInfiniteLoopDetector, object)
    assert issubclass(BiometricDistributionValidator, object)


def test_powerplay_package_exports_all_seven_engines():
    """Confirms powerplay module re-exports the exact same 7 classes."""
    assert powerplay.BiomechanicalTremorEngine is BiomechanicalTremorEngine
    assert powerplay.LinguisticKeystrokeDynamicsEngine is LinguisticKeystrokeDynamicsEngine
    assert powerplay.ResolvedChromiumMemoryPIDController is ResolvedChromiumMemoryPIDController
    assert powerplay.ResolvedSchemaIntegrityGuard is ResolvedSchemaIntegrityGuard
    assert powerplay.UltimateVisionLanguageActionGuard is UltimateVisionLanguageActionGuard
    assert powerplay.ResolvedCAPTCHAInfiniteLoopDetector is ResolvedCAPTCHAInfiniteLoopDetector
    assert powerplay.BiometricDistributionValidator is BiometricDistributionValidator


def test_bp_powerplay_namespace_attachment():
    """Verifies that bp.powerplay provides lazy-initialized engine instances and class handles."""
    bp = BP()

    # 1. BiomechanicalTremorEngine (bp.powerplay.biomechanics)
    assert isinstance(bp.powerplay.biomechanics, BiomechanicalTremorEngine)
    assert bp.powerplay.BiomechanicalTremorEngine is BiomechanicalTremorEngine

    # 2. LinguisticKeystrokeDynamicsEngine (bp.powerplay.keystrokes)
    assert isinstance(bp.powerplay.keystrokes, LinguisticKeystrokeDynamicsEngine)
    assert bp.powerplay.LinguisticKeystrokeDynamicsEngine is LinguisticKeystrokeDynamicsEngine

    # 3. ResolvedChromiumMemoryPIDController (bp.powerplay.memory_pid)
    assert isinstance(bp.powerplay.memory_pid, ResolvedChromiumMemoryPIDController)
    assert bp.powerplay.ResolvedChromiumMemoryPIDController is ResolvedChromiumMemoryPIDController

    # 4. ResolvedSchemaIntegrityGuard (bp.powerplay.schema_guard)
    assert isinstance(bp.powerplay.schema_guard, ResolvedSchemaIntegrityGuard)
    assert bp.powerplay.ResolvedSchemaIntegrityGuard is ResolvedSchemaIntegrityGuard

    # 5. UltimateVisionLanguageActionGuard (bp.powerplay.vision_guard)
    assert isinstance(bp.powerplay.vision_guard, UltimateVisionLanguageActionGuard)
    assert bp.powerplay.UltimateVisionLanguageActionGuard is UltimateVisionLanguageActionGuard

    # 6. ResolvedCAPTCHAInfiniteLoopDetector (bp.powerplay.loop_detector)
    assert isinstance(bp.powerplay.loop_detector, ResolvedCAPTCHAInfiniteLoopDetector)
    assert bp.powerplay.ResolvedCAPTCHAInfiniteLoopDetector is ResolvedCAPTCHAInfiniteLoopDetector

    # 7. BiometricDistributionValidator (bp.powerplay.validator)
    assert isinstance(bp.powerplay.validator, BiometricDistributionValidator)
    assert bp.powerplay.BiometricDistributionValidator is BiometricDistributionValidator


def test_bp_facade_top_level_property_forwarders():
    """Verifies that bp.<module> forwards directly to bp.powerplay.<module>."""
    bp = BP()
    assert bp.biomechanics is bp.powerplay.biomechanics
    assert bp.keystrokes is bp.powerplay.keystrokes
    assert bp.memory_pid is bp.powerplay.memory_pid
    assert bp.schema_guard is bp.powerplay.schema_guard
    assert bp.vision_guard is bp.powerplay.vision_guard


def test_bp_powerplay_execution_of_each_engine():
    """Executes the primary mathematical responsibility of each of the 5 engines through the facade."""
    bp = BP()

    # 1. Biomechanics: Mouse Trajectory with Costello Bezier & Tremor
    trajectory = bp.powerplay.generate_mouse_trajectory((100, 100), (400, 300), steps=25)
    assert len(trajectory) == 25
    assert abs(trajectory[0][0] - 100) < 10
    assert abs(trajectory[-1][0] - 400) < 10

    # 2. Keystrokes: QWERTY Distance + Weibull Timings
    sequence = bp.powerplay.generate_keystroke_sequence("Test")
    assert len(sequence) == 8  # 4 chars * (down + up)
    assert sequence[0]["event"] == "keydown"
    assert sequence[0]["key"] == "T"

    # 3. Memory PID: Closed-Loop Chromium RSS Regulation
    mem_action = bp.powerplay.compute_memory_adjustment(current_rss_mb=650.0, target_rss_mb=500.0)
    assert "error_mb" in mem_action
    assert "correction_intensity_pct" in mem_action
    assert mem_action["error_mb"] == 150.0
    assert mem_action["correction_intensity_pct"] > 0.0

    # 4. Schema Integrity: Entropy, JSD, and Honeypot Audit
    sample_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head><title>Legitimate Web Content</title></head>
    <body>
        <h1>Production E-Commerce Catalogue</h1>
        <p>Full authentic text describing products and legitimate DOM structure.</p>
        <p>Another paragraph providing high information entropy and balanced density.</p>
    </body>
    </html>
    """
    audit = bp.powerplay.audit_content_entropy(sample_html)
    assert audit["decision"] == ResolvedSchemaIntegrityGuard.DECISION_NORMAL
    assert audit["is_safe_to_proceed"] is True

    # 5. Vision Guard: Spatial GIoU & Multi-Modal Action Verification
    vis_res = bp.powerplay.evaluate_visual_action(
        intended_box=(100.0, 100.0, 200.0, 150.0),
        scanned_box=(105.0, 102.0, 202.0, 152.0)
    )
    assert vis_res["decision"] == "PASS"
    assert vis_res["giou"] > 0.7
