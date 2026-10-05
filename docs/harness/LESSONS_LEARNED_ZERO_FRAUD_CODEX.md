# ZERO-FRAUD ENGINEERING CODEX & HARNESS LESSONS LEARNED

**Repository**: `sadik004/behavioral-playwright`  
**Governance Standard**: Enterprise Architectural Governance & Radical Anti-Sycophancy ("জিরো তেলবাজি" পলিসি)  
**Classification**: Permanent Harness Reference Codex  
**Target Milestone**: Phase 1–8 Architectural Completion & Production Release  

---

## 1. Core Engineering Philosophy: "Zero-Fraud Engineering"

### A. The Reality Gap: Working Code vs. Honest Code
- **Working Code**: Executes an action and exits without throwing an unhandled exception.
- **Honest Code**: Refuses to declare success unless physical, observable, and cryptographically signed live state changes have occurred in the live runtime.
- **The Core Law**: "A test suite with 100% green checkmarks can still conceal complete architectural bankruptcy if tests rely on tautologies (`assert True`), mock assertions, or unvalidated return values."

### B. Radical Anti-Sycophancy ("জিরো তেলবাজি")
- Flattery, agreeing with flawed premises, or marking broken code as "passing" to please reviewers or test runners is classified as engineering malpractice.
- Software deployed in production manages financial capital, user privacy, and critical automated workflows. An unnoticed silent failure or false positive in fraud detection or workflow automation causes catastrophic loss.

---

## 2. The Verification-First Architecture

### A. Trust Boundary Hierarchy
Under no circumstances may an untrusted layer establish trusted execution:
```text
Proposal (Agent / LLM / Deterministic Planner)
       <
Execution (WorkflowExecutor via PageSession)
       <
Observation (Live DOM Snapshot, Attributes, Elements)
       <
Verification (Independent WorkflowVerifier)
       <
Cryptographic Audit (WorkflowProvenanceChain HMAC-SHA256)
```

### B. Absolute Separation of Planner and Verifier
- **The Planner Has Zero Verification Authority**: An AI agent or deterministic planner proposing a step sequence can never mark a step as `COMPLETED` or `VERIFIED`. Its proposal remains in `StepStatus.PENDING`.
- **The Executor Cannot Verify Itself**: Execution captures live runtime evidence (`dom_hash`, `url`, `element_count`, `inner_text`). Only the independent `WorkflowVerifier` evaluates whether the evidence satisfies postconditions and freshness constraints.

### C. Cryptographic Provenance Chaining (Anti-Tampering)
- Every step lifecycle phase (`PLANNED`, `EXECUTED`, `OBSERVED`, `VERIFIED`, `RECOVERED`) generates an immutable `StepProvenanceRecord`.
- The record binds `workflow_id`, `step_id`, `action`, `action_type`, `timestamp`, `input_hash`, `evidence_hash`, and `verified` into an `HMAC-SHA256` digest signed with a dedicated secret key.
- **Cross-Workflow Injection Defense**: `verify_chain_integrity()` strictly verifies that `rec.workflow_id == self.workflow_id`. Any record injected from Workflow X into Workflow Y invalidates the HMAC signature and is immediately rejected.

---

## 3. Biomechanical & Human-Mimetic Input Modeling

### A. Why Linear Automation Fails
- Naive Playwright commands (`page.click()`, `page.fill()`) generate mathematical anomalies: perfectly linear vectors, constant zero-variance velocity, instant teleports, and zero physiological tremor.
- Modern anti-bot engines (Cloudflare Turnstile, PerimeterX, Akamai Bot Manager, DataDome) inspect trajectory curvature, velocity variance, and timing entropy via mousemove listeners.

### B. The Biomechanical Stack
1. **Costello's Two-Phase Saccadic Search Model**:
   - *Phase 1 (Ballistic)*: Rapid, high-velocity saccadic movement (80% steps) targeting a slightly overshot/undershot target ($\alpha \in [0.92, 1.08]$) modeled via Quadratic Bézier curves.
   - *Phase 2 (Micro-Correction)*: Fine motor adjustment (20% steps) settling onto the true target coordinate, incorporating numerical guards against zero-distance division.
2. **Harris-Wolpert Signal-Dependent Noise (SDN)**:
   - Motor noise variance scales quadratically with motor command velocity ($\sigma^2 = k_{\text{sdn}} \cdot \|v\|^2$).
3. **Physiological Tremor Engine**:
   - Speed-modulated sinusoidal micro-tremor ($8\text{--}12\text{ Hz}$) dampened during high-speed transit and magnified during fine landing.
