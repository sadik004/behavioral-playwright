# API Quick Reference & Cheat Sheet

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

| Method | Exact Signature | Purpose | Return Value | Throws / Errors | Minimal Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `bp.boot()` | `async def boot() -> BP` | Launch stealth browser | `self (BP)` | `BrowserLaunchError` | `await bp.boot()` |
| `bp.browser.goto()` | `async def goto(url: str) -> bool` | Navigate page | `bool` | `NavigationError` | `await bp.browser.goto("https://...")` |
| `bp.browser.click()` | `async def click(sel: str, text=None) -> Any` | Bio-emulated click | Element / Result | `ElementResolutionError` | `await bp.browser.click("#btn")` |
| `bp.browser.type()` | `async def type(sel: str, text: str) -> Any` | Log-normal typing | Element / Result | `ElementResolutionError` | `await bp.browser.type("#in", "txt")` |
| `bp.browser.scroll()` | `async def scroll(dist=500.0) -> None` | Saccade scroll | `None` | `RuntimeError` if not booted | `await bp.browser.scroll(300.0)` |
| `bp.browser.screenshot()` | `async def screenshot(path=None) -> bytes` | Viewport screenshot | `bytes` | `RuntimeError` if not booted | `await bp.browser.screenshot("a.png")` |
| `bp.web.scrape()` | `async def scrape(url_or_html: str, ...) -> Res` | Stateless DOM scrape | `AcquisitionResult` | `ValueError` | `await bp.web.scrape("https://...")` |
| `bp.web.crawl_recursive()`| `async def crawl_recursive(url, max_depth, ...)`| Bounded BFS crawl | `List[str]` (URLs) | `ValueError` | `await bp.web.crawl_recursive("...")` |
| `bp.document.ocr_image()` | `async def ocr_image_with_autocorrect(path)` | Tesseract image OCR | `Dict[str, Any]` | `FileNotFoundError`, `ProviderUnavailableError` | `await bp.document.ocr_image_with_autocorrect("a.png")` |
| `bp.document.parse_pdf()` | `async def parse_pdf(path: str) -> Dict` | 2-column PDF parse | `Dict[str, Any]` | `FileNotFoundError` | `await bp.document.parse_pdf("a.pdf")` |
| `bp.ai.re_rank()` | `def re_rank(query: str, docs: List[str])` | TF-IDF document rank | `List[Dict]` | None | `bp.ai.re_rank("query", docs)` |
| `bp.ai.coerce_data()` | `def coerce_data_to_schema(data, schema)` | Schema type casting | `Dict[str, Any]` | None | `bp.ai.coerce_data_to_schema(d, s)` |
| `bp.network.measure()` | `async def measure_response_time_async(url)` | HTTP HEAD latency | `float` (ms) | `ValueError`, `TimeoutError` | `await bp.network.measure_response_time_async("...")` |
| `bp.integrations.slack()` | `async def slack_webhook_notify_async(url, msg)`| Send Slack message | `bool` | `ValueError`, `HTTPError` | `await bp.integrations.slack_webhook_notify_async(u, m)` |
| `bp.integrations.mcp()` | `async def mcp_call_tool_async(tool, args)` | Execute MCP tool | `Any` | `ValueError` | `await bp.integrations.mcp_call_tool_async("scrape", a)` |
| `bp.infrastructure.push()`| `def push_task(db, url, op, priority=0)` | Push to task queue | `int` (task_id) | `sqlite3.Error` | `bp.infrastructure.push_task(db, u, op)` |
| `bp.infrastructure.cache()`| `def save_to_cache(db, url, html, md)` | Encrypt page cache | `bool` | `sqlite3.Error` | `bp.infrastructure.save_to_cache(db, u, h, m)` |
| `bp.observability.trace()` | `def end_trace(trace_id, url=None, db=...)` | Log trace duration | `float` (ms) | None | `bp.observability.end_trace("t1")` |
| `bp.observability.report()`| `def generate_qa_report(db="metrics.db")` | Generate QA report | `Dict[str, Any]` | None | `bp.observability.generate_qa_report()` |
| `bp.intelligence.shield()` | `def detect_bot_shields(html: str)` | Scan anti-bot shields | `Dict[str, Any]` | None | `bp.intelligence.detect_bot_shields(h)` |
| `bp.intelligence.heal()` | `def auto_correct_selectors(broken, opts)` | Levenshtein selector | `str` | None | `bp.intelligence.auto_correct_selectors(s, o)` |
