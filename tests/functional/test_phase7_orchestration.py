"""Phase 7 Functional & Adversarial Verification Suite: Advanced Orchestration & Agentic Workflow Integrity.

Covers all Phase 7 mandates and attack vectors:
- ATTACK-P7-001: Planner fabricates successful execution -> REJECT
- ATTACK-P7-002: Executor returns True without runtime evidence -> REJECT
- ATTACK-P7-003: Stale verification evidence is reused -> REJECT
- ATTACK-P7-004: Agent attempts to bypass resolver / safety -> REJECT
- ATTACK-P7-005: Agent attempts positional fallback (.first() / nth-child) -> REJECT
- ATTACK-P7-006: Infinite repeated action / planner loop -> REJECT (RunawayLoopError)
- ATTACK-P7-007: Recovery loop bounded termination -> REJECT (RunawayLoopError)
- ATTACK-P7-008: Child operation exceeds parent timeout -> REJECT (WorkflowTimeoutError)
- ATTACK-P7-009: Cancellation never converted to success -> CancelledError raised
- ATTACK-P7-010: Non-idempotent action safe retry gating -> REJECT
- ATTACK-P7-011: Cross-session workflow state isolation -> VERIFIED
- ATTACK-P7-012: Forged workflow state / invalid transition -> REJECT (StateTransitionError)
- ATTACK-P7-013: Forged verification / provenance tampering -> REJECT
- ATTACK-P7-014: MCP handler policy & contract preservation -> VERIFIED
- ATTACK-P7-015: Unauthorized side effect triggers approval gate -> VERIFIED
- REAL END-TO-END Chromium Workflow with DOM mutation and verification.
"""

from __future__ import annotations

import asyncio
import time
from urllib.parse import quote
import pytest

from behavioral_playwright.config.settings import AutomationConfig, BrowserConfig
from behavioral_playwright.facade import BP
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
    DeterministicPlanner,
    ExternalAgentPlanner,
)
from behavioral_playwright.orchestration.policies import (
    ApprovalManager,
    SafetyPolicy,
)
from behavioral_playwright.orchestration.provenance import (
    StepProvenanceRecord,
    WorkflowProvenanceChain,
)
from behavioral_playwright.orchestration.state import WorkflowState
from behavioral_playwright.orchestration.verification import WorkflowVerifier
from behavioral_playwright.page.session import BrowserSession, PageSession


def make_data_url(html: str) -> str:
    return f"data:text/html;charset=utf-8,{quote(html)}"


HTML_FIXTURE = """<!DOCTYPE html>
<html>
<head><title>Phase 7 Orchestration Testbed</title></head>
<body>
    <h1 id="heading">Autonomous Intelligence Hub</h1>
    <input id="user-input" type="text" placeholder="Enter command" />
    <button id="submit-btn" onclick="document.getElementById('status').innerText = 'Processed: ' + document.getElementById('user-input').value; document.getElementById('counter').innerText = '1';">Execute</button>
    <div id="status">Standby</div>
    <div id="counter">0</div>
</body>
</html>
"""


# ============================================================================
# 1. Adversarial Attack Tests: ATTACK-P7-001 through ATTACK-P7-015
# ============================================================================

@pytest.mark.asyncio
async def test_attack_p7_001_planner_fabricates_success():
    """ATTACK-P7-001: Planner attempts to return fake execution evidence without runtime execution."""
    verifier = WorkflowVerifier()
    step = WorkflowStep.create(
        action="extract",
        action_type=ActionType.DATA_EXTRACTION,
        input_data={"selector": "#heading"},
    )
    # Planner claims success by passing an empty or fake result
    step.result = None
    fake_evidence = {"timestamp": time.monotonic(), "dom_hash": "dummy_hash"}

    with pytest.raises(VerificationFailedError) as exc_info:
        await verifier.verify_step_execution(
            step=step,
            session=None,
            runtime_evidence=fake_evidence,
        )
    assert "Extraction step produced None result" in str(exc_info.value)


@pytest.mark.asyncio
async def test_attack_p7_002_executor_returns_without_evidence():
    """ATTACK-P7-002: Executor returns without runtime evidence dict; verifier must reject."""
    verifier = WorkflowVerifier()
    step = WorkflowStep.create(
        action="resolve",
        action_type=ActionType.DOM_INTERACTION,
        input_data={"selector": "#heading"},
    )
    with pytest.raises(VerificationFailedError) as exc_info:
        await verifier.verify_step_execution(
            step=step,
            session=None,
            runtime_evidence={},  # Empty evidence
        )
    assert "missing or not a dictionary" in str(exc_info.value)


