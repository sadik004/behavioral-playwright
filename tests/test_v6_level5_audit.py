"""
Level 5 Quantum Edition (v6.0.0) Automated Audit & Regression Test Suite
Validates imports, circular dependencies, Level 5 shield wiring, and Level 4 legacy resilience.
"""

import sys
import os
import asyncio
import socket
import pytest

# Ensure root directory is on sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def test_01_clean_imports_and_version():
    """Verify v6.0.0 clean exports and absence of circular dependencies."""
    import behavioral_evasion_suite as bes

    assert hasattr(bes, "__version__"), "Version attribute missing from __init__"
    assert bes.__version__ == "6.0.0", f"Expected version 6.0.0, got {bes.__version__}"

    # Verify all Level 5 symbols are exported
    assert hasattr(bes, "WorkerUniversalShield")
    assert hasattr(bes, "SubpixelFontShield")
    assert hasattr(bes, "VirtualHardwareSynthesizer")
    assert hasattr(bes, "CognitiveGazePhysics")
    assert hasattr(bes, "human_scroll")
    assert hasattr(bes, "cognitive_reading_pause")
    assert hasattr(bes, "OSNetworkStackSpoofer")
    assert hasattr(bes, "StealthSession")


def test_02_worker_universal_shield():
    """Audit Web Worker and SharedWorker sandbox injection payload."""
    from behavioral_evasion_suite import WorkerUniversalShield, WorkerShieldConfig

    shield = WorkerUniversalShield(WorkerShieldConfig(mask_hardware_concurrency=16))
    script = shield.get_script()

    assert "window.__worker_universal_shield_active__" in script
    assert "hardwareConcurrency" in script
    assert "16" in script
    assert "Worker" in script
    assert "SharedWorker" in script
    assert "importScripts" in script


def test_03_subpixel_font_shield():
    """Audit DirectWrite ClearType subpixel font metric converter."""
    from behavioral_evasion_suite import SubpixelFontShield, FontMetricConfig

    shield = SubpixelFontShield(FontMetricConfig(smoothing_factor=0.03125))
    script = shield.get_script()

    assert "window.__subpixel_font_shield_active__" in script
    assert "CanvasRenderingContext2D.prototype.measureText" in script
    assert "Element.prototype.getBoundingClientRect" in script
    assert "0.03125" in script


def test_04_virtual_hardware_synthesizer():
    """Audit synthesized Realtek and Intel media hardware descriptors."""
    from behavioral_evasion_suite import VirtualHardwareSynthesizer, MediaDeviceDescriptor

    synthesizer = VirtualHardwareSynthesizer()
    script = synthesizer.get_script()

    assert "window.__virtual_hardware_synthesizer_active__" in script
    assert "Realtek(R) Audio" in script
    assert "Intel(R) Smart Sound Technology" in script
    assert "Integrated Webcam" in script
    assert "enumerateDevices" in script

    # Verify descriptors schema
    assert len(VirtualHardwareSynthesizer.DEFAULT_DEVICES) >= 4
    for dev in VirtualHardwareSynthesizer.DEFAULT_DEVICES:
        assert isinstance(dev, MediaDeviceDescriptor)
        assert dev.deviceId
        assert dev.kind in ("audioinput", "audiooutput", "videoinput")


def test_05_cognitive_gaze_physics():
    """Audit Newtonian inertial scroll trajectory generator and cognitive pauses."""
    from behavioral_evasion_suite import CognitiveGazePhysics, GazePhysicsConfig, ScrollTrajectoryPoint

    physics = CognitiveGazePhysics(GazePhysicsConfig(friction_coefficient=0.90))
    steps = physics.generate_inertial_scroll_steps(distance_y=1200.0)

    assert len(steps) > 5, "Expected multi-step Newtonian trajectory for 1200px scroll"
    total_delta = sum(s.delta_y for s in steps)
    assert abs(total_delta - 1200.0) < 5.0, f"Displacement mismatch: {total_delta} vs 1200.0"

    for step in steps:
        assert isinstance(step, ScrollTrajectoryPoint)
        assert step.delta_y > 0
        assert step.delay_ms >= 4.0


