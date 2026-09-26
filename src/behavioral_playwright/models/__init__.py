"""Data models for behavioral-playwright."""

from behavioral_playwright.models.elements import BoundingBox, DOMElement
from behavioral_playwright.models.results import (
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
from behavioral_playwright.models.seo_dtos import (
    AIOAuditResult,
    CannibalizationReport,
    CSRDriftReport,
    PAANode,
    SuggestResult,
)

__all__ = [
    "BoundingBox",
    "DOMElement",
    "ExtractionRecord",
    "ResolutionResult",
    "ResolutionStrategy",
    "PAANode",
    "AIOAuditResult",
    "CannibalizationReport",
    "SuggestResult",
    "CSRDriftReport",
    "LinkedInProfileDTO",
    "LinkedInAuthStatusDTO",
    "LinkedInUpdateResultDTO",
    "RedditLeadDTO",
    "RedditLeadAuditDTO",
    "RedditAuthStatusDTO",
]

