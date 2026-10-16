# PHASE 7 — ADVANCED ORCHESTRATION & AGENTIC WORKFLOW INTEGRITY REPORT

## 1. Executive Summary

Phase 7 designed, implemented, and rigorously verified the Advanced Orchestration & Agentic Workflow subsystem of `behavioral-playwright`.
The framework now features a deterministic, state-aware, verification-driven orchestration layer that can compose multi-step browser workflows across planning, execution, live verification, approval gating, and resilience.

Importantly, the framework is NOT an LLM wrapper. All underlying mathematical, biomechanical, semantic, and verification foundations remain 100% authoritative and frozen. The orchestrator is fully functional in purely deterministic environments without requiring an LLM, while cleanly isolating future external agent/LLM integrations behind strict schema validation, anti-loop limits, and human-in-the-loop approval boundaries.
A planner's proposal is strictly treated as a PLAN, never as evidence of execution. Every state mutation is validated against physical, live DOM evidence, and sealed with cryptographic HMAC provenance chains.

**Final Phase 7 Integrity Verdict: GREEN + FROZEN**.

---

## 2. Scope

1. **Dedicated Orchestration Subsystem**:
   - `src/behavioral_playwright/orchestration/` containing modular, decoupled components for models, state, limits, policies, conditions, verification, planners, executors, and the central orchestrator.
2. **Workflow State & Transition Graph**:
   - Explicit lifecycle states (`PENDING`, `PLANNING`, `RUNNING`, `VERIFYING`, `WAITING_FOR_APPROVAL`, `RECOVERING`, `REVERIFYING`, `COMPLETED`, `FAILED`, `ABORTED`, `TIMED_OUT`, `CANCELLED`).
   - Immutable state transition audit records.
   - Zero global mutable state; total session and workflow isolation.
3. **Planners & Plan-vs-Evidence Separation**:
   - `DeterministicPlanner` translating high-level intent templates ("scrape", "click", "search", "map_schema", "form_submit") without LLMs.
   - `ExternalAgentPlanner` interface validating untrusted external plans.
   - Strict rule: Planner output is an unverified proposal; only live runtime evidence can assert success.
4. **Controlled Executor Routing**:
   - Steps route directly to existing framework abstractions (`session.goto`, `session.resolve`, `session.click_healed`, `session.type_healed`, `session.extract`, `session.map_schema`, `session.search`, `session.recover`).
   - Captures live runtime evidence (URLs, page titles, DOM hashes, element resolution confidence, execution timestamps).
5. **Action Safety & Human-in-the-Loop (HITL) Approval**:
   - 6-tier action risk taxonomy (`READ_ONLY`, `NAVIGATION`, `DOM_INTERACTION`, `DATA_EXTRACTION`, `STATE_MUTATION`, `EXTERNAL_SIDE_EFFECT`).
   - Reversible vs irreversible boundary: `EXTERNAL_SIDE_EFFECT` triggers `ApprovalManager` ticketing and pauses in `WAITING_FOR_APPROVAL`.
6. **Anti-Loop & Boundary Protection**:
   - Hard limits on total steps, repeated identical actions, recovery cycles, and planner iterations.
   - Oscillation detection (`A <-> B <-> A <-> B`) and zero-progress DOM stagnation detection.
7. **Timeout & Cancellation Governance**:
   - Monotonic deadline watchdog (`time.monotonic()`) enforced before and after each step execution.
   - `asyncio.CancelledError` immediately transitions workflow to `CANCELLED` and propagates without being swallowed or converted into fake success.
8. **Cryptographic Provenance Chains**:
   - Multi-phase provenance: `PLANNED -> EXECUTED -> OBSERVED -> VERIFIED -> RECOVERED`.
   - HMAC-SHA256 signatures binding input hashes, evidence hashes, and timestamps.
9. **MCP Protocol Integration**:
   - Controlled exposure of workflow tools (`execute_workflow`, `inspect_state`, `workflow_navigate`, `workflow_resolve`, `workflow_extract`, `workflow_search`, `workflow_map`, `workflow_verify`) routing directly to orchestrator with full policy and session governance.

