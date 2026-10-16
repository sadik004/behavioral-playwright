"""Domain models and DTOs for 4-Tier Adaptive Crawling Subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CrawlerTier(str, Enum):
    """4-Tier Escalation Hierarchy for Crawling Operations."""
    HTTP_FAST = "HTTP_FAST"
    TLS_IMPERSONATE = "TLS_IMPERSONATE"
    BROWSER_HEADLESS = "BROWSER_HEADLESS"
    BROWSER_STEALTH_KINEMATICS = "BROWSER_STEALTH_KINEMATICS"


@dataclass
class CrawlRequest:
    """Incoming request payload for tiered crawling."""
    url: str
    headers: Optional[Dict[str, str]] = None
    timeout_s: float = 30.0
    max_tier: CrawlerTier = CrawlerTier.BROWSER_STEALTH_KINEMATICS
    initial_tier: CrawlerTier = CrawlerTier.HTTP_FAST
    anti_bot_detection: bool = True
    extract_rules: Optional[Dict[str, Any]] = None


@dataclass
class EscalationRecord:
    """Telemetry record captured upon each tier escalation or failure."""
    tier: CrawlerTier
    status_code: Optional[int] = None
    reason: str = ""
    latency_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value if isinstance(self.tier, CrawlerTier) else str(self.tier),
            "status_code": self.status_code,
            "reason": self.reason,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
        }


@dataclass
class CrawlResponse:
    """Consolidated crawl response with full escalation telemetry."""
    url: str
    status_code: int
    body: str
    headers: Dict[str, str] = field(default_factory=dict)
    resolved_tier: CrawlerTier = CrawlerTier.HTTP_FAST
    escalation_history: List[EscalationRecord] = field(default_factory=list)
    is_success: bool = True
    challenge_detected: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None

    @property
    def escalations_count(self) -> int:
        return len(self.escalation_history)
