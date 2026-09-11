---
name: browser-automation
description: Master skill for enterprise-grade web automation, resilient scraping, Playwright browser orchestration, anti-leak lifecycle pooling, and Pydantic-validated data pipelines. Triggers on all web automation, crawler, Playwright, scraping, and browser extraction tasks.
---

# Browser Automation, Web Scraping & Resilient Data Pipeline Engineering Guidelines

This skill codifies the architectural rules, browser lifecycle constraints, resilience standards, and engineering conventions mandated by the Lead Architect. When executing any browser automation, crawling, Playwright scripting, or web scraping task, these guardrails and invariants are strictly binding.

---

## The 50 Master Architectural & Behavioral Guardrails for Automation & Extraction

### Quadrant 1: Client Environment & Header Integrity (Rules 1–10)
1. **Deterministic User-Agent & Platform Alignment**: Always synchronize the HTTP `User-Agent` header with the underlying platform navigator properties (`navigator.platform`, `navigator.userAgentData`, `navigator.appVersion`). Never emit a Windows `User-Agent` from a Linux Chromium runtime without patching the corresponding navigator object properties.
2. **Standardized Sec-CH-UA Client Hints**: Ensure modern Chromium client hints (`Sec-CH-UA`, `Sec-CH-UA-Mobile`, `Sec-CH-UA-Platform`, `Sec-CH-UA-Platform-Version`) match the exact browser major and minor versions specified in the User-Agent string to prevent automated fingerprint discrepancy flags.
3. **Locale, Timezone & Geo-Location Triad**: Always align `locale`, `timezone_id`, and `geolocation` coordinates within browser context options (`browser.new_context(locale="en-US", timezone_id="America/New_York", geolocation={"latitude": 40.7128, "longitude": -74.0060})`). Mismatched timezones and IP geolocations trigger immediate anti-bot challenges.
4. **Isolated Ephemeral Browser Contexts**: Never reuse a single `BrowserContext` across unrelated scrape targets or independent tenant sessions. Isolate cookies, local storage, cache, and HTTP credentials by instantiating isolated contexts per scrape mission.
5. **Sanitized Default HTTP Headers**: Emit authentic browser header orders and casings (`Accept`, `Accept-Language`, `Accept-Encoding`, `Sec-Fetch-Dest`, `Sec-Fetch-Mode`, `Sec-Fetch-Site`, `Sec-Fetch-User`, `Upgrade-Insecure-Requests`). Never inject bot-identifying default Python HTTP headers into browser sessions.
6. **WebGL & Canvas Consistent Profile**: Keep WebGL vendor (`Google Inc. (NVIDIA)`), renderer strings, and canvas rendering configurations consistent with the simulated operating system and GPU hardware profiles.
7. **Navigator Automation Flag Neutralization**: When launching browser instances, permanently disable automated testing indicators using Playwright initialization scripts (`page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")`) and browser launch flags (`--disable-blink-features=AutomationControlled`).
8. **Screen Resolution & Viewport Consistency**: Configure authentic desktop viewport resolutions (`1920x1080`, `1440x900`, `1366x768`) with matching window outer dimensions. Avoid unnatural, static headless resolutions like `800x600`.
9. **Strict Cookie & Storage State Persistence**: When maintaining authenticated sessions across runs, persist state exclusively via encrypted storage state files (`context.storage_state(path="state.json")`). Never hardcode authentication tokens or session cookies in source code.
10. **WebRTC Leak Mitigation**: When routing traffic through proxies, configure WebRTC policies to block local IP address leakage (`--force-webrtc-ip-handling-policy=default_public_interface_only` or disabling WebRTC UDP candidates).