4. **Linguistic Keystroke Dynamics**:
   - Log-normal digraph flight times and Gaussian key-hold distributions reflecting natural human typing muscle memory rather than fixed random sleeps.

---

## 4. Intelligent Selector Resolution & The Strict Ban on Positional Fallbacks

### A. The 3-Tier Resolution Cascade
```text
Target Selector
      │
      ▼
 Tier 1: L1 Exact Match (CSS / XPath / Text)
      │ (Fails if ambiguous or missing)
      ▼
 Learned Memory (Instance-scoped past successful selector)
      │ (Invalidated on page navigation or DOM mutation)
      ▼
 Tier 2: L2 Semantic / ARIA (Accessible Name, aria-label, role boost, placeholder)
      │ (Fails if score < threshold or multiple identical scores)
      ▼
 Tier 3: L3 Fuzzy Match (Normalized Levenshtein ratio on text / attributes)
      │ (Strict threshold >= 0.70; strict tie rejection)
      ▼
 ElementResolutionError (Honest Failure)
```

### B. The Absolute Ban on Positional Fallbacks
- **Rule**: Never use `.first()`, `.nth(0)`, or arbitrary top-candidate selection when a selector resolves to multiple ambiguous DOM elements.
- **Catastrophe**: In e-commerce checkout or banking operations, clicking `.first()` when two identical cards or buttons exist results in mutating or purchasing the wrong entity.
- **Binding Law**: Ambiguity must immediately raise `ElementResolutionError` or `AmbiguityError`.

---

## 5. Live DOM Authority & Financial Precision

### A. Missing vs. Empty Distinction
- An element missing from the DOM must return `None` (representing structural absence).
- An element present in the DOM with empty text must return `""` (representing valid empty content).
- Conflating `None` and `""` causes false-positive extraction and conceals DOM structural drift.

### B. Strict Financial Precision (`Decimal(18, 4)`)
- Binary floating-point `float` is strictly prohibited for monetary values. `0.1 + 0.2 != 0.3` in IEEE 754 floating-point arithmetic.
- All price extraction must route through `parse_price()` returning `Decimal` quantized to financial decimal places.

### C. Source Precedence Order
When structured data conflicts between page layers, precedence must be strictly ordered by authority:
$$\text{Live DOM} > \text{JSON-LD} > \text{OpenGraph} > \text{Next/Nuxt Hydration State}$$
Static metadata (JSON-LD, OpenGraph) can be stale or manipulated; the rendered live DOM represents what the user actually sees and interacts with.

---

## 6. Resilience, Taxonomy & Safe Recovery

### A. 13-Category Failure Taxonomy
Errors must never be lumped into generic exceptions. `classify_failure()` maps errors to specific categories:
- `CANCELLATION`: Must immediately halt and propagate without consuming retries.
- `NON_RECOVERABLE`: Code syntax errors, bad configuration, schema mismatches, and assertion errors fail fast.
- `TIMEOUT` / `TRANSIENT` / `NETWORK_FAILURE`: Eligible for bounded in-place retry with jittered exponential backoff.
- `PAGE_FAILURE` / `BROWSER_FAILURE`: Requires process-level or context-level recreation via `RecoveryManager`.

### B. Idempotency Safe-Retry Gating
- Read-only operations (`READ_ONLY`, `DATA_EXTRACTION`) are safe to retry.
- State-mutating operations (`STATE_MUTATION`, `EXTERNAL_SIDE_EFFECT`, `NON_IDEMPOTENT_WRITE`) must never be automatically retried without explicit idempotent confirmation.
- Retrying a failed checkout click without idempotency verification risks duplicate financial charges.

### C. Single-Flight Coordinated Recovery
- When multiple concurrent tasks encounter page crashes simultaneously, `RecoveryManager` acquires an asynchronous single-flight lock.
- Exactly one recovery operation runs; all other callers await its completion, preventing cascading browser launch storms.
- Post-recovery live evaluation (`() => 2 + 2 == 4`) is mandatory before declaring `RecoveryState.RECOVERED`.

---

## 7. Concurrency, Multi-Session Isolation & Resource Hygiene

### A. Zero Global Mutable State
- Never store active browsers, pages, contexts, or selector memories in global variables.
- Every `BrowserSession` manages its own isolated pool. Every `PageSession` maintains its own scoped `SelfHealingResolver` instance.
- Workflows running concurrently in `asyncio.gather()` must be completely isolated: Session A DOM values, inputs, and selector caches can never bleed into Session B.

