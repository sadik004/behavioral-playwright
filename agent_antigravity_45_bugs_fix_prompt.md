# ROLE: Autonomous Principal 45-Bug Remediation & 12-Layer Verification Agent

**Working Directory**: `E:\Scraping\behavioral-playwright-main\behavioral-playwright-main`

> **CRITICAL EXECUTION RULES**:
> 1. **Cryptographic Lock Invariant**: NEVER modify, overwrite, or delete any of the 32 files sealed in `LOCK.json`.
> 2. **Zero-Mock Invariant**: Never use `unittest.mock`, `MagicMock`, `AsyncMock`, or `monkeypatch` in any `*_real.py` test file.
> 3. **Strict Syntax & DAG Invariant**: Every `.py` file must parse with `0` `SyntaxError`/`IndentationError`, `0` `SWALLOW-001` (`except: pass`), and `0` circular dependencies (`0 cycles`).

---

## STEP 1: Extract `veil_master_bugfree_bundle.zip` & Run the Autonomous Installer

1. If `veil_master_bugfree_bundle_v2.zip` was downloaded into the project root (or Downloads folder), copy/rename it to `veil_master_bugfree_bundle.zip` in `E:\Scraping\behavioral-playwright-main\behavioral-playwright-main`:
   ```powershell
   if (Test-Path .\veil_master_bugfree_bundle_v2.zip) {
       Copy-Item .\veil_master_bugfree_bundle_v2.zip .\veil_master_bugfree_bundle.zip -Force
   }
   ```
2. Extract `veil_master_bugfree_bundle.zip` and run `install_master_bugfree_bundle.py`:
   ```powershell
   Expand-Archive -Path .\veil_master_bugfree_bundle.zip -DestinationPath . -Force
   $env:PYTHONIOENCODING="utf-8"
   python install_master_bugfree_bundle.py
   ```

---

## STEP 2: Verify the 15 Newly Remediated Bugs (Bugs 31–45) on Top of Bugs 01–30

Confirm that all 15 post-remediation fixes below are active in the repository:

- [ ] **Bug 31 (`src/veil/cli/main.py`)**: Clean single `try ... except Exception:` blocks for `PAAMiner` and `GoogleSuggestMiner` (zero nested `try:` `IndentationError`s) plus `if miner is not None:` guards before calling `PAAMiner(max_depth=depth)`.
- [ ] **Bug 32 (`src/veil/crawling/service.py`)**: Clean indentation in `CrawlingService.escalate_and_fetch()` and `TieredCrawlerService.check_and_rotate_context()` (20-space indent inside `if hasattr(...)`), delegating Tiers 2–4 to `TieredCrawlerService().crawl(...)` with zero fake `"Tier 2/3 Content"` HTML strings.
- [ ] **Bug 33 (`behavioral_evasion_suite/mouse_physics.py`)**: `BiomechanicalMousePhysics.__init__(self, page=None, seed=None)` always initializes `self._rng = random.Random(seed)` and `self.timer = None` so `generate_trajectory()` never raises `AttributeError: 'BiomechanicalMousePhysics' object has no attribute '_rng'`.
- [ ] **Bug 34 (`src/veil/extraction/auto_schema.py` & `src/veil/extraction/__init__.py`)**: `AutoSchemaExtractor` is defined and exported alongside `AdaptiveSchemaSynthesizer`, enabling `AINamespace().extract(raw_html)` and Layer 6/11 tests to extract structured cards/prices/JSON-LD offline.
- [ ] **Bug 35 (`src/veil/crawling/mapper.py` & `src/veil/facade.py`)**: `SiteMapper.__init__(self, fetcher=None)` provides a default non-blocking async HTTP fetcher (`asyncio.to_thread` + `urllib.request.urlopen`), and `BP.map(url)` converts `List[MappedUrl]` into `{"base_url": url, "links": [...], "mapped_urls": [...], "total_urls": ...}`.
- [ ] **Bug 36 (`src/veil/facade.py`)**: `BP.crawl(start_url, max_pages=5, max_depth=2)` uses `async with DeepSiteCrawler(max_host_pages=max_pages) as crawler:` (closing SQLite handles cleanly) and returns `res.get("pages")`.
- [ ] **Bug 37 (`src/veil/crawling/bandit_proxy_rotator.py`)**: `BanditProxyRotator(proxies=None)` defaults to `["direct://local"]` when `proxies is None`, safely uses `self._arms.setdefault(...)` in `record_outcome`, and implements `add_proxy`, `add_proxy_url`, `get_proxy`, `report_success`, and `report_failure`.
- [ ] **Bug 38 (`src/veil/crawling/world_class_engine.py`)**: `_raw_http_fetch` runs blocking `urllib.request` inside `await asyncio.to_thread(...)`, honors `proxy` via `ProxyHandler`, and `scrape_url` forwards `proxy` and supports `html_override`.
- [ ] **Bug 39 (`src/veil/crawling/service.py`)**: Both `_execute_tier3` and `_execute_tier4` wrap synchronous browser launch/navigation in `await asyncio.to_thread(...)`.
- [ ] **Bug 40 (`src/veil/facade.py`)**: `ObservabilityNamespace._ensure_legacy_db()` closes `conn` in a `finally:` block.
- [ ] **Bug 41 (`src/veil/mcp/tools.py` & `src/veil/cli/main.py`)**: `_mcp_rec_to_dict` and `_rec_to_dict` safely convert `dict`, `str`, Pydantic models, and objects without `vars(r)` `TypeError`, and `crawl_domain` / `run_crawl` execute `await bp.crawl(...)` without forcing `await bp.boot()`.
- [ ] **Bug 42 (`src/veil/extraction/dom.py`)**: `extract_next_data(page)` catches `(json.JSONDecodeError, ValueError)` on malformed `<script id="__NEXT_DATA__">` strings and returns `None`.
- [ ] **Bug 43 (`src/veil/cli/main.py`)**: `run_audit(target="src/veil")` performs a real AST syntax and `SWALLOW-001` scan on `target`.
- [ ] **Bug 44 (`src/veil/crawling/models.py` & `src/veil/crawling/checkpoint.py`)**: `CrawlResponse` exposes `.html`, `.success`, and `.escalations_count` properties, and `CheckpointStore` persists responses in SQLite WAL mode with clean NTFS handle release.
- [ ] **Bug 45 (`run_full_project_12_layer_tests.py` & `fix_all_master_repo_bugs.py`)**: Layer 2 & Layer 3 fail immediately on any `SyntaxError`/`IndentationError`, and `fix_all_master_repo_bugs.py` is 100% idempotent and AST-verified.

---

## STEP 3: Run All Verification Gates (All Must Exit Code `0`)

Run the following commands in sequence and verify every gate passes with `0` errors:

```powershell
$env:PYTHONIOENCODING="utf-8"

# Gate 1: Cryptographic Lock Verification (32/32 locked files untouched)
python lock_and_guard_harness.py --verify

# Gate 2: Idempotent 45-Bug Master Remediation Check
python fix_all_master_repo_bugs.py --repo-root . --apply

# Gate 3: Zero-Mock 45-Bug Regression Suite
python tests/integration/test_master_bugfree_real.py

# Gate 4: Master 12-Layer Verification & 50-Worker Concurrency Stress Runner
python run_full_project_12_layer_tests.py --repo-root . --run-full-pytest

# Gate 5: Architecture DAG & AST Anti-Gaming Audit
python scripts/audit_architecture.py --target src/veil
python scripts/ast_anti_gaming.py --tests "tests/**/*.py" --src "src/**/*.py"
```
