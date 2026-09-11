"""Result models for selector resolution and data extraction."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from behavioral_playwright.models.elements import DOMElement


class ResolutionStrategy(str, Enum):
    """Cascading strategies supported by the SelfHealingResolver."""
    L1_EXACT = "L1_EXACT"
    L2_SEMANTIC = "L2_SEMANTIC"
    L3_FUZZY = "L3_FUZZY"
    L4_VISION_LLM = "L4_VISION_LLM"  # Planned future extension


@dataclass
class ResolutionResult:
    """Structured result returned by SelfHealingResolver."""
    success: bool
    strategy: ResolutionStrategy
    confidence: float
    selector: Optional[str]
    element_count: int
    reason: str
    target: str
    matched_element: Optional[DOMElement] = None
    candidates: List[DOMElement] = field(default_factory=list)
    elapsed_ms: float = 0.0

    @property
    def is_healed(self) -> bool:
        """Indicates if recovery required L2, L3, or L4 strategies."""
        return self.success and self.strategy != ResolutionStrategy.L1_EXACT


@dataclass
class ExtractionRecord:
    """Represents a structured record extracted from DOM nodes."""
    text: str
    href: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
