"""Safety, authorization, and Human-in-the-Loop approval policies."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from behavioral_playwright.orchestration.exceptions import ApprovalRequiredError, PolicyViolationError
from behavioral_playwright.orchestration.models import ActionType, WorkflowStep


@dataclass
class ApprovalTicket:
    """Represents an active human-in-the-loop approval request."""
    ticket_id: str
    workflow_id: str
    step_id: str
    action: str
    action_type: ActionType
    input_data: Dict[str, Any]
    status: str = "PENDING"                   # "PENDING", "APPROVED", "REJECTED"
    approved_by: Optional[str] = None
    reason: Optional[str] = None


class SafetyPolicy:
    """Enforces execution boundaries, privilege restrictions, and safety gating."""

    def __init__(
        self,
        disallowed_actions: Optional[Set[str]] = None,
        allow_external_side_effects: bool = False,
        allow_arbitrary_code_eval: bool = False,
        require_unique_resolution: bool = True,
    ) -> None:
        self.disallowed_actions = disallowed_actions or set()
        self.allow_external_side_effects = allow_external_side_effects
        self.allow_arbitrary_code_eval = allow_arbitrary_code_eval
        self.require_unique_resolution = require_unique_resolution

    def validate_step(self, step: WorkflowStep) -> None:
        """Validates that a proposed step complies with safety boundaries."""
        # 1. Disallowed explicit action names
        if step.action in self.disallowed_actions:
            raise PolicyViolationError(
                f"Policy Violation: Action '{step.action}' is explicitly forbidden by safety policy."
            )

        # 2. External side effect without permission
        if step.action_type == ActionType.EXTERNAL_SIDE_EFFECT and not self.allow_external_side_effects:
            raise PolicyViolationError(
                f"Policy Violation: External side-effect action '{step.action}' is blocked. "
                "Explicit allow_external_side_effects authorization required."
            )

        # 3. Direct unescaped code eval prohibition
        if step.action in ("evaluate_raw", "exec", "eval") and not self.allow_arbitrary_code_eval:
            raise PolicyViolationError(
                f"Policy Violation: Arbitrary runtime code evaluation '{step.action}' is prohibited."
            )

        # 4. Anti-positional fallback invariant: forbid blind .first() / nth=0 where uniqueness required
        if self.require_unique_resolution and step.action in ("resolve", "click", "type"):
            sel = step.input_data.get("selector", "")
            if ":nth-child(" in sel or ".first()" in sel or sel.endswith(":first-child"):
                # If specifically requested positional without semantic scoping
                if step.input_data.get("allow_positional") is not True:
                    raise PolicyViolationError(
                        f"Policy Violation: Fragile positional selector '{sel}' is prohibited. "
                        "Unique semantic or ARIA resolution is mandatory."
                    )


class ApprovalManager:
    """Manages Human-in-the-Loop (HITL) approval ticketing and status resolution."""

    def __init__(self, require_approval_for: Optional[Set[ActionType]] = None) -> None:
        self.require_approval_for = require_approval_for or {
            ActionType.EXTERNAL_SIDE_EFFECT,
        }
        self._tickets: Dict[str, ApprovalTicket] = {}

    def needs_approval(self, step: WorkflowStep) -> bool:
        """Determines whether a step triggers an approval gate."""
        return step.action_type in self.require_approval_for

    def create_ticket(self, workflow_id: str, step: WorkflowStep) -> ApprovalTicket:
        """Generates a pending approval ticket for an action."""
        ticket_id = f"ticket_{uuid.uuid4().hex[:8]}"
        ticket = ApprovalTicket(
            ticket_id=ticket_id,
            workflow_id=workflow_id,
            step_id=step.step_id,
            action=step.action,
            action_type=step.action_type,
            input_data=dict(step.input_data),
        )
        self._tickets[ticket_id] = ticket
        return ticket

    def approve(self, ticket_id: str, approver: str, reason: str = "") -> None:
        """Approves a pending ticket."""
        if ticket_id not in self._tickets:
            raise KeyError(f"Approval ticket '{ticket_id}' not found.")
        t = self._tickets[ticket_id]
        t.status = "APPROVED"
        t.approved_by = approver
        t.reason = reason

    def reject(self, ticket_id: str, rejector: str, reason: str = "") -> None:
        """Rejects a pending ticket."""
        if ticket_id not in self._tickets:
            raise KeyError(f"Approval ticket '{ticket_id}' not found.")
        t = self._tickets[ticket_id]
        t.status = "REJECTED"
        t.approved_by = rejector
        t.reason = reason

    def is_ticket_approved(self, ticket_id: str) -> bool:
        """Checks if a ticket has been explicitly approved."""
        ticket = self._tickets.get(ticket_id)
        return ticket is not None and ticket.status == "APPROVED"

    def get_ticket_for_step(self, workflow_id: str, step_id: str) -> Optional[ApprovalTicket]:
        """Finds any existing ticket created for a specific workflow step."""
        for t in self._tickets.values():
            if t.workflow_id == workflow_id and t.step_id == step_id:
                return t
        return None
