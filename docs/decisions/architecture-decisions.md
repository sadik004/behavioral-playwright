# Architecture Decision Records (ADRs)

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## ADR-001: 9-Namespace Domain Architecture
- **Context**: The `BP` public API surface had grown to 109 capabilities. Consolidating all methods into a single class caused massive method pollution and poor maintainability.
- **Problem**: How to provide an intuitive, single-import developer experience without creating a monolithic, unmaintainable class.
- **Chosen Solution**: Partitioned all capabilities into 9 domain namespaces (`web`, `browser`, `document`, `ai`, `network`, `integrations`, `infrastructure`, `observability`, `intelligence`), exposed via a thin coordinator facade (`BP`).
- **Consequences**: Clear separation of concerns, isolated testing per domain, and full backward compatibility via top-level delegation aliases.
- **Status**: Accepted & Implemented.

---

## ADR-002: Zero-Cost Offline Core (No Mandatory Cloud Subscriptions)
- **Context**: Many automation platforms enforce external API subscriptions (e.g. Firecrawl, cloud OCR, paid LLM endpoints) for basic functionality.
- **Problem**: Users require an autonomous scraping, crawling, and OCR pipeline that functions offline and locally with zero operational cost.
- **Chosen Solution**: Implemented local BeautifulSoup4 DOM parsing, local bounded BFS crawling, local Tesseract OCR with contrast enhancement, and local TF-IDF vector ranking. External providers remain optional plugins.
- **Consequences**: High privacy, zero per-run fees, and offline testability.
- **Status**: Accepted & Implemented.

---

## ADR-003: Non-Blocking Event Loop with Worker Thread Offloading
- **Context**: Operations like `pytesseract` image OCR, `urllib.request` socket probes, and SQLite disk writes are blocking synchronous calls.
- **Problem**: Calling synchronous I/O directly inside `async def` methods blocks the Python `asyncio` event loop, freezing concurrent tasks.
- **Chosen Solution**: Offloaded all synchronous blocking operations to thread pools via `asyncio.to_thread`.
- **Consequences**: Clean async execution, zero loop freezing, and seamless concurrency.
- **Status**: Accepted & Implemented.

---

## ADR-004: In-Memory DDL Caching for Observability
- **Context**: The observability namespace writes metric logs and session replays to SQLite frequently.
- **Problem**: Repeatedly executing `CREATE TABLE IF NOT EXISTS` on every write caused severe disk contention and latency penalties.
- **Chosen Solution**: Maintained an in-memory set `_initialized_dbs` tracking initialized databases. Schema DDL is executed once; subsequent writes perform pure DML `INSERT` statements.
- **Consequences**: Drastic latency reduction in metric logging with zero database locking overhead.
- **Status**: Accepted & Implemented.

---

## ADR-005: Dual-Layer Browser Action Fallbacks
- **Context**: Advanced humanizer algorithms require layout coordinates and mathematical physics engines that may not always be mounted.
- **Problem**: Browser automation calls would crash if optional humanizer models failed or were absent.
- **Chosen Solution**: Implemented a try/except delegation wrapper that executes `BehavioralHumanizer` algorithms and automatically falls back to native Playwright `page` methods on failure.
- **Consequences**: Bulletproof reliability and smooth graceful degradation.
- **Status**: Accepted & Implemented.
