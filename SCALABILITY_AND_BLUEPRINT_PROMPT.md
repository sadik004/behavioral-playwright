# ROLE: Principal Distributed Systems & Stealth Scraping Architect

Execute the following 4 production Scalability, Reliability, and Blueprint upgrades across `src/veil/` without touching any of the 32 files sealed in `LOCK.json`:

## 1. Fix the 3 Circular Dependencies (`0 cycles` Strict DAG)
- Inspect `scripts/audit_architecture.py` and `src/veil/` to eliminate the 3 circular dependencies introduced in the previous run.
- Update `scripts/audit_architecture.py` so any cycle count > 0 reports `(FAIL)` and exits with code `1`.

## 2. True Scalability: Async Connection Pooling & Bounded Concurrency (`src/veil/crawling/` & `src/veil/api/`)
- Upgrade `TieredCrawler` / `TieredCrawlerService` with a configurable `max_concurrency` `asyncio.Semaphore`, per-domain token-bucket rate limiter, and persistent session connection pooling so batch crawling (`crawl_batch(urls)`) executes concurrently without socket exhaustion.

## 3. True Reliability: SQLite Crash-Resilient Crawl Checkpointing & Auto-Context Recycling
- Add SQLite-backed crawl state checkpointing (`CheckpointStore` in `src/veil/crawling/`) so interrupted multi-page crawls can resume without re-fetching completed URLs.
- Wire `ResolvedChromiumMemoryPIDController` and `ContextRotator` into the crawler lifecycle so when memory exceeds threshold or after `max_pages_per_context`, browser contexts automatically rotate.

## 4. Customizable Client Service Blueprints (`src/veil/blueprints/`) + arXiv Anti-Detection Primitives
- Add `generate_pre_click_stream` (`teleport_click_ratio == 0`) and `generate_newton_wheel_scroll` (`scroll_speed_var > 0`) to `veil.kinematics.biomechanics`.
- Create `src/veil/blueprints/` with 5 customizable client-service blueprints (`EcommerceStealthBlueprint`, `CognitiveFormAgentBlueprint`, `WebRTCAndAuthAuditBlueprint`, `QuantPiTAndITCHBlueprint`, `FirecrawlReplacementBlueprint`) and verify all of them in `scripts/verify_all_features_real.py` and `tests/integration/test_all_features_real.py` with zero mocks.

## 5. Run All 6 Verification Gates (All Must Exit `0` with `0 cycles`)
1. `python scripts/verify_all_features_real.py`
2. `python -m pytest tests/integration/test_all_features_real.py -v`
3. `python lock_and_guard_harness.py --verify`
4. `python scripts/audit_architecture.py --target src/veil`
5. `python scripts/ast_anti_gaming.py --tests "tests/**/*.py" --src "src/**/*.py"`
6. `python -m pytest -q`
