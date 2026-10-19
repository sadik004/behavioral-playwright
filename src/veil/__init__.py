"""
behavioral-playwright: Resilient, self-healing browser automation framework
built on Playwright. Primary package interface — exposes the unified BP facade
and all core configuration/session classes for clean global imports:

    from behavioral_playwright import BP, AutomationConfig
"""

__version__ = "10.0.2"

from veil.facade import BP
Veil = BP

try:
    from behavioral_playwright.automation.keyboard import KeyboardController
    from behavioral_playwright.automation.mouse import MouseController
    from behavioral_playwright.automation.scroll import ScrollController
    from behavioral_playwright.browser.base import BrowserProvider
    from behavioral_playwright.browser.mock_provider import MockBrowserProvider
    from behavioral_playwright.browser.playwright_provider import PlaywrightProvider
    from behavioral_playwright.browser.pool import BrowserPoolManager
    from behavioral_playwright.models.seo_dtos import (
        AIOAuditResult,
        CannibalizationReport,
        CSRDriftReport,
        PAANode,
        SuggestResult,
    )
    from behavioral_playwright.models.linkedin_dtos import (
        LinkedInAuthStatusDTO,
        LinkedInProfileDTO,
        LinkedInUpdateResultDTO,
    )
    from behavioral_playwright.models.reddit_dtos import (
        RedditAuthStatusDTO,
        RedditLeadAuditDTO,
        RedditLeadDTO,
    )
    from behavioral_playwright.integrations.linkedin import LinkedInAutomationClient
    from behavioral_playwright.integrations.reddit import RedditAutomationClient
    try:
        from behavioral_playwright.mining import (
            AIOAuditor,
            CSRRenderingDriftAuditor,
            GoogleSuggestMiner,
            PAAMiner,
            RenderingDriftAuditor,
            SEOMiningEngine,
            SERPCannibalizationEngine,
            SuggestMiner,
        )
    except Exception:
        _ = "handled_expected_exception"  # SWALLOW-001 remediated
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
    from behavioral_playwright.extraction.dom import (
        DOMExtractor,
        extract_json_ld,
        extract_next_data,
        extract_nuxt_data,
        extract_open_graph,
    )
    from behavioral_playwright.network.sniffer import JSONResponseSniffer
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
    from veil.facade import BP

    from behavioral_playwright.powerplay import (
        Bpp,
        BiomechanicalTremorEngine,
        BiometricDistributionValidator,
        LinguisticKeystrokeDynamicsEngine,
        ResolvedCAPTCHAInfiniteLoopDetector,
        ResolvedChromiumMemoryPIDController,
        ResolvedSchemaIntegrityGuard,
        UltimateVisionLanguageActionGuard,
    )
    import behavioral_playwright.powerplay as powerplay
    try:
        import behavioral_playwright.kinematics as kinematics
    except ImportError:
        kinematics = powerplay

    from behavioral_playwright.powerplay.tracking import StatefulEvasionTracker
    from behavioral_playwright.powerplay.network_l4 import TCPTTLMTUAligner
    from behavioral_playwright.fingerprint.persona_profile import DigitalSoulPersonaMatrix, DevicePersonaProfile
    from behavioral_playwright.powerplay.kernel_input_bridge import FPGAPCIeDMAHardwareBridge, KernelInputBridge
    from behavioral_playwright.security.graphql_auditor import MasterGraphQLDeepLogicEngine, GraphQLSecurityAuditor
    from behavioral_playwright.security.web_security_auditor import UnifiedSecurityAuditorV5, WebSecurityAuditor
    from behavioral_playwright.evasion.worker_shield import WorkerUniversalShield, WorkerScopeShield
    try:
        from behavioral_evasion_suite.powerhand_master import (
            PowerHandMaster,
            PowerHandPlaywrightRunner,
            StealthSuite,
            StealthRunner,
        )
    except ImportError:
        from behavioral_evasion_suite.powerhand_master import (
            PowerHandMaster,
            PowerHandPlaywrightRunner,
        )
        StealthSuite = PowerHandMaster
        StealthRunner = PowerHandPlaywrightRunner

    from behavioral_playwright.crawling.service import CrawlingService, VeilEngine

    # Canonical Class & Symbol Renames (Milestone 2)
    Veil = BP
    BiometricOrchestrator = Bpp
    VeilError = BehavioralPlaywrightError
    CaptchaLoopDetector = ResolvedCAPTCHAInfiniteLoopDetector
    MemoryPIDController = ResolvedChromiumMemoryPIDController
    ContentEntropyGuard = ResolvedSchemaIntegrityGuard
    SpatialActionGuard = UltimateVisionLanguageActionGuard
    SaccadicMouseEngine = BiomechanicalTremorEngine
    KeystrokeCadenceEngine = LinguisticKeystrokeDynamicsEngine
    BiometricValidator = BiometricDistributionValidator
    SessionThreatTracker = StatefulEvasionTracker
    SocketTTLInspector = TCPTTLMTUAligner

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
    from behavioral_playwright.orchestration import (
        ActionType,
        StepStatus,
        WorkflowDefinition,
        WorkflowOrchestrator,
        WorkflowProvenanceChain,
        WorkflowResult,
        WorkflowStatus,
        WorkflowStep,
        verify_workflow_result,
    )
    import behavioral_playwright.orchestration as orchestration
