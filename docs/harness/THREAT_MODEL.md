# Adversarial Threat Model & Anti-Gaming Specification

**Repository**: `sadik004/behavioral-playwright`  
**Governance Standard**: Radical Anti-Sycophancy & Zero-Fraud Engineering  

---

## 1. The Core Threat: Self-Referential Validation Bias
When code and test suites are developed in tandem by the same engineering agent or team, tests naturally gravitate toward confirming internal implementation assumptions rather than validating operational truth.

In behavioral web automation and anti-bot evasion systems, this creates catastrophic vulnerabilities:
- An automation tool claims to bypass enterprise bot detection, but only tests that its own mock returns `True`.
- An evasion runner crashes on live Playwright execution, catches the crash, returns `{"status": "dry_run_success"}`, and the test suite passes because it checked `assert "success" in res["status"]`.
- A trajectory generator claims deterministic seed reproducibility, but calls unseeded global `random.uniform()` in its internal jitter calculations.

---

## 2. Catalog of Discovered Failure Modes & Antipatterns

### Threat 1: The Substring Assertion Trap (`assert "success" in status`)
- **Vulnerability**: Tests check whether `"success"` is a substring of the returned status string:
  ```python
  # tests/test_evasion_suite.py:75
  assert "success" in res["status"]
  ```
- **Exploitation**: The production runner (`PowerHandPlaywrightRunner.execute_stealth_session`) catches any unhandled exception or browser crash and returns:
  ```python
  # behavioral_evasion_suite/powerhand_master.py:126
  except Exception as e:
      return {"status": "dry_run_success", "error": str(e), ...}
  ```
- **Impact**: `"success"` is a substring of `"dry_run_success"`. A catastrophic browser crash that completely fails live navigation registers as a PASS in existing tests.
- **Harness Countermeasure**: The independent oracle requires exact equivalence `status == "success"` AND checks `not dry_run` AND `not simulated`.

---

### Threat 2: Silent Exception Swallowing (`except Exception: pass`)
- **Vulnerability**: 54 instances across `src/` where exceptions are caught with `pass` or returned as dummy default values (`0.0`, `None`, empty list).
  - Example: `behavioral_playwright/providers/agents.py:76` catches all exceptions during agent execution and returns `None` without logging or telemetry.
  - Example: `behavioral_playwright/storage/exporters.py` formats without propagating IO errors to callers in certain fallback modes.
- **Impact**: Downstream callers assume the operation succeeded, resulting in silent data loss or phantom sessions.
- **Harness Countermeasure**: `StaticIntegrityAuditor` flags all broad exception clauses with P0/P1 severity. Fault-injection tests inject invalid inputs and verify exceptions are raised loudly.

---

### Threat 3: Pseudo-Seeded Nondeterminism
- **Vulnerability**: An API accepts `seed: int = 42`, but internally invokes unseeded global random generators:
  ```python
  # behavioral_evasion_suite/powerhand_master.py:70-71
  # seed is accepted in signature, but tremor jitter calls:
  tremor = random.uniform(0.5, 1.5)  # Global unseeded random!
  ```
- **Impact**: Consecutive runs with identical seeds produce distinct trajectory coordinates, breaking reproducibility, debugging, and audit trails.
- **Harness Countermeasure**: `test_powerhand_saccade_path_seed_contract_falsification` tests consecutive runs under identical seeds and asserts coordinates must match within $10^{-6}$ precision.

---

### Threat 4: Monolithic Mock Tautologies
- **Vulnerability**: Tests mock the exact method being evaluated and assert that the mock returned what was mocked:
  ```python
  page.evaluate = AsyncMock(return_value={"webdriver": False})
  res = await page.evaluate("...")
  assert res["webdriver"] is False
  ```
- **Impact**: Zero verification of actual browser behavior, CDP protocol bindings, or DOM stealth patches.
- **Harness Countermeasure**: Separation of static script verification from runtime browser execution.

---

### Threat 5: Duplicate Exception Hierarchy Divergence
- **Vulnerability**: Two distinct exception classes named `ProviderUnavailableError`:
  - `src/behavioral_playwright/exceptions.py: class ProviderUnavailableError(BehavioralPlaywrightError)`
  - `src/behavioral_playwright/providers/base.py: class ProviderUnavailableError(RuntimeError)`
- **Impact**: Any user or client code catching `exceptions.BehavioralPlaywrightError` or `exceptions.ProviderUnavailableError` fails to catch exceptions raised by the provider subsystem.
- **Harness Countermeasure**: Flagged as static defect `DUPLICATE-EXC-001` and tested in independent provider integrity suite.

---

## 3. Severity Classification Matrix

| Severity | Definition | Mandatory Gate Action |
|:---|:---|:---|
| **P0 (Critical Fraud)** | Fake success, swallowed crash converted to success, hardcoded statistical claim, or security breach. | Immediate Gate FAIL. Release blocked. |
| **P1 (High Defect)** | Unseeded RNG where seed is claimed, uncaught provider exception divergence, unhandled crash, or weak assertion concealing failures. | Gate FAIL until reviewed and locked. |
| **P2 (Medium Inconsistency)** | Missing type annotations, ambiguous docstring claims, legacy deprecated aliases, or missing optional provider instructions. | Documented in audit log. |
| **P3 (Low Hygiene)** | Unused imports, whitespace formatting, or minor styling inconsistencies. | Informational. |
