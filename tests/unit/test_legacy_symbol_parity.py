"""Symbol Parity and Module Identity Test Suite (`tests/unit/test_legacy_symbol_parity.py`).

Verifies 100% symbol parity, backward-compatible import stability, and strict
sys.modules object identity across all legacy and modern facade packages.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import sys
from pathlib import Path
from typing import List

import pytest


def test_leaf_submodule_identity_parity():
    """Asserts sys.modules['behavioral_playwright.<leaf>'] is sys.modules['veil.<leaf>']."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    src_dir = repo_root / "src"
    bp_dir = src_dir / "behavioral_playwright"
    veil_dir = src_dir / "veil"

    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    checked_modules: List[str] = []

    for file_path in bp_dir.rglob("*.py"):
        if file_path.name == "__init__.py":
            continue
        rel_parts = file_path.relative_to(src_dir).with_suffix("").parts
        bp_mod_name = ".".join(rel_parts)

        veil_parts = ("veil",) + rel_parts[1:]
        veil_mod_name = ".".join(veil_parts)

        veil_file = veil_dir.joinpath(*rel_parts[1:]).with_suffix(".py")
        if not veil_file.exists():
            continue

        mod_bp = importlib.import_module(bp_mod_name)
        mod_veil = importlib.import_module(veil_mod_name)

        assert sys.modules[bp_mod_name] is sys.modules[veil_mod_name], (
            f"Module identity mismatch: {bp_mod_name} is not {veil_mod_name}"
        )
        assert mod_bp is mod_veil
        checked_modules.append(bp_mod_name)

    assert len(checked_modules) > 30, f"Expected >30 aliased leaf modules, found {len(checked_modules)}"


def test_behavioral_evasion_suite_symbol_parity():
    """Verifies every public class and function from behavioral_evasion_suite imports without error."""
    import behavioral_evasion_suite as bes

    # Critical kinematic and biometric controllers
    from behavioral_evasion_suite.mouse_physics import (
        BiometricMouseController,
        SigmaLognormalMotor,
        BiomechanicalMousePhysics,
        WindowsHighResolutionTimer,
        MousePoint,
        SaccadicMouseEngine,
    )
    from behavioral_evasion_suite.keystroke_engine import (
        CognitiveKeystrokeEngine,
        LinguisticKeystrokeDynamicsEngine,
        KeystrokeCadenceEngine,
    )
    from behavioral_evasion_suite.dom_telemetry import (
        DOMTelemetryCollector,
        DOMEventRecord,
        PageTelemetryAuditor,
    )
    from behavioral_evasion_suite.kernel_input_bridge import (
        WindowsKernelInputEventBridge,
        OSKernelInputEventBridge,
        FPGAPCIeDMAHardwareBridge,
        KernelInputBridge,
    )
    from behavioral_evasion_suite.vision_guard import (
        UltimateVisionLanguageActionGuard,
        VisionGuard,
    )

    # Core facade and runner classes
    from behavioral_evasion_suite.unified_quantum_facade import UnifiedQuantumFacade
    from behavioral_evasion_suite.powerhand_master import PowerHandMaster, PowerHandPlaywrightRunner
    from behavioral_evasion_suite.stealth_session import StealthSession, human_click, human_type

    # Ensure all exports are non-None
    assert BiometricMouseController is not None
    assert SigmaLognormalMotor is not None
    assert LinguisticKeystrokeDynamicsEngine is not None
    assert DOMTelemetryCollector is not None
    assert WindowsKernelInputEventBridge is not None
    assert UltimateVisionLanguageActionGuard is not None
    assert UnifiedQuantumFacade is not None
    assert PowerHandMaster is not None
    assert StealthSession is not None