### Quadrant 2: Browser Lifecycle, Memory Leak & Process Hygiene (Rules 11–20)
11. **Single Browser Instance, Multi-Context Pooling**: Never launch a new browser executable (`playwright.chromium.launch()`) per URL or request. Launch a single long-running browser process and pool lightweight, isolated `BrowserContext` instances. Browser launches take 1500–3000ms and consume 150MB+ RAM; context creation takes 10–25ms and consumes < 2MB.
12. **Mandatory Context Disposal in `finally:`**: Always wrap `BrowserContext` and `Page` lifecycles inside `try...finally:` or asynchronous context managers (`async with`). Never let failed extraction attempts abandon open contexts or pages on the heap.
13. **Proactive Route Interception & Media Aborting**: Always abort unnecessary bandwidth and memory sinks (images, fonts, stylesheets, media, tracking beacons) via route interception (`await page.route("**/*.{png,jpg,jpeg,webp,svg,gif,woff,woff2,ttf,mp4}", lambda r: r.abort())`) unless the task explicitly requires screenshot rendering or optical OCR.
14. **Process Recycling Thresholds**: Periodically recycle long-running browser worker processes after processing a bounded quota of pages (e.g. 500–1,000 pages) or upon reaching an RSS memory threshold (e.g. 1.2 GB) to permanently eliminate internal Chromium V8 engine memory fragmentation and heap bloat.
15. **Explicit CDPSession & Frame Detachment**: When utilizing Chrome DevTools Protocol (`CDPSession`) or iframe listeners, explicitly detach listeners and close sessions on page teardown to prevent uncollectible circular event emitter references.
16. **Orphaned Process & Zombie Reaper Guard**: Implement signal handlers (`SIGTERM`, `SIGINT`) and `atexit` hooks that actively sweep and terminate orphaned headless browser sub-processes (`chromium`, `node`, `cat`) when the Python orchestrator process exits.
17. **Bounded Concurrency Semaphores**: Guard parallel browser scraping with `asyncio.Semaphore(max_concurrency)`. Never launch unbounded concurrent pages simultaneously, which causes CPU thread thrashing, tab crashes (`TargetCrashException`), and OS OOM kills.
18. **Page Dialog Auto-Handling**: Always register a default dialog handler (`page.on("dialog", lambda dialog: dialog.dismiss())`) to prevent alert/prompt/confirm JavaScript dialogs from permanently freezing the page execution thread.
19. **Single-Page Isolation in Fast Sweeps**: When crawling hundreds of links, reuse a single pooled context and close individual `Page` objects sequentially (`await page.close()`), allowing browser context caches to benefit from connection keep-alive without leaking DOM node trees.
20. **Zero Synchronous File I/O in Async Crawlers**: Offload heavy disk writes (saving downloaded PDFs, large HTML dumps, binary images) to `asyncio.to_thread(write_file, path, data)` to prevent blocking the asynchronous crawler event loop.

### Quadrant 3: Resilience, Rate-Limiting & Network Invariants (Rules 21–30)
21. **Strict Ban on Arbitrary Sleeping**: Never invoke `time.sleep()`, `asyncio.sleep(5)`, or `page.wait_for_timeout(3000)` with static magic delays. Always await deterministic DOM state transitions via `page.wait_for_selector(..., state="visible")` or `page.expect_response(...)`.
22. **Full-Jitter Exponential Backoff on 429/503**: On receiving HTTP 429 (Too Many Requests), HTTP 503 (Service Unavailable), or CAPTCHA challenges, apply AWS Full-Jitter Exponential Backoff: $\text{delay} = \text{random}(0, \min(\text{max\_delay}, \text{base} \times 2^{\text{attempt}}))$. Never retry in lockstep intervals.
23. **Proxy Quarantine & Health Scoring**: Maintain an active proxy pool with health scoring. When a proxy IP encounters a connection reset, SSL handshake failure, or 403 block, immediately place that IP into a timed quarantine pool ($t_{\text{quarantine}} \ge 300\text{s}$) and rotate to the next healthy proxy.
24. **Deterministic Navigation Timeouts**: Always specify explicit, bounded timeouts on navigation calls (`page.goto(url, timeout=30000, wait_until="domcontentloaded")`). Avoid waiting for `"networkidle"` indefinitely on pages with continuous background polling or tracking beacons.
25. **Pydantic DTO Extraction Boundary**: Raw extracted HTML dictionaries must NEVER escape the scraping layer. Transform all raw extracted attributes into strictly validated, typed Pydantic models with defensive fallback defaults before passing to persistence or domain services.
26. **Network Request Payload Bounding**: Reject or abort outbound/inbound responses exceeding maximum allowable size limits (e.g. > 25 MB) to protect against decompression bombs and memory-exhaustion exploits.
27. **Idempotent Data Sink Operations**: When persisting scraped entities to databases or object stores, use atomic upsert operations (`ON CONFLICT DO UPDATE` or deterministic document hash deduplication) so that interrupted and restarted crawlers do not produce duplicate records.
28. **Token Bucket Request Throttling**: Regulate request dispatch per domain using an in-memory or Redis-backed Token Bucket rate limiter. Enforce polite, domain-specific request ceilings (e.g. 5 requests/sec per domain) to prevent denial-of-service impacts on target hosts.
29. **SSL/TLS Strict Verification**: Always enforce valid TLS certificates in production scrapers. Never disable certificate verification (`ignore_https_errors=True`) unless explicitly targeting an audited, private local development environment with self-signed test certificates.
30. **Circuit Breaker for Target Outages**: Wrap target domain scrapers in a Circuit Breaker FSM (`CLOSED`, `OPEN`, `HALF_OPEN`). When a target website encounters sustained 5xx failures or blockades (> 10 consecutive failures), trip the breaker to `OPEN` for 10 minutes to protect compute resources and prevent proxy burning.

