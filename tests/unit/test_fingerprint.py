"""Unit tests for dynamic fingerprint and hardware profile generator."""

import pytest
from behavioral_playwright.fingerprint.models import OSPlatform, FingerprintProfile
from behavioral_playwright.fingerprint.generator import FingerprintGenerator


def test_fingerprint_generator_coherence():
    gen = FingerprintGenerator(seed=42)

    # Windows profile
    win_prof = gen.generate(platform=OSPlatform.WINDOWS)
    assert win_prof.platform == OSPlatform.WINDOWS
    assert win_prof.platform_string == "Win32"
    assert "Windows" in win_prof.user_agent
    assert win_prof.screen.width > 0
    assert win_prof.webgl.vendor != ""
    assert win_prof.canvas_noise_seed > 0

    # macOS profile
    mac_prof = gen.generate(platform=OSPlatform.MACOS)
    assert mac_prof.platform == OSPlatform.MACOS
    assert mac_prof.platform_string == "MacIntel"
    assert "Macintosh" in mac_prof.user_agent
    assert "Apple" in mac_prof.webgl.vendor

    # Browser Context Mapping
    opts = win_prof.to_browser_context_options()
    assert "user_agent" in opts
    assert "viewport" in opts
    assert opts["viewport"]["width"] == win_prof.screen.width

    # Evasion Script generation
    script = gen.generate_evasion_script(win_prof)
    assert "WebGLRenderingContext" in script
    assert "hardwareConcurrency" in script
    assert str(win_prof.hardware_concurrency) in script
