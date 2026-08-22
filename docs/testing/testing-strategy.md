# Testing Strategy & Test Matrix

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Test Architecture & Execution

The test suite validates the entire 9-namespace architecture without requiring live network connections (using mock servers, in-memory SQLite, and synthetic fixtures).

### Command to Run Full Test Suite:
```bash
pytest test_browser_actions.py test_crawler.py test_ocr.py test_network.py test_integrations.py test_observability.py -v
```

---

## 2. Test Suite Matrix (39 Tests Total)

| Test File | Covered Namespace | Test Count | Key Guarantees Verified |
| :--- | :--- | :---: | :--- |
| **`test_browser_actions.py`** | `BrowserNamespace` | **6** | Preboot guards, humanizer delegation, native Playwright fallbacks, focus-blur, error propagation, non-blocking `asyncio.sleep`. |
| **`test_crawler.py`** | `WebNamespace` | **6** | Real link extraction via BeautifulSoup4, depth limits, page limits, domain isolation, loop trap detection, SQLite session tracking. |
| **`test_ocr.py`** | `DocumentNamespace` | **5** | Missing file `FileNotFoundError`, missing Tesseract `ProviderUnavailableError`, PIL contrast + OCR success, SHA256 checksum, watermark cleaning. |
| **`test_network.py`** | `NetworkNamespace` | **7** | URL schema validation, HTTP HEAD probe timing, 405 GET fallback, socket timeout propagation, async wrappers, BP facade delegation. |
| **`test_integrations.py`**| `IntegrationsNamespace`| **9** | Webhook URL validation, real JSON HTTP POST to Slack/Discord/n8n, MCP tool bridge execution (`scrape`, `crawl`), manifest generation. |
| **`test_observability.py`** | `ObservabilityNamespace` | **6** | Metrics DB initialization, repeated DDL idempotency, metric writes executing pure DML without repeated DDL, trace timers, QA reports. |
