# Known Problems & Engineering Resolutions

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Problem: Injected JavaScript Runtime Error on Boot
- **Symptoms**: Browser boot crashed with `ReferenceError: logger is not defined` when injecting CDP anti-fingerprint shims.
- **Root Cause**: The JS stealth script referenced a non-existent Python variable `logger.debug` in browser client context.
- **Fix**: Replaced `logger.debug` with `console.debug` in the browser init template.
- **Regression Test**: `test_browser_actions.py::test_part1_regressions_intact`.

---

## 2. Problem: Blocking `time.sleep` in Async Browser Interaction
- **Symptoms**: High-concurrency browser automation froze the entire Python event loop during typing and scrolling.
- **Root Cause**: `time.sleep` was invoked directly inside `async def type` and `async def scroll`.
- **Fix**: Replaced `time.sleep(d)` with `await asyncio.sleep(d)`.
- **Regression Test**: `test_browser_actions.py::test_part1_regressions_intact`.

---

## 3. Problem: Simulated Links & Loop Traps in Recursive Crawler
- **Symptoms**: Crawler returned hardcoded fake links without fetching real web pages or crashed on cyclical URL loops.
- **Root Cause**: `crawl_recursive` was a mock returning synthetic URLs.
- **Fix**: Implemented real BFS crawler acquiring HTML via `self.scrape()`, extracting links via BeautifulSoup4, resolving relative paths with `urljoin`, filtering domains, and detecting redirect cycles with `detect_redirection_loops`.
- **Regression Test**: `test_crawler.py::test_crawl_recursive_real_links_extraction`.

---

## 4. Problem: Mocked OCR Output & Missing Error Propagation
- **Symptoms**: `ocr_image_with_autocorrect` returned static string templates instead of actual image text.
- **Root Cause**: Placeholder implementation returning simulated dictionary.
- **Fix**: Implemented real PIL grayscale + 1.5x contrast boost, background thread execution of `pytesseract.image_to_string()`, SHA256 checksum generation, and proper propagation of `FileNotFoundError` and `ProviderUnavailableError`.
- **Regression Test**: `test_ocr.py::test_ocr_real_pipeline_success_with_engine`.

---

## 5. Problem: Simulated Network Response Times
- **Symptoms**: `measure_response_time` simulated network latency using `hash(url) % 50`.
- **Root Cause**: Mock latency calculation.
- **Fix**: Replaced with real HTTP `HEAD` probes (with `405 GET` fallback) measuring elapsed monotonic milliseconds via `time.perf_counter()`.
- **Regression Test**: `test_network.py::test_measure_response_time_success`.

---

## 6. Problem: Repeated SQLite DDL Table Creation
- **Symptoms**: Observability logging slowed down exponentially under load due to disk locking.
- **Root Cause**: `CREATE TABLE IF NOT EXISTS` was executed on every single metric write.
- **Fix**: Implemented in-memory `_initialized_dbs` tracking set. Table schemas are created once; subsequent writes execute pure DML `INSERT` queries.
- **Regression Test**: `test_observability.py::test_metric_writes_do_not_reexecute_ddl`.
