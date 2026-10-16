# Architecture Overview & Engineering Philosophy

> **Framework Version**: `10.0.2 Quantum Architecture`  
> **Status**: [VERIFIED & PASSING 742 GATES]

---

## 1. System Vision & Purpose
**Behavioral Playwright** (powered by the **Veil** engine) is an autonomous, high-resilience web automation and data intelligence platform in Python. It solves the critical fragility and bot-detection challenges associated with standard browser automation through four pillars:
1. **Bio-Emulated Behavioral Humanization**: Replaces synthetic browser signals with biomechanical trajectories, log-normal keystroke timing, and realistic saccade scrolling.
2. **Zero-Cost Local Architecture**: All essential capabilities (crawling, scraping, document parsing, OCR, vector ranking, queueing, caching) run 100% locally with zero cloud subscription fees.
3. **3-Tier Clean Architecture**: Strict separation of concerns between Controllers/Routers, Domain Services, and Repository persistence abstractions under `src/veil/`.
4. **Unified Ergonomic Facade (`BP`)**: A fluent, decoupled public API that coordinates underlying domain subsystems without god-object anti-patterns.

---

## 2. Core Architectural Structure

### I. 3-Tier Clean Architecture Layering (`src/veil/`)

```text
src/
├── veil/                                  # Pure Clean Architecture Core
│   ├── api/                               # Direct HTTP client with connection pooling
│   ├── automation/                        # Biomechanical input controllers (mouse, keyboard, scroll)
│   ├── crawling/                          # 4-tier adaptive crawler, SQLite WAL, SimHash dedup
│   ├── extraction/                        # DOM extraction & lossless block-tree compression
│   ├── kinematics/                        # Physical trajectory generators, Saccades & micro-tremor
│   ├── mapping/                           # Structural site & DOM tree mapper
│   ├── mcp/                               # JSON-RPC 2.0 MCP server with 20+ tools
│   ├── mining/                            # SEO, AEO, PAA, & Google Suggest intelligence miners
│   ├── models/                            # Typed Pydantic request/response DTOs and contracts
│   ├── orchestration/                     # Declarative workflow planners and execution engines
│   ├── powerplay/                         # High-level behavioral orchestrator & schema sentinels
│   ├── providers/                         # Multi-engine browser & network adapters
│   ├── resilience/                        # Circuit breakers, retry policy, self-healing memory
│   ├── security/                          # GraphQL, CSRF, IDOR, and OOB attack listeners
│   ├── selectors/                         # Multi-tier self-healing selector resolvers (CSS, ARIA, Fuzzy)
│   ├── storage/                           # Multi-format exporters (JSON, NDJSON, CSV, SQLite)
│   └── verification/                      # Live DOM auditor & rendering assertion sentinels
└── behavioral_playwright/                 # 100% Backward-Compatible Symbol Parity Facade Layer
    └── facade.py                          # Unified `BP` entrypoint delegating to `veil` subsystems
```

### II. Unified Facade Subsystems

```text
BP (Coordinator & Context Manager)
├── bp.web             (Stateless Web & 4-Tier Adaptive Crawling)
├── bp.browser         (Stateful Playwright Humanization)
├── bp.document        (PDF/DOCX & Tesseract OCR)
├── bp.ai              (Multilingual TF-IDF & Schema Validation)
├── bp.network         (Real HTTP Latency & Compression)
├── bp.integrations    (Webhooks & MCP Tool Bridges)
├── bp.infrastructure  (SQLite WAL Queue & Encrypted Cache)
├── bp.observability   (Metrics, Traces & QA Reports)
├── bp.intelligence   (Shield Detection & Levenshtein Healing)
└── bp.powerplay       (Kinematic Orchestration & Schema Guards)
```

---

## 3. Engineering Invariants

### I. Truth Over Simulation
Never use simulated delays (`hash(url) % 50`), fake return values (`return True`), or placeholder responses. If an engine or provider is unavailable, raise explicit exceptions (`ProviderUnavailableError`, `ProviderError`) so upstream callers can adapt or fail cleanly.

### II. Non-Blocking Async Event Loop
Any CPU-intensive or blocking synchronous I/O (such as `pytesseract` image decoding, `urllib.request` socket probes, or file writes) MUST be offloaded to worker threads via `asyncio.to_thread` to prevent stalling the `asyncio` event loop.

### III. DDL & DML Separation in Observability
Database schema definitions (`CREATE TABLE`) must be executed during initialization or cached in-memory. Regular metric writes and telemetry logging must execute pure DML (`INSERT`) statements to prevent disk lock thrashing.
