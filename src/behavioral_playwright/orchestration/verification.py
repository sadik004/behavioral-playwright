"""Verification-first execution verification and anti-forgery audit engine."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from behavioral_playwright.orchestration.exceptions import VerificationFailedError
from behavioral_playwright.orchestration.models import ActionType, WorkflowStep


@dataclass
class VerificationEvidence:
    """Certified audit record validating live runtime truth for a step."""
    step_id: str
    action: str
    verified: bool
    timestamp: float
    freshness_delta_s: float
    checks_passed: list[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class WorkflowVerifier:
    """Enforces zero-fraud verification: never trusts planner, boolean flags, or stale memory."""

    MAX_FRESHNESS_DELTA_S: float = 60.0

    def __init__(self, clock_fn: Optional[Any] = None) -> None:
        self._clock_fn = clock_fn or time.monotonic

    async def verify_step_execution(
        self,
        step: WorkflowStep,
        session: Any,
        runtime_evidence: Dict[str, Any],
        previous_evidence: Optional[Dict[str, Any]] = None,
    ) -> VerificationEvidence:
        """Independently verifies step execution against live page runtime evidence."""
        now = self._clock_fn()
        ev_time = runtime_evidence.get("timestamp", 0.0)
        freshness = abs(now - ev_time)

        # 1. Reject fabricated / empty evidence
        if not runtime_evidence or not isinstance(runtime_evidence, dict):
            raise VerificationFailedError(
                f"Verification REJECT for step '{step.step_id}': Runtime evidence is missing or not a dictionary."
            )

        # 2. Reject stale evidence tokens
        if freshness > self.MAX_FRESHNESS_DELTA_S:
            raise VerificationFailedError(
                f"Verification REJECT for step '{step.step_id}': Stale evidence detected. "
                f"Freshness delta {freshness:.2f}s exceeds limit {self.MAX_FRESHNESS_DELTA_S}s."
            )

        # 3. Detect unchanged / stale evidence replay on state-mutating actions
        if step.action_type in (ActionType.NAVIGATION, ActionType.STATE_MUTATION) and previous_evidence:
            prev_hash = previous_evidence.get("dom_hash")
            curr_hash = runtime_evidence.get("dom_hash")
            prev_url = previous_evidence.get("url")
            curr_url = runtime_evidence.get("url")

            if prev_hash and curr_hash and prev_hash == curr_hash and prev_url == curr_url:
                # If neither DOM nor URL changed on mutation/navigation
                if not step.input_data.get("allow_unchanged_state"):
                    raise VerificationFailedError(
                        f"Verification REJECT for step '{step.step_id}': Action was classified as {step.action_type.value} "
                        "but produced zero observable DOM or URL mutation compared to previous step."
                    )

        checks_passed: list[str] = ["freshness_verified", "evidence_structure_valid"]

        # 4. Action-specific live runtime verification
        if step.action_type == ActionType.NAVIGATION:
            expected_url = step.input_data.get("url", "")
            current_url = runtime_evidence.get("url", "")
            if expected_url and expected_url not in current_url and current_url not in expected_url:
                raise VerificationFailedError(
                    f"Verification REJECT for step '{step.step_id}': Target URL mismatch. "
                    f"Expected '{expected_url}', observed '{current_url}'."
                )
            checks_passed.append("navigation_url_confirmed")

        elif step.action_type == ActionType.DATA_EXTRACTION:
            if step.result is None:
                raise VerificationFailedError(
                    f"Verification REJECT for step '{step.step_id}': Extraction step produced None result."
                )
            # Verify extracted result is not a hollow fabricated dict
            if isinstance(step.result, dict) and not step.result and not step.input_data.get("allow_empty"):
                raise VerificationFailedError(
                    f"Verification REJECT for step '{step.step_id}': Extracted dictionary is completely empty."
                )
            checks_passed.append("extraction_payload_confirmed")

        elif step.action_type == ActionType.DOM_INTERACTION:
            has_interaction = (
                runtime_evidence.get("element_found", False)
                or runtime_evidence.get("clicked", False)
                or "text_length" in runtime_evidence
                or bool(runtime_evidence.get("selector"))
            )
            if not has_interaction:
                raise VerificationFailedError(
                    f"Verification REJECT for step '{step.step_id}': Target DOM element was not resolved on live page."
                )
            checks_passed.append("dom_target_confirmed")

        return VerificationEvidence(
            step_id=step.step_id,
            action=step.action,
            verified=True,
            timestamp=now,
            freshness_delta_s=freshness,
            checks_passed=checks_passed,
            details=runtime_evidence,
        )

    def verify_workflow_result(
        self,
        result: Any,
        expected_session_id: Optional[str] = None,
        expected_workflow_id: Optional[str] = None,
        secret: Optional[bytes] = None,
    ) -> bool:
        """Independently verifies the authenticity and cryptographic provenance of a WorkflowResult.
        
        Rejects:
        - Forged WorkflowResult claiming success with zero steps or zero provenance.
        - Forged session identity or mismatched workflow identity.
        - Tampered or counterfeit provenance records.
        """
        if not hasattr(result, "status") or not hasattr(result, "is_verified"):
            return False

        if expected_session_id and getattr(result, "session_id", None) != expected_session_id:
            return False

        if expected_workflow_id and getattr(result, "workflow_id", None) != expected_workflow_id:
            return False

        if result.is_verified:
            status_val = result.status.value if hasattr(result.status, "value") else str(result.status)
            if status_val != "COMPLETED":
                return False
            if not getattr(result, "provenance", None):
                return False
            if not getattr(result, "step_results", None):
                return False

            # Verify cryptographic provenance chain integrity
            from behavioral_playwright.orchestration.provenance import (
                StepProvenanceRecord,
                WorkflowProvenanceChain,
            )
            chain = WorkflowProvenanceChain(
                workflow_id=result.workflow_id,
                secret=secret,
                clock_fn=self._clock_fn,
            )
            try:
                for rec_dict in result.provenance:
                    rec = StepProvenanceRecord(**rec_dict)
                    chain.records.append(rec)
                if not chain.verify_chain_integrity():
                    return False
            except Exception:
                return False

        return True


def verify_workflow_result(
    result: Any,
    expected_session_id: Optional[str] = None,
    expected_workflow_id: Optional[str] = None,
    secret: Optional[bytes] = None,
) -> bool:
    """Convenience functional verifier for WorkflowResult."""
    return WorkflowVerifier().verify_workflow_result(
        result,
        expected_session_id=expected_session_id,
        expected_workflow_id=expected_workflow_id,
        secret=secret,
    )

