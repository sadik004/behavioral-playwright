"""Fingerprint data structures and device models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class OSPlatform(str, Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"


@dataclass(frozen=True)
class ScreenSpec:
    width: int
    height: int
    avail_width: int
    avail_height: int
    color_depth: int = 24
    pixel_ratio: float = 1.0


@dataclass(frozen=True)
class WebGLSpec:
    vendor: str
    renderer: str
    gl_version: str = "WebGL 2.0 (OpenGL ES 3.0 Chromium)"
    shading_language_version: str = "WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)"


@dataclass(frozen=True)
class FingerprintProfile:
    """Coherent device and browser fingerprint signature."""

    user_agent: str
    platform: OSPlatform
    platform_string: str  # e.g. "Win32", "MacIntel", "Linux x86_64"
    screen: ScreenSpec
    webgl: WebGLSpec
    languages: List[str] = field(default_factory=lambda: ["en-US", "en"])
    hardware_concurrency: int = 8
    device_memory_gb: int = 8
    canvas_noise_seed: int = 1337
    audio_noise_seed: float = 0.0001
    timezone: str = "America/New_York"
    webrtc_policy: str = "default"

    def to_browser_context_options(self) -> Dict[str, object]:
        """Maps profile to Playwright browser context options."""
        return {
            "user_agent": self.user_agent,
            "viewport": {"width": self.screen.width, "height": self.screen.height},
            "device_scale_factor": self.screen.pixel_ratio,
            "locale": self.languages[0] if self.languages else "en-US",
            "timezone_id": self.timezone,
            "color_scheme": "dark",
        }
