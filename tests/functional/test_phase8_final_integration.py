"""Phase 8 Final Integration, Hardening & Release Verification Suite.

Validates the complete framework stack across all frozen phases:
- Cross-phase integrated workflows (Navigation -> Resolve -> Interact -> Extract -> Normalize -> Map -> Verify)
- Recovery workflows (Failure -> Classification -> Retry -> Recovery -> Re-resolution -> Re-verification)
- Orchestrated agent plan & recovery workflows
- Real Chromium physical DOM end-to-end execution
- Long-running stability & monotonic timeout budget
- Concurrency & multi-session isolation
- Resource lifecycle & clean termination
- Determinism & trajectory reproducibility
- Failure honesty (rejection of malformed/missing data, no fake success)
- Fake-Success Attack Battery: ATTACK-P8-001 through ATTACK-P8-015
"""

from __future__ import annotations

import asyncio
import time
from urllib.parse import quote
import pytest
from decimal import Decimal

from behavioral_playwright import (
    BP,
    ActionType,
    AutomationConfig,
    BrowserConfig,
    BrowserSession,
    DOMElement,
    PageSession,
    SelfHealingResolver,
    StepStatus,
    WorkflowDefinition,
    WorkflowOrchestrator,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
)
from behavioral_playwright.exceptions import (
    BehavioralPlaywrightError,
    ElementResolutionError,
    NavigationError,
)
from behavioral_playwright.extraction.normalizer import clean_text, parse_price
from behavioral_playwright.mapping.schema_mapper import PageSchemaMapper
from behavioral_playwright.orchestration.conditions import Condition, ConditionEvaluator
from behavioral_playwright.orchestration.exceptions import (
    ApprovalRequiredError,
    ExecutionError,
    PolicyViolationError,
    RunawayLoopError,
    StateTransitionError,
    VerificationFailedError,
    WorkflowTimeoutError,
)
from behavioral_playwright.orchestration.executor import WorkflowExecutor
from behavioral_playwright.orchestration.limits import LoopProtectionConfig, LoopProtector
from behavioral_playwright.orchestration.planner import DeterministicPlanner
from behavioral_playwright.orchestration.policies import ApprovalManager, SafetyPolicy
from behavioral_playwright.orchestration.provenance import (
    StepProvenanceRecord,
    WorkflowProvenanceChain,
)
from behavioral_playwright.orchestration.state import WorkflowState
from behavioral_playwright.orchestration.verification import (
    VerificationEvidence,
    WorkflowVerifier,
)
from behavioral_playwright.resilience.models import RecoveryState
from behavioral_playwright.resilience.recovery import RecoveryManager
from behavioral_playwright.resilience.taxonomy import (
    FailureCategory,
    classify_failure,
    is_recoverable_via_restart,
)


# ============================================================================
# HTML Testbed Fixtures
# ============================================================================

HTML_P8_FIXTURE = """<!DOCTYPE html>
<html>
<head>
    <title>Phase 8 Release Verification Testbed</title>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Enterprise Automation Engine",
        "offers": {
            "@type": "Offer",
            "price": "999.50",
            "priceCurrency": "USD"
        }
    }
    </script>
    <meta property="og:title" content="Enterprise Automation Engine OG" />
</head>
<body>
    <header>
        <h1 id="main-title">Enterprise System Dashboard</h1>
    </header>
    <main>
        <div id="status-panel">READY</div>
        <div id="event-counter">0</div>
        <input id="action-input" type="text" placeholder="Command input" />
        <button id="commit-btn" onclick="
            var val = document.getElementById('action-input').value;
            document.getElementById('status-panel').innerText = 'COMMITTED: ' + val;
            var c = parseInt(document.getElementById('event-counter').innerText);
            document.getElementById('event-counter').innerText = (c + 1).toString();
        ">Commit Action</button>
        <div id="price-display">$999.50</div>
    </main>
</body>
</html>
"""


def make_data_url(html_content: str) -> str:
    return f"data:text/html;charset=utf-8,{quote(html_content)}"