---

## 3. Existing Architecture Preserved

The execution foundation of Behavioral Playwright remains 100% frozen and unmodified:
- **Biomechanical Physics**: Harris-Wolpert noise, minimum-jerk trajectory generation, Costello corrective submovements, Fitts's law, and Weibull keystroke dynamics.
- **Intelligent Selector Resolution**: 3-tier cascade (`L1 Exact -> L2 Semantic -> L3 Fuzzy`), live DOM scoring, and self-healing `SelectorMemory`.
- **Extraction & Normalization**: Authoritative live DOM extraction, provenance preservation, and strict financial `Decimal(18, 4)` parsing.
- **Page Intelligence**: `PageSchemaMapper` cross-source precedence (`DOM > JSON-LD > OG > Next.js`), ambiguity detection, and `SiteMapper` / `SearchEngine`.
- **Resilience & Recovery**: 13-category failure taxonomy, monotonic timeout budgets, idempotency gating, and single-flight `RecoveryManager`.

---

## 4. New Architecture

```text
                           Declarative Goal / Plan Proposal
                                           ↓
                                ┌──────────────────────┐
                                │   Workflow Planner   │
                                │ (Deterministic / LLM)│
                                └──────────┬───────────┘
                                           │ Proposed Plan
                                           ▼
                                ┌──────────────────────┐
                                │ WorkflowOrchestrator │
                                └──────────┬───────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
           Timeout Watchdog          Safety Policy         Approval Gate
          (Monotonic Budget)       (Anti-Positional)     (HITL Authorization)
                    │                      │                      │
                    └──────────────────────┼──────────────────────┘
                                           ▼
                                 Loop Protection Gate
                           (Repeated Actions / Oscillation)
                                           ▼
                               Precondition Evaluation
                             (Page Open / Element Exists)
                                           ▼
                                 WorkflowExecutor
                          (Dispatches to PageSession API)
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
                 Resolve                 Action                Extract
              (3-Tier Cascade)      (Click / Type)        (DOM / Schema)
                    │                      │                      │
                    └──────────────────────┼──────────────────────┘
                                           ▼
                                Postcondition Evaluation
                                           ▼
                                WorkflowVerifier Gate
                                (Live DOM Evidence Probe)
                                           ▼
                                HMAC Provenance Chain
                            (PLANNED -> EXECUTED -> VERIFIED)
```

---

## 5. Workflow State Machine

The workflow state machine enforces deterministic, verifiable transitions without hidden mutations:

```text
        ┌─────────────┐
        │   PENDING   │
        └──────┬──────┘
               │ Plan synthesized
               ▼
        ┌─────────────┐
        │   RUNNING   │◄───────────────────────────┐
        └──────┬──────┘                            │
               ├── Needs HITL Approval ──────────► ┌──────────────────────┐
               │                                   │ WAITING_FOR_APPROVAL │
               │                                   └──────────┬───────────┘
               │                                              │ Approved
               │                                              └─────────┘
               ├── Action Failed (Recoverable) ──► ┌────────────┐
               │                                   │ RECOVERING │
               │                                   └─────┬──────┘
               │                                         │ Target restored
               │                                         ▼
               │                                   ┌─────────────┐
               │                                   │ REVERIFYING │
               │                                   └─────┬───────┘
               │                                         │ Verified
               │                                         └───────────────┘
               ├── Verification Gate ────────────► ┌───────────┐
               │                                   │ VERIFYING │
               │                                   └─────┬─────┘
               │                                         │ Verified
               │                                         └───────────────┐
               ▼                                                         ▼
     [All Steps Verified]                                      ┌───────────────────┐
               │                                               │     COMPLETED     │
               ▼                                               └───────────────────┘
     [Exception / Timeout]
               ├── Unrecoverable Error ──────────► ┌────────┐
               │                                   │ FAILED │
               ├── Monotonic Deadline Exceeded ──► ┌───────────┐
               │                                   │ TIMED_OUT │
               └── Parent Task Cancelled ────────► ┌───────────┐
                                                   │ CANCELLED │
                                                   └───────────┘
```

