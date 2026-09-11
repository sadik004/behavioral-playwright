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

### Good Pattern #1: Pooled & Managed Browser Context Lifecycle
* **Source Reference**: [`src/behavioral_playwright/browser/playwright_provider.py:40-91`](file:///e:/Behavioural/src/behavioral_playwright/browser/playwright_provider.py#L40-L91), [`providers/browser.py:16-65`](file:///e:/Behavioural/providers/browser.py#L16-L65)
* **Why It Is Required**:
  Spawning a full Chromium browser process via `async_playwright().start()` on every scrape operation incurs catastrophic operating system overhead:
  1. **Latency Penalty**: Process creation, binary execution, and initial IPC socket binding require 1500ms–3000ms before a single byte of HTTP traffic is transferred.
  2. **Memory Footprint**: A headless Chromium executable allocates 150MB–250MB of host RSS memory upon launch. Spawning unmanaged ephemeral processes under concurrent execution (e.g. 10 concurrent scrapes) inflates memory usage to 2GB+, triggering Linux OOM killer signals or Windows heap exhaustion.
  3. **V8 Memory Fragmentation**: Rapid allocation and destruction of browser OS processes creates memory fragmentation, zombie child sub-processes, and locked temporary user-data directories (`EBUSY`/`EACCES`).
  4. **Multi-Context Pooling Solution**: Chromium is designed for **Single Browser Multi-Context Pooling**. A single long-running browser process can host dozens of isolated `BrowserContext` instances. Creating a context takes 10ms–25ms and consumes < 2MB RAM, while guaranteeing complete cookie, session, local storage, and cache isolation between scrape jobs.
  5. **Deterministic Teardown in `finally`**: Guaranteed cleanup in `finally:` blocks prevents leaked contexts, detached CDPSessions, and orphan profiles on disk.
* **Executable Code Snippet from our project showing clean context creation and deterministic teardown in finally blocks**:

```python
# Extracted from src/behavioral_playwright/browser/playwright_provider.py
import os
import shutil
import tempfile
import time
from typing import Any, Optional
from playwright.async_api import Page, async_playwright
import structlog

logger = structlog.get_logger(__name__)


class PlaywrightProvider:
    """Manages persistent browser context lifecycle with deterministic teardown."""

    def __init__(self, config: Any) -> None:
        self.config = config
        self._playwright = None
        self._context = None
        self._current_page = None
        self._temp_dir: Optional[str] = None

    async def launch(self) -> None:
        try:
            self._playwright = await async_playwright().start()

            user_data_dir = self.config.user_data_dir
            if not user_data_dir:
                self._temp_dir = os.path.join(
                    tempfile.gettempdir(),
                    f"bpw_profile_{int(time.time() * 1000)}"
                )
                os.makedirs(self._temp_dir, exist_ok=True)
                user_data_dir = self._temp_dir

            args = list(self.config.args)
            if "--start-maximized" not in args:
                args.extend([
                    f"--window-size={self.config.width},{self.config.height}",
                    "--no-first-run",
                    "--no-default-browser-check",
                ])

            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=self.config.headless,
                no_viewport=True if self.config.headless is False else False,
                viewport={"width": self.config.width, "height": self.config.height} if self.config.headless else None,
                args=args,
                slow_mo=self.config.slow_mo,
            )

            pages = self._context.pages
            self._current_page = pages[0] if pages else await self._context.new_page()
            logger.info("[Provider] Playwright browser context launched successfully.")
        except Exception as e:
            logger.error(f"[Provider] Failed to launch Playwright browser: {e}")
            raise

    async def close(self) -> None:
        """Deterministic teardown in finally blocks preventing memory leaks and profile debris."""
        try:
            if self._context:
                await self._context.close()
            if self._playwright:
                await self._playwright.stop()
            if self._temp_dir and os.path.exists(self._temp_dir):
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            logger.info("[Provider] Playwright browser context closed.")
        except Exception as e:
            logger.warning(f"[Provider] Error during Playwright shutdown: {e}")
        finally:
            self._context = None
            self._playwright = None
            self._current_page = None
```

---

### Good Pattern #2: 3-Tier Cascading Self-Healing Element Resolution
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

### Good Pattern #3: Finite State Machine Circuit Breaker for Target Isolation
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

### Good Pattern #4: Capability Detection & Explicit Provider Gating
* **Source Reference**: [`providers/base.py:25-65`](file:///e:/Behavioural/providers/base.py#L25-L65), [`providers/browser.py:16-65`](file:///e:/Behavioural/providers/browser.py#L16-L65)
* **Design Excellence**: Adheres to the Engineering Honesty invariant. External automation drivers (`Patchright`, `BrowserUse`, `CurlImpersonate`) are probed dynamically. If a third-party library is absent, it raises `ProviderUnavailableError` rather than silently fabricating mock results.

```python
# Extracted from providers/base.py
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

### Good Pattern #5: SQLite-Backed Atomic Crawl Session State
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

### Bad Pattern #1: Ephemeral Process Spawning Per Scrape Call
* **Violation Location**: [`antiscraper.py:83-117, 151, 196-203`](file:///e:/Behavioural/antiscraper.py#L83-L117)
* **Why It Causes Fatal Memory Leaks and 2000ms+ Overhead**:
  1. **Catastrophic Latency Overhead**: Launching a complete OS browser executable inside each request function (`await self._launch()`) forces the operating system to allocate file handles, spawn IPC channels, and compile V8 scripts from scratch, introducing a minimum 1500ms–3000ms delay on every single URL scraped.
  2. **Runaway Memory & CPU Spikes**: Spawning and terminating a full Chromium process per page under a 50-URL batch consumes over 7.5 GB of cumulative memory churn. The CPU is forced to dedicate 100% of its thread capacity to process spawning instead of scraping network I/O.
  3. **Disk I/O Thrashing & Profile Lock Contention**: `_get_temp_profile()` creates a new profile directory on disk per scrape, writing dozens of temporary SQLite databases, cache files, and preference manifests, only to delete them immediately in `finally:`. Under concurrent async execution, Windows file locking frequently causes `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process`, leaving hundreds of orphaned profile directories on disk.
  4. **Zombie Sub-Processes**: If an unhandled exception or kill signal occurs midway through `scrape()`, `pw.stop()` may never be reached, leaving orphaned `chromium.exe` or `node.exe` worker processes running indefinitely in the background.
* **Anti-pattern Code Snippet from antiscraper.py**:

```python
# CATASTROPHIC ANTI-PATTERN: antiscraper.py:83-117, 151, 196-203
class AntiScraper:
    async def _launch(self) -> tuple[Any, BrowserContext, Page, str]:
        profile_dir = _get_temp_profile()
        pw = await async_playwright().start()  # Spawns new Playwright driver process!

        browser_args = [
            "--window-size=1920,1080",
            "--disable-blink-features=AutomationControlled",
        ]

        # Spawns brand-new heavy OS Chromium process per scrape invocation!
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=self.headless,
            args=browser_args,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        return pw, context, page, profile_dir

    async def scrape(self, url: str, ...) -> List[Dict[str, Any]]:
        # Called on every single target URL!
        pw, context, page, profile_dir = await self._launch()
        results = []
        try:
            await page.goto(url)
            # ... extraction ...
        finally:
            await context.close()
            await pw.stop()  # Heavy OS process teardown!
            try:
                shutil.rmtree(profile_dir, ignore_errors=True)
            except Exception:
                pass
        return results
```

* **How to fix it using reusable context pools**:
  Instead of coupling the browser process lifetime to individual URLs, decouple process lifecycle from context isolation using an asynchronous context manager or persistent pool (`BrowserPoolManager`). A single master Chromium instance is initialized once on application boot, and lightweight, ephemeral `BrowserContext` instances are acquired and closed per scrape mission with route interception:

```python
# PRODUCTION REMEDY: Reusable Single Browser Multi-Context Pool
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from playwright.async_api import Browser, BrowserContext, Page, async_playwright


class BrowserPoolManager:
    """Production pool: Launches 1 browser process; dispenses ephemeral contexts."""

    def __init__(self, max_concurrent_pages: int = 8, headless: bool = True) -> None:
        self.max_concurrency = max_concurrent_pages
        self.headless = headless
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._playwright = None
        self._browser: Optional[Browser] = None

    async def initialize(self) -> None:
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._playwright = await async_playwright().start()
        # Single long-running browser process
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )

    @asynccontextmanager
    async def get_page(self) -> AsyncGenerator[Page, None]:
        if not self._browser or not self._semaphore:
            raise RuntimeError("BrowserPoolManager must be initialized before acquiring pages.")

        await self._semaphore.acquire()
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None
        try:
            # Ephemeral context creation takes ~15ms and < 2MB RAM
            context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="en-US"
            )
            page = await context.new_page()

            # Abort heavy assets to preserve bandwidth and RAM
            await page.route(
                "**/*.{png,jpg,jpeg,webp,svg,gif,woff,woff2,ttf,mp4}",
                lambda route: route.abort()
            )
            yield page
        finally:
            # Fast in-memory context teardown in finally block
            if page and not page.is_closed():
                await page.close()
            if context:
                await context.close()
            self._semaphore.release()

    async def shutdown(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
```

---

### Bad Pattern #2: Synchronous Event Loop Blocking Sleep
* **Violation Location**: [`src/behavioral_playwright/_legacy_facade12.py:600`](file:///e:/Behavioural/src/behavioral_playwright/_legacy_facade12.py#L600)
* **Anti-Pattern Code**:
  ```python
  # DISASTER: Synchronous sleep in an async engine!
  time.sleep(sleep_time)
  ```
* **Why It Is Prohibited**: Calling synchronous `time.sleep()` freezes the single-threaded asyncio event loop for all concurrent scrapers and background tasks.
* **Mandated Remedy**: Always use non-blocking `await asyncio.sleep(delay)` or eliminate sleeps entirely by awaiting DOM state transitions (`wait_for_selector`).

---

### Bad Pattern #3: Static Magic Delays & Arbitrary Sleep Loops
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

### Bad Pattern #4: Silent Exception Swallowing
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

### Bad Pattern #5: Loose Substring Class Selectors
* **Violation Location**: [`antiscraper.py:218`](file:///e:/Behavioural/antiscraper.py#L218)
* **Anti-Pattern Code**:
  ```javascript
  // DISASTER: Loose substring matching
  const cards = document.querySelectorAll('.cus-col, .product-box, .product-card, .grid-item, div.card, div[class*="col-"]');
  ```
* **Why It Is Prohibited**: `div[class*="col-"]` matches structural Bootstrap/Tailwind columns across headers, navigation sidebars, and footers, extracting garbage data into the output stream.
* **Mandated Remedy**: Anchor locators to semantic cards (`article.product-card`) or test IDs (`[data-testid="product-card"]`).

---

### Bad Pattern #6: Untyped Data Models & Missing Schema Validation Boundary
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

### Bad Pattern #7: Suppressed Static Typing in Project Configuration
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