### Quadrant 4: AI Agent Behavioral Directives (Rules 31–40)
31. **The 2-Strike Selector Failure Rule**: If a DOM locator or extraction logic fails twice on the same target page, STOP immediately. Do NOT make repeated blind guesses. Capture the page DOM snapshot, inspect the raw HTML tree, analyze selector mutations, and author an updated, verified locator.
32. **Zero Synthetic Mocks for Scraper Validation**: Never declare a web scraper "functional" based purely on synthetic in-memory string mocks or unit test assertions that feed static HTML. Always execute against real target endpoints or recorded HAR/WARC fixture files.
33. **Radical Anti-Sycophancy & Reality-Grounded Engineering ("জিরো তেলবাজি" পলিসি)**: Deliver strictly objective engineering facts regarding target site defenses, scraping feasibility, legal robot exclusion, and selector stability. Never pretend a fragile regex parser or brittle scraper is "production-ready" out of polite deference.
34. **Mandatory Terminal Script Execution**: Never conclude a browser automation task without running the crawler script from the terminal and verifying clean output, zero uncaught exceptions, and successful exit code 0.
35. **Zero Stubs, Placeholders, or TODO Slop**: Every extraction script, parser method, and error handler must be 100% realized and executable. Never leave `# TODO: extract rest of fields` or `pass` in production scraping pipelines.
36. **Transparent Technical Boundaries**: If a site employs advanced hardware-level attestation, CAPTCHA challenges, or behavioral biometrics, clearly report the exact defensive mechanism and recommend the proper integration (session tokens, authenticated APIs, or bypass architecture) rather than inventing imaginary code.
37. **The Doubling-Down Ban**: When a selector or navigation strategy fails in testing, never repeat the exact same selector or claim "it worked in my mind". Concede the failure, inspect the DOM tree, and implement the robust canonical pattern.
38. **Single-Task Scope Containment**: Focus strictly on the requested target website, data entities, and pipeline components. Do not perform unsolicited rewrites of unrelated crawler infrastructure.
39. **Destructive Action Confirmation Gate**: Never delete historical scrape archives, drop crawler database tables, or wipe persistent cache directories without explicit confirmation.
40. **Concise Communication & Zero Dramatic Padding (নো ড্রামা / নো ইমোশনাল প্যাডিং)**: Deliver direct, high-signal technical updates. Highlight status, extraction throughput, selector strategies, schema models, and verification outputs without fluff.

