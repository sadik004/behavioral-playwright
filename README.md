# behavioral-playwright

A resilient, self-healing browser automation framework built on Playwright with pluggable browser providers, semantic element recovery, structured extraction, resilience primitives, and deterministic testing.

---

## 1. Problem It Solves

Traditional browser automation scripts break constantly when web applications update their frontend layouts, change dynamic CSS class names, or re-render button identifiers.

`behavioral-playwright` provides **Cascading Self-Healing Resolution**:
1. **L1 (Exact)**: Attempts standard CSS/DOM selector queries for maximum speed.
2. **L2 (Semantic & Accessibility)**: Analyzes W3C ARIA roles, accessible names, aria-labels, placeholders, and tag context when exact selectors break.
3. **L3 (Deterministic Fuzzy Matching)**: Uses normalized Levenshtein string distance and similarity metrics to locate mutated elements.
4. **L4 (Pluggable Extension)**: Interface hooks for custom Vision/LLM cognitive reasoning plugins.

---

## 2. Architecture

```text
behavioral_playwright/
├── browser/         # Pluggable BrowserProvider interface (PlaywrightProvider, MockBrowserProvider)
├── page/            # High-level BrowserSession and PageSession context manager
├── selectors/       # SelfHealingResolver, Semantic & Fuzzy cascading resolution
├── automation/      # Deterministic Mouse, Keyboard, and Scroll controllers
├── resilience/      # RetryPolicy, CircuitBreaker state machine, and StateTracker
├── extraction/      # Structured DOMExtractor for links, tables, and articles
├── models/          # Typed data representations (DOMElement, ResolutionResult, ExtractionRecord)
└── config/          # Dependency-injectable configuration models (BrowserConfig, ResolverConfig)
```

---

## 3. Installation

```bash
pip install behavioral-playwright
playwright install chromium
```

---

## 4. Usage Examples

### A. Basic Navigation & Page Lifecycle

```python
import asyncio
from behavioral_playwright import BrowserSession, AutomationConfig, BrowserConfig

async def main():
    config = AutomationConfig(browser=BrowserConfig(headless=False))

    async with BrowserSession(config=config) as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")
        print(f"Page Title: {await page.get_title()}")

asyncio.run(main())
```

### B. Cascading Self-Healing Element Resolution

```python
import asyncio
from behavioral_playwright import BrowserSession

async def main():
    async with BrowserSession() as session:
        page = await session.new_page()
        await page.goto("https://example.com")

        # Resolves through healing cascade if exact selector mutated
        result = await page.resolve("More information")
        print(f"Healed: {result.is_healed} | Strategy: {result.strategy.value} | Selector: {result.selector}")

        # Executes click on healed target
        await page.click_healed("More information")

asyncio.run(main())
```

### C. Resilience: CircuitBreaker & RetryPolicy

```python
import asyncio
from behavioral_playwright import CircuitBreaker, CircuitBreakerConfig, RetryPolicy, RetryConfig

cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3, recovery_timeout=15.0))
retry = RetryPolicy(RetryConfig(max_attempts=3, base_delay=1.0))

@retry
async def resilient_fetch():
    return await cb.execute(lambda: some_network_call())
```

---

## 5. Testing & Verification

The test suite features fast in-memory deterministic testing using `MockBrowserProvider` (executes in < 0.2s without spawning Chrome):

```bash
pytest -v
```

---

## 6. Extension Points

- **Custom Providers**: Implement `BrowserProvider` in `behavioral_playwright.browser.base`.
- **Custom Healing Strategies**: Implement `ResolverStrategy` in `behavioral_playwright.selectors.strategies` and pass to `SelfHealingResolver(custom_strategies=[...])`.

---

## 7. License

MIT License. See [LICENSE](LICENSE) for details.
