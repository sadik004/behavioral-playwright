# **Autonomous Antigravity Remediation & Verification Agent**

**Master Execution Document & Live State Tracker** `AGENT_ANTIGRAVITY_MASTER_FIX_PROMPT.md`

**Working Directory:** `E:\Scraping\behavioral-playwright-main\behavioral-playwright-main`

**AGENT EXECUTION RULE:** Treat this document as your live state tracker. As you complete each phase and verify each bug fix below, update its checkbox from `[ ]` to `[x]`. Do NOT terminate execution until all checkboxes in Phases 1–5 are marked \[x\] and both test\_master\_bugfree\_real.py and all 12 layers of `run_full_project_12_layer_tests.py` exit with code 0\.

---

# **HARD CONSTRAINTS (ZERO EXCEPTIONS)**

1. **Cryptographic Lock Invariant:** NEVER modify, overwrite, or delete any of the 32 files listed in `LOCK.json`.  
2. **Zero-Mock & Anti-Gaming Invariant:** Never use `unittest.mock`, `MagicMock`, `AsyncMock`, or `monkeypatch` in any verification test. Never introduce bare `except ...: pass` (`SWALLOW-001`).  
3. **Strict DAG Invariant:** Maintain 0 cycles in `python scripts/audit_architecture.py --target src/veil`.

---

# **PHASE 1: Master Bundle Extraction & Auto-Installation**

- [ ] **1.1 Extract Master Bug-Free Bundle**  
      Unpack `veil_master_bugfree_bundle.zip` into the repository root:  
      `Expand-Archive -Path .\veil_master_bugfree_bundle.zip -DestinationPath . -Force`  
- [ ] **1.2 Run Master Installation & Verification Harness**  
      Execute the single-command autonomous installer:  
      `python install_master_bugfree_bundle.py`

---

# **PHASE 2: Audit & Verify All 30 Bug Remediations**

## **Section A: Core Architectural & Plumbed Gaps (Bugs 01–18)**

| Status | Bug ID | Description & Target Location |
| :---- | :---- | :---- |
| \[ \] | **Bug 01** | Method truthiness fixed (`if p1.is_available():`) in `src/veil/crawling/service.py`. |
| \[ \] | **Bug 02** | Hardcoded "Tier 2/3/4 Content" stubs removed; real crawling delegated to `TieredCrawlerService`. |
| \[ \] | **Bug 03** | Root `providers/` synchronized with `src/veil/providers/` (`afetch` and `BaseBrowserProvider` available). |
| \[ \] | **Bug 04** | Unclosed SQLite handles wrapped in `finally: conn.close()` across `facade.py` and `crawling/service.py`. |
| \[ \] | **Bug 05** | Synchronous `check_and_rotate_context()` uses `get_running_loop()` with task set tracking. |
| \[ \] | **Bug 06** | `README.md` updated to v10.0.2, 51 MCP tools, and live verified providers. |
| \[ \] | **Bug 07** | `MockStealthPage` ("Houston Youth Sports Directory") replaced with honest `is_simulated_fallback = True`. |
| \[ \] | **Bug 08** | `tls_ja4_spoofer.py` raises `RuntimeError` rather than returning fake 200 OK HTML when `curl_cffi` is absent. |
| \[ \] | **Bug 09** | `StrictContextManager` WebRTC SDP leak (`s=MockSession`) replaced with standard WebRTC parameters. |
| \[ \] | **Bug 10** | `VirtualTPMWebAuthnRelay` static bot credential replaced with origin-derived IDs. |
| \[ \] | **Bug 11** | `os_bridge.py` verifies `shutil.which("Xvfb")` rather than claiming fake virtual displays. |
| \[ \] | **Bug 12** | `OSNetworkStackSpoofer` inspects live socket `IP_TTL` rather than returning hardcoded Windows 11 reports. |
| \[ \] | **Bug 13** | Unseeded global `random.*` calls across kinematics replaced with isolated deterministic `random.Random(seed)` instances. |
| \[ \] | **Bug 14** | `WindowsHighResolutionTimer` timer acquisition moved exclusively into context manager. |
| \[ \] | **Bug 15** | Duplicate `ProviderUnavailableError` class hierarchy unified under `BehavioralPlaywrightError`. |
| \[ \] | **Bug 16** | `AINamespace.extract()` extracts records offline via `AutoSchemaExtractor` rather than echoing input. |
| \[ \] | **Bug 17** | `DOMExtractor` unwrap securely checks attributes without string `"Mock"` checks. |
| \[ \] | **Bug 18** | All bare `except ...: pass` blocks eliminated (`SWALLOW-001` count \= 0). |

