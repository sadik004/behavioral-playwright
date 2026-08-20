"""
behavioral-playwright: Resilient, self-healing browser automation framework built on Playwright.
"""

__version__ = "1.0.0"

from behavioral_playwright.automation.keyboard import KeyboardController
from behavioral_playwright.automation.mouse import MouseController
from behavioral_playwright.automation.scroll import ScrollController
from behavioral_playwright.browser.base import BrowserProvider
from behavioral_playwright.browser.mock_provider import MockBrowserProvider
from behavioral_playwright.browser.playwright_provider import PlaywrightProvider
from behavioral_playwright.config.settings import (
    AutomationConfig,
    BrowserConfig,
    CircuitBreakerConfig,
    ResolverConfig,
    RetryConfig,
)
from behavioral_playwright.exceptions import (
    BehavioralPlaywrightError,
    BrowserProviderError,
    CircuitBreakerError,
    ConfigurationError,
    ElementResolutionError,
    ExtractionError,
    NavigationError,
    TimeoutError,
)
from behavioral_playwright.extraction.dom import DOMExtractor
from behavioral_playwright.models.elements import BoundingBox, DOMElement
from behavioral_playwright.models.results import (
    ExtractionRecord,
    ResolutionResult,
    ResolutionStrategy,
)
from behavioral_playwright.page.session import BrowserSession, PageSession
from behavioral_playwright.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
)
from behavioral_playwright.resilience.retry import RetryPolicy
from behavioral_playwright.resilience.state import PageStateEntry, StateTracker
from behavioral_playwright.selectors.fuzzy import FuzzyResolverStrategy
from behavioral_playwright.selectors.resolver import SelfHealingResolver
from behavioral_playwright.selectors.semantic import SemanticResolverStrategy

__all__ = [
    "__version__",
    "AutomationConfig",
    "BehavioralPlaywrightError",
    "BoundingBox",
    "BrowserConfig",
    "BrowserProvider",
    "BrowserProviderError",
    "BrowserSession",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerError",
    "CircuitState",
    "ConfigurationError",
    "DOMElement",
    "DOMExtractor",
    "ElementResolutionError",
    "ExtractionError",
    "ExtractionRecord",
    "FuzzyResolverStrategy",
    "KeyboardController",
    "MockBrowserProvider",
    "MouseController",
    "NavigationError",
    "PageSession",
    "PageStateEntry",
    "PlaywrightProvider",
    "ResolutionResult",
    "ResolutionStrategy",
    "ResolverConfig",
    "RetryConfig",
    "RetryPolicy",
    "ScrollController",
    "SelfHealingResolver",
    "SemanticResolverStrategy",
    "StateTracker",
    "TimeoutError",
]
