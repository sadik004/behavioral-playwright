# Functional Validation & Real Observable Behavior Audit

**Date**: 2026-10-05T01:48:00+06:00  
**Repository**: `sadik004/behavioral-playwright`  
**Validation Suite**: `tests/functional/`  
**Overall Status**: **RED** (Functional defects independently discovered and confirmed)

---

## 1. Feature Verification Matrix

| # | Feature Domain | Public Entry Point | Required Inputs | Observable Expected Output | Tested Locally | Real Runtime Required | Status |
|---|---|---|---|---|---|---|---|
| 1 | **Browser/Context Lifecycle** | `BrowserSession`, `BP.boot()`, `BP.close()` | `BrowserConfig` | Browser process launches, context created, clean shutdown | Yes | Yes (Playwright Chromium) | **PASS** / **DEFECT** (Multi-page clobber) |
| 2 | **Navigation** | `bp.open()`, `bp.page.goto()` | URL string | Target page loads, URL updates, title verified, state tracked | Yes | Yes | **PASS** |
| 3 | **Selector Resolution (L1)** | `SelfHealingResolver.resolve()` | CSS selector, Page | `ResolutionResult` with `strategy=L1_EXACT`, `confidence=1.0` | Yes | Yes | **PASS** |
| 4 | **Semantic Selectors (L2)** | `SelfHealingResolver.resolve()` | Role / aria-label / accessible text | `ResolutionResult` with `strategy=L2_SEMANTIC`, `confidence>=0.7` | Yes | Yes | **PASS** |
| 5 | **Fuzzy Selectors (L3)** | `SelfHealingResolver.resolve()` | Approximated title / text | `ResolutionResult` with `strategy=L3_FUZZY`, `confidence>=0.6` | Yes | Yes | **PASS** |
| 6 | **Click Automation** | `bp.click()`, `page.mouse.click()` | Selector or (x, y) coordinates | Browser DOM onclick event executes, DOM state mutates | Yes | Yes | **PASS** |
| 7 | **Type / Input Automation** | `bp.type()`, `bp.fill()` | Selector, text string | DOM input element `value` attribute reflects typed text | Yes | Yes | **PASS** / **DEFECT** (Generic tag fallback) |
| 8 | **Scroll Automation** | `page.scroll.down()`, `to_top()` | Distance in px, smooth boolean | `window.scrollY` viewport position changes | Yes | Yes | **PASS** |
| 9 | **Wait / Retry Resilience** | `RetryPolicy.execute()` | Async coroutine callable | Retries transient failures with backoff, returns result | Yes | No (Injectable clock/mock) | **PASS** |
| 10 | **Extraction Pipeline** | `DOMExtractor`, `extract_json_ld`, `extract_open_graph` | Page / HTML string | Unpacked structured records, JSON-LD @graph flattened | Yes | Yes | **PASS** |
| 11 | **Storage & Serialization** | `DataStorageManager.export()` | Records sequence, target file path | Target file created on disk, byte-for-byte readable | Yes | No | **PASS** |
| 12 | **Provider Lifecycle** | `provider_matrix()`, `create_browser_provider()` | Provider name string | Truthful installed state; `ProviderUnavailableError` on uninstalled | Yes | No | **PASS** |
| 13 | **Error Propagation** | `ElementResolutionError`, `NavigationError`, `CircuitBreakerError` | Invalid selectors, URLs, trips | Explicit typed exceptions raised, zero silent suppression | Yes | Yes | **PASS** |
| 14 | **Self-Healing Recovery** | `page.click_healed()`, `page.type_healed()` | Mutated/broken target identifier | Cascades to semantic/fuzzy match, executes action on element | Yes | Yes | **PASS** |
| 15 | **MCP Server / Tools** | `McpToolDispatcher.execute_tool()` | Tool name, argument dict | Executes real browser action (e.g. screenshot base64 PNG) | Yes | Yes | **PASS** |
| 16 | **End-to-End Scenarios** | Full framework workflow | E-commerce / Catalog application | Form input -> search -> click cart -> state mutation -> export | Yes | Yes | **PASS** |

---

## 2. Test Execution Summary

- **Total Functional Tests Executed**: 39
- **Passed**: 37 (94.9%)
- **Failed**: 2 (5.1% — Confirmed production defects)
- **Blocked**: 0
- **Skipped**: 0
- **Real Browser Runtime Tests**: 27 tests executed against headless Chromium via Playwright.
- **End-to-End Tests**: 5 complete scenarios (A, B, C, D, E) executed.

---

## 3. Environment & Runtime Infrastructure

- **Operating System**: Windows 10 / 11 (64-bit)
- **Python Version**: 3.14.0
- **Real Installed Browser**: Playwright Chromium (Headless mode)
- **Pytest Version**: 9.1.1 (`pytest-asyncio` 1.4.0, `anyio` 4.11.0)
- **Mocking Policy**: Zero browser mocking for functional tests. All page interactions execute in genuine Chromium contexts.

