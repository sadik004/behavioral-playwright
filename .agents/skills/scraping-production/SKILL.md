---
name: scraping-production
description: Master skill for production-grade scraping and browser automation codified directly from the behavioral-playwright architecture audit. Enforces the 50 Master Guardrails, core agent directives, concrete verified good patterns, and strictly forbidden bad patterns.
---

# Scraping & Automation Production Engineering Codex

This skill codifies the architectural rules, verified engineering patterns, and strictly forbidden anti-patterns extracted directly from the baseline audit of the `behavioral-playwright` codebase. All web scraping, Playwright automation, crawler, and data pipeline tasks must adhere to these directives.

---

## 1. Core Agent Directives (90-Day Standard Invariants)

1. **The 2-Strike Debugging & RCA Escalation Rule**:
   - If a test, selector, or terminal command fails twice on the same target, STOP immediately.
   - Do NOT execute repeated blind guesses or iterate endlessly.
   - Capture a DOM snapshot (`forensics/dom_dump.html`) and screenshot (`forensics/error.png`), perform root-cause analysis (RCA), log the finding, and implement an architecturally sound fix.
2. **Zero Stubs, Placeholders, or TODO Slop**:
   - Strictly no `# TODO: implement rest`, `# FIXME`, or `pass` in production scraping paths.
   - Every function, locator cascade, error handler, and extractor must be fully realized, typed, and executable.
3. **Radical Anti-Sycophancy ("জিরো তেলবাজি" পলিসি)**:
   - Deliver strictly objective, mathematically grounded engineering facts.
   - Flattery, emotional theatrics, or agreeing with flawed premises out of polite deference is strictly prohibited. If a site cannot be reliably scraped with static headless mode due to hardware attestation, state the technical reality directly.
4. **Mandatory Terminal Verification Gate**:
   - Never declare work completed based on code generation alone.
   - Execute the crawler script or test suite via the terminal and verify clean exit code 0 before concluding.
5. **Engineering Honesty & Zero Fabricated Fallbacks**:
   - If an optional provider (e.g. `Patchright`, `CurlImpersonate`, `UndetectedChromedriver`) is not installed, raise an explicit, machine-detectable `ProviderUnavailableError`. Never fabricate fake data or pretend a driver is active when it is absent.
6. **Plan-First Workflow**:
   - Before executing multi-file modifications or introducing new modules, outline the exact dependency flow, component responsibilities, and test plan.

---

## 2. Verified Good Patterns (Extracted from Codebase Audit)

