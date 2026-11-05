"""Dynamic fingerprint and hardware profile generator."""

from behavioral_playwright.fingerprint.models import (
    FingerprintProfile,
    OSPlatform,
    ScreenSpec,
    WebGLSpec,
)
from behavioral_playwright.fingerprint.generator import FingerprintGenerator
from behavioral_playwright.fingerprint.profiles import CURATED_PROFILES

__all__ = [
    "FingerprintProfile",
    "FingerprintGenerator",
    "OSPlatform",
    "ScreenSpec",
    "WebGLSpec",
    "CURATED_PROFILES",
]
