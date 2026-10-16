"""Backward-compatibility forwarding module for providers.agents.

Exposes all agent provider classes forwarded from
src.behavioral_playwright.providers to ensure legacy imports never break.
"""

from __future__ import annotations

from src.behavioral_playwright.providers import (
    BrowserUseProvider,
    StagehandProvider,
)

__all__ = [
    "BrowserUseProvider",
    "StagehandProvider",
]
