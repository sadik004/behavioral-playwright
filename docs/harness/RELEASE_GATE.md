# Production Integrity Release Gate Specification

**Repository**: `sadik004/behavioral-playwright`  
**Governance Standard**: Enterprise Architectural Governance & Zero-Fraud Engineering  
**Harness Entry Point**: `python -m harness.gate`  

---

## 1. Zero-Fraud Engineering Invariants (Binding Law)

The production release gate is an unyielding, non-sycophantic quality barrier. It evaluates mathematical and runtime truth, completely independent of whether existing tests pass.

### The 14 Invariant Laws:
1. **Zero Monolithic Code Slop**: No monolithic multi-thousand-line files with untyped dict returns escaping the API boundary.
2. **Untrusted Existing Test Assumption**: Existing tests are evidence only. Passing existing tests does NOT grant a release pass.
3. **Falsification Over Confirmation**: Every claim must have an adversarial test designed to disprove it.
4. **Dry-Run Never Counts as Live Success**: A dry-run or static script generation must NEVER return `status: "success"` or register as `REAL_SUCCESS`.
5. **Swallowed Exceptions Never Count as Success**: Any silent catch (`except Exception: pass`) or fallback returning dummy success is classified as P0 fraud.
6. **Explicit Gating for Absent Providers**: Missing dependencies (`patchright`, `browser-use`) must raise `ProviderUnavailableError` or return `PROVIDER_UNAVAILABLE`, never fabricate success or dummy responses.
7. **Strict RNG Determinism**: Any method accepting `seed: int` must deterministically control all internal stochastic processes without leaking to or from global state.
8. **No Metric Impersonation**: Brier score is not ECE; static string generation is not runtime DOM evasion; synthetic simulated packets are not physical PCIe DMA events.
9. **Mutation Score Hurdle**: The test suite must achieve $\ge 85\%$ kill rate against in-memory adversarial mutations before production approval.
10. **Zero Raw SQL / In-Memory O(1) Lookups**: In-memory lookups must be strictly $O(1)$ (`dict`/`set`); zero quadratic scans.
11. **Non-Destructive Observability**: Sniffers and metrics collectors must never alter intercepted response streams or introduce memory leaks.
12. **Double-Entry Auditing for State**: State storage must record timestamps, depths, and statuses without mutating historical audit records.
13. **Mandatory Terminal Verification**: Every gate run must execute cleanly from the terminal and output unambiguous metrics.
14. **Phased Lifecycle**: The repository must follow `RED -> REVIEW -> LOCK -> FIX -> GREEN`. No code fixing is permitted before baseline review.

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