### Quadrant 5: Optical Illusions & Selector Robustness Defense (Rules 41–45)
41. **Strict Ban on Fragile Absolute XPaths**: Never use full absolute XPaths (e.g. `/html/body/div[2]/div[1]/section/div[3]/ul/li[2]/a`). Any minor DOM restructuring or layout update instantly breaks the entire scraper. Always use semantic, resilient locators.
42. **Semantic ARIA & Data-Attribute Priority**: Anchor locators using resilient priority tiers: (1) `data-testid` / `data-cy` / `data-automation-id`, (2) Semantic ARIA role and accessible name (`page.get_by_role("button", name="Submit")`), (3) Semantic CSS classes or unique IDs (`article.product-card`), (4) Scoped relative XPath with stable text or attributes (`//div[contains(@class, 'product')]//span[contains(@class, 'price')]`).
43. **The Falsy Zero & Free-Tier Trap**: Never treat `0` or `0.00` as falsy when extracting prices, discounts, stock quantities, or review counts (`price = raw_price or None` is a critical bug when `raw_price = 0.0`). Always explicitly check `if raw_price is not None:`.
44. **Whitespace & Unicode Normalization**: Web pages contain non-breaking spaces (`\xa0`), zero-width spaces (`\u200b`), and un-trimmed carriage returns. Always pass extracted string content through `unicodedata.normalize("NFKC", text).strip()` before regex matching or schema validation.
45. **Dynamic DOM Mutation Wait Over Timers**: When waiting for dynamic single-page application (SPA) updates (e.g. infinite scroll loading, modal popups, dropdown renders), wait for element count changes or element visibility mutations (`page.wait_for_function("() => document.querySelectorAll('.product-item').length > 10")`) rather than fixed delays.

### Quadrant 6: The 5 Supporting Fortress Layers & Tooling (Rules 46–50)
46. **Layer 1: Automated Failure Forensic Snapshotting**: When any extraction or navigation step fails, automatically dump the full page HTML DOM to `forensics/<timestamp>_dump.html` and capture a full-page screenshot to `forensics/<timestamp>_screenshot.png` before context teardown.
47. **Layer 2: Local Verification Harness (`scripts/run_crawlers.sh`)**: Provide and maintain a standardized shell script (`scripts/run_crawlers.sh`) that sets up virtual environments, verifies browser binary installations (`playwright install chromium`), executes linters, and runs automated crawler integration suites with fail-fast `set -e`.
48. **Layer 3: Strict Static Type Checking & Code Quality**: Enforce `mypy --strict` compliance across all automation code. Type all browser contexts, page handles, element locators, and Pydantic schemas explicitly. Disallow untyped dictionaries as return types.
49. **Layer 4: Self-Evolving Selector Postmortem Log**: Document every broken selector incident, target website layout redesign, or bot defense update in `docs/crawler_postmortems/` with root-cause analysis, previous selector, new resilient locator, and prevention rules.
50. **Layer 5: Structured JSON Logging with Trace Correlation**: Never output unstructured `print()` statements. Use structured JSON logging (`structlog` or `logging` with JSON formatter) including `target_url`, `proxy_ip`, `status_code`, `duration_ms`, `items_extracted`, and `attempt_number`.

---

## 1. Browser Lifecycle & Context Pool Architecture

### The Anti-Leak Context Pooling Model
In production web scraping, spawning a fresh browser process (`chromium.launch()`) per scrape request is the primary cause of CPU spikes, memory exhaustion, and sluggish response times. A single Chromium browser process requires significant operating system overhead, launches dozens of internal helper threads, and consumes 100MB–250MB of RSS memory upon initialization.

Instead, production architectures maintain a **Single Browser, Multi-Context Pooling Engine**:
1. A master `Browser` instance is launched at application startup with hardened flags.
2. For each scrape job or batch, a lightweight, ephemeral `BrowserContext` is spawned.
3. Network route interception is attached to the context or page to abort unneeded media.
4. Data extraction executes within isolated pages.
5. In the `finally:` block, `page.close()` and `context.close()` execute unconditionally, immediately freeing all memory buffers without terminating the master browser process.
6. A bounded worker semaphore ensures that no more than $N$ concurrent pages execute in parallel.

```
┌────────────────────────────────────────────────────────┐
│               Master Browser Process                   │
│   (Chromium / Firefox Headless - Persistent Lifespan)   │
└──────────────────────────┬─────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Context #1   │    │ Context #2   │    │ Context #K   │
│ (Proxy A)    │    │ (Proxy B)    │    │ (Proxy C)    │
│ (Cookies A)  │    │ (Cookies B)  │    │ (Cookies C)  │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       ▼                   ▼                   ▼
 ┌───────────┐       ┌───────────┐       ┌───────────┐
 │  Page #1  │       │  Page #2  │       │  Page #K  │
 │ (Extract) │       │ (Extract) │       │ (Extract) │
 └───────────┘       └───────────┘       └───────────┘
       │                   │                   │
       ▼                   ▼                   ▼
 [finally: close]    [finally: close]    [finally: close]
```

