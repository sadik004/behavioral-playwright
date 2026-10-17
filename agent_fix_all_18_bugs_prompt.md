# ROLE: Autonomous Principal Remediation & Verification Agent (`AGENT_FIX_ALL_18_BUGS_PROMPT.md`)

**Working Directory**: `E:\Scraping\behavioral-playwright-main\behavioral-playwright-main`

> **AGENT EXECUTION RULE**: To prevent context loss across turns, you MUST treat this file (`AGENT_FIX_ALL_18_BUGS_PROMPT.md`) as your live state tracker. After completing each phase or bug fix below, update its checkbox in this file from `- [ ]` to `- [x]` before moving to the next item. Do NOT stop until all checkboxes in Phases 1–5 are marked `[x]` and all 7 verification gates exit with code `0`.

## HARD CONSTRAINTS (ZERO EXCEPTIONS)

1. **Cryptographic Lock Invariant**: NEVER modify, overwrite, or delete any of the 32 files listed in `LOCK.json`. Run `python lock_and_guard_harness.py --verify` after your changes to prove zero locked files were touched.
2. **Zero-Mock & Anti-Gaming Invariant**: Never use `unittest.mock`, `MagicMock`, `AsyncMock`, or `monkeypatch` in any verification or integration test. Never introduce bare `except ...: pass` (`SWALLOW-001`).
3. **Strict DAG Invariant**: Maintain `0 cycles` in `python scripts/audit_architecture.py --target src/veil`.

## PHASE 1: Ensure Wave 1 + Wave 2 (13-Pillar) Deep Crawler Modules Are Installed

- [x] **1.1 Check & Extract Wave 2 Bundle**: If `veil_top_01_wave2_deep_crawler.zip` exists in the repository root and `src/veil/crawling/deep_crawler.py` is missing or outdated, extract it and run the installer:
  ```powershell
  Expand-Archive -Path .\veil_top_01_wave2_deep_crawler.zip -DestinationPath . -Force
  python install_wave2_deep_crawler.py
  ```
- [x] **1.2 Verify 13-Pillar Files**: Confirm `src/veil/crawling/deep_crawler.py`, `src/veil/crawling/host_budget.py`, `src/veil/crawling/bandit_proxy_rotator.py`, `src/veil/extraction/block_tree_pruner.py`, and `src/veil/extraction/rag_chunker_exporter.py` exist and import cleanly.

## PHASE 2: Run `fix_all_18_repo_bugs.py` & Verify All 18 Bug Remediations

- [x] **2.0 Execute Auto-Remediation Script**: If `fix_all_18_repo_bugs.py` is present in the root directory, run it first:
  ```powershell
  python fix_all_18_repo_bugs.py --repo-root . --apply
  ```
  *(If `fix_all_18_repo_bugs.py` is not present or any item below still needs adjustment, apply the exact fix directly in the target file.)*

- [x] **Bug 01 — Uncalled `.is_available` Method Truthiness (`src/veil/crawling/service.py` Lines 469 & 486)**:
  - **Issue**: `CrawlingService.escalate_and_fetch()` wrote `if p1.is_available:` and `if p2.is_available:` without parentheses `()`, evaluating the bound method object (always `True`).
  - **Fix**: Change to `if p1.is_available():` and `if p2.is_available():`.

- [x] **Bug 02 — Hardcoded Fake HTML & Broken Import in `CrawlingService.escalate_and_fetch()` (`src/veil/crawling/service.py` Lines 488–514)**:
  - **Issue**: Returned hardcoded `"<html><body>Tier 2 Content for {url}</body></html>"`, `"Tier 3 Biometric Content"`, and imported non-existent `from behavioral_playwright.human.handoff import SessionHandoff` (`ModuleNotFoundError`).
  - **Fix**: Remove all fake HTML strings; delegate Tiers 2–4 to `TieredCrawlerService().crawl(CrawlRequest(url=url), use_checkpoint=False)` and use the real `from veil.handoff.session_handoff import SessionHandoff` import.

