"""
Behavioral Evasion Suite & PowerHand Unified Master Engine (v6.0.0 Level 5 Quantum Edition)
Unified Modular Anti-Bot Evasion Architecture, Statistical Biometric Engine, and Quantum Shields
"""

from .utils import NATIVE_SPOOF_JS, SanitizedLogFormatter, setup_sanitized_logger
from .cdp_evasion import CDPEvasionShield
from .tls_ja4_spoofer import TLSJA4Spoofer, AsyncSession
from .mouse_physics import BiomechanicalMousePhysics
from .hardware_os_spoofer import HardwareOSSpoofer
from .context_rotator import ContextRotator
from .os_resource_guard import OSResourceGuard
from .session_vault import SessionStateVault
from .circuit_breaker import StatusGranularCircuitBreaker
from .persistence_pipeline import BasePersistencePipeline
from .backpressure_queue import BackpressureQueue
from .quality_sentinel import QualitySentinel
from .hybrid_router import SmartAcquisitionRouter
from .strict_context import StrictContextManager

# PowerHand Extensions
from .dma_kernel_bridge import OSKernelInputEventBridge, FPGAPCIeDMAHardwareBridge
from .persona_matrix import ProfileVault, BehavioralDNA, IdentityAnchor, DigitalSoulPersonaMatrix
from .honeypot_shield import HoneypotIsolationShield
from .v8_shield import V8BytecodeShield
from .keystroke_engine import CognitiveKeystrokeEngine
from .webauthn_virtual_tpm import VirtualTPMWebAuthnRelay, attach_cdp_virtual_authenticator
from .canvas_shader_spoofer import CanvasWebGLShaderSpoofer
from .swarm_orchestrator import MultiTabSwarmOrchestrator
from .powerhand_master import PowerHandMaster, PowerHandPlaywrightRunner

# Level 5 Quantum Edition Shields
from .worker_universal_shield import WorkerUniversalShield, WorkerShieldConfig
from .subpixel_font_shield import SubpixelFontShield, FontMetricConfig
from .virtual_hardware_synthesizer import (
    VirtualHardwareSynthesizer,
    MediaDeviceDescriptor,
    HardwareSynthesisConfig
)
from .cognitive_gaze_physics import (
    CognitiveGazePhysics,
    GazePhysicsConfig,
    ScrollTrajectoryPoint,
    human_scroll,
    cognitive_reading_pause
)
from .os_network_stack_spoofer import OSNetworkStackSpoofer, NetworkStackConfig
from .stealth_session import StealthSession, human_click, human_type, stealth_async

# Unified Quantum Architecture & MCP Orchestration Layer
from .unified_quantum_facade import (
    UnifiedQuantumFacade,
    PersistentSessionManager,
    TokenOptimizedDOMReader,
    HardenedBrowserDomain,
    HardwareNetworkDomain,
    BiometricKinematicsDomain,
    SecurityDataDomain,
    OrchestrationDomain
)

# Ergonomic Presets & Fluent Developer API (Code UX)
from .presets import Preset, StealthConfig
from .stealth_browser import StealthBrowser, StealthPage
from .stealthify import stealthify, AutonomousChallengeSolver


# Unified Security Auditor v5 Integration
try:
    from .unified_security_auditor_v5 import (
        UnifiedSecurityAuditorV5,
        attach_dom_sink_auditor,
        get_dom_sink_events,
        SAMLTrustChainAuditor,
        OAuth2TrustChainAuditor,
        DualContextAuditor,
        MCPSchemaAuditor,
        StateDiffAuditor,
        PoCEngine,
        AgentHijackAuditor,
        ClosedLoopFuzzer,
        DesyncEngine,
        CVEReproducer,
    )
except ImportError:
    UnifiedSecurityAuditorV5 = None
    attach_dom_sink_auditor = None
    get_dom_sink_events = None
    SAMLTrustChainAuditor = None
    OAuth2TrustChainAuditor = None
    DualContextAuditor = None
    MCPSchemaAuditor = None
    StateDiffAuditor = None
    PoCEngine = None
    AgentHijackAuditor = None
    ClosedLoopFuzzer = None
    DesyncEngine = None
    CVEReproducer = None


# GraphQL Deep Logic & Protected Attribute Security Engine Integration
try:
    from .graphql_security_auditor import (
        GraphQLIntrospectionAuditor,
        GraphQLProtectedAttributeAuditor,
        GraphQLAliasedBatchingAuditor,
        GraphQLQueryComplexityAuditor,
        GraphQLCSRFAuditor,
        GraphQLPoCEngine,
        MasterGraphQLDeepLogicEngine,
    )
except ImportError:
    GraphQLIntrospectionAuditor = None
    GraphQLProtectedAttributeAuditor = None
    GraphQLAliasedBatchingAuditor = None
    GraphQLQueryComplexityAuditor = None
    GraphQLCSRFAuditor = None
    GraphQLPoCEngine = None
    MasterGraphQLDeepLogicEngine = None