---

## 2. Network Interception & Resource Optimization

Loading stylesheets, images, tracking pixels, video assets, and custom web fonts slows page navigation by 300%–800% and increases server egress costs. 

Production crawlers intercept all outbound network requests at the context route layer:
* **Abort Patterns**: Images (`.png`, `.jpg`, `.jpeg`, `.webp`, `.svg`, `.gif`), Fonts (`.woff`, `.woff2`, `.ttf`), Media (`.mp4`, `.webm`, `.mp3`), Tracking analytics (Google Analytics, Segment, Datadog, Hotjar).
* **Allow Patterns**: Documents (`document`), Fetch/XHR (`xhr`, `fetch`), Essential JavaScript (`script` when rendering dynamic SPAs).

When a page is purely API-driven or server-rendered HTML, JavaScript can also be disabled (`java_script_enabled=False` in `new_context`), slashing execution time to under 150ms per page.

---

## 3. Resilient Waiting & Anti-Flake Invariants

Flaky scrapers invariably stem from arbitrary delays (`time.sleep(5)`) or premature assertions.

### The Invariants of Resilient Waiting
1. **Never use static sleeps**: `time.sleep()` blocks the entire asyncio event loop, freezing all concurrent scrapers. `page.wait_for_timeout()` burns CPU cycles and still fails whenever a network hiccup exceeds the arbitrary timeout.
2. **Auto-Waiting Locators**: Playwright's native locators (`page.locator("...")`) automatically wait for elements to be present in DOM, visible, stable, and ready for action.
3. **Explicit State Transitions**: When navigating or waiting for dynamic updates, explicitly wait for DOM state:
   - `locator.wait_for(state="visible", timeout=10000)`
   - `page.wait_for_load_state("domcontentloaded")`
   - `page.wait_for_function("() => window.__DATA_LOADED__ === true")`
4. **Response Predicate Interception**: When submitting a form or clicking a pagination button that triggers an API call, wait for the network response directly:
   ```python
   async with page.expect_response(lambda r: "api/catalog" in r.url and r.status == 200) as response_info:
       await page.locator("button.next-page").click()
   response = await response_info.value
   data = await response.json()
   ```

---

## 4. Robust Locator Hierarchy

Never rely on fragile generated selectors like `#app > div.main__3x7y > div:nth-child(2) > span`.

| Tier | Selector Strategy | Example | Resiliency Grade |
|---|---|---|---|
| **Tier 1** | Test & Automation IDs | `page.get_by_test_id("product-title")` | **A+ (Immutable Contract)** |
| **Tier 2** | ARIA Roles & Accessible Names | `page.get_by_role("heading", name="Specifications")` | **A (Semantic Accessibility)** |
| **Tier 3** | Text Content Anchor | `page.locator("article").filter(has_text="In Stock")` | **B+ (Human Readable)** |
| **Tier 4** | Scoped Semantic CSS | `page.locator("section.pricing-matrix .price-val")` | **B (Scoped Structural)** |
| **Tier 5** | Scoped Relative XPath | `page.locator("//div[contains(@class,'card')]//h3")` | **C+ (Permitted with Scope)** |
| **FORBIDDEN** | Absolute Full XPath | `/html/body/div[1]/div[2]/div[4]/span[1]` | **F (Strictly Prohibited)** |

---

## 5. Pydantic-Validated Extraction Pipeline

Every extracted record must pass through a strict Pydantic model boundary before entering storage. This guarantees:
- **Type Coercion**: Converting `" $1,299.99 "` into `Decimal("1299.99")`.
- **Falsy Zero Protection**: Preserving `0` stock or free prices rather than converting to `None`.
- **URL Resolution**: Transforming relative paths `/item/123` into absolute canonical URLs `https://example.com/item/123`.
- **Defensive Error Handling**: Catching validation errors at the record level so a single malformed item in a 100-item catalog does not crash the entire crawl.

---

## 6. Rate Limiting, Exponential Backoff & Jitter

When a scraper encounters rate limits (HTTP 429) or transient server errors (HTTP 503), naive immediate retries trigger cascading IP bans. 

Scrapers must apply **AWS Full-Jitter Exponential Backoff**:
$$\text{Sleep Delay} = \text{Uniform}(0, \min(\text{max\_backoff}, \text{base\_delay} \times 2^{\text{attempt}}))$$

