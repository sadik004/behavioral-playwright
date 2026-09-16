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

__version__ = "6.0.0"

__all__ = [
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
    "OrchestrationDomain"
]
