"""
PowerPlay Subsystem for Behavioral Playwright.

Provides mathematical models, statistical estimation tools, and behavioral simulation
components:
- Biomechanical mouse trajectory generation (Costello saccades + Harris-Wolpert noise)
- Keystroke dynamics (Euclidean QWERTY distance + Weibull latency distribution)
- Closed-loop PID memory management with anti-windup clamping
- Normalized GIoU and centroid spatial action verification
- O(N) Shannon entropy content auditing
- Poisson CDF CAPTCHA loop risk modeling
- Stateful session tracking and threat indexing
- OS-level virtual display and input simulation stubs

Note on Evasion and Bypasses:
The models in this package provide mathematical trajectory and timing synthesis.
They do not guarantee bypasses of third-party anti-bot systems such as Cloudflare,
Akamai, Kasada, or DataDome.
"""

from behavioral_playwright.kinematics.tracking import StatefulEvasionTracker
from behavioral_playwright.kinematics.os_bridge import (
    VirtualDisplayManager,
    OSLevelInputBridge,
    OSLevelDisplayInputBridge,
)
from behavioral_playwright.kinematics.biomechanics import (
    BiomechanicalTremorEngine,
    BiometricMouseController,
    generate_pre_click_stream,
    generate_newton_wheel_scroll,
    compute_teleport_click_ratio,
    compute_scroll_speed_variance,
)
from behavioral_playwright.kinematics.keystrokes import LinguisticKeystrokeDynamicsEngine
from behavioral_playwright.kinematics.network_l4 import TCPTTLMTUAligner
from behavioral_playwright.kinematics.captcha import ResolvedCAPTCHAInfiniteLoopDetector
from behavioral_playwright.kinematics.schema_guard import ResolvedSchemaIntegrityGuard
from behavioral_playwright.kinematics.vision_guard import UltimateVisionLanguageActionGuard
from behavioral_playwright.kinematics.memory_pid import ResolvedChromiumMemoryPIDController
from behavioral_playwright.kinematics.validator import BiometricDistributionValidator
from behavioral_playwright.kinematics.orchestrator import Bpp

# Canonical Renames (Milestone 2)
BiometricOrchestrator = Bpp
SaccadicMouseEngine = BiomechanicalTremorEngine
KeystrokeCadenceEngine = LinguisticKeystrokeDynamicsEngine
SocketTTLInspector = TCPTTLMTUAligner
CaptchaLoopDetector = ResolvedCAPTCHAInfiniteLoopDetector
ContentEntropyGuard = ResolvedSchemaIntegrityGuard
SpatialActionGuard = UltimateVisionLanguageActionGuard
MemoryPIDController = ResolvedChromiumMemoryPIDController
BiometricValidator = BiometricDistributionValidator
SessionThreatTracker = StatefulEvasionTracker

__all__ = [
    "Bpp",
    "BiometricOrchestrator",
    "StatefulEvasionTracker",
    "SessionThreatTracker",
    "VirtualDisplayManager",
    "OSLevelInputBridge",
    "OSLevelDisplayInputBridge",
    "BiomechanicalTremorEngine",
    "SaccadicMouseEngine",
    "BiometricMouseController",
    "generate_pre_click_stream",
    "generate_newton_wheel_scroll",
    "compute_teleport_click_ratio",
    "compute_scroll_speed_variance",
    "LinguisticKeystrokeDynamicsEngine",
    "KeystrokeCadenceEngine",
    "TCPTTLMTUAligner",
    "SocketTTLInspector",
    "ResolvedCAPTCHAInfiniteLoopDetector",
    "CaptchaLoopDetector",
    "ResolvedSchemaIntegrityGuard",
    "ContentEntropyGuard",
    "UltimateVisionLanguageActionGuard",
    "SpatialActionGuard",
    "ResolvedChromiumMemoryPIDController",
    "MemoryPIDController",
    "BiometricDistributionValidator",
    "BiometricValidator",
]