### B. Leak-Proof Context Management
- In production, scrapers run for days. Any dangling page handle, background listener, or unclosed browser process consumes system file descriptors and RAM.
- `BrowserSession` and `PageSession` must implement `is_closed()` checks and enforce deterministic release across all execution paths:
  1. Normal completion
  2. Handled exception
  3. Unhandled runtime crash
  4. Monotonic timeout expiration
  5. Asynchronous cancellation (`asyncio.CancelledError`)

---

## 8. Catalog of Adversarial Attacks & Hardened Countermeasures

| Attack ID | Attack Vector | Vulnerability / Malpractice | Hardened Architectural Countermeasure |
| :--- | :--- | :--- | :--- |
| **ATTACK-P8-001** | Return `True` without execution | Empty workflow declaring success | `WorkflowOrchestrator` checks `not workflow.steps` and raises `ExecutionError`. |
| **ATTACK-P8-002** | Forge `WorkflowResult` | Synthetic `WorkflowResult` with fake `is_verified=True` | `validate_integrity()` checks non-empty provenance & step results; `WorkflowVerifier.verify_workflow_result()` audits HMAC signatures. |
| **ATTACK-P8-003** | Forge verification result | Altering evidence payload while claiming verified | `WorkflowProvenanceChain.verify_chain_integrity()` recalculates SHA-256 evidence digests against signed HMAC. |
| **ATTACK-P8-004** | Stale evidence replay | Reusing old tokens from previous workflows | `WorkflowVerifier` computes `freshness_delta_s = abs(now - ev_time)`; rejects if $> 60\text{s}$. |
| **ATTACK-P8-005** | Forge session identity | Executing Workflow A on Session B | `WorkflowOrchestrator` verifies `session.session_id == workflow.session_id`; raises `PolicyViolationError`. |
| **ATTACK-P8-006** | Forge workflow identity | Injecting step record from Workflow X into Workflow Y | `verify_chain_integrity()` strictly verifies `rec.workflow_id == self.workflow_id`. |
| **ATTACK-P8-007** | Replace evidence artifact | Modifying JSON evidence after step execution | Cryptographic hash binding in provenance record invalidates chain on any modified key/value. |
| **ATTACK-P8-008** | Modify DOM after capture | Zero-progress state mutation | `WorkflowVerifier` verifies that state-mutating actions produce non-zero DOM hash or URL delta. |
| **ATTACK-P8-009** | Fake browser/page object | Passing `session=None` or unbacked mock | `WorkflowExecutor` checks session presence and interfaces; raises typed `ExecutionError`. |
| **ATTACK-P8-010** | Forge MCP response | External client fabricating MCP result | MCP tool handler executes through authoritative framework and serializes verified result. |
| **ATTACK-P8-011** | Planner declares success | Planner trying to mark steps as `COMPLETED` | Planner only returns proposals with `StepStatus.PENDING`; has zero authority to set execution status. |
| **ATTACK-P8-012** | Executor declares success | Step with `None` result claiming verified | `WorkflowVerifier` explicitly rejects `result is None` or empty payloads without `allow_empty=True`. |
| **ATTACK-P8-013** | Recovery declares success | Dead dummy session recovery attempt | Dead session recovery fails live verification and enters `RecoveryState.TERMINAL_FAILURE` (never fake True). |
| **ATTACK-P8-014** | Direct tool bypass of policies | Invoking high-impact side effects directly | `ApprovalManager` forces approval ticket generation; execution halts with `ApprovalRequiredError`. |
| **ATTACK-P8-015** | Cross-session evidence substitution | Substituting Session B proof into Session A | `verify_workflow_result()` evaluates `result.session_id == expected_session_id`. |

---

## 9. The Mutation Testing Mandate: 100% Score as True Production Gate

- Standard unit tests only measure **code execution coverage** (lines touched). They tell you nothing about **assertion strength** (whether tests actually detect bugs).
- **Adversarial Mutation Testing**: The harness injects deliberate defects (e.g. bypassing safety checks, inverting verification booleans, disabling timeout limits, returning dummy success).
- If a mutated test suite passes, the tests are tautological or weak.
- **The Invariant**: All 8 adversarial mutants in `harness/mutation.py` must be killed by the independent oracle before any release can be certified. Real score achieved: **8/8 killed (100.0%)**.

---

## 10. Summary Invariant
> **"Engineering integrity is not the absence of errors; it is the absolute refusal to report success without live, independent, observable proof."**
