"""Curated real-device hardware signature database."""

from behavioral_playwright.fingerprint.models import (
    FingerprintProfile,
    OSPlatform,
    ScreenSpec,
    WebGLSpec,
)

CURATED_PROFILES: list[FingerprintProfile] = [
    # 1. Modern Windows 11 / Chrome 124 / RTX 4070
    FingerprintProfile(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        platform=OSPlatform.WINDOWS,
        platform_string="Win32",
        screen=ScreenSpec(width=1920, height=1080, avail_width=1920, avail_height=1040, color_depth=24, pixel_ratio=1.0),
        webgl=WebGLSpec(
            vendor="Google Inc. (NVIDIA)",
            renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        languages=["en-US", "en"],
        hardware_concurrency=16,
        device_memory_gb=16,
        canvas_noise_seed=48271,
        audio_noise_seed=0.00012,
        timezone="America/New_York",
    ),
    # 2. Windows 10 / Chrome 123 / Intel Iris Xe
    FingerprintProfile(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        platform=OSPlatform.WINDOWS,
        platform_string="Win32",
        screen=ScreenSpec(width=2560, height=1440, avail_width=2560, avail_height=1400, color_depth=24, pixel_ratio=1.25),
        webgl=WebGLSpec(
            vendor="Google Inc. (Intel)",
            renderer="ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        languages=["en-US", "en"],
        hardware_concurrency=8,
        device_memory_gb=16,
        canvas_noise_seed=91823,
        audio_noise_seed=0.00008,
        timezone="America/Chicago",
    ),
    # 3. macOS Sonoma / Chrome 124 / Apple M2 Pro
    FingerprintProfile(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        platform=OSPlatform.MACOS,
        platform_string="MacIntel",
        screen=ScreenSpec(width=1728, height=1117, avail_width=1728, avail_height=1080, color_depth=30, pixel_ratio=2.0),
        webgl=WebGLSpec(
            vendor="Google Inc. (Apple)",
            renderer="ANGLE (Apple, ANGLE Metal Renderer: Apple M2 Pro, Version 14.4.1 (Build 23E224))",
        ),
        languages=["en-US", "en"],
        hardware_concurrency=12,
        device_memory_gb=16,
        canvas_noise_seed=12938,
        audio_noise_seed=0.00015,
        timezone="America/Los_Angeles",
    ),
    # 4. macOS Sonoma / Chrome 122 / Apple M3 Max
    FingerprintProfile(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        platform=OSPlatform.MACOS,
        platform_string="MacIntel",
        screen=ScreenSpec(width=2056, height=1329, avail_width=2056, avail_height=1290, color_depth=30, pixel_ratio=2.0),
        webgl=WebGLSpec(
            vendor="Google Inc. (Apple)",
            renderer="ANGLE (Apple, ANGLE Metal Renderer: Apple M3 Max, Version 14.3 (Build 23D56))",
        ),
        languages=["en-US", "en"],
        hardware_concurrency=16,
        device_memory_gb=32,
        canvas_noise_seed=84920,
        audio_noise_seed=0.00018,
        timezone="America/New_York",
    ),
    # 5. Linux / Chrome 124 / AMD Radeon
    FingerprintProfile(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        platform=OSPlatform.LINUX,
        platform_string="Linux x86_64",
        screen=ScreenSpec(width=1920, height=1080, avail_width=1920, avail_height=1055, color_depth=24, pixel_ratio=1.0),
        webgl=WebGLSpec(
            vendor="Google Inc. (AMD)",
            renderer="ANGLE (AMD, AMD Radeon RX 6700 XT (radeonsi, navi22, LLVM 17.0.6), OpenGL 4.6)",
        ),
        languages=["en-US", "en"],
        hardware_concurrency=12,
        device_memory_gb=16,
        canvas_noise_seed=57102,
        audio_noise_seed=0.00011,
        timezone="Europe/London",
    ),
]