@pytest.mark.asyncio
async def test_attack_p7_003_stale_verification_evidence_rejected():
    """ATTACK-P7-003: Stale evidence (>60s) or replayed evidence on state mutation is rejected."""
    verifier = WorkflowVerifier()
    step = WorkflowStep.create(
        action="click",
        action_type=ActionType.STATE_MUTATION,
        input_data={"selector": "#btn"},
    )
    # Stale timestamp
    stale_evidence = {
        "timestamp": time.monotonic() - 120.0,
        "dom_hash": "hash_a",
        "url": "http://example.com",
    }
    with pytest.raises(VerificationFailedError) as exc_info:
        await verifier.verify_step_execution(
            step=step,
            session=None,
            runtime_evidence=stale_evidence,
        )
    assert "Stale evidence detected" in str(exc_info.value)

    # Replayed unchanged state on mutation action
    now = time.monotonic()
    prev_ev = {"timestamp": now - 1.0, "dom_hash": "hash_same", "url": "http://example.com"}
    curr_ev = {"timestamp": now, "dom_hash": "hash_same", "url": "http://example.com"}
    with pytest.raises(VerificationFailedError) as exc_info2:
        await verifier.verify_step_execution(
            step=step,
            session=None,
            runtime_evidence=curr_ev,
            previous_evidence=prev_ev,
        )
    assert "zero observable DOM or URL mutation" in str(exc_info2.value)


@pytest.mark.asyncio
async def test_attack_p7_004_agent_attempts_to_bypass_safety():
    """ATTACK-P7-004: Agent attempts to run explicitly forbidden or dangerous action."""
    policy = SafetyPolicy(disallowed_actions={"exec_shell", "format_disk"})
    step = WorkflowStep.create(
        action="exec_shell",
        action_type=ActionType.EXTERNAL_SIDE_EFFECT,
        input_data={"cmd": "whoami"},
    )
    with pytest.raises(PolicyViolationError) as exc_info:
        policy.validate_step(step)
    assert "explicitly forbidden" in str(exc_info.value)


@pytest.mark.asyncio
async def test_attack_p7_005_agent_attempts_positional_fallback():
    """ATTACK-P7-005: Agent attempts .first() / nth-child positional fallback where uniqueness required."""
    policy = SafetyPolicy(require_unique_resolution=True)
    step = WorkflowStep.create(
        action="click",
        action_type=ActionType.DOM_INTERACTION,
        input_data={"selector": "div.card:nth-child(1)"},
    )
    with pytest.raises(PolicyViolationError) as exc_info:
        policy.validate_step(step)
    assert "Fragile positional selector" in str(exc_info.value)


@pytest.mark.asyncio
async def test_attack_p7_006_infinite_action_loop():
    """ATTACK-P7-006: Hard termination when an agent attempts repeated identical actions or loops."""
    protector = LoopProtector(LoopProtectionConfig(max_repeated_actions=3, max_steps=10))

    protector.record_action("click", {"selector": "#btn"})
    protector.record_action("click", {"selector": "#btn"})

    with pytest.raises(RunawayLoopError) as exc_info:
        protector.record_action("click", {"selector": "#btn"})
    assert "Runaway loop detected" in str(exc_info.value)


@pytest.mark.asyncio
async def test_attack_p7_007_recovery_loop_bounded_termination():
    """ATTACK-P7-007: Continuous recovery cycles trigger bounded termination."""
    protector = LoopProtector(LoopProtectionConfig(max_recovery_attempts=2))

    protector.record_recovery()
    protector.record_recovery()

    with pytest.raises(RunawayLoopError) as exc_info:
        protector.record_recovery()
    assert "Recovery loop detected" in str(exc_info.value)


@pytest.mark.asyncio
async def test_attack_p7_008_child_operation_exceeds_parent_timeout():
    """ATTACK-P7-008: Workflow execution strictly respects parent timeout budget."""
    mock_clock = 1000.0

    def clock_fn():
        return mock_clock

    orchestrator = WorkflowOrchestrator(clock_fn=clock_fn)
    wf = WorkflowDefinition.create(
        session_id="timeout_sess",
        timeout_budget_s=5.0,
        steps=[
            WorkflowStep.create(
                action="navigate",
                action_type=ActionType.NAVIGATION,
                input_data={"url": "http://example.com"},
            )
        ],
    )

    class FastMockSession:
        async def goto(self, url):
            nonlocal mock_clock
            mock_clock += 10.0  # Advance clock during step execution past the 5.0s budget

    with pytest.raises(WorkflowTimeoutError) as exc_info:
        await orchestrator.execute_workflow(wf, session=FastMockSession())
    assert "timed out after" in str(exc_info.value)


