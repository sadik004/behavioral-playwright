"""Models for structured page intelligence, schema mapping, and search."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    """Source layer of extracted field evidence."""
    DOM = "DOM"
    JSON_LD = "JSON_LD"
    OPEN_GRAPH = "OPEN_GRAPH"
    NEXT_DATA = "NEXT_DATA"
    NUXT_DATA = "NUXT_DATA"
    METADATA = "METADATA"


class FieldEvidence(BaseModel):
    """Observed candidate evidence for a structured schema field."""
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str
    source_type: SourceType = SourceType.DOM
    raw_value: Any = None
    normalized_value: Any = None
    confidence: float = 0.0
    selector: Optional[str] = None
    tag: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    page_url: str = ""
    timestamp: str = ""
    reason: str = ""


class MappedField(BaseModel):
    """A resolved and verified schema field with provenance and ambiguity markers."""
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str
    value: Any = None
    confidence: float = 0.0
    evidence: Optional[FieldEvidence] = None
    is_ambiguous: bool = False
    candidate_count: int = 1
    alternative_candidates: List[FieldEvidence] = Field(default_factory=list)


class MappingResult(BaseModel):
    """Structured result returned by PageSchemaMapper."""
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    success: bool = False
    model: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    fields: Dict[str, MappedField] = Field(default_factory=dict)
    confidence: float = 0.0
    ambiguities: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    page_url: str = ""
    timestamp: str = ""
    elapsed_ms: float = 0.0

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def __getitem__(self, item: str) -> Any:
        return self.data[item]

    def __contains__(self, item: str) -> bool:
        return item in self.data


class SearchResultItem(BaseModel):
    """Structured item returned from search execution."""
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    title: str = ""
    href: str = ""
    snippet: str = ""
    position: int = 0
    page_url: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