Adding full randomization prevents multiple concurrent crawler workers from hammering the target server at identical intervals (the "Thundering Herd" problem).

---

## Canonical Implementations: Good vs. Bad Code Patterns

### Good Pattern 1: Production Browser Context Pool Manager with Resource Interception

```python
"""
app/crawler/browser_pool.py - Production-Grade Playwright Context Pool Manager.
Enforces single browser pooling, resource route aborting, bounded concurrency,
and guaranteed cleanup in finally blocks.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Final, Optional
import structlog
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

logger = structlog.get_logger(__name__)

# Extensions to abort to conserve bandwidth and RAM
ABORTED_RESOURCE_TYPES: Final[frozenset[str]] = frozenset({
    "image",
    "font",
    "media",
    "stylesheet",
    "imageset",
})

DEFAULT_VIEWPORT: Final[dict[str, int]] = {"width": 1920, "height": 1080}
DEFAULT_USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)


class BrowserPoolManager:
    """
    Manages a single Chromium browser process with dynamic, isolated context pooling.
    Guarantees thread-safe bounded concurrency and zero leaked contexts.
    """

    def __init__(self, max_concurrent_pages: int = 8, headless: bool = True) -> None:
        self._max_concurrency: int = max_concurrent_pages
        self._headless: bool = headless
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._is_running: bool = False
        self._lock: asyncio.Lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Launches the master Chromium process with anti-automation flags."""
        async with self._lock:
            if self._is_running:
                return

            self._semaphore = asyncio.Semaphore(self._max_concurrency)
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self._headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                    "--disable-extensions",
                    "--no-first-run",
                ],
            )
            self._is_running = True
            logger.info("browser_pool.initialized", max_concurrency=self._max_concurrency)

    @asynccontextmanager
    async def get_page(
        self,
        proxy_url: Optional[str] = None,
        abort_media: bool = True,
    ) -> AsyncGenerator[Page, None]:
        """
        Yields an isolated Page within an ephemeral BrowserContext.
        Enforces route interception, concurrency bounding, and guaranteed disposal.
        """
        if not self._is_running or self._browser is None or self._semaphore is None:
            raise RuntimeError("BrowserPoolManager must be initialized before acquiring pages.")

        await self._semaphore.acquire()
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None

        try:
            # Configure isolated context options
            context_options: dict[str, object] = {
                "viewport": DEFAULT_VIEWPORT,
                "user_agent": DEFAULT_USER_AGENT,
                "locale": "en-US",
                "timezone_id": "America/New_York",
                "java_script_enabled": True,
                "ignore_https_errors": False,
            }
            if proxy_url:
                context_options["proxy"] = {"server": proxy_url}

            context = await self._browser.new_context(**context_options)

            # Strip webdriver property on page initialization
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            page = await context.new_page()

            # Dismiss unhandled JavaScript dialogs
            page.on("dialog", lambda dialog: asyncio.create_task(dialog.dismiss()))

            # Attach route interception to abort heavy media
            if abort_media:
                async def _route_interceptor(route: object) -> None:
                    req = getattr(route, "request", None)
                    if req and req.resource_type in ABORTED_RESOURCE_TYPES:
                        await route.abort()  # type: ignore[attr-defined]
                    else:
                        await route.continue_()  # type: ignore[attr-defined]

                await page.route("**/*", _route_interceptor)

            yield page

        finally:
            # Unconditional teardown in reverse order
            if page and not page.is_closed():
                try:
                    await page.close()
                except Exception as exc:
                    logger.warning("page_close_error", error=str(exc))

            if context:
                try:
                    await context.close()
                except Exception as exc:
                    logger.warning("context_close_error", error=str(exc))

            self._semaphore.release()

    async def shutdown(self) -> None:
        """Drains and terminates the master browser process."""
        async with self._lock:
            if not self._is_running:
                return

            logger.info("browser_pool.shutting_down")
            if self._browser:
                await self._browser.close()
                self._browser = None

            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            self._is_running = False
            logger.info("browser_pool.shutdown_complete")
```

---

### Good Pattern 2: Resilient Pydantic Data Extraction Pipeline with AWS Full-Jitter Backoff

