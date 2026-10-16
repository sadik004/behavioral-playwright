# ROLE: Hostile Red-Team Auditor & E2E Verification Engineer

We caught a broken backward-compatibility export (`from behavioral_evasion_suite.mouse_physics import BiometricMouseController` raised `ImportError` because your shim or `src/veil/kinematics/biomechanics.py` dropped `BiometricMouseController`).

Execute the following 4 mandatory verification and remediation steps autonomously using your terminal and file tools. Do NOT touch any of the 32 files sealed in `LOCK.json`.

## STEP 1: 100% Symbol Parity Across All Legacy Shims
1. Compare every module in `archive/deduplicated_legacy/behavioral_evasion_suite/` against `behavioral_evasion_suite/` and `src/veil/kinematics/`.
2. Ensure every class and function that originally existed in `behavioral_evasion_suite` is genuinely implemented in `src/veil/` and re-exported by both `src/veil/kinematics/` and `behavioral_evasion_suite/*.py`:
   - `behavioral_evasion_suite.mouse_physics.BiometricMouseController` (must exist in `veil.kinematics.biomechanics` alongside `SigmaLognormalMotor`, with relative timestamps `0.0 <= t < 10.0` and isolated `random.Random(seed)` determinism).
   - Every class/function in `behavioral_evasion_suite/dom_telemetry.py`, `kernel_input_bridge.py`, `vision_guard.py`, `mcp_server.py`, and `__init__.py`.
3. Write an automated symbol-parity test `tests/unit/test_legacy_symbol_parity.py` that dynamically imports every module in `src/veil/`, `src/behavioral_playwright/`, `src/veil/powerplay/`, and `behavioral_evasion_suite/` and asserts that:
   - `sys.modules["behavioral_playwright.<submod>"] is sys.modules["veil.<submod>"]` for all leaf submodules.
   - Every public class/function from the legacy suite is importable without `ImportError`.

## STEP 2: Audit & Harden `src/veil/crawling/` (No Toy Stubs Allowed)
1. Inspect `src/veil/crawling/service.py` and `models.py`. Ensure `TieredCrawlerService` is a real production implementation:
   - Tier 1 (`HTTP_FAST`): Real `urllib.request` / async HTTP execution when no custom `tier1_fetcher` is injected.
   - Tier 2 (`TLS_IMPERSONATE`): Wires into `CurlCffiProvider.afetch()` by default when no custom fetcher is injected, and cleanly records `ProviderUnavailableError` in `escalation_history` if `curl_cffi` is not installed.
   - Tier 3 (`BROWSER_HEADLESS`) & Tier 4 (`BROWSER_STEALTH_KINEMATICS`): Wires into the real browser provider (`PatchrightProvider` / `PlaywrightProvider`) and `SigmaLognormalMotor` / `BiometricMouseController`, while gracefully recording `ProviderUnavailableError` in `escalation_history` if browser binaries are absent.
   - Challenge Detection: Accurately detects HTTP `403`, `429`, `503`, Cloudflare (`cf-mitigated`, `Just a moment...`, `Attention Required!`), DataDome (`datadome`), and CAPTCHA markers (`g-recaptcha`, `h-captcha`, `cf-turnstile`).

## STEP 3: Real Local HTTP Server End-to-End (E2E) Verification (`tests/integration/test_real_local_server_e2e.py`)
Create `tests/integration/test_real_local_server_e2e.py` that spins up a real local `http.server` on `127.0.0.1` (ephemeral port) in a background thread serving:
1. `GET /clean` -> `200 OK` with real HTML (`<html><body><h1>Real Data</h1></body></html>`). Verify `TieredCrawlerService` fetches it over a real TCP socket at Tier 1 (`HTTP_FAST`) with `0` escalations.
2. `GET /cf-challenge` -> `403 Forbidden` with header `cf-mitigated: challenge` and body `Just a moment... cf-turnstile`. Verify `TieredCrawlerService` hits the real socket at Tier 1, detects the Cloudflare challenge, and escalates through Tier 2 -> Tier 3 -> Tier 4 with full `escalation_history` telemetry.
3. CLI & MCP E2E Check: Execute `veil.cli.main` and invoke all 12 tools in `veil.mcp.tools` with real arguments to prove zero runtime crashes.

## STEP 4: Full Verification Gate
Run all 6 commands below in sequence and show their complete terminal output. Every single command must exit with code `0`:
1. `python lock_and_guard_harness.py --verify`
2. `python scripts/validate_findings.py`
3. `python scripts/audit_architecture.py --target src/veil`
4. `python scripts/ast_anti_gaming.py --tests "tests/**/*.py" --src "src/**/*.py"`
5. `python -m pytest tests/unit/test_legacy_symbol_parity.py tests/integration/test_real_local_server_e2e.py -v`
6. `python -m pytest -q`
