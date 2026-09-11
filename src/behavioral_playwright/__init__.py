"""
behavioral-playwright: Resilient, self-healing browser automation framework
built on Playwright. Primary package interface — exposes the unified BP facade
and all core configuration/session classes for clean global imports:

    from behavioral_playwright import BP, AutomationConfig
"""

__version__ = "10.0.0"

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
from behavioral_playwright.proxy.pool import ProxyPool
from behavioral_playwright.fingerprint.generator import FingerprintGenerator
from behavioral_playwright.storage.exporters import DataStorageManager
from behavioral_playwright.facade import BP
from behavioral_playwright.powerplay import Bpp
import behavioral_playwright.powerplay as powerplay
from behavioral_playwright.providers import (
    BaseBrowserProvider,
    PatchrightProvider,
    UndetectedChromedriverProvider,
    BrowserUseProvider,
    StagehandProvider,
    CurlCffiProvider,
    create_browser_provider,
    create_network_provider,
    create_agent_provider,
    provider_matrix,
)

__all__ = [
    "__version__",
    "AutomationConfig",
    "BaseBrowserProvider",
    "BehavioralPlaywrightError",
    "BoundingBox",
    "BP",
    "Bpp",
    "BrowserConfig",
    "BrowserProvider",
    "BrowserProviderError",
    "BrowserSession",
    "BrowserUseProvider",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerError",
    "CircuitState",
    "ConfigurationError",
    "create_agent_provider",
    "create_browser_provider",
    "create_network_provider",
    "CurlCffiProvider",
    "DataStorageManager",
    "DOMElement",
    "DOMExtractor",
    "ElementResolutionError",
    "ExtractionError",
    "ExtractionRecord",
    "FingerprintGenerator",
    "FuzzyResolverStrategy",
    "KeyboardController",
    "MockBrowserProvider",
    "MouseController",
    "NavigationError",
    "PageSession",
    "PageStateEntry",
    "PatchrightProvider",
    "PlaywrightProvider",
    "powerplay",
    "provider_matrix",
    "ProxyPool",
    "ResolutionResult",
    "ResolutionStrategy",
    "ResolverConfig",
    "RetryConfig",
    "RetryPolicy",
    "ScrollController",
    "SelfHealingResolver",
    "SemanticResolverStrategy",
    "StagehandProvider",
    "StateTracker",
    "TimeoutError",
    "UndetectedChromedriverProvider",
]

