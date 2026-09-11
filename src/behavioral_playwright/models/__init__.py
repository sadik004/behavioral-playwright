"""Data models for behavioral-playwright."""

from behavioral_playwright.models.elements import BoundingBox, DOMElement
from behavioral_playwright.models.results import (
    ExtractionRecord,
    ResolutionResult,
    ResolutionStrategy,
)

__all__ = [
    "BoundingBox",
    "DOMElement",
    "ExtractionRecord",
    "ResolutionResult",
    "ResolutionStrategy",
]
