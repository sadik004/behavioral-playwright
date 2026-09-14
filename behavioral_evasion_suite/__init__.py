"""
Behavioral Evasion Suite & PowerHand Unified Master Engine (Hardened Enterprise v5.1 - Level 4 Edition)
Unified Modular Anti-Bot Evasion Architecture & Statistical Biometric Engine
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

# Formally Verified PowerHand Frontiers
from .powerhand_master import (
    SmartDataExtractionEngine,
    JSDeobfuscator,
    WASMPoWSolver,
    PayloadDecryptor,
    ReverseEngineeringEngine,
    DiffusionBiomechanicalTrajectoryEngine,
    ZeroDOMVLAMultimodalAgent,
    SourceLevelChromiumPatcher,
    PQTLSMLEKEMFingerprinter,
    RLHFBiomechanicalController,
    PCIeTLPFPGAIPCore,
    EBPFXDPNetworkCoProcessor,
    DecentralizedSwarmConsensus,
    ZKTelemetryGenerator,
)

# Optional Level 4 Additions: Coherent Profiles & High-Level Developer API
try:
    from .coherent_profile_loader import CoherentProfileLoader, CoherentDeviceProfile
except ImportError:
    CoherentProfileLoader = None  # type: ignore
    CoherentDeviceProfile = None  # type: ignore

try:
    from .stealth_session import StealthSession, stealth_async, human_type, human_click
except ImportError:
    StealthSession = None  # type: ignore
    stealth_async = None  # type: ignore
    human_type = None  # type: ignore
    human_click = None  # type: ignore

__all__ = [
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
    "SmartDataExtractionEngine",
    "JSDeobfuscator",
    "WASMPoWSolver",
    "PayloadDecryptor",
    "ReverseEngineeringEngine",
    "DiffusionBiomechanicalTrajectoryEngine",
    "ZeroDOMVLAMultimodalAgent",
    "SourceLevelChromiumPatcher",
    "PQTLSMLEKEMFingerprinter",
    "RLHFBiomechanicalController",
    "PCIeTLPFPGAIPCore",
    "EBPFXDPNetworkCoProcessor",
    "DecentralizedSwarmConsensus",
    "ZKTelemetryGenerator",
    "CoherentProfileLoader",
    "CoherentDeviceProfile",
    "StealthSession",
    "stealth_async",
    "human_type",
    "human_click",
]
