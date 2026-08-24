"""Configuration dataclasses for behavioral-playwright."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BrowserConfig:
    """Configuration for browser instance launching and management."""
    headless: bool = True
    width: int = 1920
    height: int = 1080
    user_data_dir: Optional[str] = None
    browser_type: str = "chromium"  # chromium, firefox, webkit
    timeout_ms: int = 30000
    slow_mo: float = 0.0
    args: List[str] = field(default_factory=list)


@dataclass
class ResolverConfig:
    """Configuration for SelfHealingResolver engine."""
    enabled: bool = True
    strategies: List[str] = field(default_factory=lambda: ["L1_EXACT", "L2_SEMANTIC", "L3_FUZZY"])
    confidence_threshold: float = 0.60
    fuzzy_similarity_threshold: float = 0.65
    max_candidates: int = 50
    timeout_ms: int = 10000


@dataclass
class RetryConfig:
    """Configuration for resilience RetryPolicy."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 10.0
    exponential_backoff: bool = True
    jitter: bool = False


@dataclass
class CircuitBreakerConfig:
    """Configuration for CircuitBreaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_attempts: int = 2


@dataclass
class AutomationConfig:
    """Root configuration container for dependency injection."""
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    resolver: ResolverConfig = field(default_factory=ResolverConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
