"""Backward-compatibility forwarding module for providers.browser.

Exposes all browser provider classes forwarded from
src.behavioral_playwright.providers to ensure legacy imports never break.
"""

from __future__ import annotations

from src.behavioral_playwright.providers import (
    BaseBrowserProvider,
    BrowserSession,
    PatchrightProvider,
    PlaywrightProvider,
    UndetectedChromedriverProvider,
)

__all__ = [
    "BaseBrowserProvider",
    "BrowserSession",
    "PatchrightProvider",
    "PlaywrightProvider",
    "UndetectedChromedriverProvider",
]