### Good Pattern 1: 3-Tier Cascading Self-Healing Element Resolution
* **Source Reference**: [`src/behavioral_playwright/selectors/resolver.py:134-210`](file:///e:/Behavioural/src/behavioral_playwright/selectors/resolver.py#L134-L210)
* **Design Excellence**: Combines fast-path exact CSS matching with progressive heuristic self-healing (Semantic ARIA $\to$ Fuzzy Levenshtein Distance). Captures live DOM candidates into structured `DOMElement` instances with bounding box geometries.

```python
# Extracted from src/behavioral_playwright/selectors/resolver.py
async def resolve(self, page: Any, target: str) -> ResolutionResult:
    start_time = time.time()

    # Tier 1: Exact CSS / DOM Selector Match (Fast-Path)
    if "L1_EXACT" in self.config.strategies:
        try:
            exact_matches = await page.query_selector_all(target)
            if exact_matches and len(exact_matches) > 0:
                elapsed_ms = (time.time() - start_time) * 1000.0
                return ResolutionResult(
                    success=True,
                    strategy=ResolutionStrategy.L1_EXACT,
                    confidence=1.0,
                    selector=target,
                    element_count=len(exact_matches),
                    reason=f"L1 Exact selector matched {len(exact_matches)} element(s)",
                    target=target,
                    elapsed_ms=elapsed_ms
                )
        except Exception:
            pass  # Cascade to self-healing

    # Tier 2: Semantic & Accessibility Recovery (ARIA, text, labels)
    candidates = await self.get_dom_candidates(page)
    if "L2_SEMANTIC" in self.config.strategies and candidates:
        semantic_res = await self.semantic_strategy.resolve(page, target, candidates)
        if semantic_res and semantic_res.confidence >= self.config.confidence_threshold:
            semantic_res.elapsed_ms = (time.time() - start_time) * 1000.0
            return semantic_res

    # Tier 3: Fuzzy Levenshtein Similarity Recovery
    if "L3_FUZZY" in self.config.strategies and candidates:
        fuzzy_res = await self.fuzzy_strategy.resolve(page, target, candidates)
        if fuzzy_res and fuzzy_res.confidence >= self.config.fuzzy_similarity_threshold:
            fuzzy_res.elapsed_ms = (time.time() - start_time) * 1000.0
            return fuzzy_res

    return ResolutionResult(
        success=False,
        strategy=ResolutionStrategy.L1_EXACT,
        confidence=0.0,
        selector=None,
        element_count=0,
        reason=f"All resolution strategies exhausted for target '{target}'",
        target=target,
        elapsed_ms=(time.time() - start_time) * 1000.0
    )
```

---

### Good Pattern 2: Finite State Machine Circuit Breaker for Target Isolation
* **Source Reference**: [`src/behavioral_playwright/resilience/circuit_breaker.py:23-105`](file:///e:/Behavioural/src/behavioral_playwright/resilience/circuit_breaker.py#L23-L105)
* **Design Excellence**: Prevents proxy burning, server hammering, and cascading worker failures during target outages using a 3-state FSM (`CLOSED`, `OPEN`, `HALF_OPEN`). Features an injectable clock function for deterministic $\mathcal{O}(1)$ testing without sleeping.

```python
# Extracted from src/behavioral_playwright/resilience/circuit_breaker.py
class CircuitBreaker:
    def __init__(self, config=None, clock_fn=None) -> None:
        self.config = config or CircuitBreakerConfig()
        self._clock_fn = clock_fn or time.time
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_state_change = self._clock_fn()

    @property
    def state(self) -> CircuitState:
        current_time = self._clock_fn()
        if self._state == CircuitState.OPEN:
            elapsed = current_time - self._last_state_change
            if elapsed >= self.config.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    async def execute(self, coro_fn: Callable[[], Coroutine[Any, Any, T]], operation_name="op") -> T:
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(f"CircuitBreaker is OPEN for {operation_name}. Fast failing.")
        try:
            result = await coro_fn()
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise
```

---

### Good Pattern 3: Capability Detection & Explicit Provider Gating
* **Source Reference**: [`src/behavioral_playwright/providers/base.py:25-65`](file:///e:/Behavioural/src/behavioral_playwright/providers/base.py#L25-L65)
* **Design Excellence**: Adheres to the Engineering Honesty invariant. External automation drivers (`Patchright`, `BrowserUse`, `CurlImpersonate`) are probed dynamically. If a third-party library is absent, it raises `ProviderUnavailableError` rather than silently fabricating mock results.

```python
# Extracted from src/behavioral_playwright/providers/base.py
class ProviderUnavailableError(RuntimeError):
    """Raised when a selected provider's backing library is not importable."""
    def __init__(self, provider: str, module: str, install_hint: str) -> None:
        super().__init__(
            f"{provider} provider is UNAVAILABLE: module {module!r} cannot be "
            f"imported. Optional install: {install_hint}. "
            "No fallback or fabricated behavior is provided."
        )

def detect_provider(provider: str, module: str) -> ProviderInfo:
    try:
        mod = importlib.import_module(module)
        version = getattr(mod, "__version__", None)
        return ProviderInfo(provider=provider, module=module, installed=True, version=version)
    except Exception as exc:
        return ProviderInfo(provider=provider, module=module, installed=False, error=str(exc))
```

---

### Good Pattern 4: SQLite-Backed Atomic Crawl Session State
* **Source Reference**: [`src/behavioral_playwright/crawling/service.py:47-75`](file:///e:/Behavioural/src/behavioral_playwright/crawling/service.py#L47-L75)
* **Design Excellence**: Crawl state is persisted in an embedded SQLite database (`crawl_urls`), ensuring that interrupted scrapes can recover from disk without re-scraping visited URLs or duplicating records. Guaranteed connection closing in `finally:`.

```python
# Extracted from src/behavioral_playwright/crawling/service.py
def save_crawl_state(self, db_path: str, url: str, status: str = "completed", depth: int = 0) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO crawl_urls (url, depth, status, timestamp) "
            "VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (url, depth, status)
        )
        conn.commit()
    finally:
        conn.close()
```

---

## 3. Identified Bad Patterns & Prohibited Anti-Patterns

### Bad Pattern 1: Ephemeral Browser Spawning Anti-Pattern
* **Violation Location**: [`antiscraper.py:96-104, 151`](file:///e:/Behavioural/antiscraper.py#L96-L104)
* **Anti-Pattern Code**:
  ```python
  # DISASTER: Spawning an entire OS Chromium process per scrape invocation
  async def scrape(self, url: str, ...):
      pw, context, page, profile_dir = await self._launch()
      # Launches pw.chromium.launch_persistent_context(...)
  ```
* **Why It Is Prohibited**: Spawning an OS Chromium process takes 2,000ms+ and consumes 150MB+ RAM per scrape. Under concurrent load, this spawns dozens of processes, thrashing CPU and causing OOM process crashes.
* **Mandated Remedy**: Launch a single master browser process and pool lightweight `BrowserContext` instances via `BrowserPoolManager`.

---

### Bad Pattern 2: Synchronous Event Loop Blocking Sleep
* **Violation Location**: [`src/behavioral_playwright/_legacy_facade12.py:600`](file:///e:/Behavioural/src/behavioral_playwright/_legacy_facade12.py#L600)
* **Anti-Pattern Code**:
  ```python
  # DISASTER: Synchronous sleep in an async engine!
  time.sleep(sleep_time)
  ```
* **Why It Is Prohibited**: Calling synchronous `time.sleep()` freezes the single-threaded asyncio event loop for all concurrent scrapers and background tasks.
* **Mandated Remedy**: Always use non-blocking `await asyncio.sleep(delay)` or eliminate sleeps entirely by awaiting DOM state transitions (`wait_for_selector`).

---

### Bad Pattern 3: Static Magic Delays & Arbitrary Sleep Loops
* **Violation Location**: [`antiscraper.py:135, 160, 171`](file:///e:/Behavioural/antiscraper.py#L135)
* **Anti-Pattern Code**:
  ```python
  # DISASTER: Static magic delays
  await page.keyboard.press("Enter")
  await asyncio.sleep(5)  # Blind 5-second sleep!
  ```
* **Why It Is Prohibited**: Static magic delays violate Guardrail 21. If the server responds in 400ms, 4600ms of compute time is wasted; if the server takes 5100ms, the scraper crashes with a false negative.
* **Mandated Remedy**: Wait for dynamic DOM state (`page.locator('.results').wait_for(state='visible')`) or network responses (`page.expect_response(...)`).

---

### Bad Pattern 4: Silent Exception Swallowing
* **Violation Location**: [`antiscraper.py:112-115, 132-133, 194-196`](file:///e:/Behavioural/antiscraper.py#L112-L115)
* **Anti-Pattern Code**:
  ```python
  # DISASTER: Swallowing exceptions silently
  try:
      await page.bring_to_front()
  except Exception:
      pass

  except Exception as e:
      logger.error(f"[!] Scrape error: {e}", exc_info=True)
  return results  # Returns empty results list as if scrape succeeded!
  ```
* **Why It Is Prohibited**: Violates Guardrail 11. Swallowing errors disguises fatal selector, authentication, or network failures as "empty pages," corrupting analytics and hiding production bugs.
* **Mandated Remedy**: Propagate typed domain exceptions (`ExtractionError`, `NavigationError`) or log forensic diagnostics before re-raising.

---

### Bad Pattern 5: Loose Substring Class Selectors
* **Violation Location**: [`antiscraper.py:218`](file:///e:/Behavioural/antiscraper.py#L218)
* **Anti-Pattern Code**:
  ```javascript
  // DISASTER: Loose substring matching
  const cards = document.querySelectorAll('.cus-col, .product-box, .product-card, .grid-item, div.card, div[class*="col-"]');
  ```
* **Why It Is Prohibited**: `div[class*="col-"]` matches structural Bootstrap/Tailwind columns across headers, navigation sidebars, and footers, extracting garbage data into the output stream.
* **Mandated Remedy**: Anchor locators to semantic cards (`article.product-card`) or test IDs (`[data-testid="product-card"]`).

---

### Bad Pattern 6: Untyped Data Models & Missing Schema Validation Boundary
* **Violation Location**: [`src/behavioral_playwright/models/results.py:39-45`](file:///e:/Behavioural/src/behavioral_playwright/models/results.py#L39-L45), [`antiscraper.py:147`](file:///e:/Behavioural/antiscraper.py#L147)
* **Anti-Pattern Code**:
  ```python
  # DISASTER: Untyped dataclass accepting raw arbitrary dictionaries
  @dataclass
  class ExtractionRecord:
      text: str
      href: Optional[str] = None
      attributes: Dict[str, Any] = field(default_factory=dict)
      metadata: Dict[str, Any] = field(default_factory=dict)
  ```
* **Why It Is Prohibited**: Raw extracted attributes are not validated, leaving downstream consumers vulnerable to missing fields, string-casted numbers, and corrupted data shapes.
* **Mandated Remedy**: Wrap all scraped entities in strict Pydantic models (`ProductExtractionDTO`) with `@field_validator` data normalizers.

---

### Bad Pattern 7: Suppressed Static Typing in Project Configuration
* **Violation Location**: [`pyproject.toml:50-60`](file:///e:/Behavioural/pyproject.toml#L50-L60)
* **Anti-Pattern Code**:
  ```toml
  # DISASTER: Disabling static type checking
  check_untyped_defs = false
  disallow_untyped_defs = false
  warn_redundant_casts = false
  warn_unused_ignores = false
  ```
* **Why It Is Prohibited**: Suppressing `mypy` type checks allows `NoneType` attribute crashes, invalid arguments, and broken signatures to evade CI detection.
* **Mandated Remedy**: Enforce `mypy --strict` with `disallow_untyped_defs = true`.