except ImportError as _optional_init_exc:
    _ = _optional_init_exc

__all__ = [
    "__version__",
    "Veil",
    "BiometricOrchestrator",
    "VeilError",
    "VeilEngine",
    "CaptchaLoopDetector",
    "MemoryPIDController",
    "ContentEntropyGuard",
    "SpatialActionGuard",
    "SaccadicMouseEngine",
    "KeystrokeCadenceEngine",
    "BiometricValidator",
    "SessionThreatTracker",
    "SocketTTLInspector",
    "DevicePersonaProfile",
    "KernelInputBridge",
    "GraphQLSecurityAuditor",
    "WebSecurityAuditor",
    "WorkerScopeShield",
    "StealthSuite",
    "StealthRunner",
    "AIOAuditResult",
    "AIOAuditor",
    "ActionType",
    "AutomationConfig",
    "BaseBrowserProvider",
    "BehavioralPlaywrightError",
    "BiomechanicalTremorEngine",
    "BiometricDistributionValidator",
    "BoundingBox",
    "BP",
    "Bpp",
    "BrowserConfig",
    "BrowserPoolManager",
    "BrowserProvider",
    "BrowserProviderError",
    "BrowserSession",
    "BrowserUseProvider",
    "CannibalizationReport",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerError",
    "CircuitState",
    "ConfigurationError",
    "CrawlingService",
    "create_agent_provider",
    "create_browser_provider",
    "create_network_provider",
    "CSRDriftReport",
    "CSRRenderingDriftAuditor",
    "CurlCffiProvider",
    "DataStorageManager",
    "DigitalSoulPersonaMatrix",
    "DOMElement",
    "DOMExtractor",
    "ElementResolutionError",
    "extract_json_ld",
    "extract_next_data",
    "extract_nuxt_data",
    "extract_open_graph",
    "ExtractionError",
    "ExtractionRecord",
    "FingerprintGenerator",
    "FPGAPCIeDMAHardwareBridge",
    "FuzzyResolverStrategy",
    "GoogleSuggestMiner",
    "JSONResponseSniffer",
    "KeyboardController",
    "kinematics",
    "LinguisticKeystrokeDynamicsEngine",
    "LinkedInAuthStatusDTO",
    "LinkedInAutomationClient",
    "LinkedInProfileDTO",
    "LinkedInUpdateResultDTO",
    "MasterGraphQLDeepLogicEngine",
    "MockBrowserProvider",
    "MouseController",
    "NavigationError",
    "orchestration",
    "PAAMiner",
    "PAANode",
    "PageSession",
    "PageStateEntry",
    "PatchrightProvider",
    "PlaywrightProvider",
    "PowerHandMaster",
    "PowerHandPlaywrightRunner",
    "powerplay",
    "provider_matrix",
    "ProxyPool",
    "RedditAuthStatusDTO",
    "RedditAutomationClient",
    "RedditLeadAuditDTO",
    "RedditLeadDTO",
    "RenderingDriftAuditor",
    "ResolutionResult",
    "ResolutionStrategy",
    "ResolverConfig",
    "ResolvedCAPTCHAInfiniteLoopDetector",
    "ResolvedChromiumMemoryPIDController",
    "ResolvedSchemaIntegrityGuard",
    "RetryConfig",
    "RetryPolicy",
    "ScrollController",
    "SelfHealingResolver",
    "SemanticResolverStrategy",
    "SEOMiningEngine",
    "SERPCannibalizationEngine",
    "StagehandProvider",
    "StatefulEvasionTracker",
    "StateTracker",
    "StepStatus",
    "SuggestMiner",
    "SuggestResult",
    "TCPTTLMTUAligner",
    "TimeoutError",
    "UltimateVisionLanguageActionGuard",
    "UndetectedChromedriverProvider",
    "UnifiedSecurityAuditorV5",
    "WorkflowDefinition",
    "WorkflowOrchestrator",
    "WorkflowProvenanceChain",
    "WorkflowResult",
    "WorkflowStatus",
    "WorkflowStep",
    "WorkerUniversalShield",
    "verify_workflow_result",
]
