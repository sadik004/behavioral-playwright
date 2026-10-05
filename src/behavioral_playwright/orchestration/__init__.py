"""Advanced Orchestration & Agentic Workflow Subsystem."""

from __future__ import annotations

from behavioral_playwright.orchestration.conditions import ConditionEvaluator
from behavioral_playwright.orchestration.exceptions import (
    ApprovalRequiredError,
    ExecutionError,
    OrchestrationError,
    PlanError,
    PolicyViolationError,
    PostconditionFailedError,
    PreconditionFailedError,
    RunawayLoopError,
    StateTransitionError,
    VerificationFailedError,
    WorkflowError,
    WorkflowTimeoutError,
)
from behavioral_playwright.orchestration.executor import WorkflowExecutor
from behavioral_playwright.orchestration.limits import LoopProtectionConfig, LoopProtector
from behavioral_playwright.orchestration.models import (
    ActionType,
    Condition,
    StepStatus,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
)
from behavioral_playwright.orchestration.orchestrator import WorkflowOrchestrator
from behavioral_playwright.orchestration.planner import (
    BasePlanner,
    DeterministicPlanner,
    ExternalAgentPlanner,
)
from behavioral_playwright.orchestration.policies import (
    ApprovalManager,
    ApprovalTicket,
    SafetyPolicy,
)
from behavioral_playwright.orchestration.provenance import (
    StepProvenanceRecord,
    WorkflowProvenanceChain,
)
from behavioral_playwright.orchestration.state import StateTransitionRecord, WorkflowState
from behavioral_playwright.orchestration.verification import (
    VerificationEvidence,
    WorkflowVerifier,
    verify_workflow_result,
)

__all__ = [
    # Models
    "WorkflowStatus",
    "StepStatus",
    "ActionType",
    "Condition",
    "WorkflowStep",
    "WorkflowDefinition",
    "WorkflowResult",
    # State & Provenance
    "WorkflowState",
    "StateTransitionRecord",
    "StepProvenanceRecord",
    "WorkflowProvenanceChain",
    # Limits & Policies
    "LoopProtectionConfig",
    "LoopProtector",
    "SafetyPolicy",
    "ApprovalManager",
    "ApprovalTicket",
    # Conditions & Verification
    "ConditionEvaluator",
    "WorkflowVerifier",
    "VerificationEvidence",
    "verify_workflow_result",
    # Planner & Executor
    "BasePlanner",
    "DeterministicPlanner",
    "ExternalAgentPlanner",
    "WorkflowExecutor",
    # Central Orchestrator
    "WorkflowOrchestrator",
    # Exceptions
    "OrchestrationError",
    "WorkflowError",
    "PlanError",
    "ExecutionError",
    "PreconditionFailedError",
    "PostconditionFailedError",
    "PolicyViolationError",
    "ApprovalRequiredError",
    "RunawayLoopError",
    "VerificationFailedError",
    "WorkflowTimeoutError",
    "StateTransitionError",
]
