"""Typed exceptions for the orchestration and agentic workflow subsystem."""

from __future__ import annotations

from typing import Any, Optional
from behavioral_playwright.exceptions import BehavioralPlaywrightError


class OrchestrationError(BehavioralPlaywrightError):
    """Base exception for all orchestration subsystem errors."""
    pass


class WorkflowError(OrchestrationError):
    """Raised when workflow construction or execution fails."""
    pass


class PlanError(OrchestrationError):
    """Raised when a planner fails to produce a valid execution plan."""
    pass


class ExecutionError(OrchestrationError):
    """Raised when an underlying workflow step execution fails."""
    pass


class PreconditionFailedError(OrchestrationError):
    """Raised when a step precondition check fails prior to action execution."""
    pass


class PostconditionFailedError(OrchestrationError):
    """Raised when a step postcondition check fails after action execution."""
    pass


class PolicyViolationError(OrchestrationError):
    """Raised when a proposed action violates safety, security, or execution policy."""
    pass


class ApprovalRequiredError(OrchestrationError):
    """Raised when a sensitive or irreversible action requires human or policy approval."""
    pass


class RunawayLoopError(OrchestrationError):
    """Raised when an autonomous loop, action oscillation, or runaway execution is detected."""
    pass


class VerificationFailedError(OrchestrationError):
    """Raised when live runtime post-execution verification fails to validate state."""
    pass


class WorkflowTimeoutError(OrchestrationError):
    """Raised when a workflow or step exceeds its monotonic timeout budget."""
    pass


class StateTransitionError(OrchestrationError):
    """Raised when an invalid or corrupt workflow state transition is attempted."""
    pass