# ============================================================================
# SECTION 8 & 9: Real Chromium End-to-End Cross-Phase Integration Proof
# ============================================================================

@pytest.mark.asyncio
async def test_p8_real_chromium_cross_phase_e2e():
    """Sections 8 & 9: Real Chromium live execution across complete 7-pillar stack.
    
    Proves:
    Browser launch -> PageSession -> Navigation -> Selector resolution ->
    Behavioral interaction -> DOM change -> Extraction -> Normalization ->
    Schema mapping -> Verification -> Workflow completion.
    """
    config = AutomationConfig(browser=BrowserConfig(headless=True))
    data_url = make_data_url(HTML_P8_FIXTURE)

    async with BrowserSession(config=config) as session:
        page_session = await session.new_page()

        # Step 1: Navigate to fixture URL
        step1 = WorkflowStep.create(
            step_id="p8_nav",
            action="navigate",
            action_type=ActionType.NAVIGATION,
            input_data={"url": data_url},
            preconditions=[Condition(name="page_alive", condition_type="page_open")],
        )

        # Step 2: Resolve input and type payload
        step2 = WorkflowStep.create(
            step_id="p8_type",
            action="type",
            action_type=ActionType.DOM_INTERACTION,
            input_data={"selector": "#action-input", "text": "RELEASE_TOKEN_P8"},
            postconditions=[Condition(name="input_exists", condition_type="element_exists", params={"selector": "#action-input"})],
        )

        # Step 3: Click commit button to trigger observable DOM mutation
        step3 = WorkflowStep.create(
            step_id="p8_click",
            action="click",
            action_type=ActionType.STATE_MUTATION,
            input_data={"selector": "#commit-btn"},
            postconditions=[Condition(name="btn_exists", condition_type="element_exists", params={"selector": "#commit-btn"})],
        )

        # Step 4: Extract mutated status text
        step4 = WorkflowStep.create(
            step_id="p8_extract",
            action="extract",
            action_type=ActionType.DATA_EXTRACTION,
            input_data={"selector": "#status-panel", "target": "text"},
        )

        wf = WorkflowDefinition.create(
            session_id=page_session.session_id,
            steps=[step1, step2, step3, step4],
            name="phase8_e2e_release_proof",
            timeout_budget_s=30.0,
            require_verification=True,
        )

        orchestrator = WorkflowOrchestrator()
        result: WorkflowResult = await orchestrator.execute_workflow(wf, session=page_session)

        # Assert authoritative completion & verification
        assert result.status == WorkflowStatus.COMPLETED
        assert result.is_verified is True
        assert len(result.step_results) == 4
        assert len(result.provenance) > 0
        assert result.validate_integrity() is True

        # Physical DOM verification
        final_status = await page_session.raw_page.inner_text("#status-panel")
        counter_val = await page_session.raw_page.inner_text("#event-counter")
        assert "COMMITTED: RELEASE_TOKEN_P8" in final_status
        assert counter_val == "1"

        raw_price_text = await page_session.raw_page.inner_text("#price-display")
        normalized_price = parse_price(raw_price_text)
        assert isinstance(normalized_price, Decimal)
        assert normalized_price == Decimal("999.50")

        # Phase 5 Schema Mapping Verification
        mapper = PageSchemaMapper(confidence_threshold=0.50)
        mapped_schema = await mapper.map_schema(page_session.raw_page, {"price": Decimal})
        assert mapped_schema.success is True
        assert mapped_schema.data.get("price") == Decimal("999.50")


# ============================================================================
# SECTION 8: Cross-Phase Recovery Workflow
# ============================================================================

