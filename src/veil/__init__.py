"""Veil: Enterprise Behavioral Automation and Anti-Bot Evasion Engine."""
from __future__ import annotations

__version__ = "10.0.2"

from veil.facade import BP
from veil.config.settings import AutomationConfig, AuthConfig, BrowserConfig
from veil.page.session import BrowserSession, PageSession
from veil.proxy.models import ProxyProtocol
from veil.models.elements import DOMElement
from veil.selectors.resolver import SelfHealingResolver

# Core Kinematic & Mathematical Engines
from veil.kinematics.biomechanics import BiomechanicalTremorEngine, SaccadicMouseEngine
from veil.kinematics.keystrokes import LinguisticKeystrokeDynamicsEngine
from veil.kinematics.validator import BiometricDistributionValidator
from veil.kinematics.captcha import ResolvedCAPTCHAInfiniteLoopDetector
from veil.kinematics.memory_pid import ResolvedChromiumMemoryPIDController
from veil.kinematics.schema_guard import ResolvedSchemaIntegrityGuard
from veil.kinematics.vision_guard import UltimateVisionLanguageActionGuard
from veil.kinematics.orchestrator import Bpp
from veil.kinematics import orchestrator as powerplay

# Orchestration & Workflow Models
from veil.orchestration.orchestrator import WorkflowOrchestrator
from veil.orchestration.models import (
    ActionType,
    StepStatus,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
)

# Integrations
from veil.integrations.linkedin import LinkedInAutomationClient
from veil.integrations.reddit import RedditAutomationClient

__all__ = [
    "BP",
    "AutomationConfig",
    "AuthConfig",
    "BrowserConfig",
    "BrowserSession",
    "PageSession",
    "ProxyProtocol",
    "DOMElement",
    "SelfHealingResolver",
    "Bpp",
    "powerplay",
    "BiomechanicalTremorEngine",
    "SaccadicMouseEngine",
    "LinguisticKeystrokeDynamicsEngine",
    "BiometricDistributionValidator",
    "ResolvedCAPTCHAInfiniteLoopDetector",
    "ResolvedChromiumMemoryPIDController",
    "ResolvedSchemaIntegrityGuard",
    "UltimateVisionLanguageActionGuard",
    "WorkflowOrchestrator",
    "ActionType",
    "StepStatus",
    "WorkflowDefinition",
    "WorkflowResult",
    "WorkflowStatus",
    "WorkflowStep",
    "LinkedInAutomationClient",
    "RedditAutomationClient",
    "__version__",
]


def __getattr__(name: str):
    import importlib
    import veil.facade as _facade

    if hasattr(_facade, name):
        val = getattr(_facade, name)
        globals()[name] = val
        return val

    try:
        submod = importlib.import_module(f"veil.{name}")
        globals()[name] = submod
        return submod
    except ImportError as err:
        raise AttributeError(f"module 'veil' has no attribute '{name}'") from err
