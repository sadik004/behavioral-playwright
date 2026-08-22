# Development & Release Changelog

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## [Unreleased / Stable HEAD] - 2026-08-22
- **Documentation**: Added complete 20-section `README.md` and created the permanent engineering knowledge base in `docs/` (`architecture/`, `core/`, `features/`, `decisions/`, `evolution/`, `debugging/`, `testing/`, `usage/`).

## [v1.0.0-facade] - Commit `bdfbb3d`
- **Feature**: Completed Parts 1–7 refactor consolidating 109 capabilities into 9 decoupled namespaces in `bp_facade12.py`.
- **Fix**: Replaced crawler mock links with real BFS crawler using BeautifulSoup4 and SQLite.
- **Fix**: Replaced mock OCR with real PIL contrast enhancement and Tesseract worker thread execution.
- **Fix**: Replaced simulated network latency with real HTTP HEAD probe and monotonic performance counter timing.
- **Fix**: Implemented real HTTP POST webhook dispatchers and MCP tool bridge.
- **Optimization**: Separated DDL table creation from metric logging via in-memory DDL caching in `ObservabilityNamespace`.
- **Testing**: Added 39 automated tests across 6 dedicated test suites.

## [v10.1.0a1] - Commit `9715118`
- **Feature**: Added initial unified BP facade class and core workflows (`crawling`, `mapping`, `search`, `handoff`, `verification`).

## [v1.0.0] - Commit `381be14`
- **Feature**: Clean-room rewrite decoupling controllers, cascading `SelfHealingResolver`, DOM extractors, and resilience state trackers into `behavioral_playwright/`.
