# Namespace Consolidation & Root-Cause Elimination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate `src/behavioral_playwright` as the single canonical package, eliminate the dual-namespace circular import loop between `veil` and `behavioral_playwright`, remove fatal fallback in `facade.py`, enforce typing compliance across `behavioral_evasion_suite`, and purge lockdown locks.

**Architecture:** Relocate all genuine implementation modules from `src/veil/` into `src/behavioral_playwright/`, replacing internal `veil` references with self-contained `behavioral_playwright` imports. Provide a lightweight backward-compatible stub in `src/veil/` that directs to `behavioral_playwright` without cyclic dependencies. Eliminate `BrowserSession, PageSession = Any, Any` fallback in `facade.py` in favor of explicit typed imports, expose `bp.boot()` factory, add `from __future__ import annotations` across `behavioral_evasion_suite/`, and add Pydantic v1/v2 compatibility shims.

**Tech Stack:** Python 3.10+, Playwright, NumPy, SciPy, Pydantic (v1/v2 dual compatibility), pytest.

**Spec:** Direct user prompt: `MISSION: REFACTOR & ROOT-CAUSE ELIMINATION FOR behavioral-playwright`.

## Global Constraints
- NO MOCKING / NO DUMMIES: forbidden from using `unittest.mock.MagicMock`, dummy stubs, empty functions with `pass`, or returning hardcoded fake values to satisfy tests.
- NO SILENT EXCEPTION SWALLOWING: NEVER write bare `try ... except: pass` or catch `Exception` just to bypass import crashes. Real objects must be imported and instantiated.
- NO MONKEY-PATCHING: Do NOT use `sys.modules[__name__] = ...` dynamic re-export hacks or runtime monkey patches in the canonical `behavioral_playwright` codebase.
- MATHEMATICAL INTEGRITY: You MUST NOT touch or alter the core biometric mathematical algorithms (`biometric_bench.py`, Costello saccadic velocity models, Dhakal typing distribution, Weibull timers). They must execute with real numpy/scipy operations.
- ATOMIC REFACTORING ONLY: All files must retain valid, functional Python syntax and pass AST parsing.

## Review Focus
1. Circular import recursion between `src/veil` and `src/behavioral_playwright` eliminated at the package root level.
2. `behavioral_playwright.boot()` and `BP().boot()` instantiate valid `BrowserSession` objects without raising `TypeError`.
3. Biometric benchmarking passes 5/5 without synthetic overrides.
4. Legacy tests expecting backward-compatible `veil` imports succeed through clean alias stubs.
5. All 209 unit tests and full test suites pass with exit code 0.

---

### Task 1: Purge Lockdown Artifacts
- **Files:**
  - Delete: `LOCK.json`
- **Steps:**
  - [ ] Delete `LOCK.json` from the repository root.
  - [ ] Verify that `lock_and_guard_harness.py` and test runners operate cleanly in legacy/unlocked mode.

### Task 2: Consolidate Canonical Implementation into `src/behavioral_playwright/`
- **Files:**
  - Modify/Move: All 184 files from `src/veil/` into `src/behavioral_playwright/`.
  - Modify: All imports in `src/behavioral_playwright/` to reference `behavioral_playwright` instead of `veil`.
- **Steps:**
  - [ ] Copy all genuine implementation files from `src/veil/` to `src/behavioral_playwright/`, replacing the forwarding shims.
  - [ ] Perform a global AST-safe refactoring of import statements across all files in `src/behavioral_playwright/`:
        - Replace `from veil.` with `from behavioral_playwright.`
        - Replace `import veil.` with `import behavioral_playwright.`
        - Replace `import veil` with `import behavioral_playwright`
  - [ ] Verify using Python script that zero references to `veil` remain in `src/behavioral_playwright/`.
  - [ ] Verify all Python files in `src/behavioral_playwright/` pass `ast.parse` without SyntaxError.

### Task 3: Establish Clean Backward-Compatibility Stub in `src/veil/`
- **Files:**
  - Modify: `src/veil/__init__.py` and leaf submodule stubs in `src/veil/`.
- **Steps:**
  - [ ] Configure `src/veil/__init__.py` to re-export all public symbols from `behavioral_playwright`.
  - [ ] Create clean leaf module stubs in `src/veil/` so that tests checking `test_leaf_submodule_identity_parity` and legacy imports (`from veil.facade import BP`, etc.) resolve directly to `behavioral_playwright` modules.
  - [ ] Ensure that `behavioral_playwright` has NO dependence on `src/veil/`, guaranteeing an acyclic import hierarchy.

### Task 4: Fix `facade.py` Session Instantiation & Public Boot Factory
- **Files:**
  - Modify: `src/behavioral_playwright/facade.py`
  - Modify: `src/behavioral_playwright/__init__.py`
- **Steps:**
  - [ ] In `src/behavioral_playwright/facade.py`, remove the fallback `BrowserSession, PageSession = Any, Any`.
  - [ ] Directly import `BrowserSession` and `PageSession` from `behavioral_playwright.page.session`.
  - [ ] Directly import `AutomationConfig`, `ExtractionRecord`, `ProviderUnavailableError`, `CrawlingService`, `DocumentNamespace`, `BrowserActionNamespace`, `ObservabilityMetrics`, `IntegrationExtensions`.
  - [ ] In `src/behavioral_playwright/__init__.py`, define top-level `boot(...)` factory function:
        ```python
        def boot(config: Optional[AutomationConfig] = None, provider: Optional[Any] = None, **kwargs: Any) -> BrowserSession:
            return BrowserSession(config=config, provider=provider, **kwargs)
        ```
  - [ ] Test `python -c "import behavioral_playwright as bp; session = bp.boot(); print('BOOT SUCCESS:', type(session))"`.

### Task 5: Global Typing Compliance for `behavioral_evasion_suite`
- **Files:**
  - Modify: All 47 Python files under `behavioral_evasion_suite/`
- **Steps:**
  - [ ] Add `from __future__ import annotations` to the top of all `.py` files in `behavioral_evasion_suite/`.
  - [ ] Ensure `from typing import Tuple, List, Dict, Optional, Any, Callable, Set, Union` are imported where type annotations use them (e.g. in `keystroke_engine.py`, `mouse_physics.py`).
  - [ ] Verify all files pass AST compilation and syntax checks.

### Task 6: Pydantic v1/v2 Compatibility Shim
- **Files:**
  - Modify: `src/behavioral_playwright/models/results.py`
  - Modify: `src/behavioral_playwright/models/seo_dtos.py`
- **Steps:**
  - [ ] Wrap `field_validator` import with fallback to `from pydantic import validator as field_validator` for dual v1/v2 compatibility.
  - [ ] Ensure model serialization and validation works under both Pydantic v1 and v2.

### Task 7: Comprehensive Verification & Quality Gates
- **Steps:**
  - [ ] Run `python biometric_bench.py` and confirm 5/5 passes.
  - [ ] Run `python -c "import behavioral_playwright as bp; session = bp.boot(); print('BOOT SUCCESS:', type(session))"`.
  - [ ] Run `python -m pytest tests/unit/ -v --maxfail=5` and confirm 100% pass rate.
  - [ ] Run `python -m pytest tests/ -v --maxfail=10` and confirm full suite integrity.

