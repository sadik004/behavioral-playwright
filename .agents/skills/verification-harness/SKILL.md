---
name: verification-harness
description: Independent external verification, runtime provenance, cryptographic artifact sealing, fail-closed gate architecture, and adversarial testing for web automation, behavioral Playwright, and mission-critical backend systems.
---

# Independent Verification Harness & Runtime Provenance Codex

> **Core Philosophy:** "জিরো ফ্রড ইঞ্জিনিয়ারিং" (Zero-Fraud Engineering) & "জিরো তেলবাজি" (Radical Anti-Sycophancy).  
> **Primary Rule:** Never trust in-memory state or green test tallies without physical, cryptographic, and out-of-process OS runtime proof.

---

## 🏛️ The 20 Zero-Fraud Engineering Invariants (Binding Law)

The verification harness is an unyielding, non-sycophantic quality barrier. It evaluates mathematical and runtime truth, completely independent of whether existing tests pass.

1. **Zero Monolithic Code Slop**: No monolithic multi-thousand-line files with untyped dict returns escaping the API boundary.
2. **Untrusted Existing Test Assumption**: Existing tests are evidence only. Passing existing tests does NOT grant a release pass.
3. **Falsification Over Confirmation**: Every claim must have an adversarial test designed to disprove it.
4. **Dry-Run Never Counts as Live Success**: A dry-run or static script generation must NEVER return `status: "success"` or register as `REAL_SUCCESS`.
5. **Swallowed Exceptions Never Count as Success**: Any silent catch (`except Exception: pass`) or fallback returning dummy success is classified as P0 fraud.
6. **Explicit Gating for Absent Providers**: Missing dependencies (`patchright`, `browser-use`) must raise `ProviderUnavailableError` or return `PROVIDER_UNAVAILABLE`, never fabricate success or dummy responses.
7. **Strict RNG Determinism**: Any method accepting `seed: int` must deterministically control all internal stochastic processes using isolated instances (`random.Random(traj_seed)`), never leaking to or from global state.
8. **No Metric Impersonation**: Brier score is not ECE; static string generation is not runtime DOM evasion; synthetic simulated packets are not physical PCIe DMA events.
9. **Mutation Score Hurdle**: The test suite must achieve $\ge 85\%$ kill rate against in-memory adversarial mutations before production approval.
10. **Zero Raw SQL / In-Memory O(1) Lookups**: In-memory lookups must be strictly $O(1)$ (`dict`/`set`); zero quadratic scans.
11. **Non-Destructive Observability**: Sniffers and metrics collectors must never alter intercepted response streams or introduce memory leaks.
12. **Double-Entry Auditing for State**: State storage must record timestamps, depths, and statuses without mutating historical audit records.
13. **Mandatory Terminal Verification**: Every gate run must execute cleanly from the terminal and output unambiguous metrics (exit code 0).
14. **Phased Lifecycle**: The repository must follow `RED -> REVIEW -> LOCK -> FIX -> GREEN`. No code fixing is permitted before baseline review.
15. **Decoupled Out-of-Process External Verification**: In-memory verification is untrusted; final release verification must execute via isolated OS subprocess pipes (`IndependentExternalVerifier`) to protect against single-process memory patching.
16. **Live Physical OS & Artifact Hashing**: Claims of browser execution require verified live OS PIDs (`OpenProcess`/`os.kill`) in the OS process table and live filesystem SHA-256 byte recalculation of all generated artifacts.
17. **Cryptographic HMAC Provenance Chains**: Observation bundles must be sealed at capture time with HMAC-SHA256 signatures binding execution IDs, session IDs, PIDs, and artifact hashes. Any subsequent mutation invalidates the seal.
18. **Anti-Replay Nonce & Freshness Boundaries**: Previously verified evidence tokens cannot be replayed across runs; evidence must enforce strict timestamp freshness ($\Delta t < 60\text{s}$), out-of-process replay registries, and future-timestamp rejection.
19. **Strict Prohibition of Arbitrary Sleeps**: `time.sleep`, `asyncio.sleep` with magic numbers, and `page.wait_for_timeout` are strictly banned; dynamic DOM mutation checks and event listeners are mandatory.
20. **Zero Tautological Tests & Environment-Aware Provider Assertions**: Tautologies like `assert True` are classified as P0 fraud; optional modular providers must verify dynamic environment availability (`is Provider().is_available()`).

---

## 🔬 Core Architectural Pillars

