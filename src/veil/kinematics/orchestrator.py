"""
PowerPlay Master Orchestrator (Bpp).
Unified entrypoint encapsulating all 10 mathematical and behavioral subsystems.
"""

from veil.kinematics.tracking import StatefulEvasionTracker
from veil.kinematics.os_bridge import (
    OSLevelDisplayInputBridge,
)
from veil.kinematics.biomechanics import BiomechanicalTremorEngine
from veil.kinematics.keystrokes import LinguisticKeystrokeDynamicsEngine
from veil.kinematics.network_l4 import TCPTTLMTUAligner
from veil.kinematics.captcha import ResolvedCAPTCHAInfiniteLoopDetector
from veil.kinematics.schema_guard import ResolvedSchemaIntegrityGuard
from veil.kinematics.vision_guard import UltimateVisionLanguageActionGuard
from veil.kinematics.memory_pid import ResolvedChromiumMemoryPIDController
from veil.kinematics.validator import BiometricDistributionValidator


class Bpp:
    """
    Master Orchestrator alias exposing all mathematical and OS-level shields.
    Usage:
        from veil.kinematics import Bpp
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
