# Behavioral Playwright (AI-Native Enterprise Hardened Edition)

A resilient, self-healing browser automation, direct HTTP API, and stealth AI agent execution framework built on Playwright with multi-provider bridges, high-frequency quantitative market data pipelines, dynamic proxy pool & device fingerprint generators, deep behavioral evasion, and standard Model Context Protocol (MCP) tool integration.

---

## 🏛️ Architecture Overview

The framework is organized around a unified, decoupled facade (`BP`) coordinating specialized domain namespaces:

```text
behavioral-playwright/
├── pyproject.toml                         # Standardized PEP 517/518 build & dependency manifest
├── README.md                              # Comprehensive AI-native manual and capability guide
├── docs/                                  # Architectural specifications, cookbooks & audit logs
│   ├── architecture/                      # Component interactions & system flows
│   ├── core/                              # Stealth evasion, biomechanics, self-healing
│   ├── usage/                             # Cookbooks, API quick reference, crawling guides
│   └── development/                       # Audit registers, checkpoints & reconciliation reports
├── src/
│   └── behavioral_playwright/
│       ├── __init__.py                    # Global exports: BP, AutomationConfig, AuthConfig, ProxyPool
│       ├── facade.py                      # Unified BP facade orchestrating all domain namespaces
│       ├── api/                           # Direct asynchronous HTTP client with in-memory TTL caching
│       ├── automation/                    # Biomechanical mouse curves, natural keyboard typing, scroll
│       ├── browser/                       # Browser abstractions & session lifecycle
│       ├── cli/                           # Command-line interface (`bp scrape`, `crawl`, `mcp-server`, etc.)
│       ├── config/                        # AutomationConfig, AuthConfig, BrowserConfig, CircuitBreakerConfig
│       ├── core/                          # Hardened V15 Evasion Core & verified ITCH-5.0 wire parser
│       ├── crawling/                      # Async recursive crawler & sitemap generator
│       ├── document/                      # OCR & document parsing pipelines
│       ├── extraction/                    # DOM extraction & structured markdown simplification
│       ├── fingerprint/                   # Dynamic hardware profiles & WebGL/Canvas noise generator
│       ├── handoff/                       # Session state, cookie & context serialization
│       ├── integrations/                  # Extension hooks, webhook triggers, alert dispatchers
│       ├── mapping/                       # Structural site & DOM tree mapper
│       ├── mcp/                           # Standard JSON-RPC 2.0 Stdio MCP Server & AI Tool Dispatcher
│       ├── models/                        # Typed data contracts (DOMElement, ExtractionRecord, Quote)
│       ├── observability/                 # SQLite event sink, performance tracing, QA metrics
│       ├── page/                          # PageSession & context controllers
│       ├── providers/                     # Multi-provider adapters (Playwright, Patchright, UC, curl-cffi, Browser-Use, Stagehand)
│       ├── proxy/                         # Intelligent proxy pool, rotation, and sticky session manager
│       ├── resilience/                    # Circuit breakers, retry policy, self-healing memory
│       ├── search/                        # Visual & DOM query search engine
│       ├── selectors/                     # Multi-tier selector resolver (CSS, Semantic, Fuzzy, Self-Healing)
│       ├── storage/                       # Unified data storage & exporters (JSON, NDJSON, CSV, SQLite)
│       └── verification/                  # Element verification & assertion sentinels
└── tests/
    ├── unit/                              # 112 unit tests (all modules & namespaces covered)
    ├── integration/                       # 3 multi-component and live provider tests
    ├── test_baseline_protection.py        # 13 core V15 baseline capability protection tests
    ├── test_honesty_hardening.py          # 11 data contract & honesty hardening tests
    ├── test_itch_binary.py                # 17 NASDAQ ITCH-5.0 wire parser verification tests
    ├── test_providers.py                  # 18 multi-provider live & double verification tests
    └── test_v23_quarantine.py             # 7 V23 quarantine pins
```