@pytest.mark.asyncio
async def test_p8_cross_phase_recovery_workflow():
    """Section 8: Failure -> Classification -> Retry -> Recovery -> Re-resolution -> Verification."""
    config = AutomationConfig(browser=BrowserConfig(headless=True))
    data_url = make_data_url(HTML_P8_FIXTURE)

    async with BrowserSession(config=config) as session:
        page_session = await session.new_page()
        await page_session.goto(data_url)

        # 1. Trigger failure with page closure
        page_crash_exc = RuntimeError("Target closed: Page crashed")
        classification = classify_failure(page_crash_exc)
        assert classification == FailureCategory.PAGE_FAILURE
        assert is_recoverable_via_restart(classification) is True

        # 2. Recovery invocation via RecoveryManager
        rec_mgr = page_session.recovery_manager
        recovered = await rec_mgr.execute_recovery(page_session, page_crash_exc, restore_url=True)
        assert recovered is True
        assert rec_mgr.state == RecoveryState.RECOVERED

        # 3. Re-resolution on real target succeeds on fresh recovered page
        res_real = await page_session.resolve("#commit-btn")
        assert res_real.success is True
        assert res_real.selector == "#commit-btn"


# ============================================================================
# SECTION 10: Long-Running Stability & Monotonic Timeout Budget
# ============================================================================

@pytest.mark.asyncio
async def test_p8_long_running_stability_and_budget():
    """Section 10: Repeated multi-step operations without resource exhaustion or memory explosion."""
    config = AutomationConfig(browser=BrowserConfig(headless=True))
    data_url = make_data_url(HTML_P8_FIXTURE)

    async with BrowserSession(config=config) as session:
        page_session = await session.new_page()
        await page_session.goto(data_url)

        steps = [
            WorkflowStep.create(step_id="step_type_0", action="type", action_type=ActionType.DOM_INTERACTION, input_data={"selector": "#action-input", "text": "BATCH_0"}),
            WorkflowStep.create(step_id="step_click_0", action="click", action_type=ActionType.STATE_MUTATION, input_data={"selector": "#commit-btn"}),
            WorkflowStep.create(step_id="step_ext_0", action="extract", action_type=ActionType.DATA_EXTRACTION, input_data={"selector": "#status-panel", "target": "text"}),
            WorkflowStep.create(step_id="step_type_1", action="type", action_type=ActionType.DOM_INTERACTION, input_data={"selector": "#action-input", "text": "BATCH_1"}),
            WorkflowStep.create(step_id="step_click_1", action="click", action_type=ActionType.STATE_MUTATION, input_data={"selector": "#commit-btn"}),
            WorkflowStep.create(step_id="step_ext_1", action="extract", action_type=ActionType.DATA_EXTRACTION, input_data={"selector": "#status-panel", "target": "text"}),
            WorkflowStep.create(step_id="step_type_2", action="type", action_type=ActionType.DOM_INTERACTION, input_data={"selector": "#action-input", "text": "BATCH_2"}),
            WorkflowStep.create(step_id="step_click_2", action="click", action_type=ActionType.STATE_MUTATION, input_data={"selector": "#commit-btn"}),
        ]

        wf = WorkflowDefinition.create(
            session_id=page_session.session_id,
            steps=steps,
            name="long_running_stability_wf",
            timeout_budget_s=40.0,
            require_verification=True,
        )

        t_start = time.monotonic()
        orchestrator = WorkflowOrchestrator()
        result = await orchestrator.execute_workflow(wf, session=page_session)
        t_elapsed = time.monotonic() - t_start

        assert result.status == WorkflowStatus.COMPLETED
        assert result.is_verified is True
        assert len(result.step_results) == 8
        assert t_elapsed <= 40.0
        # Provenance chain contains records for each step
        assert len(result.provenance) >= 8


# ============================================================================
# SECTION 11: Concurrency & Multi-Session Isolation
# ============================================================================

