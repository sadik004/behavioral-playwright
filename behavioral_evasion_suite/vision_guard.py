"""Backward-compatible module forwarding to `veil.kinematics.vision_guard`."""

from veil.kinematics.vision_guard import (
    UltimateVisionLanguageActionGuard,
)

# Legacy alias
VisionGuard = UltimateVisionLanguageActionGuard

__all__ = [
    "UltimateVisionLanguageActionGuard",
    "VisionGuard",
]