- [x] **Bug 03 — Root `providers/` vs `src/veil/providers/` Divergence (`providers/network.py` & `providers/__init__.py`)**:
  - **Issue**: Root `providers/network.py` lacked `afetch()` and `importlib.import_module` verification; root `providers/__init__.py` lacked `BaseBrowserProvider`.
  - **Fix**: Copy `src/veil/providers/network.py` to `providers/network.py` and `src/veil/providers/__init__.py` to `providers/__init__.py`.

- [x] **Bug 04 — Unclosed SQLite Connection on Exception (`src/veil/facade.py` Lines 354–370)**:
  - **Issue**: `ObservabilityNamespace._ensure_legacy_db()` opened `conn = sqlite3.connect(db_path)` without closing `conn` in a `finally:` block, risking `PermissionError: [WinError 32]` on Windows NTFS.
  - **Fix**: Wrap `conn = sqlite3.connect(db_path, timeout=30.0)` in `try ... finally: if conn is not None: conn.close()`.

- [x] **Bug 05 — Dangling `asyncio.create_task()` in Synchronous `check_and_rotate_context()` (`src/veil/crawling/service.py` Line 728)**:
  - **Issue**: Called `asyncio.create_task(self.context_rotator.get_healthy_context())` inside a synchronous method without checking for a running event loop or storing a strong reference to the task.
  - **Fix**: Use `loop = asyncio.get_running_loop()`, store the task in `self._bg_rotation_tasks: set = set()`, attach `t.add_done_callback(self._bg_rotation_tasks.discard)`, and catch `RuntimeError` cleanly when called outside an event loop.

- [x] **Bug 06 — `README.md` Out of Sync with `v10.0.2` & 51 MCP Tools (`README.md`)**:
  - **Issue**: `README.md` still showed `v6.2.0`, `20 Tools` / `16 Production AI Tools`, and `curl_cffi` as `✘ Optional | PROVIDER-GATED`.
  - **Fix**: Update `README.md` header/badges to `v10.0.2`, `51_Tools`, `curl_cffi` (`AsyncSession`) as `✔ Available | VERIFIED-LIVE`, and `### 5. MCP Server Integration (Exposes 51 Production AI Tools)`.

- [x] **Bug 07 — `StealthSession` Silent Fake Page Fallback (`stealth_session.py` / `src/veil/stealth/session.py`)**:
  - **Issue**: `MockStealthPage.title()` returned hardcoded `"Houston Youth Sports Directory"` when browser launch failed.
  - **Fix**: Replace `"Houston Youth Sports Directory"` with `"SimulatedFallbackPage (Browser Binary Unavailable)"` and set `self.is_simulated_fallback = True` on fallback.

- [x] **Bug 08 — `tls_ja4_spoofer.py` Fake `200 OK` HTML Fallback (`tls_ja4_spoofer.py` / `src/veil/stealth/tls_spoofer.py`)**:
  - **Issue**: Fallback `AsyncSession.get()` returned `MockResponse("<html>Static Output</html>", 200)` when `curl_cffi` was missing, fooling `SmartAcquisitionRouter`.
  - **Fix**: Raise `RuntimeError("curl_cffi is not installed; refusing to return fake Static Output HTML")` instead of returning fake `200 OK` HTML.

- [x] **Bug 09 — WebRTC SDP Bot Fingerprint Leak (`strict_context.py` / `src/veil/stealth/context_isolation.py`)**:
  - **Issue**: `webrtc_mask_js` hardcoded `s=MockSession` and `o=- 12345 12345 IN IP4 127.0.0.1` in `RTCPeerConnection.prototype.createOffer`.
  - **Fix**: Replace `s=MockSession` with standard WebRTC `s=-` and `o=- 4611731400430051336 2 IN IP4 0.0.0.0`.

