# SQ — V23 Port Audit & Hardening Workspace

This workspace is the audit and hardening site for evaluating and reconciling
capabilities from the supplied **Hardened Evasion Suite v23**
(`bp_biomechanical_engine-v23.py`) against the **protected personal baseline**
(`behavioral_evasion_ten_patches_hardened_v15.py`).

## Contents

| Path | Role |
| --- | --- |
| `behavioral_evasion_ten_patches_hardened_v15.py` | Protected baseline framework (Phase 2 honesty-hardened; authoritative) |
| `bp_biomechanical_engine-v23.py` | Supplied V23 source under audit (quarantined — not integrated) |
| `evasion_v23_documentation.md` | Supplied V23 marketing/spec document (claims audited against source) |
| `itch_binary.py` | NEW: genuine ITCH-5.0 binary subset parser (Phase 3; isolated module) |
| `providers/` | Optional provider-gated adapters: playwright, patchright, undetected_chromedriver, curl_cffi, browser_use, stagehand |
| `tests/` | 66 tests: baseline protection, V23 quarantine pins, honesty hardening, ITCH binary, provider adapters |
| `docs/development/current-checkpoint.md` | Live capability status, quarantine register, resume point |
| `docs/development/v23-port-audit-report.md` | Full V23 PORT AUDIT REPORT (initial audit) |
| `docs/development/v23-reconciliation-report.md` | Phase 1–5 hardening & reconciliation report |

## Honesty constitution (binding)

- REAL RESULT → return it.
- REAL FAILURE → raise/report it.
- UNIMPLEMENTED → explicitly quarantine it.
- NEVER → fabricate successful output (no fake payloads, fake addresses, fake status strings).

## Test suite

```bash
python -m pytest tests -q    # 66 tests: 65 passed, 0 failed, 1 skipped (opt-in UC live)
```

- `test_baseline_protection.py` — 13 tests protecting legacy baseline behavior.
- `test_v23_quarantine.py` — 7 pins proving the rejected V23 theater cannot resurface.
- `test_honesty_hardening.py` — 11 tests pinning the five Phase 2 honesty fixes.
- `test_itch_binary.py` — 17 tests for the verified-layout ITCH-5.0 binary parser
  (golden fixtures + truncation/unknown-type/lifecycle negative tests).
- `test_providers.py` — 18 tests: honest provider gating, deterministic-double
  adapter logic for ALL five providers, and LIVE browser integration for the
  two providers installed on this host (Patchright + Playwright launch real
  headless Chromium; UC live opt-in via `SQ_LIVE_UC=1`).

## Optional provider adapters (`providers/` package)

The V15 core remains authoritative and runs with **zero** optional providers
installed. Providers are selected explicitly by name and are provider-gated:
absence raises `ProviderUnavailableError` with an install hint — never a fake
fallback. These adapters support **authorized automation/testing/research**;
no provider is represented as a guaranteed bypass of any site's security controls.

```
Core (V15 + itch_binary)
├── BrowserProvider      playwright | patchright | undetected_chromedriver
├── Network/TLS Provider curl_cffi
└── AI Browser/Agent     browser_use | stagehand
```

## Final provider matrix (Phase 4 — verified)

| Provider | Available | Integrated | Tested | Optional dependency | Status |
| --- | --- | --- | --- | --- | --- |
| **Patchright** | ✔ v1.59.1 | ✔ real `sync_playwright()` API wired | ✔ **LIVE** headless Chromium, data: URL navigation + adapter doubles | `patchright` | INTEGRATED / VERIFIED-LIVE |
| **Undetected-Chromedriver** | ✔ v3.5.5 | ✔ real `uc.Chrome(headless=, use_subprocess=True)` wired | ✔ adapter doubles + live opt-in via `SQ_LIVE_UC=1` (downloads chromedriver) | `undetected-chromedriver` | INTEGRATED / PROVIDER-GATED-LIVE |
| **curl-cffi** | ✘ | ✔ real `curl_cffi.requests.<method>(url, impersonate=...)` wired | ✔ adapter doubles; absence raises `ProviderUnavailableError` | `curl-cffi` | INTEGRATED / PROVIDER-GATED |
| **Browser-Use** | ✘ | ✔ real `browser_use.Agent(task=..., llm=...).run()` wired | ✔ adapter doubles; absence raises `ProviderUnavailableError`; LLM mandatory (never fabricated) | `browser-use` (+ LLM) | INTEGRATED / PROVIDER-GATED |
| **Stagehand** | ✘ | ✔ real async `stagehand.Stagehand.create(browser=, model=, model_api_key=)` wired | ✔ adapter doubles; absence raises `ProviderUnavailableError`; model+key mandatory (never fabricated) | `stagehand` (+ model API key) | INTEGRATED / PROVIDER-GATED |

**Definitions** (per Phase 4 mandate):
- *Available* — backing module actually importable in the selected interpreter.
- *Integrated* — real API call wired in code, not a stub.
- *Tested* — meaningful behavior verified (deterministic doubles for absent providers; live integration for installed ones).
- *VERIFIED-LIVE* — a real headless Chromium was launched by this provider in this repo's test suite.
- *PROVIDER-GATED* — adapter wired but unavailable on this host; every call raises `ProviderUnavailableError` with an install hint. No fallback, no synthetic response.

Architecture is preserved: the V15 core (`behavioral_evasion_ten_patches_hardened_v15.py`) is untouched and runs with **zero** optional providers installed. Providers are selected explicitly by name:

```python
from providers import (
    create_browser_provider, create_network_provider, create_agent_provider,
)

pw  = create_browser_provider("patchright")                  # headless Chromium
hl  = create_network_provider("curl_cffi")                   # TLS impersonation
ag  = create_agent_provider("browser_use")                   # AI browser agent
```

Unknown names raise `UnknownProviderError` listing the valid choices (machine-detectable — never a `KeyError`).

## Git

Local repository on branch `main`. Commits record the protected V23-audit
baseline, the Phase 1–5 hardening release, the provider-integration release,
and final reconciliation. **No remote; nothing pushed.**