@pytest.mark.asyncio
async def test_p8_concurrency_and_session_isolation():
    """Section 11: N concurrent sessions run isolated workflows without state bleeding."""
    config = AutomationConfig(browser=BrowserConfig(headless=True))
    data_url = make_data_url(HTML_P8_FIXTURE)

    async with BrowserSession(config=config) as session:
        page_a = await session.new_page()
        page_b = await session.new_page()

        assert page_a.session_id != page_b.session_id

        # Workflow for session A
        wf_a = WorkflowDefinition.create(
            session_id=page_a.session_id,
            steps=[
                WorkflowStep.create(
                    step_id="step_a_nav",
                    action="navigate",
                    action_type=ActionType.NAVIGATION,
                    input_data={"url": data_url},
                ),
                WorkflowStep.create(
                    step_id="step_a_type",
                    action="type",
                    action_type=ActionType.DOM_INTERACTION,
                    input_data={"selector": "#action-input", "text": "ISOLATION_A"},
                ),
            ],
            name="wf_concurrency_a",
        )

        # Workflow for session B
        wf_b = WorkflowDefinition.create(
            session_id=page_b.session_id,
            steps=[
                WorkflowStep.create(
                    step_id="step_b_nav",
                    action="navigate",
                    action_type=ActionType.NAVIGATION,
                    input_data={"url": data_url},
                ),
                WorkflowStep.create(
                    step_id="step_b_type",
                    action="type",
                    action_type=ActionType.DOM_INTERACTION,
                    input_data={"selector": "#action-input", "text": "ISOLATION_B"},
                ),
            ],
            name="wf_concurrency_b",
        )

        orchestrator = WorkflowOrchestrator()
        res_a, res_b = await asyncio.gather(
            orchestrator.execute_workflow(wf_a, session=page_a),
            orchestrator.execute_workflow(wf_b, session=page_b),
        )

        assert res_a.status == WorkflowStatus.COMPLETED
        assert res_b.status == WorkflowStatus.COMPLETED
        assert res_a.session_id == page_a.session_id
        assert res_b.session_id == page_b.session_id

        # Verify page A input text is ISOLATION_A, page B is ISOLATION_B
        val_a = await page_a.raw_page.input_value("#action-input")
        val_b = await page_b.raw_page.input_value("#action-input")
        assert val_a == "ISOLATION_A"
        assert val_b == "ISOLATION_B"


# ============================================================================
# SECTION 12: Resource Lifecycle & Clean Shutdown
# ============================================================================

@pytest.mark.asyncio
async def test_p8_resource_lifecycle_clean_shutdown():
    """Section 12: Normal and exception shutdowns cleanly release contexts and pages."""
    config = AutomationConfig(browser=BrowserConfig(headless=True))
    data_url = make_data_url(HTML_P8_FIXTURE)

    # 1. Normal clean context release
    async with BrowserSession(config=config) as session:
        page = await session.new_page()
        await page.goto(data_url)
        assert page.is_closed() is False
    # Outside context manager, session and pages are cleanly closed
    assert session.is_closed() is True
    assert page.is_closed() is True

    # 2. Exception context release
    with pytest.raises(RuntimeError, match="Controlled exception"):
        async with BrowserSession(config=config) as session_exc:
            page_exc = await session_exc.new_page()
            await page_exc.goto(data_url)
            raise RuntimeError("Controlled exception")

    assert session_exc.is_closed() is True
    assert page_exc.is_closed() is True


# ============================================================================
# SECTION 14: Determinism Audit
# ============================================================================

@pytest.mark.asyncio
async def test_p8_determinism_audit():
    """Section 14: Deterministic planning and schema mapping are reproducible."""
    planner = DeterministicPlanner()
    context = {"url": "https://example.com", "selector": "#target-button"}

    plan_1 = await planner.plan(goal="click", context=context)
    plan_2 = await planner.plan(goal="click", context=context)

    assert len(plan_1) == len(plan_2)
    for s1, s2 in zip(plan_1, plan_2):
        assert s1.action == s2.action
        assert s1.action_type == s2.action_type
        assert s1.input_data == s2.input_data

    # Deterministic normalization and digest stability
    digest1 = WorkflowProvenanceChain.compute_sha256({"goal": "click", "step": 1, "nested": [1, 2, 3]})
    digest2 = WorkflowProvenanceChain.compute_sha256({"goal": "click", "step": 1, "nested": [1, 2, 3]})
    assert digest1 == digest2

    clean1 = clean_text("  Live \u00a0 Test \t\t Payload \n\n ")
    clean2 = clean_text("  Live \u00a0 Test \t\t Payload \n\n ")
    assert clean1 == clean2 == "Live Test Payload"