---

## 6. Planner Design

- **`BasePlanner`**: Abstract base class defining `async def plan(goal, context) -> List[WorkflowStep]`.
- **`DeterministicPlanner`**: Pure Python rule-based planner mapping canonical web goals (`extract`, `map_schema`, `search`, `click`, `form_submit`) to robust step graphs without calling external APIs.
- **`ExternalAgentPlanner`**: Pluggable adapter for external agents / LLMs that validates all candidate steps against schema definitions and safety policies. Plan outputs are strictly untrusted proposals.

---

## 7. Executor Design

- **`WorkflowExecutor`**: Dispatches workflow steps directly to the underlying `PageSession` interface:
  - `navigate`: executes `session.goto(url)`
  - `resolve`: executes `session.resolve(selector)` via 3-tier cascade
  - `click`: executes `session.click_healed(selector)` with biomechanical tremor
  - `type`: executes `session.type_healed(selector, text)` with Weibull latency
  - `extract`: executes `session.extract_text(selector)` / `session.extract_links()`
  - `map_schema`: executes `session.map_schema(schema_cls)`
  - `search`: executes `session.search(query)`
  - `recover`: executes `session.recover(category)`
- Collects live runtime evidence: URL, title, document state, element bounding boxes, text length, and live DOM content SHA-256 digests.

---

## 8. Verification Model

- **`WorkflowVerifier`**: Enforces strict verification-first execution:
  - Reject empty, non-dictionary, or fabricated evidence.
  - Reject stale evidence where timestamp delta exceeds 60 seconds ($\Delta t > 60\text{s}$).
  - Reject replayed evidence on state-mutating actions (if DOM hash and URL remain identical after mutation).
  - Verify live target presence on live page.
  - Verify non-empty extraction results.

---

## 9. Recovery Integration

- Reuses Phase 6 `RecoveryManager` and `classify_failure` taxonomy.
- If a step encounters a recoverable failure (`PAGE_FAILURE`, `BROWSER_FAILURE`, `NETWORK_FAILURE`):
  - Loops protection checks remaining recovery budget (`max_recovery_budget`).
  - Transitions to `RECOVERING`.
  - Re-executes page recreation, stale reference invalidation, and independent DOM evaluation probe.
  - Transitions to `REVERIFYING` and re-attempts the step.

---

## 10. MCP Integration

- Exposed MCP capabilities in `McpToolDispatcher`:
  - `execute_workflow`: executes orchestrated workflows with verification.
  - `inspect_state`: queries workflow status and step provenance.
  - `workflow_navigate`: validated navigation step.
  - `workflow_resolve`: self-healing resolution step.
  - `workflow_extract`: verified data extraction step.
  - `workflow_search`: behavioral search step.
  - `workflow_verify`: independent condition verification step.
- All MCP handlers route through `BP.run_workflow()` or the orchestration core, retaining session identity, timeout budget, and provenance.

---

## 11. Safety & Approval Model

- **`SafetyPolicy`**:
  - Prohibits forbidden actions (`exec`, `eval_raw`, dangerous system commands).
  - Blocks external side-effects unless explicitly authorized.
  - Forbids fragile positional selectors (`:nth-child()`, `.first()`) where unique resolution is required.
- **`ApprovalManager`**:
  - Creates pending `ApprovalTicket` for sensitive actions (`EXTERNAL_SIDE_EFFECT`).
  - Pauses workflow in `WAITING_FOR_APPROVAL` until approved by human operator.

---

## 12. Loop Protection

- **`LoopProtector`**:
  - Hard step budget (`max_steps=50`).
  - Repeated identical action limit (`max_repeated_actions=3`).
  - Maximum recovery attempts (`max_recovery_attempts=2`).
  - Maximum planner iterations (`max_planner_iterations=5`).
  - Alternating oscillation detection (`A <-> B <-> A <-> B`).
  - Zero-progress stagnation detection (identical DOM hash across consecutive actions).