@pytest.mark.asyncio
async def test_attack_p7_009_cancellation_never_converted_to_success():
    """ATTACK-P7-009: CancelledError is immediately propagated and never reported as success."""
    orchestrator = WorkflowOrchestrator()
    wf = WorkflowDefinition.create(
        session_id="cancel_sess",
        steps=[
            WorkflowStep.create(
                action="navigate",
                action_type=ActionType.NAVIGATION,
                input_data={"url": "http://example.com"},
            )
        ],
    )

    class CancellingSession:
        async def goto(self, url):
            raise asyncio.CancelledError("Task aborted by user")

    with pytest.raises(asyncio.CancelledError):
        await orchestrator.execute_workflow(wf, session=CancellingSession())


@pytest.mark.asyncio
async def test_attack_p7_010_non_idempotent_action_safe_retry_gating():
    """ATTACK-P7-010: Non-idempotent actions must fail honestly without blind re-execution once initiated."""
    from behavioral_playwright.resilience.idempotency import IdempotencyPolicy, OperationType

    # Non-idempotent write that started execution is unsafe to retry
    safe = IdempotencyPolicy.is_safe_to_retry(
        op_type=OperationType.NON_IDEMPOTENT_WRITE,
        attempt=2,
        started_execution=True,
    )
    assert safe is False


@pytest.mark.asyncio
async def test_attack_p7_011_cross_session_state_isolation():
    """ATTACK-P7-011: Independent workflow states share zero mutable memory across sessions."""
    state_a = WorkflowState(workflow_id="wf_1", session_id="sess_1")
    state_b = WorkflowState(workflow_id="wf_2", session_id="sess_2")

    state_a.set_variable("auth_token", "SECRET_TOKEN_A")
    assert state_b.get_variable("auth_token") is None

    state_a.transition_to(WorkflowStatus.RUNNING, "Started A")
    assert state_b.status == WorkflowStatus.PENDING


@pytest.mark.asyncio
async def test_attack_p7_012_invalid_state_transition_rejected():
    """ATTACK-P7-012: Forged or illegal workflow state transitions raise StateTransitionError."""
    state = WorkflowState(workflow_id="wf_audit", session_id="sess_audit")
    assert state.status == WorkflowStatus.PENDING

    # PENDING cannot jump directly to COMPLETED or VERIFYING
    with pytest.raises(StateTransitionError) as exc_info:
        state.transition_to(WorkflowStatus.COMPLETED, "Premature completion claim")
    assert "Invalid workflow state transition" in str(exc_info.value)

    # Valid transition to RUNNING
    state.transition_to(WorkflowStatus.RUNNING, "Valid start")
    state.transition_to(WorkflowStatus.COMPLETED, "All steps verified")

    # COMPLETED is terminal: cannot transition back to RUNNING
    with pytest.raises(StateTransitionError):
        state.transition_to(WorkflowStatus.RUNNING, "Resurrect completed workflow")


@pytest.mark.asyncio
async def test_attack_p7_013_provenance_tampering_detected():
    """ATTACK-P7-013: Tampering with a sealed provenance record is detected by cryptographic signature check."""
    chain = WorkflowProvenanceChain(workflow_id="wf_prov_test")
    rec = chain.record_phase(
        step_id="step_1",
        action="navigate",
        action_type="NAVIGATION",
        phase="VERIFIED",
        input_data={"url": "http://example.com"},
        evidence_data={"status": 200},
        verified=True,
    )
    assert chain.verify_chain_integrity() is True

    # Mutate the in-memory record to forge an action
    tampered_rec = StepProvenanceRecord(
        workflow_id=rec.workflow_id,
        step_id=rec.step_id,
        action="malicious_action",  # Tampered field
        action_type=rec.action_type,
        phase=rec.phase,
        timestamp=rec.timestamp,
        input_hash=rec.input_hash,
        evidence_hash=rec.evidence_hash,
        verified=rec.verified,
        signature=rec.signature,  # Signature now mismatches
    )
    chain.records[0] = tampered_rec
    assert chain.verify_chain_integrity() is False


@pytest.mark.asyncio
async def test_attack_p7_014_mcp_workflow_tool_integration():
    """ATTACK-P7-014: MCP execute_workflow and workflow tools maintain schema contracts and validation."""
    from behavioral_playwright.mcp.tools import McpToolDispatcher

    dispatcher = McpToolDispatcher()
    # Missing required argument on workflow_navigate
    res = await dispatcher.execute_tool("workflow_navigate", {})
    assert "error" in res
    assert "Missing required argument 'url'" in res["error"]

    # inspect_state requires workflow_id
    res_inspect = await dispatcher.execute_tool("inspect_state", {})
    assert "error" in res_inspect
    assert "Missing required argument 'workflow_id'" in res_inspect["error"]