```python
"""
app/crawler/pipeline.py - Pydantic-Validated Extraction with AWS Full-Jitter Retry.
Guarantees clean data typing, falsy zero protection, and anti-crash error boundaries.
"""
from __future__ import annotations

import asyncio
import random
import re
import unicodedata
from decimal import Decimal
from typing import Any, Callable, Coroutine, Final, Optional, TypeVar
import structlog
from pydantic import BaseModel, ConfigDict, Field, field_validator, HttpUrl
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

logger = structlog.get_logger(__name__)

T = TypeVar("T")
PRICE_REGEX: Final[re.Pattern[str]] = re.compile(r"[\d,]+(?:\.\d{2})?")


class ProductExtractionDTO(BaseModel):
    """Clean, typed domain transfer model for scraped e-commerce items."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    sku: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=256)
    price: Decimal = Field(ge=Decimal("0.00"))
    currency: str = Field(default="USD", min_length=3, max_length=3)
    in_stock: bool
    rating: Optional[Decimal] = Field(default=None, ge=Decimal("0.0"), le=Decimal("5.0"))
    review_count: int = Field(default=0, ge=0)
    url: HttpUrl

    @field_validator("title", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> str:
        """Normalizes Unicode characters and collapses redundant whitespace."""
        if not isinstance(value, str):
            raise ValueError("Title must be a valid string.")
        normalized = unicodedata.normalize("NFKC", value)
        return re.sub(r"\s+", " ", normalized).strip()

    @field_validator("price", mode="before")
    @classmethod
    def parse_currency_amount(cls, value: Any) -> Decimal:
        """Defensively extracts arbitrary precision Decimal from raw currency string."""
        if isinstance(value, (int, float, Decimal)):
            return Decimal(str(value))
        if isinstance(value, str):
            clean_str = unicodedata.normalize("NFKC", value).replace(",", "").strip()
            match = PRICE_REGEX.search(clean_str)
            if match:
                return Decimal(match.group(0))
        raise ValueError(f"Unable to parse valid monetary amount from '{value}'.")


async def retry_with_full_jitter(
    operation: Callable[[], Coroutine[Any, Any, T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 16.0,
) -> T:
    """
    Executes an async operation with AWS Full-Jitter Exponential Backoff.
    Formula: delay = random.uniform(0, min(max_delay, base_delay * 2 ** attempt))
    """
    attempt = 0
    while True:
        try:
            return await operation()
        except (PlaywrightTimeoutError, ConnectionError) as exc:
            attempt += 1
            if attempt > max_retries:
                logger.error("operation_retries_exhausted", attempts=attempt, error=str(exc))
                raise

            sleep_duration = random.uniform(0, min(max_delay, base_delay * (2 ** (attempt - 1))))
            logger.warning(
                "transient_error_backing_off",
                attempt=attempt,
                sleep_sec=round(sleep_duration, 2),
                error=type(exc).__name__,
            )
            await asyncio.sleep(sleep_duration)


async def extract_catalog_page(page: Page, target_url: str) -> list[ProductExtractionDTO]:
    """
    Navigates to a catalog page and extracts items into validated Pydantic DTOs.
    Uses resilient semantic selectors and auto-waiting.
    """
    async def _navigate() -> None:
        await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)

    await retry_with_full_jitter(_navigate, max_retries=3)

    # Wait for the main catalog container to become visible
    catalog_container = page.locator("div[data-testid='product-grid'], section.catalog-grid")
    await catalog_container.first.wait_for(state="visible", timeout=10000)

    # Scoped card locators
    card_locators = page.locator("article.product-card, div[data-testid='product-card']")
    count = await card_locators.count()
    logger.info("catalog_cards_detected", count=count, url=target_url)

    extracted_items: list[ProductExtractionDTO] = []

    for i in range(count):
        card = card_locators.nth(i)
        try:
            # Semantic relative extractions
            raw_title = await card.locator("h2, .product-title").inner_text()
            raw_price = await card.locator("[data-testid='price'], .price-amount").inner_text()
            sku = await card.get_attribute("data-sku") or f"sku-unknown-{i}"
            
            # Stock detection without throwing on missing badges
            stock_badge = card.locator(".out-of-stock-badge, [data-stock='false']")
            is_out_of_stock = await stock_badge.count() > 0

            # Safe href resolution
            link_locator = card.locator("a[href]").first
            raw_href = await link_locator.get_attribute("href") or ""
            absolute_url = page.url if not raw_href else f"{page.url.rstrip('/')}/{raw_href.lstrip('/')}"

            dto = ProductExtractionDTO(
                sku=sku,
                title=raw_title,
                price=raw_price,  # Validator handles string -> Decimal parsing
                in_stock=not is_out_of_stock,
                url=absolute_url,
            )
            extracted_items.append(dto)

        except Exception as exc:
            # Boundary isolation: single malformed card does not destroy batch
            logger.warning("item_extraction_skipped", index=i, error=str(exc))
            continue

    return extracted_items
```

