"""Domain models and data structures for orchestration and agentic workflows."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class WorkflowStatus(str, Enum):
    """Lifecycle statuses of an orchestrator workflow."""
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    RECOVERING = "RECOVERING"
    REVERIFYING = "REVERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


class StepStatus(str, Enum):
    """Execution statuses of an individual workflow step."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ABORTED = "ABORTED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"


class ActionType(str, Enum):
    """Authoritative taxonomy of workflow action risk and execution characteristics."""
    READ_ONLY = "READ_ONLY"                   # Safe, non-mutating inspection (e.g. resolve, inspect DOM)
    NAVIGATION = "NAVIGATION"                 # Network transition (e.g. goto, reload)
    DOM_INTERACTION = "DOM_INTERACTION"       # Interaction with page elements (e.g. hover, focus, scroll)
    DATA_EXTRACTION = "DATA_EXTRACTION"       # Structural extraction / schema mapping
    STATE_MUTATION = "STATE_MUTATION"         # Page or form mutation (e.g. click, type, submit)
    EXTERNAL_SIDE_EFFECT = "EXTERNAL_SIDE_EFFECT"  # High-impact external side-effect (e.g. purchase, external API call)


@dataclass
class Condition:
    """Precondition or postcondition definition for a workflow step."""
    name: str
    condition_type: str = "custom"            # "page_open", "element_exists", "url_matches", "data_present", "custom"
    description: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    evaluator: Optional[Callable[..., Any]] = None


@dataclass
class WorkflowStep:
    """Single declarative or planned step in an orchestrated workflow."""
    step_id: str
    action: str                               # e.g. "navigate", "resolve", "click", "type", "extract", "map_schema", "search"
    action_type: ActionType
    input_data: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[Condition] = field(default_factory=list)
    postconditions: List[Condition] = field(default_factory=list)
    timeout_s: float = 30.0
    require_verification: bool = True
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    attempts: int = 0

    @classmethod
    def create(
        cls,
        action: str,
        action_type: ActionType,
        input_data: Optional[Dict[str, Any]] = None,
        step_id: Optional[str] = None,
        preconditions: Optional[List[Condition]] = None,
        postconditions: Optional[List[Condition]] = None,
        timeout_s: float = 30.0,
        require_verification: bool = True,
    ) -> WorkflowStep:
        return cls(
            step_id=step_id or f"step_{uuid.uuid4().hex[:8]}",
            action=action,
            action_type=action_type,
            input_data=input_data or {},
            preconditions=preconditions or [],
            postconditions=postconditions or [],
            timeout_s=timeout_s,
            require_verification=require_verification,
        )


@dataclass
class WorkflowDefinition:
    """Complete specification of a multi-step workflow."""
    workflow_id: str
    session_id: str
    name: str = "default_workflow"
    steps: List[WorkflowStep] = field(default_factory=list)
    timeout_budget_s: float = 120.0
    max_step_count: int = 50
    max_recovery_budget: int = 3
    require_verification: bool = True
    require_approval_for: List[ActionType] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        session_id: str,
        steps: Optional[List[WorkflowStep]] = None,
        name: str = "workflow",
        workflow_id: Optional[str] = None,
        timeout_budget_s: float = 120.0,
        max_step_count: int = 50,
        max_recovery_budget: int = 3,
        require_verification: bool = True,
        require_approval_for: Optional[List[ActionType]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowDefinition:
        return cls(
            workflow_id=workflow_id or f"wf_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            name=name,
            steps=steps or [],
            timeout_budget_s=timeout_budget_s,
            max_step_count=max_step_count,
            max_recovery_budget=max_recovery_budget,
            require_verification=require_verification,
            require_approval_for=require_approval_for or [],
            metadata=metadata or {},
        )


@dataclass
class WorkflowResult:
    """Immutable final output and verification record of an orchestrated workflow."""
    workflow_id: str
    session_id: str
    status: WorkflowStatus
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    output: Any = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    elapsed_s: float = 0.0
    error: Optional[str] = None
    is_verified: bool = False

    def validate_integrity(self) -> bool:
        """Validates that a supposedly COMPLETED / is_verified result has authentic non-empty provenance records."""
        if self.is_verified:
            if not self.provenance or not self.step_results:
                return False
            status_val = self.status.value if hasattr(self.status, "value") else str(self.status)
            if status_val != "COMPLETED":
                return False
        return True