---

## 🤖 AI Agent Capability & Decision Guide

If you are an AI assistant, autonomous agent, or MCP client interacting with this repository, use the following intent-driven decision table to select the correct interface:

| User / Task Intent | Recommended Capability | Python API | MCP Tool | CLI Equivalent | Fallback Mechanism | Status / Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fetch raw JSON / REST data** | Asynchronous API Client | `bp.api.get()`, `post()` | *Internal Execution* | *Use Python API* | Direct socket request | In-memory TTL cache; threadpool urllib transport |
| **Render dynamic JS webpage** | Browser Navigation | `bp.goto()`, `bp.web.navigate()` | `scrape_page` | `bp scrape <url>` | Direct HTTP API fetch | Requires Chromium / Patchright installed |
| **Extract structured links/text** | Structured DOM Extractor | `bp.extract(target="links")` | `scrape_page` | `bp scrape <url> -o out.json` | Regex / outerHTML parse | Extracts semantic cards, links, headings |
| **Recursive domain exploration** | Asynchronous Crawler | `bp.crawl(url, max_pages=N)` | `crawl_domain` | `bp crawl <url> -m 10` | Single page `goto()` | In-memory URL queue; depth-limited |
| **Multimodal visual inspection** | Viewport Screenshot | `bp.screenshot()` | `take_screenshot` | *Use Python API* | Page DOM extraction | Returns Base64 PNG string in MCP |
| **Resilient element interaction** | Multi-Tier Selector Engine | `bp.click()`, `bp.type()` | *Internal Execution* | *Use Python API* | L1 Exact ➔ L2 Semantic ➔ L3 Fuzzy | Confidence threshold >= 0.60 |
| **Circumvent bot protection** | V15 Stealth Evasion | Built-in via `bp.goto()` | *Internal Execution* | *Built-in to CLI* | Provider switch (`patchright`) | 10 runtime patches + dynamic WebGL noise |
| **Align financial data (PiT)** | SEC Point-in-Time Aligner | `bp.quant.align_edgar_filing()`| `quant_pit_align` | *Use Python API* | Manual dual-timestamp | Strict rejection of look-ahead filings |
| **Parse high-frequency ITCH** | NASDAQ ITCH-5.0 Wire Parser | `bp.quant.create_itch_parser()`| *Use Python API* | *Use Python API* | Standard LOB reconstructor | High-speed binary wire format layout |
| **Inspect engine provider status**| Provider Matrix Inspector | `bp.providers.matrix()` | `get_provider_matrix` | `bp matrix` | *Static inspection* | Real-time import & host availability test |
| **Run Stdio MCP Server for AI** | JSON-RPC 2.0 MCP Server | `McpServer().run_stdio()` | *N/A (Host Server)* | `bp mcp-server` | Direct Python Facade | Stdio JSON-RPC 2.0 transport |

---

## 🧭 Capability Reference

### 1. Direct Asynchronous API Client (`bp.api`)
- **Purpose**: High-speed HTTP requests (`GET`, `POST`, `PUT`, `DELETE`) without the overhead of launching a full headless browser instance.
- **Use When**: Interacting with public or authenticated REST endpoints, fetching static JSON/HTML payloads, or executing fast health checks.
- **Do Not Use When**: The target website requires heavy JavaScript execution, Cloudflare Turnstile/CAPTCHA challenges, or client-side single-page app rendering.
- **Python API**: `await bp.api.get(url, **kwargs)`, `await bp.api.post(url, data=..., **kwargs)`, `await bp.api.request(method, url, **kwargs)`.
- **MCP Tool**: Executed internally by tools requiring network data.
- **CLI**: Integrated with shared `--api-key` and `--token` flags.
- **Inputs**: `url: str`, `data: Optional[Union[dict, str, bytes]]`, `headers: Optional[Dict[str, str]]`, `timeout: Optional[float]`, `cache_ttl: Optional[float]`.
- **Outputs**: Typed `ApiResponse` exposing `.status_code`, `.headers`, `.body`, `.text`, `.json()`, `.elapsed_ms`, `.cached`.
- **Dependencies**: Standard Python library (`urllib.request`, `asyncio`).
- **Authentication**: Automatically attaches credentials from `AutomationConfig.auth` (`Authorization: Bearer <token>` or `X-API-Key`).
- **Fallback**: Direct unauthenticated request or headless browser navigation via `bp.goto()`.
- **Failure Modes**: Catches `HTTPError` returning status code; raises `CircuitBreakerError` if downstream service has failed repeatedly.
- **Status**: `VERIFIED`.

