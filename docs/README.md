# Behavioral Playwright — Permanent Engineering Knowledge Base & Documentation Index

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED] Production Documentation & Architecture Truth Engine

Welcome to the comprehensive engineering documentation for **Behavioral Playwright**. This directory serves as the single source of truth for the system's architecture, historical evolution, operational guidelines, debugging knowledge, and usage manuals.

---

## 📚 Documentation Index

### 1. Architecture & System Design (`docs/architecture/`)
- [Overview & Philosophy](file:///c:/Users/User/SAA/docs/architecture/overview.md): High-level mission, core paradigms, and zero-cost design principles.
- [System Execution Flow](file:///c:/Users/User/SAA/docs/architecture/system-flow.md): Step-by-step lifecycle from initialization to teardown.
- [Dependency Map](file:///c:/Users/User/SAA/docs/architecture/dependency-map.md): Source-level module relationships and boundaries.
- [Namespace Architecture](file:///c:/Users/User/SAA/docs/architecture/namespace-architecture.md): Deep dive into the 9 decoupled namespaces.
- [Acquisition Architecture](file:///c:/Users/User/SAA/docs/architecture/acquisition-architecture.md): Router design, providers, and DOM extraction pipelines.
- [Browser Architecture](file:///c:/Users/User/SAA/docs/architecture/browser-architecture.md): CDP shims, session management, and Playwright integration.
- [Data Flow & Caching](file:///c:/Users/User/SAA/docs/architecture/data-flow.md): How data moves through queues, transformers, and SQLite.
- [Future Development](file:///c:/Users/User/SAA/docs/architecture/future-development.md): Roadmap and guidelines for non-breaking extensions.

### 2. Core Foundations (`docs/core/`)
- [V10 Quantum Heritage](file:///c:/Users/User/SAA/docs/core/v10-core.md): Analysis of the monolithic V10 math/physics engine.
- [Behavioral Humanizer](file:///c:/Users/User/SAA/docs/core/behavioral-humanizer.md): Biomechanical mouse curves, keystroke hold models, and saccades.
- [Navigation & Resilience](file:///c:/Users/User/SAA/docs/core/navigation.md): Circuit breaker state machines and loop detection.
- [Stealth & Anti-Detection](file:///c:/Users/User/SAA/docs/core/stealth.md): CDP evasion, prototype guards, and canvas jittering.

### 3. Namespace Feature Specifications (`docs/features/`)
- [Web Namespace (`bp.web`)](file:///c:/Users/User/SAA/docs/features/web.md): Scraping, recursive crawling, sitemaps, and robots.txt.
- [Browser Namespace (`bp.browser`)](file:///c:/Users/User/SAA/docs/features/browser.md): Form controls, focus-blur, and screenshots.
- [Document Namespace (`bp.document`)](file:///c:/Users/User/SAA/docs/features/document.md): PDF spatial parsing, DOCX, and contrast OCR.
- [AI Namespace (`bp.ai`)](file:///c:/Users/User/SAA/docs/features/ai.md): Multilingual TF-IDF re-ranking and schema coercion.
- [Network Namespace (`bp.network`)](file:///c:/Users/User/SAA/docs/features/network.md): Real HTTP latency probers and gzip compression.
- [Integrations Namespace (`bp.integrations`)](file:///c:/Users/User/SAA/docs/features/integrations.md): Webhooks, MCP tool bridge, and HAR export.
- [Infrastructure Namespace (`bp.infrastructure`)](file:///c:/Users/User/SAA/docs/features/infrastructure.md): SQLite task queues and encrypted caching.
- [Observability Namespace (`bp.observability`)](file:///c:/Users/User/SAA/docs/features/observability.md): Performance traces, DDL caching, and QA audits.
- [Intelligence Namespace (`bp.intelligence`)](file:///c:/Users/User/SAA/docs/features/intelligence.md): Bot shield detection and Levenshtein healing.

### 4. Engineering Decisions & History (`docs/decisions/`, `docs/evolution/`, `docs/changelog/`)
- [Architecture Decision Records (ADRs)](file:///c:/Users/User/SAA/docs/decisions/architecture-decisions.md): Formal record of key technical choices.
- [Project Evolution](file:///c:/Users/User/SAA/docs/evolution/project-history.md): Chronological history from V10 Quantum to 9-Namespace Core.
- [Development Log](file:///c:/Users/User/SAA/docs/changelog/development-log.md): Commit-by-commit changelog.

### 5. Debugging & Quality Assurance (`docs/debugging/`, `docs/testing/`)
- [Known Problems & Resolutions](file:///c:/Users/User/SAA/docs/debugging/known-problems.md): RCA and prevention guides for all resolved bugs.
- [Testing Strategy & Matrix](file:///c:/Users/User/SAA/docs/testing/testing-strategy.md): Regression guarantees, suites, and test commands.

### 6. User Manuals & Practical Guides (`docs/usage/`)
- [Getting Started Guide](file:///c:/Users/User/SAA/docs/usage/getting-started.md): Installation, quickstart, and basic idioms.
- [API Quick Reference](file:///c:/Users/User/SAA/docs/usage/api-quick-reference.md): Concise signature cheat-sheet.
- [Which API Should I Use?](file:///c:/Users/User/SAA/docs/usage/which-api.md): Decision guide mapping tasks to methods.
- [Cookbook & Recipes](file:///c:/Users/User/SAA/docs/usage/cookbook.md): Copy-paste code recipes for real-world automation.
- **Dedicated Usage Guides**: [Browser](file:///c:/Users/User/SAA/docs/usage/browser.md) | [Web](file:///c:/Users/User/SAA/docs/usage/web.md) | [Crawling](file:///c:/Users/User/SAA/docs/usage/crawling.md) | [Document](file:///c:/Users/User/SAA/docs/usage/document.md) | [OCR](file:///c:/Users/User/SAA/docs/usage/ocr.md) | [AI](file:///c:/Users/User/SAA/docs/usage/ai.md) | [Network](file:///c:/Users/User/SAA/docs/usage/network.md) | [Integrations](file:///c:/Users/User/SAA/docs/usage/integrations.md) | [MCP](file:///c:/Users/User/SAA/docs/usage/mcp.md) | [Infrastructure](file:///c:/Users/User/SAA/docs/usage/infrastructure.md) | [Observability](file:///c:/Users/User/SAA/docs/usage/observability.md) | [Intelligence](file:///c:/Users/User/SAA/docs/usage/intelligence.md) | [Humanization](file:///c:/Users/User/SAA/docs/usage/humanization.md)

---

## 🎯 Verification Standard
Every guide and reference document in this tree has been verified against active source code ([`bp_facade12.py`](file:///c:/Users/User/SAA/bp_facade12.py), [`behavioral_playwright/`](file:///c:/Users/User/SAA/behavioral_playwright)) and validated by the 39-test automated test suite.
