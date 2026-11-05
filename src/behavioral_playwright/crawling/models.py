"""Data models for 4-Tier Adaptive Crawling (`veil.crawling.models`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class CrawlerTier(str, Enum):
    HTTP_FAST = "HTTP_FAST"
    TLS_IMPERSONATE = "TLS_IMPERSONATE"
    BROWSER_HEADLESS = "BROWSER_HEADLESS"
    BROWSER_STEALTH_KINEMATICS = "BROWSER_STEALTH_KINEMATICS"


@dataclass
class CrawlRequest:
    url: str
    initial_tier: CrawlerTier = CrawlerTier.HTTP_FAST
    max_tier: CrawlerTier = CrawlerTier.BROWSER_STEALTH_KINEMATICS
    headers: Optional[Dict[str, str]] = None
    timeout_s: float = 15.0
    anti_bot_detection: bool = True


@dataclass
class EscalationRecord:
    tier: CrawlerTier
    status_code: Optional[int]
    reason: str
    latency_ms: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value if hasattr(self.tier, "value") else str(self.tier),
            "status_code": self.status_code,
            "reason": self.reason,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


@dataclass
class CrawlResponse:
    url: str
    status_code: int
    body: str
    headers: Dict[str, str] = field(default_factory=dict)
    resolved_tier: CrawlerTier = CrawlerTier.HTTP_FAST
    escalation_history: List[EscalationRecord] = field(default_factory=list)
    is_success: bool = True
    challenge_detected: Optional[str] = None

    @property
    def html(self) -> str:
        return self.body

    @property
    def success(self) -> bool:
        return self.is_success

    @property
    def escalations_count(self) -> int:
        return len(self.escalation_history)


__all__ = [
    "CrawlerTier",
    "CrawlRequest",
    "EscalationRecord",
    "CrawlResponse",
]
