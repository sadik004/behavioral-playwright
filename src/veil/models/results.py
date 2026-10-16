"""Result models for selector resolution and data extraction."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from behavioral_playwright.models.elements import DOMElement


class ResolutionStrategy(str, Enum):
    """Cascading strategies supported by the SelfHealingResolver."""
    L1_EXACT = "L1_EXACT"
    L2_SEMANTIC = "L2_SEMANTIC"
    L3_FUZZY = "L3_FUZZY"
    MEMORY = "MEMORY"
    L4_VISION_LLM = "L4_VISION_LLM"  # Planned future extension


class ResolutionResult(BaseModel):
    """Structured result returned by SelfHealingResolver."""
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True, extra="allow")

    success: bool
    strategy: ResolutionStrategy
    confidence: float
    selector: Optional[str] = None
    element_count: int = 0
    reason: str = ""
    target: str = ""
    matched_element: Optional[DOMElement] = None
    candidates: List[DOMElement] = Field(default_factory=list)
    elapsed_ms: float = 0.0

    def __init__(
        self,
        success: bool = False,
        strategy: ResolutionStrategy = ResolutionStrategy.L1_EXACT,
        confidence: float = 0.0,
        selector: Optional[str] = None,
        element_count: int = 0,
        reason: str = "",
        target: str = "",
        matched_element: Optional[DOMElement] = None,
        candidates: Optional[List[DOMElement]] = None,
        elapsed_ms: float = 0.0,
        **data: Any,
    ) -> None:
        if candidates is None:
            candidates = []
        super().__init__(
            success=success,
            strategy=strategy,
            confidence=confidence,
            selector=selector,
            element_count=element_count,
            reason=reason,
            target=target,
            matched_element=matched_element,
            candidates=candidates,
            elapsed_ms=elapsed_ms,
            **data,
        )

    @property
    def is_healed(self) -> bool:
        """Indicates if recovery required L2, L3, or L4 strategies."""
        return self.success and self.strategy != ResolutionStrategy.L1_EXACT

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return self.model_dump()

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class ExtractionRecord(BaseModel):
    """Represents a structured record extracted from DOM nodes."""
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True, extra="allow")

    text: str = ""
    href: Optional[str] = None
    url: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    page_url: Optional[str] = None
    selector: Optional[str] = None
    timestamp: Optional[str] = None
    extracted_at: Optional[float] = None
    raw_value: Optional[str] = None

    def __init__(
        self,
        text: str = "",
        href: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        url: Optional[str] = None,
        page_url: Optional[str] = None,
        selector: Optional[str] = None,
        timestamp: Optional[str] = None,
        extracted_at: Optional[float] = None,
        raw_value: Optional[str] = None,
        **data: Any,
    ) -> None:
        if href is None and url is not None:
            href = url
        elif url is None and href is not None:
            url = href
        if attributes is None:
            attributes = {}
        if metadata is None:
            metadata = {}
        super().__init__(
            text=text,
            href=href,
            url=url,
            attributes=attributes,
            metadata=metadata,
            page_url=page_url,
            selector=selector,
            timestamp=timestamp,
            extracted_at=extracted_at,
            raw_value=raw_value,
            **data,
        )


    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        d = self.model_dump()
        if d.get("url") is None and d.get("href") is not None:
            d["url"] = d["href"]
        return d

    def __getitem__(self, item: str) -> Any:
        if item == "url":
            val = getattr(self, "url", None) or getattr(self, "href", None)
            if val is not None:
                return val
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def __contains__(self, item: str) -> bool:
        if item == "url" and (self.url is not None or self.href is not None):
            return True
        return hasattr(self, item)

    def get(self, key: str, default: Any = None) -> Any:
        if key == "url":
            val = getattr(self, "url", None) or getattr(self, "href", None)
            return val if val is not None else default
        return getattr(self, key, default)


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


__all__ = ["ResolutionStrategy", "ResolutionResult", "ExtractionRecord", "CSRDriftReport"]

