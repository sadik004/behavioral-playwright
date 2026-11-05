"""Configuration dataclasses for behavioral-playwright."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
    allow_media: bool = False
    channel: Optional[str] = None
    extra_options: Dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        headless: bool = True,
        width: int = 1920,
        height: int = 1080,
        user_data_dir: Optional[str] = None,
        browser_type: str = "chromium",
        timeout_ms: int = 30000,
        slow_mo: float = 0.0,
        args: Optional[List[str]] = None,
        allow_media: bool = False,
        channel: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.headless = headless
        self.width = width
        self.height = height
        self.user_data_dir = user_data_dir
        self.browser_type = browser_type
        self.timeout_ms = timeout_ms
        self.slow_mo = slow_mo
        self.args = list(args) if args is not None else []
        self.allow_media = allow_media
        self.channel = channel
        self.extra_options = kwargs


@dataclass
class ResolverConfig:
    """Configuration for SelfHealingResolver engine."""
    enabled: bool = True
    strategies: List[str] = field(default_factory=lambda: ["L1_EXACT", "L2_SEMANTIC", "L3_FUZZY"])
    confidence_threshold: float = 0.60
    fuzzy_similarity_threshold: float = 0.65
    max_candidates: int = 50
    timeout_ms: int = 10000
    require_unique: bool = False
    enable_memory: bool = True


@dataclass
class RetryConfig:
    """Configuration for resilience RetryPolicy."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 10.0
    exponential_backoff: bool = True
    jitter: bool = False

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_backoff: bool = True,
        jitter: bool = False,
        max_retries: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        self.max_attempts = max_retries if max_retries is not None else max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff
        self.jitter = jitter

    @property
    def max_retries(self) -> int:
        return self.max_attempts

    @max_retries.setter
    def max_retries(self, value: int) -> None:
        self.max_attempts = value


@dataclass
class CircuitBreakerConfig:
    """Configuration for CircuitBreaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_attempts: int = 2


@dataclass
class AuthConfig:
    """
    Shared authentication and credential configuration.
    Resolves credentials with deterministic precedence:
      1. Explicit instance arguments
      2. Environment variables (BP_API_KEY, BP_BEARER_TOKEN)
    """
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None
    api_key_header: str = "X-API-Key"
    custom_headers: dict[str, str] = field(default_factory=dict)

    def resolve(self) -> "AuthConfig":
        """Returns a resolved copy with environment variable fallbacks."""
        import os
        resolved_api_key = self.api_key or os.environ.get("BP_API_KEY")
        resolved_bearer_token = self.bearer_token or os.environ.get("BP_BEARER_TOKEN")
        return AuthConfig(
            api_key=resolved_api_key,
            bearer_token=resolved_bearer_token,
            api_key_header=self.api_key_header,
            custom_headers=dict(self.custom_headers),
        )

    def get_headers(self) -> dict[str, str]:
        """
        Builds HTTP headers for authentication.
        Merges custom_headers, Bearer token, and API key header without mutating state.
        """
        resolved = self.resolve()
        headers = dict(resolved.custom_headers)
        if resolved.bearer_token:
            headers["Authorization"] = f"Bearer {resolved.bearer_token}"
        if resolved.api_key:
            headers[resolved.api_key_header] = resolved.api_key
        return headers


@dataclass
class AutomationConfig:
    """Root configuration container for dependency injection."""
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    resolver: ResolverConfig = field(default_factory=ResolverConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    humanize: bool = True

    def __init__(
        self,
        browser: Optional[BrowserConfig] = None,
        resolver: Optional[ResolverConfig] = None,
        retry: Optional[RetryConfig] = None,
        circuit_breaker: Optional[CircuitBreakerConfig] = None,
        auth: Optional[AuthConfig] = None,
        headless: Optional[bool] = None,
        humanize: bool = True,
        **kwargs: Any,
    ) -> None:
        if browser is not None:
            self.browser = browser
            if headless is not None:
                self.browser.headless = headless
        else:
            self.browser = BrowserConfig(headless=headless if headless is not None else True)
        self.resolver = resolver or ResolverConfig()
        self.retry = retry or RetryConfig()
        self.circuit_breaker = circuit_breaker or CircuitBreakerConfig()
        self.auth = auth or AuthConfig()
        self.humanize = humanize