- [x] **Bug 10 — WebAuthn Static Bot Credential ID (`webauthn_virtual_tpm.py` / `src/veil/stealth/webauthn_bridge.py`)**:
  - **Issue**: Hardcoded `id: 'powerhand_p256_credential_1337'` in `navigator.credentials.get`.
  - **Fix**: Replace static `'powerhand_p256_credential_1337'` with origin-derived `btoa(targetOrigin).replace(/=/g, '').slice(0, 22)`.

- [x] **Bug 11 — `os_bridge.py` Unverified Xvfb Claim (`os_bridge.py` / `src/veil/kinematics/os_bridge.py`)**:
  - **Issue**: `VirtualDisplayManager.initialize_virtual_framebuffer()` claimed Xvfb was mounted without checking `shutil.which("Xvfb")`.
  - **Fix**: Check `xvfb_bin = shutil.which("Xvfb")` and include `"execution_mode": "LIVE_OS" if xvfb_bin else "SIMULATION_FALLBACK"` and `"xvfb_binary_detected": bool(xvfb_bin)`.

- [x] **Bug 12 — `OSNetworkStackSpoofer` Hardcoded p0f Identity Report (`os_network_stack_spoofer.py` / `src/veil/stealth/network_spoofer.py`)**:
  - **Issue**: `get_network_identity_report()` returned static `ip_ttl: 128` without inspecting live socket `IP_TTL`.
  - **Fix**: Inspect `s.getsockopt(socket.IPPROTO_IP, socket.IP_TTL)` on a real `socket.socket` and include `observed_socket_ttl` and `host_platform: sys.platform`.

- [x] **Bug 13 — Unseeded Global `random.*` Calls Breaking Seed Determinism (`mouse_physics.py`, `keystroke_engine.py`, `cognitive_gaze_physics.py`)**:
  - **Issue**: Called global `random.gauss()`, `random.uniform()`, `random.choice()`, and `random.weibullvariate()` instead of an isolated `random.Random(seed)` instance.
  - **Fix**: Add `seed: Optional[int] = None` and `self._rng = random.Random(seed)` to `BiomechanicalMousePhysics`, `CognitiveKeystrokeEngine`, and `CognitiveGazePhysics`, routing all RNG calls through `self._rng`.

- [x] **Bug 14 — `WindowsHighResolutionTimer` OS Timer Handle Leak (`mouse_physics.py`)**:
  - **Issue**: `BiomechanicalMousePhysics.__init__` called `self.timer = WindowsHighResolutionTimer()`, leaving `winmm.timeBeginPeriod(1)` active indefinitely.
  - **Fix**: Set `self.timer = None` in `__init__` so the timer is only acquired inside the `with WindowsHighResolutionTimer():` context manager during `human_move_to()`.

- [x] **Bug 15 — Duplicate `ProviderUnavailableError` Class Hierarchy (`providers/base.py`)**:
  - **Issue**: `providers/base.py` defined `class ProviderUnavailableError(RuntimeError):` unrelated to `behavioral_playwright.exceptions.ProviderUnavailableError`.
  - **Fix**: Inherit from both `behavioral_playwright.exceptions.ProviderUnavailableError` and `RuntimeError` so `except BehavioralPlaywrightError:` catches it cleanly.

- [x] **Bug 16 — `AINamespace.extract()` Silent Echo Dict When Unbooted (`src/veil/facade.py` Lines 617–621)**:
  - **Issue**: Returned `{"url": url_or_html, "schema": schema}` without extracting anything when `self._bp` was `None`.
  - **Fix**: When `url_or_html` contains raw HTML (`"<" in url_or_html and ">" in url_or_html`), parse and extract records offline using `AutoSchemaExtractor().extract(url_or_html)`.

