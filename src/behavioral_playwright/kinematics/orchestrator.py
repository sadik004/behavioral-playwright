"""
PowerPlay Master Orchestrator (Bpp).
Unified entrypoint encapsulating all 10 mathematical and behavioral subsystems.
"""

from behavioral_playwright.kinematics.tracking import StatefulEvasionTracker
from behavioral_playwright.kinematics.os_bridge import (
    OSLevelDisplayInputBridge,
)
from behavioral_playwright.kinematics.biomechanics import BiomechanicalTremorEngine
from behavioral_playwright.kinematics.keystrokes import LinguisticKeystrokeDynamicsEngine
from behavioral_playwright.kinematics.network_l4 import TCPTTLMTUAligner
from behavioral_playwright.kinematics.captcha import ResolvedCAPTCHAInfiniteLoopDetector
from behavioral_playwright.kinematics.schema_guard import ResolvedSchemaIntegrityGuard
from behavioral_playwright.kinematics.vision_guard import UltimateVisionLanguageActionGuard
from behavioral_playwright.kinematics.memory_pid import ResolvedChromiumMemoryPIDController
from behavioral_playwright.kinematics.validator import BiometricDistributionValidator


class Bpp:
    """
    Master Orchestrator alias exposing all mathematical and OS-level shields.
    Usage:
        from behavioral_playwright.kinematics import Bpp
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