---

### Bad Patterns (Strictly Forbidden by Lead Architect)

#### 1. Ephemeral Browser Spawning Anti-Pattern
```python
# CATASTROPHIC ANTI-PATTERN: Launching a brand new browser executable per URL
async def scrape_url(url: str):
    async with async_playwright() as p:
        # Spawns heavy OS Chromium process, burning 2000ms & 200MB RAM each time!
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        return await page.content()
```
*Why It Is Prohibited*: Spawning an entire browser process per scrape iteration thrashes the OS kernel, causes runaway CPU load, and exhausts memory within minutes under concurrent traffic.

#### 2. Arbitrary Static Sleep & Blind Timeout Anti-Pattern
```python
# CATASTROPHIC ANTI-PATTERN: Blind static sleep
import time

async def fetch_prices(page):
    await page.goto("https://store.example.com")
    time.sleep(5)  # BLOCKS the asyncio event loop! Freezes all parallel tasks.
    await page.wait_for_timeout(3000)  # Flaky! Fails if server takes 3050ms.
    price = await page.locator(".price").inner_text()
    return price
```
*Why It Is Prohibited*: `time.sleep()` freezes the single-threaded Python event loop, halting all concurrent tasks. `wait_for_timeout(3000)` is inherently flaky, failing on slow network connections and wasting seconds on fast ones.

#### 3. Fragile Absolute XPath & Regex Anti-Pattern
```python
# CATASTROPHIC ANTI-PATTERN: Fragile absolute XPath
async def get_user_balance(page):
    # Breaks the moment any CSS class, banner, or parent container changes!
    val = await page.locator("/html/body/div[2]/div[1]/section/div[3]/ul/li[2]/span").inner_text()
    return float(val.replace("$", ""))  # Float causes precision loss!
```
*Why It Is Prohibited*: Absolute XPaths depend on every parent tag in the hierarchy. A single promotional banner injected into `<header>` shifts all indices and shatters the scraper. Using `float` introduces binary floating-point rounding errors.

#### 4. The Falsy Zero & Missing Error Boundary Anti-Pattern
```python
# CATASTROPHIC ANTI-PATTERN: Falsy zero bug and unhandled exception batch crash
def parse_items(raw_items):
    clean = []
    for item in raw_items:
        # Falsy Zero Trap: If stock is 0, '0 or 10' sets in_stock to 10!
        stock = item.get("stock") or 10
        # If price is 0.0 (Free item), '0.0 or 9.99' silently charges $9.99!
        price = item.get("price") or 9.99
        clean.append({"stock": stock, "price": price})
    return clean
```
*Why It Is Prohibited*: Falsy evaluation (`or`) treats legitimate `0` values as falsy, causing silent business logic errors, incorrect pricing calculations, and data corruption.

---

## 7. Forensic Error Capture Protocol

When a scraping script encounters an unhandled exception or selector timeout during automated execution:
1. Capture an immediate timestamped screenshot: `await page.screenshot(path=f"forensics/failure_{ts}.png", full_page=True)`.
2. Write the complete HTML DOM snapshot: `with open(f"forensics/dom_{ts}.html", "w", encoding="utf-8") as f: f.write(await page.content())`.
3. Capture the current page URL and response status code.
4. Emit a structured error log entry with complete forensic telemetry.
5. Cleanly close the page and context before propagating or re-raising the exception.

This protocol guarantees that engineers and AI agents have 100% ground-truth artifacts to inspect, eliminating blind guesswork when debugging selector failures.