### 2. Multi-Tier Self-Healing Selector Engine (`bp.selectors`)
- **Purpose**: Resolves UI elements even when IDs, classes, or DOM hierarchies change across web deployments.
- **Use When**: Interacting with dynamic web applications where CSS selectors frequently break or are obfuscated by build tools.
- **Do Not Use When**: Interacting with raw APIs or non-browser data streams.
- **Python API**: `await bp.resolve_selector(selector_query)` or transparently inside `await bp.click(selector)`, `await bp.type(selector, text)`.
- **Resolution Pipeline**:
  1. **L1 Exact**: Direct CSS / XPath selector resolution.
  2. **L2 Semantic**: ARIA role, accessibility name, placeholder, and text content matching.
  3. **L3 Fuzzy**: Levenshtein / token similarity scoring across candidates (similarity threshold >= 0.65).
- **Status**: `VERIFIED`.

### 3. Biomechanical Automation (`bp.automation` / `bp.browser`)
- **Purpose**: Emulates natural human physical interaction to evade behavioral anti-bot scoring systems.
- **Features**: Bézier curve mouse trajectories with sub-pixel micro-jitter, velocity ramp-up/down, natural typing intervals with realistic key-press dwell times, and humanized page scrolling.
- **Python API**: `await bp.click(selector)`, `await bp.type(selector, text)`, `await bp.browser.hover(selector)`, `await bp.browser.drag_and_drop(src, dst)`.
- **Status**: `VERIFIED`.

### 4. Recursive Web Crawler & Sitemap Explorer (`bp.crawling`)
- **Purpose**: Recursively discovers and crawls links within a domain up to a user-defined depth and page limit.
- **Python API**: `await bp.crawl(start_url, max_pages=10, depth=2)`.
- **MCP Tool**: `crawl_domain` (`{"url": "https://example.com", "max_pages": 5}`).
- **CLI**: `bp crawl https://example.com --max-pages 10 --depth 2 -o crawled.ndjson`.
- **Status**: `VERIFIED`.

### 5. Structured Data Storage & Exporters (`bp.storage`)
- **Purpose**: Serializes extracted records to standardized formats without boilerplate code.
- **Supported Formats**: JSON (`.json`), Newline-Delimited JSON (`.ndjson`), Comma-Separated Values (`.csv`), SQLite relational database (`.db`).
- **Python API**: `bp.storage.export(records, "output.ndjson")`.
- **CLI**: `-o / --output` flag on `bp scrape` and `bp crawl`.
- **Status**: `VERIFIED`.

### 6. Intelligent Proxy Pool & Session Manager (`bp.proxy`)
- **Purpose**: Manages multi-node HTTP/SOCKS proxy pools with automated health tracking, round-robin/latency/least-used rotation, quarantine on failure, and sticky session binding.
- **Python API**: `bp.proxy.add_proxy(host, port, protocol)`, `bp.proxy.add_proxy_url("http://user:pass@host:port")`, `bp.proxy.get_proxy(session_id="user-1")`.
- **Integration**: Automatically binds to `AsyncApiClient` for proxy rotation.
- **Status**: `VERIFIED`.

