# System Execution Flow

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Lifecycle Overview

A typical session with Behavioral Playwright follows a structured lifecycle:

```mermaid
sequenceDiagram
    autonumber
    participant App as Client Application
    participant BP as BP Facade
    participant Browser as BrowserNamespace
    participant Stealth as CDP Stealth Engine
    participant PW as Playwright Core
    participant Obs as ObservabilityNamespace

    App->>BP: async with BP() as bp
    BP->>BP: Initialize 9 Namespaces
    App->>BP: await bp.boot() (or auto on first action)
    BP->>Browser: boot()
    Browser->>PW: launch Chromium persistent context
    Browser->>Stealth: Inject Anti-Fingerprint Scripts
    Browser-->>BP: Context & Page Ready

    App->>BP: await bp.browser.goto(url)
    BP->>Obs: start_trace(trace_id)
    BP->>Browser: goto(url)
    Browser->>PW: page.goto() with circuit breaker

    App->>BP: await bp.browser.click(selector)
    BP->>Browser: click(selector)
    Browser->>PW: blur() -> focus() -> Bezier Mouse -> click()

    App->>BP: await bp.close() (context manager exit)
    BP->>Obs: end_trace() -> log_execution()
    BP->>Browser: close()
    Browser->>PW: release browser context
    BP-->>App: Session Terminated Cleanly
```

---

## 2. Multi-Namespace Data Pipeline Flow

When executing complex extraction workflows (such as crawling, NLP ranking, and webhook dispatching), data transitions across namespaces through structured interfaces:

```text
[Target URL]
     │
     ▼
[bp.network.measure_response_time_async] ──► Checks server latency & health
     │
     ▼
[bp.web.crawl_recursive] ──────────────────► BFS crawl, domain bounds, SQLite session
     │ (Discovered URLs / HTML)
     ▼
[bp.infrastructure.save_to_cache] ─────────► Encrypts & persists raw DOM payloads
     │
     ▼
[bp.ai.re_rank] ───────────────────────────► Multilingual TF-IDF vector space scoring
     │
     ▼
[bp.ai.coerce_data_to_schema] ─────────────► JIT data casting to target schema
     │
     ▼
[bp.observability.log_execution] ──────────► Records performance & success telemetry
     │
     ▼
[bp.integrations.slack_webhook_notify] ────► Dispatches structured alert to Slack/n8n
```
