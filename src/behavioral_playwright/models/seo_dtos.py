"""
Pydantic v2 Typed Data Transfer Objects (DTOs) for SEO, AEO, and GEO Mining Engines.
Provides strict validation, normalization, and serializability for search intelligence data.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class PAANode(BaseModel):
    """Represents an extracted People Also Ask (PAA) node in a semantic query tree."""
    question: str = Field(..., min_length=1, description="The extracted accordion question.")
    snippet_text: str = Field(default="", description="The text body or snippet answering the question.")
    source_title: str = Field(default="", description="The title of the cited source domain.")
    source_url: str = Field(default="", description="The destination URL cited in the PAA answer.")
    depth: int = Field(default=1, ge=1, le=5, description="Nesting recursion depth (1 to 5).")
    parent_question: Optional[str] = Field(default=None, description="Immediate ancestor question in the expansion tree.")

    @field_validator("question", mode="before")
    @classmethod
    def normalize_question(cls, v: str) -> str:
        if isinstance(v, str):
            cleaned = v.strip().replace("\xa0", " ")
            return cleaned
        return str(v)

    @field_validator("source_url", mode="before")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        if isinstance(v, str) and v:
            v_clean = v.strip()
            if not v_clean.startswith(("http://", "https://")):
                return f"https://{v_clean}"
            return v_clean
        return v or ""


class AIOAuditResult(BaseModel):
    """Audit evaluation report for Google AI Overviews / Search Generative Experience (AEO)."""
    query: str = Field(..., min_length=1, description="Target search query evaluated.")
    has_aio_card: bool = Field(..., description="Whether an AI Overview card was detected on the SERP.")
    summary_text: Optional[str] = Field(default=None, description="Generative summary answer text.")
    citations: List[str] = Field(default_factory=list, description="Citations and linked resource URLs.")
    brand_cited: bool = Field(default=False, description="Whether the audited brand domain/name is cited.")
    brand_rank: Optional[int] = Field(default=None, ge=1, description="Position rank of brand citation (1-based index).")
    competitors_cited: List[str] = Field(default_factory=list, description="List of recognized competitor domains cited.")


class CannibalizationReport(BaseModel):
    """Cannibalization and Generative Engine Optimization (GEO) similarity report between two queries."""
    query_a: str = Field(..., min_length=1, description="First comparison search query.")
    query_b: str = Field(..., min_length=1, description="Second comparison search query.")
    jaccard_score: float = Field(..., ge=0.0, le=1.0, description="Jaccard similarity coefficient (0.0 to 1.0).")
    common_urls: List[str] = Field(default_factory=list, description="Intersecting URLs present in both SERPs.")
    recommendation: str = Field(
        ...,
        description="'MERGE_INTO_SINGLE_CANONICAL' or 'SPLIT_INTO_SEPARATE_PAGES'"
    )

    @field_validator("recommendation")
    @classmethod
    def validate_recommendation(cls, v: str) -> str:
        allowed = ("MERGE_INTO_SINGLE_CANONICAL", "SPLIT_INTO_SEPARATE_PAGES")
        if v not in allowed:
            raise ValueError(f"Recommendation must be one of {allowed}, got {v!r}")
        return v


class SuggestResult(BaseModel):
    """Represents Google Autocomplete suggestion mining and alphabet drilldown output."""
    query: str = Field(..., min_length=1, description="Root search query.")
    suggestions: List[str] = Field(default_factory=list, description="Unique suggested query list.")
    alphabet_tree: dict[str, List[str]] = Field(default_factory=dict, description="A-Z alphabetical drilldown map.")
    total_unique: int = Field(default=0, ge=0, description="Total count of unique suggested queries.")

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return str(v)

    def model_post_init(self, __context: Any) -> None:
        if self.total_unique == 0 and self.suggestions:
            object.__setattr__(self, "total_unique", len(self.suggestions))


class CSRDriftReport(BaseModel):
    """Client-Side Rendering (CSR) vs Static HTML Rendering Drift evaluation report."""
    url: Optional[str] = Field(default=None, description="Audited target URL.")
    raw_html_bytes: int = Field(default=0, ge=0, description="Initial static SSR/HTML payload size in bytes.")
    rendered_html_bytes: int = Field(default=0, ge=0, description="Fully rendered DOM HTML payload size in bytes.")
    raw_dom_nodes: int = Field(default=0, ge=0, description="DOM element count in static HTML.")
    rendered_dom_nodes: int = Field(default=0, ge=0, description="DOM element count in fully rendered page.")
    raw_text_length: int = Field(default=0, ge=0, description="Visible text length in static HTML.")
    rendered_text_length: int = Field(default=0, ge=0, description="Visible text length in rendered DOM.")
    drift_ratio: float = Field(..., ge=0.0, le=1.0, description="Drift score between static and CSR (0.0 to 1.0).")
    missing_in_raw: List[str] = Field(default_factory=list, description="Elements absent in initial HTML but present in CSR.")
    hydration_drift_detected: bool = Field(default=False, description="Whether significant client-side rendering drift was detected.")
    seo_indexation_risk: str = Field(..., description="Risk assessment: 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'.")

    @field_validator("seo_indexation_risk")
    @classmethod
    def validate_risk(cls, v: str) -> str:
        allowed = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Risk must be one of {allowed}, got {v!r}")
        return v_upper


__all__ = [
    "PAANode",
    "AIOAuditResult",
    "CannibalizationReport",
    "SuggestResult",
    "CSRDriftReport",
]