### 1. Physical Reality Principle vs The Mocking Trap (The "Ghost Browser" Fallacy)
- **The Vulnerability**: Automated tests that evaluate mock `Page` or `BrowserContext` objects without touching the real operating system or Chromium DevTools Protocol (CDP) socket create an illusion of correctness. A simulator or flawed test can return `{"status": "success", "navigated": True}` while no browser ever spawned.
- **Enforcement**: Claims of `REAL_SUCCESS` must be physically and externally observable:
  1. **OS Process Liveliness**: Checking low-level OS kernel process tables (`ctypes.windll.kernel32.OpenProcess` on Windows or `os.kill(pid, 0)` on POSIX) to prove the browser PID is genuinely alive in the OS process tree.
  2. **Live Byte-Level Artifact Hashing**: Re-reading generated artifact files (PNG screenshots, HAR traces) directly from the filesystem and recalculating their `hashlib.sha256` digest on the fly.
  3. **Observable DOM Transitions**: Verifying live DOM mutations and state transitions via CDP event streams rather than relying on unverified metadata dicts.

### 2. Strict Prohibition of Arbitrary Sleeps (`time.sleep` / `wait_for_timeout`)
- **The Vulnerability**: Using hardcoded pauses (`time.sleep(2)`, `page.wait_for_timeout(3000)`) masks race conditions, inflates execution duration, and fails under unpredictable CI CPU throttling.
- **Enforcement**: Arbitrary sleeps with magic numbers are permanently banned. Automation must strictly utilize dynamic condition polling, Playwright auto-waiting assertions (`expect(locator).to_have_text(...)`), and custom DOM MutationObserver callbacks.

### 3. Isolated PRNG Engines for Deterministic Replay
- **The Vulnerability**: Relying on Python's global `random.random()` or `random.seed()` in behavioral trajectory generators (e.g. Bézier curve mouse saccades, keystroke cadence) causes severe cross-task/cross-thread state leakage. Trajectories cannot be replayed during forensic investigations.
- **Enforcement**: Any behavioral simulator accepting a seed must instantiate an isolated generator instance:
  ```python
  rng = random.Random(traj_seed)
  ```
  derived deterministically from the seed and input vectors. Global PRNG mutation must have strictly 0 impact on generated paths.

### 4. Decoupled Out-of-Process Trust Boundary (`IndependentExternalVerifier`)
- **The Vulnerability**: When the probe (`TrustedRuntimeProbe`), the oracle (`IndependentOracle`), and the release gate (`MasterGate`) execute within the same Python memory space, an adversarial payload or compromised probe can monkey-patch `unittest.mock`, overwrite in-memory variables, or bypass HMAC verification functions.
- **Enforcement**: Final verification must execute out-of-process via an isolated OS subprocess pipe:
  ```python
  result = IndependentExternalVerifier.run_in_subprocess(serialized_evidence)
  ```
  The subprocess reads untrusted serialized input from stdin, independently performs HMAC-SHA256 signature verification, checks the OS process table, inspects on-disk artifact bytes, and returns a verified/tampered boolean exit code.

### 5. Cryptographic Provenance Chains & Artifact Sealing
- **The Vulnerability**: Modifying evidence fields or swapping screenshot artifacts *after* test execution allows compromised runners to present stale or forged evidence bundles.
- **Enforcement**: Evidence contracts must be cryptographically sealed at the exact instant of browser observation. The bundle must contain an HMAC-SHA256 signature computed using a dedicated runtime secret across `(execution_id, session_id, browser_pid, artifact_hashes, timestamp)`. Any byte mutation to the contract or the on-disk artifact immediately invalidates the signature.

### 6. Anti-Replay Tokens & Freshness Boundaries
- **The Vulnerability**: An attacker or failing worker replaying a previously signed, valid evidence bundle to falsely pass subsequent test runs or sessions.
- **Enforcement**: Every evidence contract must feature a strictly unique `execution_id` and `session_id`. Verifiers must maintain an out-of-process consumed token registry that rejects previously observed IDs (`REPLAY_DETECTED`). Timestamps must strictly obey temporal freshness boundaries ($\Delta t < 60\text{s}$, with future timestamp rejection).

### 7. Environment-Aware Provider Matrices (Zero Tautological / Fragile Tests)
- **The Vulnerability**: Statically hardcoding `assert matrix['patchright'].installed is True` fails in environments without optional native binaries. Conversely, writing `assert True` (P0 WEAK-TEST) creates a meaningless tautology that hides interface regressions.
- **Enforcement**:
  1. Never write tautological assertions (`assert True`). Assert concrete interfaces, callable signatures, and exported symbol namespaces.
  2. For modular optional providers, test dynamic capability detection (`assert matrix[name].installed is Provider().is_available()`) rather than making static, unverified assumptions about the host environment.

---

## 🛠️ Verification Commands & Quality Gates

Run these gates sequentially; if any stage fails, halt immediately and perform Root Cause Analysis (RCA):

```bash
# 1. Independent Static AST Integrity Audit (Zero P0 violations)
python harness/static_integrity.py

# 2. Existing Test Suite (Untrusted baseline check)
pytest tests/ -v

# 3. Independent Integrity & Adversarial Battery (100% Pass)
pytest tests/integrity/ -v

# 4. Mutation Testing Scorecard (100% Mutant Kill Rate)
python harness/mutation.py

# 5. Master Integrity Release Gate (Exit Code 0 Required)
python harness/gate.py
```