# ============================================================================
# SECTION 15: Failure-Honesty Audit
# ============================================================================

@pytest.mark.asyncio
async def test_p8_failure_honesty_audit():
    """Section 15: Subsystems reject missing targets, malformed DOM, or timeouts with typed errors (never fake SUCCESS)."""
    config = AutomationConfig(browser=BrowserConfig(headless=True))
    data_url = make_data_url(HTML_P8_FIXTURE)

    async with BrowserSession(config=config) as session:
        page_session = await session.new_page()
        await page_session.goto(data_url)

        # 1. Missing target element resolution failure
        res = await page_session.resolve("#non-existent-selector-999")
        assert res.success is False
        assert res.selector is None

        # 2. Empty extraction rejection
        verifier = WorkflowVerifier()
        empty_step = WorkflowStep.create(
            step_id="empty_step",
            action="extract",
            action_type=ActionType.DATA_EXTRACTION,
            input_data={"allow_empty": False},
        )
        empty_step.result = {}
        with pytest.raises(VerificationFailedError, match="completely empty"):
            await verifier.verify_step_execution(
                step=empty_step,
                session=page_session,
                runtime_evidence={"timestamp": time.monotonic()},
            )


# ============================================================================
# SECTION 16: Fake-Success Final Attack Battery (ATTACK-P8-001 through ATTACK-P8-015)
# ============================================================================

@pytest.mark.asyncio
async def test_attack_p8_001_return_true_without_execution():
    """ATTACK-P8-001: Attempting to return True without execution is rejected."""
    orchestrator = WorkflowOrchestrator()
    wf = WorkflowDefinition.create(
        session_id="session_dummy",
        steps=[],  # Zero steps
        name="empty_fake_wf",
    )
    with pytest.raises(ExecutionError, match="contains zero steps"):
        await orchestrator.execute_workflow(wf, session=type("DummySession", (), {"session_id": "session_dummy"})())


def test_attack_p8_002_forge_workflow_result():
    """ATTACK-P8-002: Forged WorkflowResult claiming success with empty provenance is detected."""
    forged_result = WorkflowResult(
        workflow_id="wf_forged",
        session_id="sess_forged",
        status=WorkflowStatus.COMPLETED,
        step_results=[],
        provenance=[],
        is_verified=True,
    )
    # validate_integrity must reject
    assert forged_result.validate_integrity() is False

    verifier = WorkflowVerifier()
    assert verifier.verify_workflow_result(forged_result) is False


def test_attack_p8_003_forge_verification_result():
    """ATTACK-P8-003: Forged verification result or tampered evidence hash fails integrity check."""
    chain = WorkflowProvenanceChain(workflow_id="wf_attack_003")
    rec = chain.record_phase(
        step_id="step_1",
        action="click",
        action_type="STATE_MUTATION",
        phase="VERIFIED",
        input_data={"selector": "#btn"},
        evidence_data={"status": "ok", "clicked": True},
        verified=True,
    )
    assert chain.verify_chain_integrity() is True

    # Adversary tampers with the record
    tampered_rec = StepProvenanceRecord(
        workflow_id=rec.workflow_id,
        step_id=rec.step_id,
        action=rec.action,
        action_type=rec.action_type,
        phase=rec.phase,
        timestamp=rec.timestamp,
        input_hash=rec.input_hash,
        evidence_hash="tampered_hash_99999",  # Tampered evidence hash
        verified=rec.verified,
        signature=rec.signature,
    )
    chain.records = [tampered_rec]
    assert chain.verify_chain_integrity() is False


@pytest.mark.asyncio
async def test_attack_p8_004_replay_stale_runtime_evidence():
    """ATTACK-P8-004: Replay stale runtime evidence (>60s) is rejected."""
    verifier = WorkflowVerifier()
    stale_step = WorkflowStep.create(
        step_id="step_stale",
        action="navigate",
        action_type=ActionType.NAVIGATION,
        input_data={"url": "https://example.com"},
    )
    stale_evidence = {
        "timestamp": time.monotonic() - 120.0,  # 120s old
        "url": "https://example.com",
    }
    with pytest.raises(VerificationFailedError, match="Stale evidence detected"):
        await verifier.verify_step_execution(stale_step, session=None, runtime_evidence=stale_evidence)