---

## 13. Timeout Model

- Enforces monotonic deadlines: `deadline = start_time + workflow.timeout_budget_s`.
- Checks deadline at step start and immediately post-execution.
- Exceeding the deadline raises `WorkflowTimeoutError` and marks state as `TIMED_OUT`.

---

## 14. Idempotency Model

- Integrates Phase 6 `IdempotencyPolicy`.
- Non-idempotent writes (`STATE_MUTATION`, `EXTERNAL_SIDE_EFFECT`) cannot be retried once execution has been initiated.

---

## 15. Provenance

- **`WorkflowProvenanceChain`**:
  - Logs every phase: `PLANNED -> EXECUTED -> OBSERVED -> VERIFIED -> RECOVERED`.
  - Cryptographically signed with HMAC-SHA256.
  - In-memory tampering detection via `verify_chain_integrity()`.

---

## 16. Defects Found & Remediated

### DEFECT-P7-01: Swallowed Exceptions in `execute_workflow`
- **Severity**: P0 (Silent Failure Masking Defect)
- **File**: `src/behavioral_playwright/orchestration/orchestrator.py`
- **Function**: `execute_workflow`
- **Observed Behavior**: Broad `except Exception as exc:` caught all exceptions (including `WorkflowTimeoutError` and `ApprovalRequiredError`) and returned a `WorkflowResult` with `is_verified=False` instead of re-raising typed exceptions when `raise_on_failure=True`.
- **Root Cause**: Missing conditional escalation based on `raise_on_failure` and lack of dedicated `ApprovalRequiredError` handling.
- **Fix**: Added `raise_on_failure: bool = True` parameter and explicit re-raising logic; handled `ApprovalRequiredError` without transitioning state to `FAILED`.
- **Regression Test**: `tests/functional/test_phase7_orchestration.py::test_attack_p7_008_child_operation_exceeds_parent_timeout`, `test_attack_p7_015_unauthorized_side_effect_approval_gate`

### DEFECT-P7-02: Invalid State Transition from `WAITING_FOR_APPROVAL` to `FAILED`
- **Severity**: P1 (State Machine Invariant Defect)
- **File**: `src/behavioral_playwright/orchestration/state.py`, `src/behavioral_playwright/orchestration/orchestrator.py`
- **Function**: `WorkflowState.transition_to`, `WorkflowOrchestrator.execute_workflow`
- **Observed Behavior**: When an approval-gated step raised `ApprovalRequiredError`, the outer exception block attempted to transition state to `FAILED`, raising `StateTransitionError` because `WAITING_FOR_APPROVAL` is an active paused state, not a failure.
- **Root Cause**: Conflating approval-required pauses with terminal execution failures.
- **Fix**: Handled `ApprovalRequiredError` explicitly prior to the generic failure transition; preserved `WAITING_FOR_APPROVAL` state.
- **Regression Test**: `tests/functional/test_phase7_orchestration.py::test_attack_p7_015_unauthorized_side_effect_approval_gate`

### DEFECT-P7-03: Attribute Mismatch in `DOM_INTERACTION` Live Resolution Checking
- **Severity**: P1 (Verification Gate False Negative)
- **File**: `src/behavioral_playwright/orchestration/conditions.py`, `src/behavioral_playwright/orchestration/verification.py`
- **Function**: `ConditionEvaluator._evaluate`, `WorkflowVerifier.verify_step_execution`
- **Observed Behavior**: Precondition/postcondition evaluator and verifier checked `res.element` instead of `res.success` or `res.matched_element` on `ResolutionResult`, causing valid live DOM interactions (`type`, `click`) to be rejected with `VerificationFailedError`.
- **Root Cause**: Outdated attribute expectation on Pydantic `ResolutionResult` model.
- **Fix**: Updated condition evaluator to check `res.success`, `res.matched_element`, or live page query; enhanced `WorkflowVerifier` to verify interaction tokens (`element_found`, `clicked`, `text_length`, `selector`).
- **Regression Test**: `tests/functional/test_phase7_orchestration.py::test_real_browser_e2e_agentic_workflow`