### 7. Quantitative Point-in-Time (PiT) Alignment & ITCH-5.0 Parser (`bp.quant`)
- **Purpose**: Eliminates financial look-ahead bias by enforcing strict dual-timestamping (`period_of_report_epoch` vs `sec_dissemination_epoch`) and provides ultra-fast parsing of raw NASDAQ ITCH-5.0 binary order book messages.
- **Python API**:
  - `bp.quant.align_edgar_filing(filing_dict)`
  - `bp.quant.create_itch_parser(dollar_threshold=50000.0)`
- **MCP Tool**: `quant_pit_align`.
- **Status**: `VERIFIED`.

---

## 🧩 Unified Facade Structure (`BP`)

The `BP` facade orchestrates all domain systems under one master entry point:

```text
BP
├── bp.api             # AsyncApiClient (HTTP GET/POST/PUT/DELETE, TTL cache)
├── bp.web             # High-level web actions (navigate, click, type, extract, crawl)
├── bp.browser         # Low-level browser actions (hover, drag_and_drop, check, press)
├── bp.selectors       # Multi-tier selector resolution & self-healing memory
├── bp.proxy           # ProxyPool (health tracking, sticky sessions, rotation)
├── bp.fingerprint     # Dynamic hardware & canvas fingerprint generator
├── bp.storage         # Unified data storage manager (JSON, NDJSON, CSV, SQLite)
├── bp.quant           # SEC PiT aligner & NASDAQ ITCH-5.0 wire parser
├── bp.providers       # Provider matrix & multi-engine selector
├── bp.observability   # Performance metrics, trace logs & QA report generator
├── bp.document        # OCR image processing & autocorrect
├── bp.integrations    # Webhook notifications & integration bridges
└── bp.infrastructure  # Task queue & worker management
```

### Initializing the Facade

```python
import asyncio
from behavioral_playwright import BP, AutomationConfig, AuthConfig, BrowserConfig

async def main():
    config = AutomationConfig(
        browser=BrowserConfig(headless=True),
        auth=AuthConfig(bearer_token="my-jwt-token"),
    )

    async with BP(config=config) as bp:
        await bp.goto("https://news.ycombinator.com")
        links = await bp.extract(target="links")
        bp.storage.export(links, "hn.json")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔐 Shared Authentication Architecture

The framework features a **single, unified authentication configuration layer** shared identically across the Python API, CLI, and MCP Server.

### Configuration Hierarchy
```text
               Shared AuthConfig / AutomationConfig
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
   Python API                 CLI                  MCP Server
   (BP.api / BP)        (--api-key / --token)   (Shared BP Context)
```

### Credential Resolution Order
Credentials resolve in deterministic precedence:
1. **Explicit Instance Arguments**: Passed directly to `AuthConfig(api_key=..., bearer_token=...)`.
2. **CLI Flags**: Passed via `--api-key <key>` or `--token <token>`.
3. **Environment Variables**:
   - `BP_API_KEY`: Injects API key header (`X-API-Key` by default).
   - `BP_BEARER_TOKEN`: Injects `Authorization: Bearer <token>` header.

*Security Guarantee*: Secrets are never logged to console, exceptions, telemetry, or debug traces.

---

## 🤖 Model Context Protocol (MCP) Server

Behavioral Playwright includes a built-in standard **JSON-RPC 2.0 Stdio MCP Server** conforming to the MCP Specification (`2024-11-05`). It enables AI assistants (such as Claude Desktop, Cursor, and custom agent loops) to invoke browser automation and data tools natively.

### Starting the MCP Server
```bash
# Launch Stdio MCP Server
bp mcp-server

