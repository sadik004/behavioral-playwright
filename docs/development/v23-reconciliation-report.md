# V23 RECONCILIATION & HARDENING REPORT (Phases 1–5)

Date: 2026-08-31 · Workspace: `E:\SQ` · Branch: `main`

## 1. Phase 1 — repository protection

- Baseline verified: **20 passed** before any change; `py_compile` OK.
- Git was already initialized at session start (protection commit `2e99811`,
  root commit on `main`, created at the end of the previous session — the
  "no repository" context note was outdated). Verified, not re-created.
- Files in protection commit: `.gitignore`, `README.md`, V15 source, V23 source,
  V23 documentation, 2 audit docs, 2 test files. No artifacts, no secrets.

## 2. Phase 2 — honesty/data-integrity hardening (5/5 fixed, in v15)

| Wart | Before | After (verified by new tests) |
| --- | --- | --- |
| A. Frida fallback | ImportError path fabricated `{"company": "Tesla", ...}` through the real-hook callback | No callback invocation on provider absence; returns `False`; explicit UNAVAILABLE logging |
| B. Mitmproxy interceptor | Ingested hardcoded `{"id": 110, "company": "Microsoft", ...}` regardless of captured bytes | Ingestion only via optional `payload_decoder(raw)`; without decoder: captured bytes preserved in flow, explicit warning, no ingestion; empty decode → skip |
| C. hash()-FIGI | `composite_figi = f"BBG{hash(...)}"` (non-deterministic, fake format) | `composite_figi = None` on both pandas and fallback paths, with explicit registry-unavailable warning |
| D. Event-time jitter | `t0 = event_time if event_time else now - random.uniform(0.1, 0.5)` | `0.0` preserved verbatim (`is not None`); missing → `event_timestamp = knowledge_timestamp` + machine-readable `event_time_estimated: True`, never random |
| E. Synthetic entity IDs | Fake-real `US…`/`BBG…` strings for unresolved companies | Visibly `SYNTH-…-ISIN/CUSIP/FIGI` + `synthetic: True`; registry hits carry `synthetic: False` |

No unrelated refactors; legacy behavior otherwise unchanged; 13 pre-existing
baseline-protection tests remained green throughout.

## 3. Phase 3 — TRUE ITCH-5.0 binary parser (`itch_binary.py`, new isolated module)

- **Layouts verified from authoritative sources before implementation** (official
  spec PDF at nasdaqtrader.com + spec-table reproductions: kevingivens.github.io
  verbatim Add Order table; shawfdong/itch5parser endianness statement; bbalouki/itch
  message field sets; docs.rs `itchy` Price4). No layout was invented.
- **Honest scope — implemented subset only:** `A` Add Order (36 B), `E` Order
  Executed (31 B), `X` Order Cancel (23 B), `D` Order Delete (19 B), `U` Order
  Replace (35 B), `P` Trade (44 B). **This is NOT a complete ITCH-5.0 implementation.**
- 2-byte big-endian length-prefix framing; strict per-type length validation;
  6-byte big-endian nanoseconds-since-midnight timestamps; prices = 4 implied
  decimals; unknown message types and malformed/truncated chunks are explicit
  typed errors, never silently accepted; deterministic order lifecycle with
  duplicate/over-execution/over-cancel rejection; stream recovery after errors.
- Dollar bars accumulated ONLY from 'E' executions and 'P' trades — never resting
  notional (regression-tested: a $10M resting bid produces zero bars).
- Legacy V15 `ITCHParserLOBReconstructor` untouched and still authoritative for
  dict-payload simulation. 18 new tests (golden byte fixtures + negatives).

## 4. Phase 4 — V23 capability reconciliation matrix

Evidence classes: `REVIEWED` = implementation read this session/prior audit with
pinned evidence; `UNREVIEWED` = classified by pattern, kept quarantined honestly.

| V23 capability | Classification | Evidence |
| --- | --- | --- |
| `PointInTimeDataContractEngine` | **REJECTED** | REVIEWED — fabricated `T_event = now−100ms`; baseline contract superior |
| `NasdaqItchLOBParser` | **REJECTED** | REVIEWED — add-only dict book, wrong dollar-bar semantics; superseded by real `itch_binary.py` |
| `FridaMemorySnoopingInterceptor` | **REJECTED** | REVIEWED — hardcoded payload/address/status; zero Frida API calls |
| `ASTJavaScriptDeobfuscator` | **REJECTED** | REVIEWED — string-replace + hardcoded `ast_nodes_parsed: 1284` |
| `HTTP2SettingsPriorityEngine` | **REJECTED** | REVIEWED this session — constant success dict, `ja4_transport_aligned: True` hardcoded |
| `V8StackDepthHarmonizer` | **REJECTED** | REVIEWED this session — hardcoded `max_call_stack_depth: 10468`, no mechanism |
| `CPPDriverZeroCDPShield` | **REJECTED** | REVIEWED this session — constant `isTrusted: True` success dict, no driver interaction |
| `AutomaticCAPTCHASolverPlugin` | **REJECTED** | REVIEWED this session — fabricates "simulated" tokens + fake latency; no API call |
| `BiomechanicalTremorEngine` | **KEEP_V15** | REVIEWED — genuine numpy motion math, but V15 baseline already covers biomechanics |
| Remaining 34 classes (spoofers, shields, routers, daemons) | **QUARANTINED (UNREVIEWED)** | Same constant-status-dict pattern in every reviewed sample; not individually audited |

**Nothing was ported from V23.** No capability satisfied all of: genuinely
functional, stronger than baseline, non-duplicative, testable, honest.

## 5. Phase 5 & 6 — final verification

- `python -m pytest tests -q` → **65 passed, 0 failed, 1 skipped** (66 collected).
- `python -m compileall .` → exit 0. `python -m pip check` → clean.
- Packaging: none exists (no `pyproject.toml`) → wheel validation **UNIMPLEMENTED**,
  honestly reported rather than faked.
- Provider layer: 5 optional adapters integrated (Playwright/Patchright verified live; UC gated live; curl_cffi/Browser-Use/Stagehand provider-gated).
- Local commits on `main`; no remote, no push, no history rewrite.

## Capability status taxonomy (Framework Standard)

1. **VERIFIED / REAL**: V15 PIT contract + as-of filtering; EDGAR aligner; data-contract sentinel;
   legacy ITCH dict simulation; dollar bars (legacy + binary); `itch_binary.py`
   verified-subset binary parsing; order-book lifecycle/snapshots; Patchright & Playwright live browser launch.
2. **PROVIDER-GATED**: `FridaNativeHookEngine` (real Frida path; degrades honestly without fake payloads);
   Undetected-Chromedriver (opt-in live); `curl_cffi`, `Browser-Use`, `Stagehand` adapters.
3. **DESIGN-ACCEPTED / SYNTHETIC**: `CapitalMarketEntityResolver` visibly synthetic IDs (`SYNTH-*-ISIN/CUSIP/FIGI`
   with `synthetic: True` and hash salt for disambiguation); legacy V15 ITCH `"C"` dictionary simulation label.
4. **QUARANTINED**: all 43 classes of V23 (reference-only file `bp_biomechanical_engine-v23.py`).
5. **UNIMPLEMENTED**: packaging/CI; remaining ITCH-5.0 message types (S/R/H/Y/L/V/W/K/J/h/I/N/Q/B/O);
   live external FIGI registry; remaining 34 unreviewed V23 classes.
6. **LIMITATIONS**: UC live test opt-in via `SQ_LIVE_UC=1` to avoid automatic binary downloads;
   local-only git repository (no remote).

— END OF REPORT —
