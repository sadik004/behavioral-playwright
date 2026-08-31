# Current Checkpoint — 2026-08-31 (V23 Port Audit)

Status: **AUDIT COMPLETE — 3× REJECT — baseline intact — quarantines pinned.**

## Workspace truth (verified on disk, not assumed)

- `E:\SQ` contains ONLY the supplied V23 sources and the artifacts of this audit.
- **No git repository** exists (`git rev-parse` → `fatal: not a git repository`).
  No commits, no remote, nothing pushed. The premise of an existing
  "protected release state" with tests/CI/docs on disk was **not** found — the
  protected personal baseline exists as a single file (below).
- No pre-existing test suite, README, `docs/`, packaging, or CI existed.
  Baseline test count before this audit: **0**.

## Protected baseline (framework of record)

`behavioral_evasion_ten_patches_hardened_v15.py` — untouched this audit.
Relevant capabilities verified by the new suite:
`ITCHParserLOBReconstructor` (order lifecycle + real dollar bars),
`EDGARPiTAligner` + `QuantDataContractSentinel` + `PITQuantEngine`
(PiT dual-timestamp contract + as-of filtering), `FridaNativeHookEngine`
(real, provider-gated Frida path).

## Capability status matrix (V23 → verdict)

| V23 capability | Verdict | Reason (one line) |
| --- | --- | --- |
| `PointInTimeDataContractEngine` | **REJECT** | Fabricates `T_event = now − 100ms`; baseline already implements the real contract with real timestamps. |
| `NasdaqItchLOBParser` | **REJECT** | Add-only dict book, no binary parsing, "dollar bar" = resting-book notional; baseline already has lifecycle + real dollar bars. |
| `FridaMemorySnoopingInterceptor` | **REJECT** | 100% hardcoded theater (fixed hex payload, invented address, fake "Hooked" status); baseline has a real provider-gated Frida path. |

Nothing from V23 was integrated. Public API and facade unchanged.

## Quarantine register

### V23 (supplied file `bp_biomechanical_engine-v23.py`) — REJECTED, pinned by tests
1. Frida interceptor: constant hex payload (33 bytes) vs claimed `intercepted_bytes=32`;
   protobuf header declares 45 bytes with fewer remaining; embedded float 1600.0 vs
   claimed strike 1599.99; invented address `0x7f83a1b2c3d4`; "Hooked into libssl.so"
   status with **zero** Frida API calls (proven via sentinel).
2. ITCH parser: only `'A'` handled; `'D'/'E'/'X'/'U'` silently "succeed"; orders never
   leave the book; dollar-bar flag fires on a $6M resting bid with zero trades.
3. PiT engine: `T_event` always `T_knowledge − 100ms` regardless of the record's real
   event time; mutates the caller's dict in place.

### Baseline (v15) known honesty warts — DOCUMENTED, NOT FIXED this audit (additive-only mandate)
1. `FridaNativeHookEngine.spawn_and_hook` ImportError fallback pushes a **fabricated**
   payload (`{"company": "Tesla", "rank": 4.5}`) through the same callback used for
   real hooks. Boolean return `False` is honest; the callback payload is not.
   Pinned for visibility in `test_frida_engine_degrades_honestly_when_frida_absent`.
2. `MitmproxyStreamInterceptor.response` ingests a hardcoded
   `{"id": 110, "company": "Microsoft", "rank": 4.8}` instead of decoding captured bytes.
3. `PITQuantEngine` synthesizes `composite_figi` via `hash()` (fabricated identifier,
   also non-deterministic across processes).
4. `QuantPersistencePipeline.ingest_market_record` fabricates `event_time` with random
   jitter when absent.
5. `CapitalMarketEntityResolver.resolve` generates synthetic ISIN/CUSIP/FIGI for
   unmatched companies (labeled in logs, but still fabricated identifiers in data).
6. V15 ITCH message-type labels diverge from ITCH 5.0 (`C` used as cancel; real ITCH:
   `X` cancel, `D` delete, `C` execute-with-price). Neither V15 nor V23 parses the
   binary ITCH wire format — **do not describe either as a full NASDAQ ITCH parser**.

## Test suite

Run: `python -m pytest tests/ -v`
- Before audit: **0 tests** (none existed).
- After audit: **20 passed, 0 failed, 0 skipped** (0.51 s).
  - `tests/test_baseline_protection.py` — 13 tests (ITCH lifecycle ×4, dollar bars ×2,
    EDGAR PiT ×2, sentinel ×2, PITQuantEngine ×2, Frida honest degradation ×1).
  - `tests/test_v23_quarantine.py` — 7 pins (Frida theater ×3, ITCH fake-success ×2,
    PiT fabrication ×1, theater-constant leak guard ×1).

## Validation record (2026-08-31)

- `python -m py_compile` on both source files: **OK** (V23 emits two `SyntaxWarning`s
  for invalid escape sequences in docstrings — pre-existing, cosmetic).
- `importlib` module load of both files: **OK**.
- Network/exec scan of both sources: no `requests`/`socket`/`subprocess`/`urlopen`.
- Secret scan: no real credentials. Findings: V15:1871 demo proxy credential
  `socks5://sec_user:secret_password_123@...` in a log line (runtime-scrubbed by
  `SanitizedLogFormatter`, still in source); V23 demo defaults `DEMO_API_KEY`,
  `ca_4f7e21a8d0b2`.
- `git diff --check`: **N/A** — no repository exists (nothing initialized, per
  audit mandate).

## Safe resume point

Next phase, step 0: `git init` + initial commit of the current tree (baseline files
byte-identical), then optionally add the real remote. Do not rewrite baseline files;
fix baseline honesty warts (register above) additively with provider-gated honest
degradation. Full report: `docs/development/v23-port-audit-report.md`.
