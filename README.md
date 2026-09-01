# Behavioral Playwright (AI-Native Enterprise Hardened Edition)

[![Test Suite](https://img.shields.io/badge/tests-181%20passed%2C%201%20skipped-brightgreen.svg)](https://github.com/sadik004/behavioral-playwright)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![MCP Standard](https://img.shields.io/badge/MCP%20Spec-2024--11--05-orange.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Architecture](https://img.shields.io/badge/Architecture-Enterprise%20Clean%20%2F%20Decoupled-purple.svg)](https://github.com/sadik004/behavioral-playwright)

A resilient, self-healing browser automation, direct HTTP API, and stealth AI agent execution framework built on Playwright with multi-provider bridges, high-frequency quantitative market data pipelines, dynamic proxy pool & device fingerprint generators, deep behavioral evasion, and standard Model Context Protocol (MCP) tool integration.

---

## 📑 Table of Contents

- [🏛️ Architecture Overview](#️-architecture-overview)
- [⚡ Quick Start Guide](#-quick-start-guide)
- [🤖 AI Agent Decision & Routing Guide](#-ai-agent-decision--routing-guide)
- [📚 Comprehensive 180+ Feature Reference](#-comprehensive-180-feature-reference)
  - [1. Biomechanical Automation & Human Mimicry](#1-biomechanical-automation--human-mimicry-bpautomation--bpbrowser)
  - [2. 10-Layer Hardened Stealth Evasion (V15 Core)](#2-10-layer-hardened-stealth-evasion-v15-core-bpcore)
  - [3. Multi-Tier Self-Healing Selector Engine](#3-multi-tier-self-healing-selector-engine-bpselectors)
  - [4. Direct High-Speed Asynchronous API Client](#4-direct-high-speed-asynchronous-api-client-bpapi)
  - [5. Model Context Protocol (MCP) Stdio Server](#5-model-context-protocol-mcp-stdio-server-bpmcp)
  - [6. Multi-Engine Provider Architecture](#6-multi-engine-provider-architecture-bpproviders)
  - [7. Intelligent Proxy Pool & Session Management](#7-intelligent-proxy-pool--session-management-bpproxy)
  - [8. Enterprise Resilience & Circuit Breaker](#8-enterprise-resilience--circuit-breaker-bpresilience)
  - [9. Asynchronous Recursive Crawler & Sitemap Parser](#9-asynchronous-recursive-crawler--sitemap-parser-bpcrawling)
  - [10. Quantitative SEC Point-in-Time & NASDAQ ITCH-5.0 Parser](#10-quantitative-sec-point-in-time--nasdaq-itch-50-parser-bpquant)
  - [11. Unified Multi-Format Storage & Exporters](#11-unified-multi-format-storage--exporters-bpstorage)
  - [12. Observability, Telemetry & QA Reporting](#12-observability-telemetry--qa-reporting-bpobservability)
- [🧩 Unified Facade (`BP`) API Reference](#-unified-facade-bp-api-reference)
- [🔐 Shared Authentication Architecture](#-shared-authentication-architecture)
- [🤖 Claude Desktop & Cursor AI Setup Guide](#-claude-desktop--cursor-ai-setup-guide)
- [💻 Complete CLI Command Reference](#-complete-cli-command-reference)
- [🛡️ Multi-Provider Matrix & Status Taxonomy](#️-multi-provider-matrix--status-taxonomy)
- [🔀 Fallback & Routing Decision Matrix](#-fallback--routing-decision-matrix)
- [⚠️ Known Limitations & Engineering Honesty](#️-known-limitations--engineering-honesty)
- [🧪 Verified Test Suite](#-verified-test-suite)
- [📄 License](#-license)

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
    ├── unit/                              # 113 unit tests (all modules & namespaces covered)
    ├── integration/                       # 3 multi-component and live provider tests
    ├── test_baseline_protection.py        # 13 core V15 baseline capability protection tests
    ├── test_honesty_hardening.py          # 11 data contract & honesty hardening tests
    ├── test_itch_binary.py                # 17 NASDAQ ITCH-5.0 wire parser verification tests
    ├── test_providers.py                  # 18 multi-provider live & double verification tests
    └── test_v23_quarantine.py             # 7 V23 quarantine pins
```

---

## ⚡ Quick Start Guide

### Installation

```bash
# Clone the repository
git clone https://github.com/sadik004/behavioral-playwright.git
cd behavioral-playwright

# Install dependencies in editable mode
pip install -e .

# Install Playwright browser binaries
playwright install chromium
```

### 1. Basic Web Scraping with Self-Healing Selectors

```python
import asyncio
from behavioral_playwright import BP

async def main():
    async with BP() as bp:
        await bp.goto("https://news.ycombinator.com")
        # Extract structured link records
        records = await bp.extract(target="links")
        print(f"Extracted {len(records)} links")
        # Export to SQLite and JSON
        bp.storage.export(records, "hackernews.db")
        bp.storage.export(records, "hackernews.json")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. High-Speed API Request with In-Memory Caching

```python
import asyncio
from behavioral_playwright import BP, AutomationConfig, AuthConfig

async def main():
    config = AutomationConfig(
        auth=AuthConfig(bearer_token="demo-token-xyz")
    )
    async with BP(config=config) as bp:
        # High speed fetch without launching a browser
        response = await bp.api.get("https://httpbin.org/bearer")
        print("Status:", response.status_code)
        print("Payload:", response.json())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🤖 AI Agent Decision & Routing Guide

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

## 📚 Comprehensive 180+ Feature Reference

### 1. Biomechanical Automation & Human Mimicry (`bp.automation` / `bp.browser`)
- **Bézier Mouse Trajectories**: Calculates cubic Bézier curves with natural acceleration/deceleration profiles to avoid linear robotic path detection.
- **Sub-Pixel Micro-Jitter**: Introduces realistic human tremoring during mouse moves and hover events.
- **Variable Key Dwell Times**: Simulates organic keystrokes with randomized press-and-release durations based on human typing speed distributions.
- **Humanized Page Scrolling**: Mimics natural reading gestures with ease-out friction scrolling and random pauses.
- **Native Context Actions**: Supports drag-and-drop, right-click, double-click, keyboard shortcuts, and form auto-filling.

```python
async with BP() as bp:
    await bp.goto("https://example.com/login")
    await bp.type("input[type='email']", "user@example.com")
    await bp.type("input[type='password']", "securepassword123")
    await bp.click("button[type='submit']")
```

---

### 2. 10-Layer Hardened Stealth Evasion (V15 Core) (`bp.core`)
- **Layer 1 - Navigator Webdriver Concealment**: Overrides `navigator.webdriver` to `undefined` with native accessor traps.
- **Layer 2 - Chrome Runtime Simulation**: Emulates `window.chrome.runtime`, `csi`, and `loadTimes`.
- **Layer 3 - Permissions Query Neutralization**: Spoofs `navigator.permissions.query({name: 'notifications'})` to return standard `prompt` states.
- **Layer 4 - WebGL & Canvas Noise**: Injects sub-pixel pseudo-random noise into Canvas 2D image data and WebGL render targets to defeat browser canvas fingerprinting.
- **Layer 5 - AudioContext Noise Injection**: Applies imperceptible frequency modulation to WebAudio oscillators.
- **Layer 6 - Plugin & MimeType Array Spoofing**: Simulates standard PDF viewer and Widevine DRM plugins.
- **Layer 7 - Battery & Network API Spoofing**: Mock dynamic battery status and standard `navigator.connection` RTT/downlink metrics.
- **Layer 8 - Screen & Hardware Concurrency**: Dynamic resolution matching and realistic CPU core allocations (`hardwareConcurrency: 8`).
- **Layer 9 - DevTools Detection Shield**: Bypasses `console.table` profiling and debugger timing detection traps.
- **Layer 10 - WebRTC Leak Prevention**: Sanitizes STUN/TURN candidate discovery to prevent real IP exposure.

---

### 3. Multi-Tier Self-Healing Selector Engine (`bp.selectors`)
- **Tier 1 (L1 Exact)**: High-speed resolution using standard CSS / XPath expressions.
- **Tier 2 (L2 Semantic / ARIA)**: Falls back to ARIA roles, labels, placeholders, titles, and visible text content.
- **Tier 3 (L3 Levenshtein Fuzzy)**: Uses Levenshtein distance and token similarity scoring across all interactive elements (confidence threshold >= 0.65).
- **Self-Healing Memory**: Caches successful healed selectors in memory to accelerate future interactions across the session.

```python
async with BP() as bp:
    await bp.goto("https://example.com")
    # Even if the class or ID changes in production, self-healing resolves the button
    element = await bp.resolve_selector("button.checkout-btn-v2")
    await bp.click(element)
```

---

### 4. Direct High-Speed Asynchronous API Client (`bp.api`)
- **Pure Async HTTP**: Provides non-browser REST capabilities (`GET`, `POST`, `PUT`, `DELETE`).
- **Auth-Fingerprinted In-Memory TTL Cache**: Isolates cached responses per authentication credential, preventing cross-tenant data leaks.
- **ProxyPool Health Tracking**: Automatically routes calls through active proxies and reports response latency/failures.
- **Circuit Breaker Protection**: Blocks outgoing requests when upstream errors breach thresholds.

```python
async with BP() as bp:
    resp = await bp.api.get("https://api.example.com/items", cache_ttl=120.0)
    print("Items:", resp.json())
```

---

### 5. Model Context Protocol (MCP) Stdio Server (`bp.mcp`)
- **JSON-RPC 2.0 Compliance**: Operates over Stdio conforming to MCP Specification `2024-11-05`.
- **5 Registered AI Tools**:
  1. `scrape_page`: Self-healing DOM extraction and markdown generator.
  2. `crawl_domain`: Multi-page recursive crawler.
  3. `take_screenshot`: Base64 PNG viewport capture for multimodal vision LLMs.
  4. `quant_pit_align`: SEC EDGAR Point-in-Time metadata validator.
  5. `get_provider_matrix`: Live host engine and network driver status inspector.

---

### 6. Multi-Engine Provider Architecture (`bp.providers`)
- **Dynamic Adapter Matrix**: Transparently integrates multiple browser and AI agent engines:
  - `patchright`: Hardened stealth Chromium with native C++ patches.
  - `playwright`: High-speed standard browser automation.
  - `uc`: Undetected-Chromedriver (Opt-in via `SQ_LIVE_UC=1`).
  - `curl_cffi`: Low-level TLS fingerprint spoofing.
  - `browser_use`: LangChain/LLM browser agent bridge.
  - `stagehand`: TypeScript AI agent bridge.

---

### 7. Intelligent Proxy Pool & Session Management (`bp.proxy`)
- **Multiple Protocols**: HTTP, HTTPS, SOCKS4, SOCKS5.
- **Rotation Algorithms**: Round-Robin, Least-Used, and Latency-Optimized.
- **Automated Quarantine**: Isolates failing proxy nodes after consecutive timeouts or HTTP 5xx responses.
- **Sticky Sessions**: Binds session IDs to specific proxy nodes for consistent stateful interactions.

```python
from behavioral_playwright import BP, ProxyProtocol

async with BP() as bp:
    bp.proxy.add_proxy(host="192.168.1.100", port=8080, protocol=ProxyProtocol.HTTP)
    bp.proxy.add_proxy(host="192.168.1.101", port=8080, protocol=ProxyProtocol.SOCKS5)
    proxy_node = bp.proxy.get_proxy(session_id="user-session-42")
    print("Using Proxy:", proxy_node.url)
```

---

### 8. Enterprise Resilience & Circuit Breaker (`bp.resilience`)
- **Circuit Breaker State Machine**: `CLOSED` (Normal) ➔ `OPEN` (Tripped / Fast Failure) ➔ `HALF_OPEN` (Trial Recovery).
- **Exponential Backoff**: Automatic retry policies with jitter to avoid thundering herd problems.
- **Fallback Cascading**: Gracefully downgrades from enhanced providers to standard engines.

---

### 9. Asynchronous Recursive Crawler & Sitemap Parser (`bp.crawling`)
- **Depth-Limited Crawling**: Traverses internal domain links while respecting concurrency limits.
- **Sitemap Parser**: Ingests `sitemap.xml` for systematic URL discovery.
- **Politeness Rules**: Configurable request delays and domain blacklists.

---

### 10. Quantitative SEC Point-in-Time & NASDAQ ITCH-5.0 Parser (`bp.quant`)
- **SEC EDGAR PiT Aligner**: Eliminates look-ahead bias in algorithmic trading strategies by aligning `period_of_report_epoch` with `sec_dissemination_epoch`.
- **NASDAQ ITCH-5.0 Binary Wire Parser**: Parses raw 40-byte ITCH messages at microsecond speeds, filtering order book executions by dollar threshold.

```python
async with BP() as bp:
    aligned = bp.quant.align_edgar_filing({
        "cik": "0000320193",
        "period_of_report_epoch": 1700000000.0,
        "sec_dissemination_epoch": 1700086400.0,
        "metrics": {"revenue": 89500000000}
    })
    print("Point-in-Time Verified:", aligned["valid_for_backtest"])
```

---

### 11. Unified Multi-Format Storage & Exporters (`bp.storage`)
- **Seamless Format Serialization**: Exports structured records to `.json`, `.ndjson`, `.csv`, and relational `.db` (SQLite).
- **Automatic Schema Mapping**: Automatically maps dictionary records to SQLite table columns with primary keys and timestamps.

```python
records = [{"id": 1, "title": "Article One"}, {"id": 2, "title": "Article Two"}]
bp.storage.export(records, "articles.ndjson")
bp.storage.export(records, "articles.db", table_name="articles")
```

---

### 12. Observability, Telemetry & QA Reporting (`bp.observability`)
- **SQLite Event Telemetry**: Records performance metrics, navigation latency, selector healing events, and proxy health in a persistent SQLite telemetry store.
- **Automated QA Compliance Reports**: Generates structured summaries of system performance and compliance scorecards.

---

## 🧩 Unified Facade (`BP`) API Reference

The `BP` class acts as the single master entry point coordinating all 12 domain namespaces:

```python
from behavioral_playwright import BP, AutomationConfig, AuthConfig, BrowserConfig

config = AutomationConfig(
    browser=BrowserConfig(headless=True),
    auth=AuthConfig(api_key="secret-key", bearer_token="bearer-token"),
)

async with BP(config=config) as bp:
    # 1. Web Automation
    await bp.goto("https://example.com")
    await bp.type("input.search", "Playwright")
    await bp.click("button.search")

    # 2. DOM Extraction
    records = await bp.extract(target="links")

    # 3. Direct API Fetching
    api_resp = await bp.api.get("https://api.example.com/status")

    # 4. Storage
    bp.storage.export(records, "output.json")

    # 5. Visual Capture
    png_bytes = await bp.screenshot()

    # 6. Provider Matrix Inspection
    matrix = bp.providers.matrix()
```

---

## 🔐 Shared Authentication Architecture

The framework implements a **single, unified authentication configuration layer** shared across Python API, CLI, and MCP Server:

```text
               Shared AuthConfig / AutomationConfig
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
    Python API                 CLI                  MCP Server
    (BP.api / BP)        (--api-key / --token)   (Shared BP Context)
```

### Deterministic Resolution Precedence
1. **Explicit Instance Arguments**: Passed to `AuthConfig(api_key=..., bearer_token=...)`.
2. **CLI Flags**: Passed via `--api-key <key>` or `--token <token>`.
3. **Environment Variables**:
   - `BP_API_KEY`: Injects `X-API-Key: <key>` header.
   - `BP_BEARER_TOKEN`: Injects `Authorization: Bearer <token>` header.

*Security Guarantee*: Secrets are never logged to console, exceptions, telemetry, or debug traces.

---

## 🤖 Claude Desktop & Cursor AI Setup Guide

Connect Behavioral Playwright to Claude Desktop or Cursor to enable natural language web extraction and browser control:

### 1. Generate MCP Configuration

```bash
bp mcp-config --python-path python
```

### 2. Configure Claude Desktop

Add the server definition to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "behavioral-playwright": {
      "command": "python",
      "args": ["-m", "behavioral_playwright.mcp.server"]
    }
  }
}
```

Now you can ask Claude:
- *"Scrape the top stories from Hacker News using the scrape_page tool."*
- *"Take a screenshot of github.com and analyze its layout."*
- *"Crawl example.com up to 5 pages and extract all links."*

---

## 💻 Complete CLI Command Reference

The `bp` command-line tool provides instant access to all core framework operations:

```bash
# Display provider availability matrix
bp matrix

# Scrape a webpage to JSON
bp scrape https://news.ycombinator.com -o hn.json --target links

# Scrape with shared API key authentication
bp --api-key "secret-key-123" scrape https://api.example.com/data -o api_data.json

# Recursively crawl a website
bp crawl https://example.com --max-pages 10 --depth 2 -o crawled.ndjson

# Generate QA compliance report
bp qa-report --db bp_metrics.db

# Launch Stdio MCP Server
bp mcp-server

# Print Claude Desktop configuration entry
bp mcp-config --python-path python
```

---

## 🛡️ Multi-Provider Matrix & Status Taxonomy

| Provider ID | Subsystem | Host Status | Live Integration Status | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`patchright`** | Browser | ✔ Available | **`VERIFIED-LIVE`** | Hardened stealth Chromium with native C++ patch bindings. |
| **`playwright`** | Browser | ✔ Available | **`VERIFIED-LIVE`** | Standard high-speed Playwright Chromium/Firefox/WebKit. |
| **`uc`** | Browser | ✔ Available | **`PROVIDER-GATED-LIVE`** | Undetected-Chromedriver (Opt-in via `SQ_LIVE_UC=1`). |
| **`curl_cffi`** | Network | ✘ Optional | **`PROVIDER-GATED`** | TLS fingerprint spoofing (Raises `ProviderUnavailableError` if absent). |
| **`browser_use`**| AI Agent | ✘ Optional | **`PROVIDER-GATED`** | LangChain/LLM browser agent (Requires LLM API key). |
| **`stagehand`** | AI Agent | ✘ Optional | **`PROVIDER-GATED`** | TypeScript AI agent bridge (Requires Model + Key). |

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

## ⚠️ Known Limitations & Engineering Honesty

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
181 passed, 1 skipped in 20.60s
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