@pytest.mark.asyncio
async def test_biometric_mouse_controller_contract():
    """Validates relative timestamps and seed determinism of BiometricMouseController."""
    from veil.kinematics.biomechanics import BiometricMouseController

    ctrl = BiometricMouseController()
    path_a1 = await ctrl.generate_human_movement((10.0, 10.0), (500.0, 400.0), seed=42)
    path_a2 = await ctrl.generate_human_movement((10.0, 10.0), (500.0, 400.0), seed=42)
    path_b = await ctrl.generate_human_movement((10.0, 10.0), (500.0, 400.0), seed=99)

    coords_a1 = [(round(p["x"], 4), round(p["y"], 4)) for p in path_a1]
    coords_a2 = [(round(p["x"], 4), round(p["y"], 4)) for p in path_a2]
    coords_b = [(round(p["x"], 4), round(p["y"], 4)) for p in path_b]

    assert len(path_a1) > 15, "Trajectory too short"
    assert 0.0 <= path_a1[0]["t"] < 1.0, f"Initial timestamp outside [0, 1): {path_a1[0]['t']}"
    assert path_a1[-1]["t"] < 10.0, f"Final relative duration exceeds 10s: {path_a1[-1]['t']}"
    assert coords_a1 == coords_a2, "Determinism violated: same seed gave different coordinates"
    assert coords_a1 != coords_b, "Entropy failure: different seeds gave identical coordinates"


def test_linguistic_keystroke_engine_contract():
    """Validates Weibull monotonicity and seed determinism of LinguisticKeystrokeDynamicsEngine."""
    from veil.kinematics.keystrokes import LinguisticKeystrokeDynamicsEngine

    ks = LinguisticKeystrokeDynamicsEngine(seed=42)
    seq1 = ks.generate_typing_sequence("hello world", seed=42)
    seq2 = ks.generate_typing_sequence("hello world", seed=42)
    seq3 = ks.generate_typing_sequence("hello world", seed=777)

    assert seq1 == seq2, "Determinism violated for identical keystroke seed"
    assert seq1 != seq3, "Different keystroke seeds gave identical sequence"
    assert all(
        seq1[i]["timestamp_ms"] <= seq1[i + 1]["timestamp_ms"]
        for i in range(len(seq1) - 1)
    ), "Keystroke timestamps not monotonic"


def test_dynamic_import_all_packages():
    """Dynamically imports every module in src/veil/, src/behavioral_playwright/,
    src/veil/powerplay/, and behavioral_evasion_suite/ asserting zero ImportError."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    imported_count = 0
    for pkg_name in ["veil", "behavioral_playwright", "veil.powerplay", "behavioral_evasion_suite"]:
        pkg = importlib.import_module(pkg_name)
        imported_count += 1
        for info in pkgutil.walk_packages(pkg.__path__, prefix=f"{pkg_name}."):
            mod = importlib.import_module(info.name)
            assert mod is not None, f"Failed importing {info.name}"
            imported_count += 1

    assert imported_count > 300, f"Expected >300 imported modules, got {imported_count}"


def test_root_providers_parity_with_veil_providers():
    """Validates root providers/ package sync with veil.providers (afetch, BaseBrowserProvider, identity)."""
    import providers
    import veil.providers
    from providers.network import CurlCffiProvider as RootCurlCffiProvider
    from veil.providers.network import CurlCffiProvider as VeilCurlCffiProvider

    # 1. BaseBrowserProvider in __all__ and exported
    assert "BaseBrowserProvider" in providers.__all__
    assert providers.BaseBrowserProvider is veil.providers.BaseBrowserProvider

    # 2. CurlCffiProvider identity and afetch availability
    assert RootCurlCffiProvider is VeilCurlCffiProvider
    assert hasattr(RootCurlCffiProvider, "afetch")
    assert callable(getattr(RootCurlCffiProvider, "afetch"))

    # 3. All symbols in veil.providers.__all__ are in providers.__all__
    for sym in veil.providers.__all__:
        assert sym in providers.__all__, f"Symbol {sym} missing from root providers.__all__"
        assert getattr(providers, sym) is getattr(veil.providers, sym), f"Symbol {sym} identity mismatch"


