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

from behavioral_playwright.powerplay.tracking import StatefulEvasionTracker
from behavioral_playwright.powerplay.os_bridge import (
    VirtualDisplayManager,
    OSLevelInputBridge,
    OSLevelDisplayInputBridge,
)
from behavioral_playwright.powerplay.biomechanics import BiomechanicalTremorEngine
from behavioral_playwright.powerplay.keystrokes import LinguisticKeystrokeDynamicsEngine
from behavioral_playwright.powerplay.network_l4 import TCPTTLMTUAligner
from behavioral_playwright.powerplay.captcha import ResolvedCAPTCHAInfiniteLoopDetector
from behavioral_playwright.powerplay.schema_guard import ResolvedSchemaIntegrityGuard
from behavioral_playwright.powerplay.vision_guard import UltimateVisionLanguageActionGuard
from behavioral_playwright.powerplay.memory_pid import ResolvedChromiumMemoryPIDController
from behavioral_playwright.powerplay.orchestrator import Bpp

__all__ = [
    "Bpp",
    "StatefulEvasionTracker",
    "VirtualDisplayManager",
    "OSLevelInputBridge",
    "OSLevelDisplayInputBridge",
    "BiomechanicalTremorEngine",
    "LinguisticKeystrokeDynamicsEngine",
    "TCPTTLMTUAligner",
    "ResolvedCAPTCHAInfiniteLoopDetector",
    "ResolvedSchemaIntegrityGuard",
    "UltimateVisionLanguageActionGuard",
    "ResolvedChromiumMemoryPIDController",
]