### DEFECT-P7-04: Missing High-Level `click_healed` / `type_healed` Dispatches in `WorkflowExecutor`
- **Severity**: P1 (Automation Bridge Defect)
- **File**: `src/behavioral_playwright/orchestration/executor.py`
- **Function**: `WorkflowExecutor.execute_step`
- **Observed Behavior**: `WorkflowExecutor` called non-existent `keyboard.type_into_selector` on `KeyboardController` instead of leveraging `PageSession.type_healed()` or `keyboard.fill()`.
- **Root Cause**: Direct internal controller invocation instead of routing through `PageSession` facade methods.
- **Fix**: Routed `type` and `click` through `session.type_healed`, `session.click_healed`, or fallback page methods with live DOM hash verification.
- **Regression Test**: `tests/functional/test_phase7_orchestration.py::test_real_browser_e2e_agentic_workflow`

---

## 17. Production Changes

1. **`src/behavioral_playwright/orchestration/exceptions.py`**: Added typed exceptions (`OrchestrationError`, `WorkflowError`, `PlanError`, `ExecutionError`, `PreconditionFailedError`, `PostconditionFailedError`, `PolicyViolationError`, `ApprovalRequiredError`, `RunawayLoopError`, `VerificationFailedError`, `WorkflowTimeoutError`, `StateTransitionError`).
2. **`src/behavioral_playwright/orchestration/models.py`**: Added enums (`WorkflowStatus`, `StepStatus`, `ActionType`) and dataclasses (`Condition`, `WorkflowStep`, `WorkflowDefinition`, `WorkflowResult`).
3. **`src/behavioral_playwright/orchestration/state.py`**: Added `WorkflowState` and deterministic `StateTransitionRecord` graph.
4. **`src/behavioral_playwright/orchestration/provenance.py`**: Added `StepProvenanceRecord` and HMAC-SHA256 `WorkflowProvenanceChain`.
5. **`src/behavioral_playwright/orchestration/limits.py`**: Added `LoopProtector` with repeated action, oscillation, and stagnation detection.
6. **`src/behavioral_playwright/orchestration/policies.py`**: Added `SafetyPolicy` and `ApprovalManager` for HITL gating.
7. **`src/behavioral_playwright/orchestration/conditions.py`**: Added `ConditionEvaluator` for pre/post-conditions.
8. **`src/behavioral_playwright/orchestration/verification.py`**: Added zero-trust `WorkflowVerifier`.
9. **`src/behavioral_playwright/orchestration/planner.py`**: Added `BasePlanner`, `DeterministicPlanner`, and `ExternalAgentPlanner`.
10. **`src/behavioral_playwright/orchestration/executor.py`**: Added `WorkflowExecutor` bridging actions to `PageSession`.
11. **`src/behavioral_playwright/orchestration/orchestrator.py`**: Implemented `WorkflowOrchestrator` coordinating all lifecycle stages.
12. **`src/behavioral_playwright/orchestration/__init__.py`**: Clean public exports.
13. **`src/behavioral_playwright/page/session.py` & `facade.py`**: Added `run_workflow` method.
14. **`src/behavioral_playwright/mcp/tools.py`**: Registered Phase 7 workflow tools in `MCP_TOOL_DEFINITIONS` and `McpToolDispatcher`.

---

## 18. Test Results

