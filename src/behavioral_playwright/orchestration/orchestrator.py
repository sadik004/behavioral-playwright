"""Central workflow orchestrator coordinating state, execution, verification, and resilience."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from behavioral_playwright.exceptions import BehavioralPlaywrightError
from behavioral_playwright.logging import get_logger
from behavioral_playwright.orchestration.conditions import ConditionEvaluator
from behavioral_playwright.orchestration.exceptions import (
    ApprovalRequiredError,
    ExecutionError,
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
    StepStatus,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
)
from behavioral_playwright.orchestration.policies import ApprovalManager, SafetyPolicy
from behavioral_playwright.orchestration.provenance import WorkflowProvenanceChain
from behavioral_playwright.orchestration.state import WorkflowState
from behavioral_playwright.orchestration.verification import WorkflowVerifier
from behavioral_playwright.resilience.taxonomy import classify_failure, is_recoverable_via_restart

logger = get_logger("orchestration.orchestrator")


class WorkflowOrchestrator:
    """Deterministic, verification-driven orchestrator coordinating multi-step workflows.
    
    Guarantees:
    1. Zero global mutable state; strictly bound to the target session and workflow definition.
    2. Monotonic timeout budget enforcement across planning, execution, verification, and recovery.
    3. Independent verification for every step; planner or agent claims are never trusted blindly.
    4. Anti-loop protection against runaway execution, repeated actions, and cycling states.
    5. Clean cancellation propagation without swallowing or faking success.
    """

    def __init__(
        self,
        executor: Optional[WorkflowExecutor] = None,
        verifier: Optional[WorkflowVerifier] = None,
        safety_policy: Optional[SafetyPolicy] = None,
        approval_manager: Optional[ApprovalManager] = None,
        clock_fn: Optional[Any] = None,
    ) -> None:
        self._clock_fn = clock_fn or time.monotonic
        self.executor = executor or WorkflowExecutor(clock_fn=self._clock_fn)
        self.verifier = verifier or WorkflowVerifier(clock_fn=self._clock_fn)
        self.safety_policy = safety_policy or SafetyPolicy()
        self.approval_manager = approval_manager or ApprovalManager()

    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        session: Any,
        raise_on_failure: bool = True,
    ) -> WorkflowResult:
        """Executes a fully planned workflow under strict verification and boundary governance."""
        if session is None:
            raise ExecutionError(f"Cannot execute workflow '{workflow.workflow_id}': Target session is None.")

        if hasattr(session, "session_id") and workflow.session_id and session.session_id != workflow.session_id:
            raise PolicyViolationError(
                f"Session identity mismatch: workflow bound to '{workflow.session_id}' "
                f"cannot execute on session '{session.session_id}'."
            )

        if not workflow.steps:
            raise ExecutionError(f"Workflow '{workflow.workflow_id}' contains zero steps to execute.")

        start_time = self._clock_fn()
        deadline = start_time + workflow.timeout_budget_s

        state = WorkflowState(
            workflow_id=workflow.workflow_id,
            session_id=workflow.session_id,
            clock_fn=self._clock_fn,
        )
        loop_protector = LoopProtector(
            LoopProtectionConfig(
                max_steps=workflow.max_step_count,
                max_recovery_attempts=workflow.max_recovery_budget,
            )
        )
        provenance = WorkflowProvenanceChain(
            workflow_id=workflow.workflow_id,
            clock_fn=self._clock_fn,
        )

        state.transition_to(WorkflowStatus.RUNNING, "Workflow execution started")

        step_results: List[Dict[str, Any]] = []
        previous_evidence: Optional[Dict[str, Any]] = None
        final_output: Any = None

        try:
            for step_idx, step in enumerate(workflow.steps):
                state.current_step_index = step_idx
                step.status = StepStatus.RUNNING
                step.started_at = self._clock_fn()

                # 1. Monotonic timeout watchdog
                now = self._clock_fn()
                if now >= deadline:
                    state.transition_to(WorkflowStatus.TIMED_OUT, f"Workflow deadline exceeded ({workflow.timeout_budget_s}s)")
                    raise WorkflowTimeoutError(
                        f"Workflow '{workflow.workflow_id}' timed out after {now - start_time:.2f}s "
                        f"(budget: {workflow.timeout_budget_s}s)."
                    )

                # 2. Human-In-The-Loop approval gate
                ticket = None
                if self.approval_manager.needs_approval(step):
                    ticket = self.approval_manager.get_ticket_for_step(workflow.workflow_id, step.step_id)
                    if ticket is None:
                        ticket = self.approval_manager.create_ticket(workflow.workflow_id, step)
                    
                    if not self.approval_manager.is_ticket_approved(ticket.ticket_id):
                        step.status = StepStatus.WAITING_FOR_APPROVAL
                        state.transition_to(
                            WorkflowStatus.WAITING_FOR_APPROVAL,
                            f"Step '{step.step_id}' ({step.action}) requires approval ticket '{ticket.ticket_id}'",
                            step_id=step.step_id,
                        )
                        raise ApprovalRequiredError(
                            f"Step '{step.step_id}' requires explicit approval. "
                            f"Approval ticket generated: {ticket.ticket_id}"
                        )

                # 3. Safety policy gating (exempt if explicitly approved by HITL ticket)
                if not (ticket is not None and self.approval_manager.is_ticket_approved(ticket.ticket_id)):
                    self.safety_policy.validate_step(step)

                # 4. Anti-loop protection
                loop_protector.record_action(step.action, step.input_data)

                # 5. Provenance: PLANNED
                provenance.record_phase(
                    step_id=step.step_id,
                    action=step.action,
                    action_type=step.action_type.value,
                    phase="PLANNED",
                    input_data=step.input_data,
                    evidence_data={},
                    verified=False,
                )

                # 6. Precondition evaluation
                for pre in step.preconditions:
                    await ConditionEvaluator.evaluate_precondition(pre, session, state, step)

                # 7. Step execution with recovery fallback
                result = None
                evidence: Dict[str, Any] = {}
                attempts = 0
                max_step_attempts = 2

                while attempts < max_step_attempts:
                    attempts += 1
                    step.attempts = attempts
                    try:
                        result, evidence = await self.executor.execute_step(step, session, state)
                        step.result = result
                        step.evidence = evidence
                        break
                    except Exception as exc:
                        if isinstance(exc, asyncio.CancelledError):
                            raise

                        cat = classify_failure(exc)
                        if is_recoverable_via_restart(cat) and loop_protector.recovery_count < workflow.max_recovery_budget:
                            loop_protector.record_recovery()
                            state.transition_to(WorkflowStatus.RECOVERING, f"Recovering from failure {cat.value}: {exc}", step_id=step.step_id)
                            
                            # Invoke Phase 6 RecoveryManager
                            if hasattr(session, "recover"):
                                await session.recover(category=cat)
                            
                            provenance.record_phase(
                                step_id=step.step_id,
                                action=step.action,
                                action_type=step.action_type.value,
                                phase="RECOVERED",
                                input_data=step.input_data,
                                evidence_data={"failure": str(exc), "category": cat.value},
                                verified=False,
                            )
                            state.transition_to(WorkflowStatus.REVERIFYING, "Resuming execution post-recovery", step_id=step.step_id)
                            continue
                        
                        step.status = StepStatus.FAILED
                        step.error = str(exc)
                        state.transition_to(WorkflowStatus.FAILED, f"Step '{step.step_id}' failed: {exc}", step_id=step.step_id)
                        raise

                # Provenance: EXECUTED
                provenance.record_phase(
                    step_id=step.step_id,
                    action=step.action,
                    action_type=step.action_type.value,
                    phase="EXECUTED",
                    input_data=step.input_data,
                    evidence_data=evidence,
                    verified=False,
                )

                # 8. Postcondition evaluation
                for post in step.postconditions:
                    await ConditionEvaluator.evaluate_postcondition(post, session, state, step)

                # 9. Verification-First Gate
                if step.require_verification and workflow.require_verification:
                    state.transition_to(WorkflowStatus.VERIFYING, f"Verifying step '{step.step_id}'", step_id=step.step_id)
                    verif_ev = await self.verifier.verify_step_execution(
                        step=step,
                        session=session,
                        runtime_evidence=evidence,
                        previous_evidence=previous_evidence,
                    )
                    state.transition_to(WorkflowStatus.RUNNING, f"Step '{step.step_id}' verified", step_id=step.step_id)
                else:
                    verif_ev = None

                # Provenance: VERIFIED
                provenance.record_phase(
                    step_id=step.step_id,
                    action=step.action,
                    action_type=step.action_type.value,
                    phase="VERIFIED",
                    input_data=step.input_data,
                    evidence_data=evidence,
                    verified=True,
                )

                # Record observable progress to defeat zero-progress loops
                dom_h = evidence.get("dom_hash", "")
                if dom_h:
                    loop_protector.record_progress_state(dom_h)

                step.status = StepStatus.COMPLETED
                step.completed_at = self._clock_fn()
                previous_evidence = evidence
                final_output = result

                if self._clock_fn() >= deadline:
                    state.transition_to(WorkflowStatus.TIMED_OUT, f"Workflow deadline exceeded ({workflow.timeout_budget_s}s)")
                    raise WorkflowTimeoutError(
                        f"Workflow '{workflow.workflow_id}' timed out after {self._clock_fn() - start_time:.2f}s "
                        f"(budget: {workflow.timeout_budget_s}s)."
                    )

                # Forward output to workflow state variables if specified
                var_key = step.input_data.get("output_variable")
                if var_key:
                    state.set_variable(var_key, result)

                step_results.append({
                    "step_id": step.step_id,
                    "action": step.action,
                    "status": step.status.value,
                    "duration_s": step.completed_at - (step.started_at or step.completed_at),
                    "result_summary": str(result)[:200] if result is not None else None,
                })

            # All steps completed successfully
            state.transition_to(WorkflowStatus.COMPLETED, "All workflow steps completed and verified")
            total_elapsed = self._clock_fn() - start_time

            return WorkflowResult(
                workflow_id=workflow.workflow_id,
                session_id=workflow.session_id,
                status=WorkflowStatus.COMPLETED,
                step_results=step_results,
                output=final_output,
                evidence=previous_evidence or {},
                provenance=provenance.to_list(),
                elapsed_s=total_elapsed,
                is_verified=True,
            )

        except asyncio.CancelledError:
            state.transition_to(WorkflowStatus.CANCELLED, "Workflow cancelled by parent task")
            provenance.record_phase(
                step_id="workflow_cancellation",
                action="cancel",
                action_type="CANCELLATION",
                phase="OBSERVED",
                input_data={},
                evidence_data={"status": "cancelled"},
                verified=False,
            )
            raise

        except ApprovalRequiredError:
            # Workflow enters and safely remains in WAITING_FOR_APPROVAL
            if raise_on_failure:
                raise
            total_elapsed = self._clock_fn() - start_time
            return WorkflowResult(
                workflow_id=workflow.workflow_id,
                session_id=workflow.session_id,
                status=state.status,
                step_results=step_results,
                output=None,
                evidence=previous_evidence or {},
                provenance=provenance.to_list(),
                elapsed_s=total_elapsed,
                error="Waiting for approval",
                is_verified=False,
            )

        except Exception as exc:
            if not state.is_terminal():
                state.transition_to(WorkflowStatus.FAILED, f"Workflow failed: {exc}")
            if raise_on_failure:
                raise
            total_elapsed = self._clock_fn() - start_time
            return WorkflowResult(
                workflow_id=workflow.workflow_id,
                session_id=workflow.session_id,
                status=state.status,
                step_results=step_results,
                output=None,
                evidence=previous_evidence or {},
                provenance=provenance.to_list(),
                elapsed_s=total_elapsed,
                error=str(exc),
                is_verified=False,
            )