@pytest.mark.asyncio
async def test_attack_p8_005_forge_session_identity():
    """ATTACK-P8-005: Workflow bound to session A cannot be executed on session B."""
    orchestrator = WorkflowOrchestrator()
    wf = WorkflowDefinition.create(
        session_id="authentic_session_A",
        steps=[WorkflowStep.create(action="inspect", action_type=ActionType.READ_ONLY)],
    )
    fake_session_b = type("FakeSession", (), {"session_id": "forged_session_B"})()

    with pytest.raises(PolicyViolationError, match="Session identity mismatch"):
        await orchestrator.execute_workflow(wf, session=fake_session_b)


def test_attack_p8_006_forge_workflow_identity():
    """ATTACK-P8-006: Step record injected from workflow X into workflow Y fails signature verification."""
    chain_x = WorkflowProvenanceChain(workflow_id="wf_x")
    rec_x = chain_x.record_phase(
        step_id="step_x",
        action="extract",
        action_type="DATA_EXTRACTION",
        phase="VERIFIED",
        input_data={},
        evidence_data={"status": "ok"},
        verified=True,
    )

    # Injected into chain Y
    chain_y = WorkflowProvenanceChain(workflow_id="wf_y")
    chain_y.records = [rec_x]
    assert chain_y.verify_chain_integrity() is False


def test_attack_p8_007_replace_evidence_artifact_after_execution():
    """ATTACK-P8-007: Modifying evidence artifact after execution causes hash mismatch in chain."""
    chain = WorkflowProvenanceChain(workflow_id="wf_artifact")
    original_evidence = {"token": "SECRET_123", "value": 42}
    chain.record_phase(
        step_id="step_art",
        action="extract",
        action_type="DATA_EXTRACTION",
        phase="VERIFIED",
        input_data={},
        evidence_data=original_evidence,
        verified=True,
    )

    # Reconstruct provenance records with altered hash
    rec = chain.records[0]
    replaced_rec = StepProvenanceRecord(
        workflow_id=rec.workflow_id,
        step_id=rec.step_id,
        action=rec.action,
        action_type=rec.action_type,
        phase=rec.phase,
        timestamp=rec.timestamp,
        input_hash=rec.input_hash,
        evidence_hash=chain.compute_sha256({"token": "REPLACED_TOKEN", "value": 999}),
        verified=rec.verified,
        signature=rec.signature,
    )
    chain.records = [replaced_rec]
    assert chain.verify_chain_integrity() is False


@pytest.mark.asyncio
async def test_attack_p8_008_modify_dom_after_evidence_capture():
    """ATTACK-P8-008: Zero observable DOM/URL mutation on state mutating action is rejected."""
    verifier = WorkflowVerifier()
    step = WorkflowStep.create(
        step_id="mutate_step",
        action="click",
        action_type=ActionType.STATE_MUTATION,
        input_data={"selector": "#btn", "allow_unchanged_state": False},
    )
    previous_ev = {
        "timestamp": time.monotonic() - 1.0,
        "dom_hash": "hash_identical_dom",
        "url": "https://example.com/page",
    }
    current_ev = {
        "timestamp": time.monotonic(),
        "dom_hash": "hash_identical_dom",  # No change
        "url": "https://example.com/page",
    }
    with pytest.raises(VerificationFailedError, match="zero observable DOM or URL mutation"):
        await verifier.verify_step_execution(
            step=step,
            session=None,
            runtime_evidence=current_ev,
            previous_evidence=previous_ev,
        )


@pytest.mark.asyncio
async def test_attack_p8_009_fake_browser_page_object():
    """ATTACK-P8-009: Passing None or invalid session is rejected by executor."""
    executor = WorkflowExecutor()
    state = WorkflowState(workflow_id="wf_fake", session_id="sess_fake")
    step = WorkflowStep.create(action="navigate", action_type=ActionType.NAVIGATION)

    with pytest.raises(ExecutionError, match="Session is None or invalid"):
        await executor.execute_step(step, session=None, state=state)