# Generate Claude Desktop configuration entry
bp mcp-config --python-path python
```

### Available MCP Tools

| Tool Name | Description | Arguments | Output |
| :--- | :--- | :--- | :--- |
| **`scrape_page`** | Scrapes a webpage with self-healing selectors and returns structured markdown or records. | `url` (string, required), `target` (`"links"\|"articles"\|"raw"`) | JSON array of records or HTML |
| **`crawl_domain`** | Recursively crawls URLs within a domain up to a maximum page count. | `url` (string, required), `max_pages` (int), `depth` (int) | JSON array of crawled pages |
| **`take_screenshot`**| Navigates to a URL and returns a Base64-encoded PNG screenshot for multimodal vision models. | `url` (string, required) | Base64 PNG image string |
| **`quant_pit_align`**| Validates and aligns SEC EDGAR financial filing metadata to prevent look-ahead bias. | `filing` (object, required) | Aligned Point-in-Time dictionary |
| **`get_provider_matrix`**| Reports real-time installation and availability status of all browser and network providers. | *None* | Provider status dictionary |

*Protocol Note*: Supported MCP methods are `initialize`, `ping`, `tools/list`, and `tools/call`. Unimplemented optional namespaces (`resources/list`, `prompts/list`) return standard JSON-RPC `-32601 Method not found`.

---

## 💻 Command-Line Interface (CLI)

The `bp` CLI provides instant access to framework operations from any terminal:

```bash
# 1. Display provider availability matrix
bp matrix

# 2. Scrape a webpage to JSON or CSV
bp scrape https://news.ycombinator.com -o hn.json --target links

# 3. Scrape with shared API key authentication
bp --api-key "secret-key-123" scrape https://api.example.com/data -o api_data.json

# 4. Recursively crawl a website
bp crawl https://example.com --max-pages 10 --depth 2 -o crawled.ndjson

# 5. Generate QA compliance report from metrics database
bp qa-report --db bp_metrics.db

# 6. Start standard Stdio MCP Server
bp mcp-server

# 7. Print Claude Desktop configuration entry
bp mcp-config --python-path python
```

---

## 🛡️ Multi-Provider Matrix & Status Taxonomy

The framework abstracts browser engines and network drivers through modular adapters. Availability is classified using a verified taxonomy:

| Provider ID | Subsystem | Host Status | Live Integration Status | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`patchright`** | Browser | ✔ Available | **`VERIFIED-LIVE`** | Hardened stealth Chromium with native C++ patch bindings. |
| **`playwright`** | Browser | ✔ Available | **`VERIFIED-LIVE`** | Standard high-speed Playwright Chromium/Firefox/WebKit. |
| **`uc`** | Browser | ✔ Available | **`PROVIDER-GATED-LIVE`** | Undetected-Chromedriver (Opt-in via `SQ_LIVE_UC=1`). |
| **`curl_cffi`** | Network | ✘ Optional | **`PROVIDER-GATED`** | TLS fingerprint spoofing (Raises `ProviderUnavailableError` if absent). |
| **`browser_use`**| AI Agent | ✘ Optional | **`PROVIDER-GATED`** | LangChain/LLM browser agent (Requires LLM API key). |
| **`stagehand`** | AI Agent | ✘ Optional | **`PROVIDER-GATED`** | TypeScript Stagehand AI bridge (Requires Model + Key). |

---

## 📊 Comprehensive Feature Matrix

| Feature | Namespace | Python API | MCP Tool | CLI | Fallback | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Direct Async API** | `bp.api` | `bp.api.get()`, `post()` | *Internal* | `bp` flags | Raw socket fetch | `VERIFIED` |
| **In-Memory TTL Cache** | `bp.api` | `bp.api.cache.get()` | *Internal* | *Automatic* | Fresh network call | `VERIFIED` |
| **Proxy Pool Rotation** | `bp.proxy` | `bp.proxy.get_proxy()` | *Internal* | *Automatic* | Direct connection | `VERIFIED` |
| **Circuit Breaker** | `bp.resilience`| `CircuitBreaker.execute()`| *Internal* | *Automatic* | Direct exception | `VERIFIED` |
| **V15 Stealth Evasion** | `bp.core` | Active on `bp.goto()` | `scrape_page` | `bp scrape` | Standard browser | `VERIFIED` |
| **Self-Healing Selectors**| `bp.selectors`| `bp.resolve_selector()` | `scrape_page` | `bp scrape` | L1 ➔ L2 ➔ L3 | `VERIFIED` |
| **Structured Extraction**| `bp.web` | `bp.extract()` | `scrape_page` | `bp scrape` | Raw outerHTML | `VERIFIED` |
| **Recursive Crawling** | `bp.web` | `bp.crawl()` | `crawl_domain`| `bp crawl` | Single page goto | `VERIFIED` |
| **Viewport Screenshot** | `bp.browser` | `bp.screenshot()` | `take_screenshot`| *Python API*| DOM HTML dump | `VERIFIED` |
| **Point-in-Time Aligner** | `bp.quant` | `bp.quant.align_edgar_filing()`| `quant_pit_align` | *Python API*| Manual timestamp | `VERIFIED` |
| **ITCH-5.0 Binary Parser**| `bp.quant` | `bp.quant.create_itch_parser()`| *Python API* | *Python API*| LOB reconstructor | `VERIFIED` |
| **OCR Image Extractor** | `bp.document` | `bp.document.ocr_image()`| *Internal* | *Python API*| Raw image | `VERIFIED` |
| **Stdio MCP Server** | `bp.mcp` | `McpServer().run_stdio()` | *Host* | `bp mcp-server`| Facade API | `VERIFIED` |

---

## 🔀 Fallback & Routing Decision Matrix

```text
                                  User Request
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
        Direct API / JSON Data                        Rendered Web Content
                │                                             │
      AsyncApiClient (bp.api)                        Headless Browser (BP)
                │                                             │
      ┌─────────┴─────────┐                         ┌─────────┴─────────┐
      ▼                   ▼                         ▼                   ▼