---

## 4. Confirmed Production Defects Discovered

### Defect 1: Multi-Page Session State Clobbering in `PlaywrightProvider` & `PageSession`
- **Failing Test**: `tests/functional/test_lifecycle_navigation.py::test_multi_page_isolation_defect`
- **Affected Modules**:
  - `src/behavioral_playwright/browser/playwright_provider.py` (lines 127–138, 155–157)
  - `src/behavioral_playwright/page/session.py` (lines 66–76, 97–100)
- **Severity**: **HIGH** (Corrupts multi-tab / multi-page concurrency and session isolation)
- **Reproduction**:
  ```python
  async with BrowserSession() as session:
      page1 = await session.new_page()
      page2 = await session.new_page()
      await page1.goto("data:text/html,<span>Page One</span>")
      await page2.goto("data:text/html,<span>Page Two</span>")
      val1 = await page1.evaluate("() => document.querySelector('span').innerText")
      # BUG: val1 evaluates on page2 and returns "Page Two" instead of "Page One"!
  ```
- **Root Cause**:
  `PageSession` receives `self.raw_page`, but methods `PageSession.evaluate()`, `PageSession.goto()`, `PageSession.get_title()`, `PageSession.get_url()` delegate to `self.provider.evaluate()`, `self.provider.goto()`, etc.
  In `PlaywrightProvider`, the provider maintains a single `self._current_page` pointer. Spawning `page2` reassigns `self._current_page = page2`. Subsequently, any call on `page1` that delegates through `self.provider` executes against `page2`.
- **Expected Behavior**: Each `PageSession` must invoke operations directly on its dedicated `self.raw_page` (`self.raw_page.evaluate()`, `self.raw_page.goto()`), preserving multi-page isolation.
- **Actual Behavior**: `page1.evaluate()` evaluates on `page2`, completely breaking DOM isolation.

---

### Defect 2: Ambiguous Generic Tag Selector Fallback in `SelfHealingResolver`
- **Failing Test**: `tests/functional/test_interactions.py::test_type_healed_on_semantic_target`
- **Affected Module**: `src/behavioral_playwright/selectors/resolver.py` (`DOM_SNAPSHOT_SCRIPT`, lines 32–43)
- **Severity**: **HIGH** (Causes self-healing actions to silently mutate the wrong DOM element)
- **Reproduction**:
  On an HTML page with multiple `<input>` elements where the target input has no `id`, `name`, `data-testid`, or `class` (e.g. `<input placeholder="Enter your email" type="email" />` following a `<input id="username" />`):
  ```python
  res = await page.type_healed("Enter your email", "user@test.com")
  # BUG: res.success is True, but "user@test.com" was typed into the first input (#username),
  # leaving the email input empty!
  ```
- **Root Cause**:
  In `DOM_SNAPSHOT_SCRIPT`:
  ```javascript
  if (el.id) {
      sel = '#' + el.id;
  } else if (el.name) {
      sel = tag + '[name="' + el.name + '"]';
  } else if (el.getAttribute('data-testid')) {
      sel = tag + '[data-testid="' + el.getAttribute('data-testid') + '"]';
  } else if (className) {
      sel = tag + className;
  } else {
      sel = tag; // <--- BUG: generates generic "input", "button", "div"
  }
  ```
  When an element lacks ID, name, testid, or class, `sel` falls back to `tag` (`"input"`). When `resolve_and_type` invokes `page.fill(result.selector, text)`, Playwright targets the *first* matching tag on the page, filling the wrong input field.
- **Expected Behavior**: `DOM_SNAPSHOT_SCRIPT` must generate unique selectors using attributes such as `placeholder`, `aria-label`, `type`, or positional CSS locators (`:nth-of-type`) so that resolved actions execute on the intended element.
- **Actual Behavior**: The resolver successfully matches the element semantically, but constructs an ambiguous selector that acts on an unintended DOM node.

---

## 5. Weak / Partially Verifiable Areas

1. **Undetected-Chromedriver & Patchright Providers**: Uninstalled in this local environment; availability checks correctly gate them and raise `ProviderUnavailableError`.
2. **`PageSession.goto()` Signature Inconsistency**: `PlaywrightProvider.goto()` accepts `timeout_ms`, but `PageSession.goto()` does not take `timeout_ms`, creating a signature mismatch for callers expecting timeout overrides.

---

## 6. Functional Validation Status Verdict

**Status**: **RED**

**Rationale**: While 37 of 39 tests pass across all 16 domains and all 5 end-to-end scenarios succeed, two high-severity functional bugs were discovered in real runtime execution:
1. Multi-page concurrent sessions on the same provider clobber each other's target page.
2. Self-healing on inputs without ID/class generates ambiguous tag-level selectors that mutate the wrong form inputs.

Per instructions, **no production code changes have been made in this phase**. Both defects are reported above with reproduction scripts, root cause analysis, and failing test cases.