## **Section B: Deep Crawler & Operational Landmines (Bugs 19–30)**

| Status | Bug ID | Description & Target Location |
| :---- | :---- | :---- |
| \[ \] | **Bug 19** | Ghost imports in `facade.py` (`bp.crawl()`, `bp.search()`, `bp.map()`) wired to real `DeepSiteCrawler` and `SiteMapper`. |
| \[ \] | **Bug 20** | CLI `vars(r)` string crash in `cli/main.py` L159 eliminated via `_rec_to_dict(r)`. |
| \[ \] | **Bug 21** | Broken CLI mining subcommands (`mine-paa`, `mine-suggest`, `check-overlap`) given resilient fallbacks. |
| \[ \] | **Bug 22** | Duplicate network fetch eliminated in `deep_crawler.py` (reuses `raw_html` returned by `scrape_url()`). |
| \[ \] | **Bug 23** | UCB-1 selected proxy piped directly into `scrape_url()` in `deep_crawler.py` and `world_class_engine.py`. |
| \[ \] | **Bug 24** | Infinite retry loop in `fail_task` eliminated (`int(status.split("retry:")[1]) + 1` correctly reaches `max_retries`). |
| \[ \] | **Bug 25** | Task queue concurrency race eliminated in `pop_task` using atomic `BEGIN IMMEDIATE;` transaction and WAL mode. |
| \[ \] | **Bug 26** | Schema fragmentation resolved: `recover_crawl_session()` checks both `crawl_state` and `crawl_urls`. |
| \[ \] | **Bug 27** | Raw HTML navigation crash resolved: `WebNamespace.scrape` and `AINamespace.extract` detect `<` tags and use `set_content()` or offline parsing. |
| \[ \] | **Bug 28** | Sync Playwright inside Async Event Loop resolved: `_execute_tier3`/`_execute_tier4` run synchronous operations inside `asyncio.to_thread`. |
| \[ \] | **Bug 29** | Missing `Tuple` typing import added to `src/veil/extraction/dom.py`. |
| \[ \] | **Bug 30** | 13 Top-0.1% modules wired directly into BP, `cli/main.py`, and `mcp/tools.py`. |

---

# **PHASE 3: Run Zero-Mock Bug Elimination Test Suite**

- [ ] **3.1 Execute Master Regression Suite**  
      Run `tests/integration/test_master_bugfree_real.py` against a live local loopback server:  
      `python tests/integration/test_master_bugfree_real.py`  
        
      *Confirm output:* `[PASS] All 8 master bug-free verification tests passed 100% with ZERO mocks!`

---

# **PHASE 4: Run the Master 12-Layer Verification & Concurrency Stress Runner**

- [ ] **4.1 Execute 12-Layer Full Runner**  
      Run the project-wide 12-layer verification runner:  
      `python run_full_project_12_layer_tests.py --repo-root .`  
        
      *Verify all 12 layers show `[PASS]` (Layers 01 to 12).*

---

# **PHASE 5: Full Pytest & Report Confirmation**

- [ ] **5.1 Run Full Repository Pytest**  
      `python -m pytest -q` *(confirm 0 failed)*  
- [ ] **5.2 Inspect Test Report**  
      Inspect `FULL_PROJECT_12_LAYER_TEST_REPORT.json` *(confirm `failed: 0` and `passed: 12`)*

