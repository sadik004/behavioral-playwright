# Production Integrity Release Gate Specification

**Repository**: `sadik004/behavioral-playwright`  
**Governance Standard**: Enterprise Architectural Governance & Zero-Fraud Engineering  
**Harness Entry Point**: `python -m harness.gate`  

---

## 1. Zero-Fraud Engineering Invariants (Binding Law)

The production release gate is an unyielding, non-sycophantic quality barrier. It evaluates mathematical and runtime truth, completely independent of whether existing tests pass.

### The 26 Invariant Laws:
1. **Zero Monolithic Code Slop**: No monolithic multi-thousand-line files with untyped dict returns escaping the API boundary.
2. **Untrusted Existing Test Assumption**: Existing tests are evidence only. Passing existing tests does NOT grant a release pass.
3. **Falsification Over Confirmation**: Every claim must have an adversarial test designed to disprove it.
4. **Dry-Run Never Counts as Live Success**: A dry-run or static script generation must NEVER return `status: "success"` or register as `REAL_SUCCESS`.
5. **Swallowed Exceptions Never Count as Success**: Any silent catch (`except Exception: pass`) or fallback returning dummy success is classified as P0 fraud.
6. **Explicit Gating for Absent Providers**: Missing dependencies (`patchright`, `browser-use`) must raise `ProviderUnavailableError` or return `PROVIDER_UNAVAILABLE`, never fabricate success or dummy responses.
7. **Strict RNG Determinism**: Any method accepting `seed: int` must deterministically control all internal stochastic processes without leaking to or from global state.
8. **No Metric Impersonation**: Brier score is not ECE; static string generation is not runtime DOM evasion; synthetic simulated packets are not physical PCIe DMA events.
9. **Mutation Score Hurdle**: The test suite must achieve $\ge 85\%$ kill rate against in-memory adversarial mutations before production approval ($\ge 95\%$ for release).
10. **Zero Raw SQL / In-Memory O(1) Lookups**: In-memory lookups must be strictly $O(1)$ (`dict`/`set`); zero quadratic scans.
11. **Non-Destructive Observability**: Sniffers and metrics collectors must never alter intercepted response streams or introduce memory leaks.
12. **Double-Entry Auditing for State**: State storage must record timestamps, depths, and statuses without mutating historical audit records.
13. **Mandatory Terminal Verification**: Every gate run must execute cleanly from the terminal and output unambiguous metrics.
14. **Phased Lifecycle**: The repository must follow `RED -> REVIEW -> LOCK -> FIX -> GREEN`. No code fixing is permitted before baseline review.
15. **Decoupled Out-of-Process External Verification**: In-memory verification is untrusted; final release verification must execute via isolated OS subprocess pipes (`IndependentExternalVerifier`) to protect against single-process memory patching.
16. **Live Physical OS & Artifact Hashing**: Claims of browser execution require verified live OS PIDs (`OpenProcess`/`os.kill`) in the OS process table and live filesystem SHA-256 byte recalculation of all generated artifacts.
17. **Cryptographic HMAC Provenance Chains**: Observation bundles must be sealed at capture time with HMAC-SHA256 signatures binding execution IDs, session IDs, PIDs, and artifact hashes. Any subsequent mutation invalidates the seal.
18. **Anti-Replay Nonce & Freshness Boundaries**: Previously verified evidence tokens cannot be replayed across runs; evidence must enforce strict timestamp freshness ($\Delta t < 60\text{s}$), out-of-process replay registries, and future-timestamp rejection.
19. **Strict Prohibition of Arbitrary Sleeps**: `time.sleep`, `asyncio.sleep` with magic numbers, and `page.wait_for_timeout` are strictly banned; dynamic DOM mutation checks and event listeners are mandatory.
20. **Zero Tautological Tests & Environment-Aware Provider Assertions**: Tautologies like `assert True` are classified as P0 fraud; optional modular providers must verify dynamic environment availability (`is Provider().is_available()`).
21. **Session & Workflow Identity Binding**: Workflows and PageSessions must be explicitly bound. Mismatched session IDs (`workflow.session_id != session.session_id`) or session-less execution must immediately fail with `WorkflowIntegrityError`.
22. **Zero Positional Ambiguity & Fallbacks**: Positional fallbacks (`.first()`, `.nth(0)`, `elements[0]`) on multi-element queries without explicit ranking metrics are strictly prohibited. Multi-match ambiguity must trigger resolution disambiguation or structured error.
23. **Anti-Loop & Zero-Progress Protection**: Execution pipelines must enforce strict loop protection (`LoopProtector`, `RunawayLoopError`). Repeated identical action sequences ($N \ge 3$) or zero DOM state hash mutation windows ($M \ge 4$) must trip fail-safes immediately.
24. **Mandatory Post-Recovery Live Verification**: Recovery attempts must actively verify the viability of the recovered target. A closed or dead session cannot be marked `RECOVERED`; it must terminate as `TERMINAL_FAILURE`.
25. **100% Adversarial Mutation Hurdle**: The complete system must achieve 100% kill score against external adversarial mutants (including state bypass, signature forgery, silent exception masking, and identity spoofing).
26. **Complete Phased Regression Invariant**: Across all phases (Phase 1 through Phase 8), all 560+ test suites and 140+ independent verification suites must run concurrently or in sequence with zero regressions, zero skipped required checks, and zero mocked core logic.

---

## 2. Release Gate Decision Tree

```
                       [Run harness.gate]
                               |
            +------------------+------------------+
            |                                     |
   Any P0 Critical Issues?                Any Contradicted Claims?
   (Fake Success, Crashes)               (EVASION-001, EVASION-002)
            |                                     |
          [YES]                                 [YES]
            |                                     |
            +------------------+------------------+
                               |
                       [GATE VERDICT: FAIL]
                               |
                  1. Log RCA in docs/rca/
                  2. Present Baseline to Architect
                  3. Await Review Before Code Modification
```

---

## 3. Mandatory Release Conditions for Phase 2 (FIX Phase)

Before a release can be designated `PASS`, the following gates must be cleared:

1. **Static AST Gate**:
   - P0 Critical Findings: `0`
   - P1 Broad Catch Findings: Audited and refactored to specific exception types.
2. **Adversarial Gate**:
   - `PowerHandPlaywrightRunner` raises `BrowserExecutionError` on failure rather than returning `dry_run_success`.
   - Existing assertions checking `assert "success" in status` refactored to exact check `assert res["status"] == "success"`.
3. **Determinism Gate**:
   - `PowerHandMaster.get_saccade_path` tremor jitter rewritten to use an isolated seeded `random.Random(self.seed)` instance.
4. **Provider Exception Gate**:
   - `ProviderUnavailableError` unified under `behavioral_playwright.exceptions.BehavioralPlaywrightError`.
5. **Mutation Gate**:
   - Mutation kill score $\ge 85\%$.
6. **Claim Registry Gate**:
   - Zero `CONTRADICTED` claims.