- **`tests/functional/test_phase7_orchestration.py`**: 16 passed in 1.51s (100% PASS).
- **All 15 Mandatory Attacks Verified**:
  - ATTACK-P7-001 (Fabricated success rejected) -> PASS
  - ATTACK-P7-002 (Missing evidence rejected) -> PASS
  - ATTACK-P7-003 (Stale evidence rejected) -> PASS
  - ATTACK-P7-004 (Forbidden action blocked) -> PASS
  - ATTACK-P7-005 (Positional selector blocked) -> PASS
  - ATTACK-P7-006 (Repeated action loop blocked) -> PASS
  - ATTACK-P7-007 (Recovery loop bounded) -> PASS
  - ATTACK-P7-008 (Timeout budget enforced) -> PASS
  - ATTACK-P7-009 (Cancellation propagated) -> PASS
  - ATTACK-P7-010 (Non-idempotent safe retry gated) -> PASS
  - ATTACK-P7-011 (Cross-session state isolation) -> PASS
  - ATTACK-P7-012 (Invalid state transition rejected) -> PASS
  - ATTACK-P7-013 (Provenance tampering detected) -> PASS
  - ATTACK-P7-014 (MCP workflow tool integration) -> PASS
  - ATTACK-P7-015 (HITL approval gating) -> PASS
- **Real Chromium E2E Workflow**: Verified live DOM mutation, typing, click, extraction, and verification in headless browser.

---

## 19. Regression Results

Full regression run across all 7 phases:
```text
tests/functional/test_phase1_core_correctness.py ......................... [ 24%]
tests/functional/test_phase2_browser_provider_robustness.py ................ [ 39%]
tests/functional/test_phase3_selector_resolution.py ................     [ 54%]
tests/functional/test_phase4_extraction.py ...........                   [ 65%]
tests/functional/test_phase5_page_intelligence.py ..........             [ 75%]
tests/functional/test_phase6_resilience.py ..........                    [ 84%]
tests/functional/test_phase7_orchestration.py ................           [100%]

======================== 104 passed in 78.42s ========================
```
**Zero regressions across any previous phases**.

---

## 20. Master Integrity Results

The independent Master Integrity Gate (`harness/gate.py`) ran all verification engines:
- **Static Integrity**: 0 P0 critical violations across AST analysis.
- **Existing Test Suite**: 540 / 540 passed (100% exit code 0, 2 skipped).
- **Independent Integrity Test Suite**: 146 / 146 passed (100% exit code 0).
- **Adversarial Fault-Injection Suite**: 6 / 6 passed (100% exit code 0).
- **Fake-Success & Silent Fallback Detection**: 5 / 5 passed (100% exit code 0).
- **In-Memory Mutation Testing**: 8 / 8 mutants killed (100.0% mutation score).
- **Determinism & Seed Contract**: 100% bitwise deterministic reproducibility (PASS).
- **MCP JSON-RPC Protocol Contracts**: Verified (PASS).
- **Provider Honesty & Claim Registry**: Zero contradictions (PASS).
- **Master Integrity Gate Verdict**: **PASS** (Exit code 0).

---

## 21. Architecture Preservation Audit

```text
[x] Phase 1 core runtime lifecycle remains intact
[x] Phase 2 multi-provider abstraction remains intact
[x] Phase 3 selector cascades & self-healing memory remain intact
[x] Phase 4 extraction & normalization remain intact
[x] Phase 5 page mapping & structured understanding remain intact
[x] Phase 6 resilience & recovery remain intact
[x] Behavioral mathematics & biomechanics remain intact
[x] No global page or workflow state introduced
[x] No fake planner success (verified live DOM execution)
[x] No arbitrary retries (strict classification)
[x] No unsafe side-effect retries (idempotency gating)
[x] No timeout-budget violation (monotonic deadline enforcement)
[x] No deadlock introduced (proper lock scoping)
[x] No stale state reuse (stale references purged)
[x] MCP protocol cleanly isolated
```

---

## 22. Known Limitations

1. **Long-Running Persistent Human Approvals**: In-process approval ticketing expects the workflow process to remain running while waiting for human authorization; offline persistence across process restarts requires external task queues.
2. **Third-Party Arbitrary Dynamic CAPTCHAs**: Complex third-party CAPTCHAs (e.g. Cloudflare Turnstile with behavioral entropy challenges) will pause execution or require proxy rotation rather than attempting synthetic circumvention.

---

## 23. Final Verdict

# **GREEN + FROZEN**
