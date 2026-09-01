# Which API Should I Use? (Decision Guide)

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

| Your Immediate Task / Goal | Recommended API Method | Why Choose This API? |
| :--- | :--- | :--- |
| **Extract structured HTML content from a URL** | `await bp.web.scrape(url, options)` | Fast, stateless, strips headers/footers, zero browser overhead. |
| **Crawl an entire website recursively** | `await bp.web.crawl_recursive(url, max_depth)` | Bounded BFS traversal with SQLite state and loop protection. |
| **Log in to a site or fill a multi-step form** | `await bp.browser.goto()`, `type()`, `click()` | Bio-emulated keystroke cadences and focus-blur evasion. |
| **Extract text from a scanned PNG/JPEG or invoice** | `await bp.document.ocr_image_with_autocorrect(path)` | 1.5x contrast enhancement, Tesseract OCR in worker thread. |
| **Parse a 2-column PDF document** | `await bp.document.parse_pdf(file_path)` | Reconstructs spatial column reading order and tables. |
| **Rank search results or documents by relevance** | `bp.ai.re_rank(query, documents)` | Multilingual TF-IDF vector space scoring ($0 external API cost). |
| **Check server health and network latency** | `await bp.network.measure_response_time_async(url)` | Real HTTP HEAD probe with monotonic millisecond timer. |
| **Send workflow completion alerts to your team** | `await bp.integrations.slack_webhook_notify_async()` | Real HTTP POST webhook dispatching for Slack/Discord/n8n. |
| **Connect Behavioral Playwright to Claude / AI agents** | `await bp.integrations.mcp_call_tool_async()` | Native Model Context Protocol tool execution. |
| **Queue up thousands of URLs for processing** | `bp.infrastructure.push_task(db_path, url, op)` | SQLite WAL atomic task queue with priorities. |
| **Measure execution latency and log QA reports** | `bp.observability.start_trace()`, `generate_qa_report()` | High-performance DDL-cached metrics database. |
| **Recover from a broken or changed CSS selector** | `bp.intelligence.auto_correct_selectors(sel, opts)` | Heuristic Levenshtein matrix edit distance correction. |