@pytest.mark.asyncio
async def test_attack_p7_015_unauthorized_side_effect_approval_gate():
    """ATTACK-P7-015: Unauthorized external side effects raise ApprovalRequiredError and pause workflow."""
    manager = ApprovalManager(require_approval_for={ActionType.EXTERNAL_SIDE_EFFECT})
    orchestrator = WorkflowOrchestrator(approval_manager=manager)

    step = WorkflowStep.create(
        action="execute_payment",
        action_type=ActionType.EXTERNAL_SIDE_EFFECT,
        input_data={"amount": "100.00"},
    )
    wf = WorkflowDefinition.create(
        session_id="approval_sess",
        steps=[step],
        name="payment_flow",
    )

    class MockSession:
        pass

    # First attempt: no approval ticket exists -> halts with ApprovalRequiredError
    with pytest.raises(ApprovalRequiredError) as exc_info:
        await orchestrator.execute_workflow(wf, session=MockSession())
    assert "Approval ticket generated" in str(exc_info.value)

    # Find generated ticket and grant approval
    ticket = manager.get_ticket_for_step(wf.workflow_id, step.step_id)
    assert ticket is not None
    assert ticket.status == "PENDING"
    manager.approve(ticket.ticket_id, approver="SecurityAdmin", reason="Verified by human operator")
    assert manager.is_ticket_approved(ticket.ticket_id) is True


# ============================================================================
# 2. Real Browser End-to-End Orchestrated Workflow
# ============================================================================

@pytest.mark.asyncio
async def test_real_browser_e2e_agentic_workflow():
    """Section 22 Proof: Live Chromium executing planned multi-step workflow with real DOM mutation & verification."""
    config = AutomationConfig(browser=BrowserConfig(headless=True))
    data_url = make_data_url(HTML_FIXTURE)

    async with BrowserSession(config=config) as session:
        page_session = await session.new_page()

        # Define 4-step workflow:
        # Step 1: Navigate to fixture URL
        # Step 2: Resolve input and type text
        # Step 3: Resolve button and click (mutates DOM status and counter)
        # Step 4: Extract text content and verify result
        step1 = WorkflowStep.create(
            step_id="step_nav",
            action="navigate",
            action_type=ActionType.NAVIGATION,
            input_data={"url": data_url},
            preconditions=[Condition(name="page_alive", condition_type="page_open")],
        )
        step2 = WorkflowStep.create(
            step_id="step_type",
            action="type",
            action_type=ActionType.DOM_INTERACTION,
            input_data={"selector": "#user-input", "text": "AGENTIC_PAYLOAD_42"},
            postconditions=[Condition(name="input_present", condition_type="element_exists", params={"selector": "#user-input"})],
        )
        step3 = WorkflowStep.create(
            step_id="step_click",
            action="click",
            action_type=ActionType.STATE_MUTATION,
            input_data={"selector": "#submit-btn"},
            postconditions=[Condition(name="btn_present", condition_type="element_exists", params={"selector": "#submit-btn"})],
        )
        step4 = WorkflowStep.create(
            step_id="step_extract",
            action="extract",
            action_type=ActionType.DATA_EXTRACTION,
            input_data={"selector": "#status", "target": "text"},
        )

        wf = WorkflowDefinition.create(
            session_id=page_session.session_id,
            steps=[step1, step2, step3, step4],
            name="live_agentic_e2e",
            timeout_budget_s=30.0,
            require_verification=True,
        )

        orchestrator = WorkflowOrchestrator()
        result: WorkflowResult = await orchestrator.execute_workflow(wf, session=page_session)

        # Authoritative assertions proving live physical execution
        assert result.status == WorkflowStatus.COMPLETED
        assert result.is_verified is True
        assert len(result.step_results) == 4
        assert len(result.provenance) > 0

        # Verify live DOM mutation occurred on page
        final_status_text = await page_session.raw_page.inner_text("#status")
        final_counter_text = await page_session.raw_page.inner_text("#counter")

        assert "Processed: AGENTIC_PAYLOAD_42" in final_status_text
        assert final_counter_text == "1"

        # Verify facade forwarder
        bp = BP(config=config)
        # Test deterministic planner integration
        planner = DeterministicPlanner()
        plan_steps = await planner.plan(goal="click", context={"url": data_url, "selector": "#submit-btn"})
        assert len(plan_steps) >= 2
        assert plan_steps[-1].action == "click"
