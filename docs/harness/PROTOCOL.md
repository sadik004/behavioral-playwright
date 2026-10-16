# Independent Verification & Integrity Protocol

**Repository**: `sadik004/behavioral-playwright`  
**Governance Standard**: Enterprise Architectural Governance & Zero-Fraud Engineering  
**Role**: Independent Verification & Integrity Harness  

---

## 1. Executive Mission
The primary objective of this protocol is to establish an **adversarial, completely decoupled integrity verification layer** across the entire `behavioral-playwright` repository.

Existing test suites (377+ tests) were developed alongside the code by the same development process. Therefore, by directive of the Lead Architect:
**EXISTING TESTS MUST BE TREATED AS UNTRUSTED EVIDENCE.**

This verification layer exists to falsify rather than confirm, actively hunting for:
- False positives and synthetic guarantees
- Fake success (`dry_run_success` reported as live execution)
- Silent exception swallowing and unhandled fallbacks
- Weak assertions (e.g. `assert "success" in res["status"]`)
- Nondeterministic algorithms that ignore seed arguments
- Static JavaScript string presence falsely counted as runtime browser execution

---

## 2. What the Harness Verifies vs What It Does Not Verify

### A. What the Harness Verifies
1. **Failure Integrity**: When a browser crashes, a selector is missing, or a circuit breaker trips, does the system raise an explicit exception or return an unambiguous error status?
2. **Fake-Success Detection**: Does `dry_run=True` or a swallowed exception masquerade as `REAL_SUCCESS`?
3. **Determinism Contracts**: When an API accepts `seed: int`, does it strictly control all stochastic processes?
4. **Provider Gating Honesty**: Are uninstalled or missing optional dependencies (`patchright`, `undetected_chromedriver`, `browser-use`, `stagehand`) honestly reported as `PROVIDER_UNAVAILABLE`?
5. **Contract Conformance**: Do MCP JSON-RPC schemas and tool dispatchers reject invalid, missing, or malformed inputs with error status codes?
6. **Mutation Kill Rate**: Does the verification suite detect and fail when critical guards, exception propagation, or validation branches are bypassed?

### B. What the Harness Does Not Verify
1. **Third-Party Live Production Targets**: Does not perform live brute-force or destructive attacks against real-world anti-bot engines (Cloudflare, Akamai, Datadome).
2. **Proprietary Hardware Guarantees**: Does not simulate physical PCIe bus signals when PCIe Screamer FPGA hardware is physically absent (explicitly classified as `SIMULATION_ONLY`).
3. **Uninstalled Provider Functionality**: Does not test the internal driver logic of uninstalled libraries (`patchright`, `browser-use`), only their gating and error signaling contracts.

---

## 3. Independent Oracle Architecture

The oracle (`harness/oracle.py`) is completely independent from implementation internals and existing assertions. It classifies observed execution states into an 8-tier taxonomy:

```
                  Observed Runtime Result
                             |
         +-------------------+-------------------+
         |                                       |
    [Exception]                             [Payload]
         |                                       |
  Explicit Failure                          Inspect Flags
  (REAL_FAILURE)                      (dry_run, simulated, status)
                                                 |
                       +-------------------------+-------------------------+
                       |                         |                         |
                 dry_run == True           simulated == True         status == "success"
                       |                         |                         |
                   [DRY_RUN]               [SIMULATION]             [REAL_SUCCESS]
                                                              (Strictly Live Only)
```

### Strict Status Taxonomy:
1. `REAL_SUCCESS`: Verified live execution on real browser engine without simulation or fallback flags.
2. `REAL_FAILURE`: Operation raised a valid, expected exception or returned an unambiguous error status.
3. `DRY_RUN`: Safe script generation or dry-run execution. **NEVER counts as REAL_SUCCESS.**
4. `SIMULATION`: Execution emulated via memory stubs or in-silico models (e.g. PCIe DMA without hardware).
5. `PROVIDER_UNAVAILABLE`: Dependency or external engine is missing, accompanied by actionable installation instructions.
6. `UNIMPLEMENTED`: Feature stubbed or flagged as TODO.
7. `PARTIAL`: Incomplete execution or degraded feature set.
8. `UNKNOWN`: Payload does not conform to recognized status taxonomy.

---

## 4. Adversarial Testing Methodology

The adversarial suite (`tests/integrity/test_failure_integrity.py` and `test_fake_success.py`) operates via **fault injection**:
- **Target Closed / CDP Disconnect**: Simulates browser/CDP disconnection during page evaluation. Confirms exception propagates.
- **Circuit Breaker Saturation**: Trips the breaker past `failure_threshold`. Confirms `CircuitBreakerError` is raised in `OPEN` state.
- **Illegal File Path / Disk Corruption**: Injects null-byte paths into `DataStorageManager.export()`. Confirms `OSError`/`ValueError` is raised, never swallowed.
- **Missing Hardware**: Injects non-existent device paths (`/nonexistent/pcie_dma_hardware`). Confirms `bridge.is_connected is False` and payload is flagged as `SIMULATION`.

---

## 5. In-Memory Mutation Testing Methodology

The mutation engine (`harness/mutation.py`) injects controlled, reversible AST and monkeypatched mutants into runtime memory without altering repository files:
- `MUT-001`: Bypasses `CircuitBreaker` OPEN state guard.
- `MUT-002`: Bypasses `PatchrightProvider` availability check.
- `MUT-003`: Injects `"success"` on dry run in `PowerHandPlaywrightRunner`.
- `MUT-004`: Swallows export errors in `DataStorageManager.export()`.
- `MUT-005`: Injects fake success on unknown MCP tools.
- `MUT-006`: Forces `PowerHandMaster.get_saccade_path` to return empty list.
- `MUT-007`: Fabricates fixed entropy on empty HTML in `ResolvedSchemaIntegrityGuard`.
- `MUT-008`: Injects falsified oracle logic accepting dry-run as live success.

Mutation score formula:
$$\text{Mutation Score} = \left(\frac{\text{Killed Mutants}}{\text{Total Valid Mutants}}\right) \times 100\%$$

---

## 6. Runtime vs Static Verification Boundary

A core finding of this harness is the distinction between **static script presence** and **runtime browser execution**:
- Generating a JavaScript string containing `navigator.webdriver = false` or `Worker` stubs is **STATIC CODE GENERATION**.
- Injecting that script into a real Chromium/Playwright context, querying `await page.evaluate("navigator.webdriver")`, and verifying that CDP leaks do not reveal automation is **RUNTIME VERIFIED**.

Existing tests frequently tested only that `runner.get_all_stealth_scripts()` returns a long string, declaring evasion "verified". The independent harness strictly separates these categories.