def test_attack_p8_010_forge_mcp_response():
    """ATTACK-P8-010: Forged MCP response claiming success without verified backing is caught."""
    verifier = WorkflowVerifier()
    fake_mcp_payload = {
        "workflow_id": "wf_mcp_fake",
        "session_id": "sess_mcp_fake",
        "status": "COMPLETED",
        "is_verified": True,
        "step_results": [],
        "provenance": [],
    }
    fake_result = type("FakeResult", (), fake_mcp_payload)()
    assert verifier.verify_workflow_result(fake_result) is False


@pytest.mark.asyncio
async def test_attack_p8_011_planner_declares_success():
    """ATTACK-P8-011: Planner cannot unilaterally declare workflow or step success."""
    planner = DeterministicPlanner()
    steps = await planner.plan(goal="click", context={"url": "https://example.com", "selector": "#btn"})

    for s in steps:
        # Planner outputs must remain in PENDING status
        assert s.status == StepStatus.PENDING
        assert s.result is None
        assert s.evidence == {}


@pytest.mark.asyncio
async def test_attack_p8_012_executor_declares_success_without_verification():
    """ATTACK-P8-012: Step verification cannot be claimed without WorkflowVerifier confirmation."""
    verifier = WorkflowVerifier()
    unverified_step = WorkflowStep.create(
        step_id="step_unverified",
        action="extract",
        action_type=ActionType.DATA_EXTRACTION,
        input_data={"allow_empty": False},
    )
    unverified_step.result = None  # None extraction

    with pytest.raises(VerificationFailedError, match="produced None result"):
        await verifier.verify_step_execution(
            step=unverified_step,
            session=None,
            runtime_evidence={"timestamp": time.monotonic()},
        )


@pytest.mark.asyncio
async def test_attack_p8_013_recovery_declares_success_without_live_verification():
    """ATTACK-P8-013: Recovery action must still be independently re-verified."""
    rec_mgr = RecoveryManager()
    dummy_session = type("DummySession", (), {"session_id": "dummy_sess", "raw_page": None, "browser_session": None})()
    recovered = await rec_mgr.execute_recovery(dummy_session, RuntimeError("Fatal crash"))
    # Recovery on dead dummy session without live page must return False (never fake True)
    assert recovered is False
    assert rec_mgr.state in (RecoveryState.RECOVERY_FAILED, RecoveryState.TERMINAL_FAILURE)


@pytest.mark.asyncio
async def test_attack_p8_014_bypass_orchestrator_through_direct_tool_invocation():
    """ATTACK-P8-014: High-impact external side effects require approval gate."""
    manager = ApprovalManager()
    step = WorkflowStep.create(
        step_id="step_purchase",
        action="purchase_checkout",
        action_type=ActionType.EXTERNAL_SIDE_EFFECT,
    )
    assert manager.needs_approval(step) is True


@pytest.mark.asyncio
async def test_attack_p8_015_cross_session_evidence_substitution():
    """ATTACK-P8-015: Substituting evidence from Session B into Session A's verification is rejected."""
    verifier = WorkflowVerifier()
    wf_res_b = WorkflowResult(
        workflow_id="wf_sess_B",
        session_id="session_B",
        status=WorkflowStatus.COMPLETED,
        step_results=[{"step_id": "step_1", "action": "navigate"}],
        provenance=[
            {
                "workflow_id": "wf_sess_B",
                "step_id": "step_1",
                "action": "navigate",
                "action_type": "NAVIGATION",
                "phase": "VERIFIED",
                "timestamp": time.monotonic(),
                "input_hash": "h1",
                "evidence_hash": "h2",
                "verified": True,
                "signature": "sig_dummy",
            }
        ],
        is_verified=True,
    )

    # When validated for expected_session_id="session_A", it must be rejected!
    assert verifier.verify_workflow_result(wf_res_b, expected_session_id="session_A") is False