Cache Hit?            Cache Miss              Patchright Available?   Playwright Fallback
      │                   │                         │                   │
Return 0.0ms        Execute Request           Verified-Live       Standard Chromium
                          │                         │                   │
                    Circuit Breaker                 └─────────┬─────────┘
                    Protected Fetch                           ▼
                          │                         Self-Healing Selectors
                   ProxyPool Routed                 (L1 Exact ➔ L2 Semantic ➔ L3 Fuzzy)
```

---

## ⚠️ Known Limitations & Engineering Notes

1. **Connection Pooling**: `AsyncApiClient` uses Python's standard library `urllib.request` running in an asynchronous threadpool. High-concurrency connection pooling using `curl_cffi` is optional roadmap work.
2. **Cache Storage**: `ApiRequestCache` is an in-memory TTL dictionary. Multi-session SQLite disk persistence and HTTP ETag validation are future enhancements.
3. **MCP Server Scope**: The MCP server focuses on tool execution (`tools/list`, `tools/call`). Resource/prompt listing methods return standard `-32601` error codes.
4. **Third-Party AI Agent Providers**: `Browser-Use` and `Stagehand` require active external LLM API credentials and dependencies.

---

## 🧪 Verified Test Suite

```bash
$ python -m pytest tests/ -q
........................................................................ [ 39%]
........s............................................................... [ 79%]
......................................                                   [100%]
181 passed, 1 skipped in 21.72s
```

- **Core Baseline Protection**: 13 tests (`tests/test_baseline_protection.py`)
- **Honesty Hardening & Synthetic Contract Guards**: 11 tests (`tests/test_honesty_hardening.py`)
- **NASDAQ ITCH-5.0 Binary Wire Parser**: 17 tests (`tests/test_itch_binary.py`)
- **Multi-Provider Verification & Doubles**: 18 tests (`tests/test_providers.py`)
- **V23 Quarantine Pins**: 7 tests (`tests/test_v23_quarantine.py`)
- **Unit & Domain Tests**: 113 tests (`tests/unit/`)
- **Integration Tests**: 3 tests (`tests/integration/`)


---

## 📄 License

Behavioral Playwright is released under the **MIT License**.
