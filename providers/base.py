"""Backward-compatibility forwarding module for providers.base.

Exposes base provider classes forwarded from
src.behavioral_playwright.providers to ensure identity consistency.
"""
from __future__ import annotations

from src.behavioral_playwright.providers.base import (
    HONESTY_NOTE,
    ProviderInfo,
    ProviderUnavailableError,
    UnknownProviderError,
    detect_provider,
)

__all__ = [
    "HONESTY_NOTE",
    "ProviderInfo",
    "ProviderUnavailableError",
    "UnknownProviderError",
    "detect_provider",
]