- [x] **Bug 17 — `DOMExtractor` Mock Check & `IdentityAnchor` Dead Default Proxy (`src/veil/extraction/dom.py` Line 28 & `persona_matrix.py` Line 69)**:
  - **Issue**: `_get_raw_page()` checked `"Mock" in page.__class__.__name__`; `IdentityAnchor.__init__` defaulted `self.proxy_pool` to dead `"http://residential.proxy.internal:8080"`.
  - **Fix**: Unwrap `raw = getattr(page, "raw_page", None)` via `hasattr(raw, "evaluate")` in `dom.py`, and default `self.proxy_pool` to `[]` in `persona_matrix.py`.

- [x] **Bug 18 — Zero Silent `except ...: pass` (`SWALLOW-001`)**:
  - **Issue**: Any remaining bare `except ...: pass` in unlocked `.py` files violates `scripts/ast_anti_gaming.py`.
  - **Fix**: Replace bare `pass` inside `except` blocks in unlocked files with explicit handling or `logger.debug(...)`.

## PHASE 3: Create Zero-Mock Regression Suite (`tests/integration/test_18_bugs_remediation_real.py`)

- [x] **3.1 Author `tests/integration/test_18_bugs_remediation_real.py`**: Write a real-execution pytest suite (zero mocks) verifying:
  1. `CrawlingService().escalate_and_fetch(url)` against a live local `127.0.0.1` HTTP server returns real HTML from the server (never `"Tier 2 Content..."`).
  2. `TieredCrawlerService().check_and_rotate_context()` called synchronously outside an event loop does not raise `RuntimeError`.
  3. Root `from providers.network import CurlCffiProvider` exposes `hasattr(CurlCffiProvider(), "afetch")`.
  4. `from veil.providers.base import ProviderUnavailableError` is a subclass of `veil.exceptions.BehavioralPlaywrightError`.
  5. `BiomechanicalMousePhysics(seed=777).generate_trajectory((0, 0), (200, 200))` and `CognitiveKeystrokeEngine(seed=777).generate_human_keystroke_plan("veil")` produce 100% identical outputs across repeated runs with `seed=777`.
  6. `IdentityAnchor().get_current_proxy()` is `None` by default (never `"http://residential.proxy.internal:8080"`).
  7. `AINamespace().extract("<html><body><article><h2>Real Item</h2><p>$49.99</p></article></body></html>")` extracts structured data offline.

## PHASE 4: Run All 7 Verification Gates (All Must Exit Code `0`)

Execute each gate below in sequence and mark `[x]` only when it exits with code `0`:

- [x] **Gate 1 — Cryptographic Lock Verification**:
  `python lock_and_guard_harness.py --verify`
- [x] **Gate 2 — Honesty & Integrity Findings Validation**:
  `python scripts/validate_findings.py`
- [x] **Gate 3 — Clean Architecture & Strict DAG Audit (`0 cycles`)**:
  `python scripts/audit_architecture.py --target src/veil`
- [x] **Gate 4 — AST Anti-Gaming & Zero `SWALLOW-001` Audit**:
  `python scripts/ast_anti_gaming.py --tests "tests/**/*.py" --src "src/**/*.py"`
- [x] **Gate 5 — Wave 1 + Wave 2 + 18-Bug Real Integration Suites**:
  `python -m pytest tests/integration/test_top_01_pillars_real.py tests/integration/test_wave2_deep_crawling_real.py tests/integration/test_18_bugs_remediation_real.py -v`
- [x] **Gate 6 — Full Real-Execution Feature Verification Runner**:
  `python scripts/verify_all_features_real.py`
- [x] **Gate 7 — Full Repository Test Suite**:
  `python -m pytest -q`

## PHASE 5: Final Summary Report

- [x] **5.1 Output Final Scorecard**: Print a summary table confirming all 18 bugs are resolved, all checkboxes in `AGENT_FIX_ALL_18_BUGS_PROMPT.md` are marked `[x]`, and all 7 verification gates passed with exit code `0`.
