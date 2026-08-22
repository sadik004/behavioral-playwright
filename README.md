# Behavioral Playwright

> **Autonomous, Bio-Emulated Browser Automation & Data Intelligence Platform**
> **Repository**: [https://github.com/sadik004/behavioral-playwright](https://github.com/sadik004/behavioral-playwright)
> **Current Version**: `v1.0.0-facade` (Verified at commit `68a3d1e`)
> **Status**: 🟢 **100% Tests Passing (39/39)** | Zero Cloud Lock-In ($0 Cost Core)

---

## ⚡ What is Behavioral Playwright?

Behavioral Playwright is an enterprise-grade web automation and data intelligence platform in Python. It replaces brittle, easily detected bot behaviors with **biomechanically modeled human interactions** and provides a **100% offline, zero-cost architecture** for web crawling, document parsing, image OCR, vector re-ranking, and telemetry.

All 109 capabilities are unified beneath a lightweight, ergonomic `BP` facade partitioned into **9 decoupled domain namespaces**:

```text
┌─────────────────────────────────────────────────────────────┐
│                           BP Facade                         │
└──────┬────────┬────────┬────────┬────────┬────────┬────────┬┘
       │        │        │        │        │        │        │
       ▼        ▼        ▼        ▼        ▼        ▼        ▼
    bp.web  bp.browser bp.document bp.ai bp.network bp.integrations ...
```

---

## 🚀 Quickstart

### 1. Installation
```bash
git clone https://github.com/sadik004/behavioral-playwright.git
cd behavioral-playwright
pip install playwright beautifulsoup4 Pillow pytesseract pypdf python-docx
playwright install chromium
```

### 2. Basic Example
```python
import asyncio
from bp_facade12 import BP

async def main():
    async with BP() as bp:
        # Bio-emulated browser automation
        await bp.browser.goto("https://example.com")
        await bp.browser.type("input#search", "Playwright automation")
        await bp.browser.click("button#submit")
        await bp.browser.screenshot("result.png")

        # Zero-cost recursive crawler
        visited = await bp.web.crawl_recursive("https://example.com", max_depth=2)
        print(f"Discovered {len(visited)} pages.")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🧭 The 9 Namespaces at a Glance

| Namespace | Focus Area | Key Capabilities |
| :--- | :--- | :--- |
| **`bp.web`** | Stateless Web & Crawling | DOM scraping, BFS recursive crawler, XML sitemaps, loop detection. |
| **`bp.browser`** | Humanized Browser | Focus-blur lifecycle, log-normal typing, Bézier mouse, saccade scroll. |
| **`bp.document`** | Document & OCR | 2-column PDF/DOCX parser, contrast-enhanced Tesseract image OCR. |
| **`bp.ai`** | Local Statistical NLP | Multilingual UTF-8 TF-IDF re-ranker, JIT schema type coercion. |
| **`bp.network`** | Network & Diagnostics | Real HTTP HEAD latency probes, user-agent injection, gzip compression. |
| **`bp.integrations`**| Webhooks & MCP | Real HTTP POST to Slack/Discord/n8n, Model Context Protocol tools. |
| **`bp.infrastructure`**| Queue & Cache | SQLite WAL priority task queues, SHA256-XOR encrypted page cache. |
| **`bp.observability`** | Metrics & QA | DDL-cached execution logging, monotonic trace timers, QA reports. |
| **`bp.intelligence`** | Adaptive Diagnostics | Bot-shield detector (Cloudflare, DataDome), Levenshtein selector healing. |

---

## 📚 Complete Engineering Knowledge Base & Documentation

For exhaustive architecture specifications, usage manuals, and debugging records, explore the **[`docs/`](file:///c:/Users/User/SAA/docs/)** directory:

- 🏛️ **Architecture & System Design**: [`docs/architecture/overview.md`](file:///c:/Users/User/SAA/docs/architecture/overview.md) | [`system-flow.md`](file:///c:/Users/User/SAA/docs/architecture/system-flow.md) | [`dependency-map.md`](file:///c:/Users/User/SAA/docs/architecture/dependency-map.md)
- 🔬 **Core Foundations**: [`docs/core/behavioral-humanizer.md`](file:///c:/Users/User/SAA/docs/core/behavioral-humanizer.md) | [`stealth.md`](file:///c:/Users/User/SAA/docs/core/stealth.md) | [`v10-core.md`](file:///c:/Users/User/SAA/docs/core/v10-core.md)
- 📖 **User Manuals & Guides**: [`docs/usage/getting-started.md`](file:///c:/Users/User/SAA/docs/usage/getting-started.md) | [`which-api.md`](file:///c:/Users/User/SAA/docs/usage/which-api.md) | [`cookbook.md`](file:///c:/Users/User/SAA/docs/usage/cookbook.md) | [`api-quick-reference.md`](file:///c:/Users/User/SAA/docs/usage/api-quick-reference.md)
- 🛠️ **Debugging & Known Issues**: [`docs/debugging/known-problems.md`](file:///c:/Users/User/SAA/docs/debugging/known-problems.md)
- 🧪 **Testing & Quality Assurance**: [`docs/testing/testing-strategy.md`](file:///c:/Users/User/SAA/docs/testing/testing-strategy.md)
- 📜 **Architecture Decisions & History**: [`docs/decisions/architecture-decisions.md`](file:///c:/Users/User/SAA/docs/decisions/architecture-decisions.md) | [`docs/evolution/project-history.md`](file:///c:/Users/User/SAA/docs/evolution/project-history.md)

---

## 🧪 Verification & Test Commands

Run the full automated test suite (39 tests):
```bash
pytest test_browser_actions.py test_crawler.py test_ocr.py test_network.py test_integrations.py test_observability.py -v
```

---

## 📄 License

MIT License. See [`LICENSE`](file:///c:/Users/User/SAA/LICENSE) for details.
