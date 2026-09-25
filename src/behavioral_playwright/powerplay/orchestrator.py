"""
PowerPlay Master Orchestrator (Bpp).
Unified entrypoint encapsulating all 10 mathematical and behavioral subsystems.
"""

from behavioral_playwright.powerplay.tracking import StatefulEvasionTracker
from behavioral_playwright.powerplay.os_bridge import (
    OSLevelDisplayInputBridge,
)
from behavioral_playwright.powerplay.biomechanics import BiomechanicalTremorEngine
from behavioral_playwright.powerplay.keystrokes import LinguisticKeystrokeDynamicsEngine
from behavioral_playwright.powerplay.network_l4 import TCPTTLMTUAligner
from behavioral_playwright.powerplay.captcha import ResolvedCAPTCHAInfiniteLoopDetector
from behavioral_playwright.powerplay.schema_guard import ResolvedSchemaIntegrityGuard
from behavioral_playwright.powerplay.vision_guard import UltimateVisionLanguageActionGuard
from behavioral_playwright.powerplay.memory_pid import ResolvedChromiumMemoryPIDController
from behavioral_playwright.powerplay.validator import BiometricDistributionValidator


class Bpp:
    """
    Master Orchestrator alias exposing all mathematical and OS-level shields.
    Usage:
        from behavioral_playwright.powerplay import Bpp
        bot = Bpp()
    """
    def __init__(self) -> None:
        self.tracker = StatefulEvasionTracker()
        self.os_bridge = OSLevelDisplayInputBridge()
        self.biomechanics = BiomechanicalTremorEngine()
        self.keystrokes = LinguisticKeystrokeDynamicsEngine()
        self.tcp_tuner = TCPTTLMTUAligner()
        self.vision_guard = UltimateVisionLanguageActionGuard()
        self.loop_detector = ResolvedCAPTCHAInfiniteLoopDetector()
        self.schema_guard = ResolvedSchemaIntegrityGuard()
        self.memory_pid = ResolvedChromiumMemoryPIDController()
        self.validator = BiometricDistributionValidator()
