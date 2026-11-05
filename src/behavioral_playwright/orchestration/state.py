"""Workflow state management and deterministic transition validation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from behavioral_playwright.orchestration.exceptions import StateTransitionError
from behavioral_playwright.orchestration.models import WorkflowStatus


@dataclass(frozen=True)
class StateTransitionRecord:
    """Immutable audit record of a single workflow state transition."""
    from_status: WorkflowStatus
    to_status: WorkflowStatus
    timestamp: float
    reason: str
    step_id: Optional[str] = None


# Explicit allowable transition graph enforcing deterministic progression
VALID_TRANSITIONS: Dict[WorkflowStatus, Set[WorkflowStatus]] = {
    WorkflowStatus.PENDING: {
        WorkflowStatus.PLANNING,
        WorkflowStatus.RUNNING,
        WorkflowStatus.ABORTED,
        WorkflowStatus.CANCELLED,
    },
    WorkflowStatus.PLANNING: {
        WorkflowStatus.RUNNING,
        WorkflowStatus.FAILED,
        WorkflowStatus.ABORTED,
        WorkflowStatus.CANCELLED,
    },
    WorkflowStatus.RUNNING: {
        WorkflowStatus.VERIFYING,
        WorkflowStatus.WAITING_FOR_APPROVAL,
        WorkflowStatus.RECOVERING,
        WorkflowStatus.COMPLETED,
        WorkflowStatus.FAILED,
        WorkflowStatus.ABORTED,
        WorkflowStatus.TIMED_OUT,
        WorkflowStatus.CANCELLED,
    },
    WorkflowStatus.VERIFYING: {
        WorkflowStatus.RUNNING,
        WorkflowStatus.COMPLETED,
        WorkflowStatus.RECOVERING,
        WorkflowStatus.FAILED,
        WorkflowStatus.ABORTED,
        WorkflowStatus.TIMED_OUT,
        WorkflowStatus.CANCELLED,
    },
    WorkflowStatus.WAITING_FOR_APPROVAL: {
        WorkflowStatus.RUNNING,
        WorkflowStatus.ABORTED,
        WorkflowStatus.CANCELLED,
    },
    WorkflowStatus.RECOVERING: {
        WorkflowStatus.REVERIFYING,
        WorkflowStatus.FAILED,
        WorkflowStatus.ABORTED,
        WorkflowStatus.TIMED_OUT,
        WorkflowStatus.CANCELLED,
    },
    WorkflowStatus.REVERIFYING: {
        WorkflowStatus.RUNNING,
        WorkflowStatus.VERIFYING,
        WorkflowStatus.COMPLETED,
        WorkflowStatus.FAILED,
        WorkflowStatus.ABORTED,
        WorkflowStatus.TIMED_OUT,
        WorkflowStatus.CANCELLED,
    },
    # Terminal states: zero outward transitions allowed
    WorkflowStatus.COMPLETED: set(),
    WorkflowStatus.FAILED: set(),
    WorkflowStatus.ABORTED: set(),
    WorkflowStatus.TIMED_OUT: set(),
    WorkflowStatus.CANCELLED: set(),
}


class WorkflowState:
    """Encapsulates the isolated runtime state of a single workflow instance.
    
    Guarantees:
    1. Zero global mutable state; strictly bound to (workflow_id, session_id).
    2. Validated state transitions with permanent immutable audit history.
    3. Scoped variable context for cross-step data forwarding.
    """

    def __init__(
        self,
        workflow_id: str,
        session_id: str,
        clock_fn: Optional[Any] = None,
    ) -> None:
        self.workflow_id = workflow_id
        self.session_id = session_id
        self._clock_fn = clock_fn or time.monotonic
        self.status = WorkflowStatus.PENDING
        self.current_step_index: int = 0
        self.variables: Dict[str, Any] = {}
        self.history: List[StateTransitionRecord] = []

    def transition_to(
        self,
        new_status: WorkflowStatus,
        reason: str,
        step_id: Optional[str] = None,
    ) -> StateTransitionRecord:
        """Executes a validated state transition or raises StateTransitionError."""
        allowed = VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise StateTransitionError(
                f"Invalid workflow state transition: cannot move from {self.status.value} to {new_status.value}. "
                f"Allowed destinations: {[s.value for s in allowed]} (Reason: '{reason}')"
            )

        now = self._clock_fn()
        record = StateTransitionRecord(
            from_status=self.status,
            to_status=new_status,
            timestamp=now,
            reason=reason,
            step_id=step_id,
        )
        self.history.append(record)
        self.status = new_status
        return record

    def set_variable(self, key: str, value: Any) -> None:
        """Sets an isolated context variable for subsequent steps."""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Retrieves an isolated context variable."""
        return self.variables.get(key, default)

    def is_terminal(self) -> bool:
        """Returns True if the workflow has reached an irreversible terminal state."""
        return self.status in {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.ABORTED,
            WorkflowStatus.TIMED_OUT,
            WorkflowStatus.CANCELLED,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Exports a clean serializable snapshot of the workflow state."""
        return {
            "workflow_id": self.workflow_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "current_step_index": self.current_step_index,
            "variables": dict(self.variables),
            "history": [
                {
                    "from_status": r.from_status.value,
                    "to_status": r.to_status.value,
                    "timestamp": r.timestamp,
                    "reason": r.reason,
                    "step_id": r.step_id,
                }
                for r in self.history
            ],
        }