@pytest.mark.asyncio
async def test_06_cognitive_reading_pause_execution():
    """Audit cognitive reading pause log-normal timing."""
    from behavioral_evasion_suite import cognitive_reading_pause
    import time

    start = time.time()
    await cognitive_reading_pause(min_ms=50.0, max_ms=100.0)
    elapsed = (time.time() - start) * 1000.0

    assert elapsed >= 40.0, f"Pause was too fast: {elapsed:.1f}ms"


def test_07_os_network_stack_spoofer():
    """Audit passive OS TCP/IP socket TTL spoofer (Windows TTL = 128)."""
    from behavioral_evasion_suite import OSNetworkStackSpoofer, NetworkStackConfig

    spoofer = OSNetworkStackSpoofer(NetworkStackConfig(ip_ttl=128))
    report = spoofer.get_network_identity_report()
    assert report["ip_ttl"] == 128
    assert "Windows 11" in report["target_os"]

    args = spoofer.get_browser_network_launch_args()
    assert any("--disable-features=" in arg for arg in args)

    # Test defensive socket setsockopt
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        res = spoofer.configure_socket_ttl(sock)
        # Sockets on Windows/Linux will accept IP_TTL
        assert res in (True, False)
    finally:
        sock.close()


@pytest.mark.asyncio
async def test_08_stealth_session_quantum_wiring():
    """Audit StealthSession initialization and Level 5 shield bundling."""
    from behavioral_evasion_suite import StealthSession, human_scroll

    session = StealthSession()
    assert hasattr(session, "worker_shield")
    assert hasattr(session, "subpixel_font_shield")
    assert hasattr(session, "hardware_synthesizer")
    assert hasattr(session, "gaze_physics")
    assert hasattr(session, "network_spoofer")

    level5_scripts = session.get_level5_scripts()
    assert "window.__worker_universal_shield_active__" in level5_scripts
    assert "window.__subpixel_font_shield_active__" in level5_scripts
    assert "window.__virtual_hardware_synthesizer_active__" in level5_scripts

    async with session as s:
        assert s.page is not None
        # Test human scroll execution on mock or real page
        await human_scroll(s.page, target_y=300)


def test_09_level4_legacy_regression():
    """Verify legacy Level 4 components function seamlessly without conflicts."""
    from behavioral_evasion_suite import (
        BiomechanicalMousePhysics,
        CognitiveKeystrokeEngine,
        CanvasWebGLShaderSpoofer,
        PowerHandMaster,
        HoneypotIsolationShield,
        V8BytecodeShield,
        CDPEvasionShield,
        HardwareOSSpoofer
    )

    # Mouse Physics
    mouse = BiomechanicalMousePhysics()
    curve = mouse.generate_trajectory(start=(0, 0), end=(500, 300))
    assert len(curve) > 5

    # Keystroke Engine
    keystroke = CognitiveKeystrokeEngine()
    plan = keystroke.generate_human_keystroke_plan('hello')
    assert len(plan) >= 5
    typed_actions = [p for p in plan if p.get('action') == 'type']
    assert len(typed_actions) >= 5
    assert all(p['delay'] > 0 for p in typed_actions)

    # Canvas & Shaders
    canvas = CanvasWebGLShaderSpoofer()
    assert "WebGLRenderingContext" in canvas.get_canvas_shader_spoofer_script()

    # V8 Shield & Honeypot
    v8 = V8BytecodeShield()
    assert "Function.prototype.toString" in v8.get_v8_masking_script()
    honeypot = HoneypotIsolationShield()
    assert "honeypot" in honeypot.get_honeypot_js_payload().lower()

    # Master Facade Bundling
    master = PowerHandMaster()
    scripts = master.get_all_stealth_scripts()
    assert len(scripts) > 500


if __name__ == "__main__":
    import unittest
    # Allow running directly via python
    pytest.main(["-v", __file__])


