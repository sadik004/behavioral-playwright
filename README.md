# Behavioral Playwright (Enterprise Hardened Edition)

A resilient, self-healing browser automation and stealth AI execution framework built on modern Playwright with integrated multi-provider bridges, high-frequency quantitative market data pipelines, and deep behavioral evasion.

---

## 🏛️ Architecture Overview

The framework provides a unified, elegant public facade (`BP`) organized into decoupled domain namespaces:

```text
behavioral-playwright/
├── pyproject.toml                         # Standardized PEP 517/518 build & dependency manifest
├── README.md                              # Unified documentation & quick-reference guide
├── docs/                                  # Comprehensive architecture, usage & audit records
│   ├── architecture/                      # Component interactions & system flows
│   ├── core/                              # Stealth evasion, biomechanics, self-healing
│   ├── usage/                             # Cookbooks, API quick reference, crawling guides
│   └── development/                       # Audit registers, checkpoints & reconciliation reports
├── src/
│   └── behavioral_playwright/
│       ├── __init__.py                    # Global exports: BP, AutomationConfig, models, exceptions
│       ├── facade.py                      # Unified BP facade orchestrating all domain namespaces
│       ├── automation/                    # Biomechanical mouse curves, natural keyboard typing, scroll
│       ├── browser/                       # Browser abstractions & session lifecycle
│       ├── config/                        # AutomationConfig, BrowserConfig, CircuitBreakerConfig
│       ├── crawling/                      # Async recursive crawler & sitemap generator
│       ├── document/                      # OCR & document parsing pipelines
│       ├── extraction/                    # DOM extraction & structured markdown simplification
│       ├── handoff/                       # Session state, cookie & context serialization
│       ├── integrations/                  # Extension hooks, MCP protocol bridges, webhook triggers
│       ├── mapping/                       # Structural site & DOM tree mapper
│       ├── models/                        # Typed data contracts (DOMElement, ExtractionRecord, Quote)
│       ├── observability/                 # SQLite event sink, performance tracing, QA metrics
│       ├── page/                          # PageSession & context controllers
│       ├── resilience/                    # Circuit breakers, retry policy, self-healing memory
│       ├── search/                        # Visual & DOM query search engine
│       ├── selectors/                     # Multi-tier selector resolver (CSS, Semantic, Fuzzy, Self-Healing)
│       ├── verification/                  # Element verification & assertion sentinels
│       ├── providers/                     # Multi-provider adapters (Playwright, Patchright, UC, curl-cffi, Browser-Use, Stagehand)
│       └── core/                          # Hardened V15 Evasion Core & verified ITCH-5.0 parser
└── tests/
    ├── unit/                              # Isolated component & action unit tests
    ├── integration/                       # Multi-component and live provider tests
    ├── test_baseline_protection.py        # Core V15 baseline capability protection tests
    ├── test_honesty_hardening.py          # Data contract & honesty hardening tests
    ├── test_itch_binary.py                # NASDAQ ITCH-5.0 wire parser verification tests
    ├── test_providers.py                  # Multi-provider live & double verification tests
    └── test_v23_quarantine.py             # V23 quarantine pins
```

---

## ⚡ Quick Start

```python
import asyncio
from behavioral_playwright import BP, AutomationConfig

async def main():
    # Initialize the unified facade
    async with BP() as bp:
        # 1. Web Automation with Self-Healing Selectors
        await bp.goto("https://example.com")
        await bp.type("#search-input", "Market Data")
        await bp.click("button.submit-btn")
        
        # 2. Structured DOM Extraction
        links = await bp.extract(target="links")
        print(f"Extracted {len(links)} links")
        
        # 3. Quantitative Market Feed & ITCH-5.0 Parser
        itch = bp.quant.create_itch_parser(dollar_threshold=50000.0)
        
        # 4. Multi-Provider Selection
        pw = bp.providers.create_browser("patchright")
        net = bp.providers.create_network("curl_cffi")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🧩 Domain Namespaces

| Namespace | Key Methods & Capabilities |
| :--- | :--- |
| **`bp.web`** | `navigate()`, `click()`, `type()`, `extract()`, `crawl()`, `session()`, `save_crawl_state()` |
| **`bp.browser`** | `hover()`, `drag_and_drop()`, `check()`, `select_option()`, `press()`, `screenshot()` |
| **`bp.quant`** | `create_itch_parser()`, `align_edgar_filing()`, `filter_pit_feed()`, `resolve_entity()`, `create_persistence_pipeline()` |
| **`bp.providers`** | `create_browser("patchright"\|"playwright"\|"uc")`, `create_network("curl_cffi")`, `create_agent("browser_use"\|"stagehand")`, `matrix()` |
| **`bp.network`** | `measure_response_time()`, `measure_response_time_async()`, `set_custom_headers()`, `set_timeout()` |
| **`bp.observability`** | `start_trace()`, `end_trace()`, `log_execution()`, `generate_qa_report()`, `audit_compliance_log()` |
| **`bp.document`** | `ocr_image()`, `ocr_image_with_autocorrect()` |
| **`bp.integrations`** | `notify_webhook()`, `mcp_call_tool()`, `n8n_webhook_trigger()`, `slack_webhook_notify()`, `discord_webhook_notify()` |
| **`bp.infrastructure`**| `init_queue()`, `push_task()`, `pop_task()`, `complete_task()`, `fail_task()` |

---

## 🧪 Comprehensive Test Suite

Run the full verified test suite:
```bash
python -m pytest tests/ -q
```
**Status**: `157 passed, 1 skipped` (158 collected).

- `tests/test_baseline_protection.py` — 13 tests (LOB reconstructor, EDGAR PiT dual-timestamps, sentinels, Frida degradation)
- `tests/test_honesty_hardening.py` — 11 tests (W1–W5 honesty hardening & synthetic identifier verification)
- `tests/test_itch_binary.py` — 17 tests (NASDAQ ITCH-5.0 wire parser layout & lifecycle tests)
- `tests/test_providers.py` — 18 tests (Provider gating & live headless Chromium tests)
- `tests/test_v23_quarantine.py` — 7 tests (Quarantine pins for V23 hardcoded constants)
- `tests/unit/` — 89 tests (Browser actions, crawler, config, extraction, fuzzy/semantic selectors, resilience, observability, OCR, quant namespaces)
- `tests/integration/` — 3 tests (Cross-site self-healing & facade integration)

---

## 🛡️ Multi-Provider Matrix

| Provider | Type | Available on Host | Live Integration Status |
| :--- | :--- | :--- | :--- |
| **Patchright** | Browser | ✔ v1.59.1 | **VERIFIED-LIVE** (Headless Chromium launched) |
| **Playwright** | Browser | ✔ v1.50.0 | **VERIFIED-LIVE** (Headless Chromium launched) |
| **Undetected-Chromedriver** | Browser | ✔ v3.5.5 | **PROVIDER-GATED-LIVE** (Opt-in via `SQ_LIVE_UC=1`) |
| **curl-cffi** | Network/TLS | ✘ Optional | **PROVIDER-GATED** (Raises `ProviderUnavailableError` on absence) |
| **Browser-Use** | AI Agent | ✘ Optional | **PROVIDER-GATED** (Mandatory LLM instance required) |
| **Stagehand** | AI Agent | ✘ Optional | **PROVIDER-GATED** (Mandatory Model + Key required) |