# Server-Side Prototype Pollution (SSPP) Security Auditor Integration
try:
    from .sspp_security_auditor import (
        SSPPPayloadGenerator,
        SSPPResponseAnalyzer,
        SSPPBlackBoxAuditor,
        MasterSSPPDeepLogicEngine,
        SSPPFinding,
        SSPPScanResult,
        CapturedAPIRequest
    )
except ImportError:
    SSPPPayloadGenerator = None
    SSPPResponseAnalyzer = None
    SSPPBlackBoxAuditor = None
    MasterSSPPDeepLogicEngine = None
    SSPPFinding = None
    SSPPScanResult = None
    CapturedAPIRequest = None

__version__ = "6.0.0"


# Clean Architecture Protocol & DTO Integration
try:
    from .security_protocol import (
        SecurityAuditorProtocol,
        BaseSecurityAuditor,
        SecurityFinding,
        AuditResultDTO
    )
except ImportError:
    SecurityAuditorProtocol = None
    BaseSecurityAuditor = None
    SecurityFinding = None
    AuditResultDTO = None


# Out-Of-Band (OOB) Interaction Subsystem
try:
    from .oob_listener import (
        OOBInteractionDTO,
        OOBProviderProtocol,
        MockOOBProvider,
        InteractshOOBProvider,
        MasterOOBClient
    )
except ImportError:
    OOBInteractionDTO = None
    OOBProviderProtocol = None
    MockOOBProvider = None
    InteractshOOBProvider = None
    MasterOOBClient = None

__all__ = [
    "OOBInteractionDTO",
    "OOBProviderProtocol",
    "MockOOBProvider",
    "InteractshOOBProvider",
    "MasterOOBClient",
    "SecurityAuditorProtocol",
    "BaseSecurityAuditor",
    "SecurityFinding",
    "AuditResultDTO",
    "__version__",
    "NATIVE_SPOOF_JS",
    "SanitizedLogFormatter",
    "setup_sanitized_logger",
    "CDPEvasionShield",
    "TLSJA4Spoofer",
    "AsyncSession",
    "BiomechanicalMousePhysics",
    "HardwareOSSpoofer",
    "ContextRotator",
    "OSResourceGuard",
    "SessionStateVault",
    "StatusGranularCircuitBreaker",
    "BasePersistencePipeline",
    "BackpressureQueue",
    "QualitySentinel",
    "SmartAcquisitionRouter",
    "StrictContextManager",
    "OSKernelInputEventBridge",
    "FPGAPCIeDMAHardwareBridge",
    "ProfileVault",
    "BehavioralDNA",
    "IdentityAnchor",
    "DigitalSoulPersonaMatrix",
    "HoneypotIsolationShield",
    "V8BytecodeShield",
    "CognitiveKeystrokeEngine",
    "VirtualTPMWebAuthnRelay",
    "attach_cdp_virtual_authenticator",
    "CanvasWebGLShaderSpoofer",
    "MultiTabSwarmOrchestrator",
    "PowerHandMaster",
    "PowerHandPlaywrightRunner",
    "WorkerUniversalShield",
    "WorkerShieldConfig",
    "SubpixelFontShield",
    "FontMetricConfig",
    "VirtualHardwareSynthesizer",
    "MediaDeviceDescriptor",
    "HardwareSynthesisConfig",
    "CognitiveGazePhysics",
    "GazePhysicsConfig",
    "ScrollTrajectoryPoint",
    "human_scroll",
    "cognitive_reading_pause",
    "OSNetworkStackSpoofer",
    "NetworkStackConfig",
    "StealthSession",
    "human_click",
    "human_type",
    "stealth_async",
    "UnifiedQuantumFacade",
    "PersistentSessionManager",
    "TokenOptimizedDOMReader",
    "HardenedBrowserDomain",
    "HardwareNetworkDomain",
    "BiometricKinematicsDomain",
    "SecurityDataDomain",
    "OrchestrationDomain",
    "Preset",
    "StealthConfig",
    "StealthBrowser",
    "StealthPage",
    "stealthify",
    "AutonomousChallengeSolver",
    "UnifiedSecurityAuditorV5",
    "attach_dom_sink_auditor",
    "get_dom_sink_events",
    "SAMLTrustChainAuditor",
    "OAuth2TrustChainAuditor",
    "DualContextAuditor",
    "MCPSchemaAuditor",
    "StateDiffAuditor",
    "PoCEngine",
    "AgentHijackAuditor",
    "ClosedLoopFuzzer",
    "DesyncEngine",
    "CVEReproducer"
    "GraphQLIntrospectionAuditor",
    "GraphQLProtectedAttributeAuditor",
    "GraphQLAliasedBatchingAuditor",
    "GraphQLQueryComplexityAuditor",
    "GraphQLCSRFAuditor",
    "GraphQLPoCEngine",
    "MasterGraphQLDeepLogicEngine",
    "SSPPPayloadGenerator",
    "SSPPResponseAnalyzer",
    "SSPPBlackBoxAuditor",
    "MasterSSPPDeepLogicEngine",
    "SSPPFinding",
    "SSPPScanResult",
    "CapturedAPIRequest",

]
