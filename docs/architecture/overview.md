# Architecture Overview & Engineering Philosophy

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. System Vision & Purpose
**Behavioral Playwright** is an autonomous, high-resilience web automation and data intelligence platform in Python. It solves the critical fragility and bot-detection challenges associated with standard browser automation through three pillars:
1. **Bio-Emulated Behavioral Humanization**: Replaces synthetic browser signals with biomechanical trajectories, log-normal keystroke timing, and realistic saccade scrolling.
2. **Zero-Cost Local Architecture**: All essential capabilities (crawling, scraping, document parsing, OCR, vector ranking, queueing, caching) run 100% locally with zero cloud subscription fees.
3. **Decoupled 9-Namespace Structure**: Provides clean domain separation beneath a unified, ergonomic `BP` facade.

---

## 2. Core Architectural Principles

### I. Thin Facade, Rich Namespaces
The top-level `BP` class acts exclusively as a lifecycle coordinator and method forwarder. It contains minimal internal logic, delegating domain responsibilities directly to the 9 underlying namespaces.

```text
BP (Coordinator & Context Manager)
├── bp.web             (Stateless Web & Acquisition)
├── bp.browser         (Stateful Playwright Humanization)
├── bp.document        (PDF/DOCX & Tesseract OCR)
├── bp.ai              (Multilingual TF-IDF & Schema Validation)
├── bp.network         (Real HTTP Latency & Compression)
├── bp.integrations    (Webhooks & MCP Tool Bridges)
├── bp.infrastructure  (SQLite WAL Queue & Encrypted Cache)
├── bp.observability   (Metrics, Traces & QA Reports)
└── bp.intelligence   (Shield Detection & Levenshtein Healing)
```

### II. Truth Over Simulation
Never use simulated delays (`hash(url) % 50`), fake return values (`return True`), or placeholder responses. If an engine or provider is unavailable, raise explicit exceptions (`ProviderUnavailableError`, `ProviderError`) so upstream callers can adapt or fail cleanly.

### III. Non-Blocking Async Event Loop
Any CPU-intensive or blocking synchronous I/O (such as `pytesseract` image decoding, `urllib.request` socket probes, or file writes) MUST be offloaded to worker threads via `asyncio.to_thread` to prevent stalling the `asyncio` event loop.

### IV. DDL & DML Separation in Observability
Database schema definitions (`CREATE TABLE`) must be executed during initialization or cached in-memory. Regular metric writes and telemetry logging must execute pure DML (`INSERT`) statements to prevent disk lock thrashing.
