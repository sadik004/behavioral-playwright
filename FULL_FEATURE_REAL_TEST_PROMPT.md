# ROLE: Principal QA & Real-Execution Feature Verification Engineer

The user wants a **100% Real-Execution Verification Suite** across **ALL previously developed features and subsystems** in the repository (`src/veil/` / `src/behavioral_playwright/` / `behavioral_evasion_suite/` / `itch_binary.py`).

CRITICAL RULE: **ZERO `unittest.mock` / `MagicMock` / `monkeypatch` ALLOWED** in this verification suite. Every feature must be executed with real inputs, real local TCP/HTTP sockets (`127.0.0.1`), real temporary filesystem/SQLite I/O, real DOM/HTML/JSON/binary payloads, and real math. Do NOT modify any of the 32 files sealed in `LOCK.json`.

---

## STEP 1: Complete Feature Discovery & Symbol Restoration
1. Scan every subpackage under `src/veil/` (all ~149 modules) and `archive/deduplicated_legacy/` to catalog every feature subsystem previously developed in this repository.
2. Restore any missing backward-compatible class/function exports (including `BiometricMouseController` in `veil.kinematics.biomechanics` and `behavioral_evasion_suite.mouse_physics`, plus all classes in `dom_telemetry`, `kernel_input_bridge`, `vision_guard`, `mcp_server`, and `itch_binary`).

---

## STEP 2: Build `scripts/verify_all_features_real.py` & `tests/integration/test_all_features_real.py`
Create a comprehensive, zero-mock real execution verifier (`scripts/verify_all_features_real.py`) and corresponding pytest suite (`tests/integration/test_all_features_real.py`) that starts a **Real Multi-Route Local HTTP Server (`http.server` / `ThreadingHTTPServer` on `127.0.0.1`)** serving:
- `/html`: Complex e-commerce/article HTML DOM with tables, links, forms, and metadata.
- `/api/json`: Paginated JSON API payload for network sniffer & extractor verification.
- `/login` & `/session`: Real `Set-Cookie` session authentication endpoint.
- `/flaky`: Returns `503 Service Unavailable` twice and `200 OK` on the 3rd attempt (to test real Resilience/Retry/Circuit-Breaker recovery).
- `/cf-challenge`: Returns `403 Forbidden` with `cf-mitigated: challenge` and Cloudflare Turnstile HTML (`cf-turnstile`).

Then execute and verify **EVERY previously developed feature subsystem** against real runtime data:
1. **Kinematics & Biomechanics (`veil.kinematics.biomechanics`, `mouse_physics`)**:
   - Execute `SigmaLognormalMotor` and `BiometricMouseController` on real coordinate pairs; verify Fitts's Law scaling, relative timestamps (`0.0 <= t < 10.0`), velocity bell-curve entropy, and 100% seed determinism.
2. **Linguistic Keystroke Dynamics (`veil.kinematics.keystrokes`)**:
   - Generate real keydown/keyup sequences for multi-sentence strings; verify QWERTY Euclidean distance scaling and monotonic Weibull timestamps.
3. **Layer-4 Network & OS Bridge (`veil.kinematics.network_l4`, `os_bridge`, `kernel_input_bridge`)**:
   - Execute real OS socket inspection (`getsockopt(IP_TTL)`), PID memory governance (`memory_pid.py`), `schema_guard.py`, `tracking.py`, `validator.py`, `vision_guard.py`, `captcha.py`, and `orchestrator.py`.
4. **Stealth, Fingerprinting & Evasion Subsystems (`veil.stealth`, `veil.fingerprinting`, `dom_telemetry`, etc.)**:
   - Execute every stealth patch generator, fingerprint profile builder, WebGL/Canvas/navigator spoof script generator, and validate the generated JS syntax and payload integrity.
5. **Extraction, Parsing & Binary Protocol (`veil.extraction`, `itch_binary.py`, DOM parsers)**:
   - Run real HTML/DOM extraction and schema validation against the live `/html` and `/api/json` endpoints, and run real binary packet encoding/decoding through `itch_binary.py`.
6. **Resilience, Orchestration & Concurrency (`veil.resilience`, `veil.orchestration`)**:
   - Run the real recovery/retry engine and conditions evaluator against the live `/flaky` server endpoint and verify it recovers on the 3rd attempt.
7. **Storage, Export & Session Vault (`veil.storage`, `DataStorageManager`, session persistence)**:
   - Write real scraped records to temporary disk files (JSON, CSV, JSONL, SQLite) and read them back byte-for-byte; test real cookie/session vault save & reload against `/login`.
8. **Network Sniffer, Proxy & Intelligence (`veil.network`, `veil.intelligence`, `facade.py`)**:
   - Execute `BehavioralPlaywrightFacade`, `facade.intel`, `log_execution`, and network sniffer/classifier on real HTTP responses and challenge payloads.
9. **Providers (`PlaywrightProvider`, `PatchrightProvider`, `CurlCffiProvider`, `OllamaProvider`, `PyAutoGuiProvider`)**:
   - Probe real installed status; if `curl_cffi` or `playwright`/`patchright` is installed on the machine, execute a real live request against `127.0.0.1`; if not installed, verify honest `ProviderUnavailableError` behavior.
10. **4-Tier Adaptive Crawler, Unified MCP Server (12 Tools) & CLI (`veil.crawling`, `veil.mcp`, `veil.cli.main`)**:
    - Run `TieredCrawlerService` against live `127.0.0.1/html` and `127.0.0.1/cf-challenge`, invoke all 12 MCP tools with real arguments, and run `veil.cli.main` commands via real subprocess execution.

---

## STEP 3: Generate Complete Feature-by-Feature Scorecard (`REAL_FEATURE_REPORT.md`)
Have `python scripts/verify_all_features_real.py` print a formatted terminal table AND write `REAL_FEATURE_REPORT.md` listing **every single tested feature module**, what real input was given, the real measured output, execution time (ms), and `PASS`/`FAIL` status.

## STEP 4: Final Verification Gate
Run and show full output for:
1. `python scripts/verify_all_features_real.py`
2. `python -m pytest tests/integration/test_all_features_real.py -v`
3. `python lock_and_guard_harness.py --verify`
4. `python scripts/audit_architecture.py --target src/veil`
5. `python scripts/ast_anti_gaming.py --tests "tests/**/*.py" --src "src/**/*.py"`
6. `python -m pytest -q`
