"""Data models for behavioral-playwright."""

from behavioral_playwright.models.elements import BoundingBox, DOMElement
from behavioral_playwright.models.results import (
    CSRDriftReport,
    ExtractionRecord,
    ResolutionResult,
    ResolutionStrategy,
)
from behavioral_playwright.models.linkedin_dtos import (
    LinkedInAuthStatusDTO,
    LinkedInProfileDTO,
    LinkedInUpdateResultDTO,
)
from behavioral_playwright.models.reddit_dtos import (
    RedditAuthStatusDTO,
    RedditLeadAuditDTO,
    RedditLeadDTO,
)

__all__ = [
    "BoundingBox",
    "DOMElement",
    "ExtractionRecord",
    "ResolutionResult",
    "ResolutionStrategy",
    "CSRDriftReport",
    "LinkedInProfileDTO",
    "LinkedInAuthStatusDTO",
    "LinkedInUpdateResultDTO",
    "RedditLeadDTO",
    "RedditLeadAuditDTO",
    "RedditAuthStatusDTO",
]

