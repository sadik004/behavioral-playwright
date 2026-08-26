# Behavioral-Playwright Hardened Engine (v15-Ultimate)

A private behavioral-evasion and point-in-time (PiT) quantitative data framework built
around a single hardened module: `behavioral_evasion_ten_patches_hardened_v15.py`.

The framework's core contract is **honesty**: every capability reports its real status.
Where a capability is not implemented, it is *explicitly* unavailable (raises or returns
`UNAVAILABLE_NOT_IMPLEMENTED` / `captured_unprocessed`). The codebase contains no
fake-success fallbacks, no fabricated financial identifiers, no fabricated HTTP traffic,
and no fabricated decrypted payloads. Generated identifiers are **visibly synthetic**
(`sim-tx-…`, deterministic `composite_figi`).

## Status

Phases 1–9 were complete and verified; Phases 10–19 completed 2026-08-26
(resilience, UX consolidation, capability reconciliation, honesty audit,
wheel verification, CI, final architecture/self-healing/test-matrix audits).
Current suite: **345 passed / 0 failed / 0 skipped / 0 errors**.

| Phase | Scope | State |
|-------|-------|-------|
| 1 | Engineering audit | Complete |
| 2 | Critical correctness hardening | Complete |
| 3 | Real implementations / explicit quarantine | Complete |
| 4 | Self-healing integration + heal memory | Complete |
| 5 | High-level orchestration facade | Complete |
| 6 | Full test suite | Complete (185 at the time) |
| 7 | Documentation | Complete |
| 8 | Final release audit | Complete (199 tests; wheel build then unverifiable) |
| 9 | Verified lower-tier self-healing write-back | Complete (230 tests) |
| 10 | Retry/backoff/jitter/circuit-breaker subsystem | Complete (273 tests) |
| 11 | Orchestration UX: navigate verb, humanized typing, session manager | Complete (300 tests) |
| 12 | Historical capability reconciliation + SQLite observability sink | Complete (313 tests) |
| 13 | Real-implementation/honesty audit (visibly-synthetic ids, auditable skips) | Complete (323 tests) |
| 14 | Package hardening: real wheel build verified, version 1.1.0 | Complete (334 tests) |
| 15 | CI workflow (py3.9–3.12 × ubuntu/windows + wheel job) | Complete |
| 16 | Documentation synchronization | Complete |
| 17 | Final architecture audit | Complete (one dead import removed; no other defects) |
| 18 | Final self-healing lifecycle audit | Complete (345 tests) |
| 19 | Final test matrix | 345 passed / 0 failed / 0 skipped / 0 errors |

## Installation & Dependencies

```bash
pip install .                    # core (pydantic>=2 only)
pip install ".[pandas,numpy]"    # DataFrame feed + fast synthetic math
pip install ".[tls]"             # curl_cffi TLS/JA4 impersonation
pip install ".[frida]"           # native memory hooks
```

Import either path — one implementation, two names:

```python
from behavioral_playwright import BehavioralPlaywright          # public surface
from behavioral_evasion_ten_patches_hardened_v15 import BehavioralPlaywright  # canonical module
```

Required:
- `pydantic` >= 2 (data contracts; v2 validation semantics)

Optional (each degrades honestly when missing):
- `pandas` — PiT feed as DataFrame; without it `PITQuantEngine` returns plain dicts
- `numpy` — faster descriptor math in `MarketSyntheticGenerator`; pure-`math` fallback used otherwise
- `curl_cffi` — TLS/JA4 impersonation (`AsyncSession`); without it instantiation raises a
  descriptive `RuntimeError` (the old fabricated-response fallback was removed)
- `frida` — native memory hooks; absent ⇒ engine reports unavailability, captures nothing, fabricates nothing
- Playwright is **never imported by the module** — you supply live browser/page/context handles.

## Architecture

```
BehavioralPlaywright (facade)
 ├─ DynamicUSGeoIPAligner        geo-sync (locale/timezone/geo) per context
 ├─ SelfHealingSelectorEngine    MEMORY→PRIMARY→L1→L2→L3→L4 recovery cascade
 │   └─ SelectorHealMemory       persistent heal memory (JSON, atomic writes,
 │                                verified lower-tier write-back)
 ├─ RetryPolicy                  bounded attempts, exp backoff + jitter,
 │                                transient/permanent classification, timeouts
 ├─ CircuitBreaker               CLOSED/OPEN/HALF_OPEN FSM (monotonic clock)
 ├─ ObservabilitySQLiteSink      durable event journal (stdlib sqlite3)
 ├─ QuantPersistencePipeline     NDJSON persistence + contract sentinel
 │   └─ QuantDataContractSentinel schema/null/throughput gates
 ├─ ContextRotator               bounded context recycling lifecycle
 │   └─ StrictContextManager     isolated contexts (WebRTC spoof intentionally absent)
 ├─ CDPEvasionShield             CDP stack-trace stealth binding
 ├─ HardwareOSSpoofer            WebGL/hardware profile injection
 └─ BiomechanicalInteractionEngine  SigmaDrift mouse trajectories, inertial scroll,
                                    humanized typing dynamics

Data plane (independent of browser):
 PITQuantEngine · EDGARPiTAligner · CapitalMarketEntityResolver · ITCHParserLOBReconstructor
 MarketSyntheticGenerator · WebSocketDataflowStreamer · BlockchainLakehouseStreamingPipeline
 IXBRLSECParser · EDGARBalanceSheetParser · SECForm4InsiderTracker
 FridaNativeHookEngine · MitmproxyStreamInterceptor · VMASTDeobfuscator
 WasmMemoryInterceptor · MicrotaskTimingAligner · BinaryOLE2REDecoder · PyarmorCPythonUnpacker
```

## High-Level API

`BehavioralPlaywright` remains a small public surface (five verbs plus the
session context manager), not an agent:

```python
bp = BehavioralPlaywright(
    region="us-east",
    output_path="bp_output.ndjson",
    min_expected_throughput=0,      # 0 disables the throughput halt (batch mode)
    confidence_threshold=0.80,      # self-healing gate, propagated to the engine
    heal_memory_path="heal.json",   # persistent heal memory (optional)
    recycle_threshold=50,           # context rotation bound (must be >= 1)
    retry_policy=RetryPolicy(...),       # optional resilience (Phase 10)
    circuit_breaker=CircuitBreaker(...), # optional fast-fail isolation
)

await bp.attach_browser(browser)            # binds a live handle, enables rotation
nav     = await bp.navigate(url)            # stealth GET navigation (Phase 11)
element = await bp.solve("button.submit", "Submit order",
                         logical_name="submit-btn", page=page)
result  = await bp.run(my_action)           # action(page) behind the stealth stack
status  = await bp.collect(record, MySchema, event_time=...)   # PiT ingest
await bp.close()                            # flush buffer + save heal memory
# or: async with BehavioralPlaywright(...) as bp: ...   # guaranteed close()
```

Pipeline semantics per verb:

- **navigate** → validate URL loudly → loop-guard check → acquire/align context →
  stealth stack → `goto` under retry/breaker → honest `{url, status, ok}` dict;
  raises `NavigationError`/`NavigationLoopError` rather than inventing success
- **run** → acquire healthy context → geo-align → CDP shield → hardware spoof → execute → verify/cleanup
- **solve** → heal-memory fast-path → exact → Levenshtein → semantic/ARIA → spatial/heuristic,
  each tier gated by `confidence_threshold`; raises `ElementResolutionError` instead of guessing
- **collect** → entity resolution → dual-timestamp PiT validation → schema contract → buffered
  NDJSON persistence; contract breaches raise loudly

Power users can reach `bp.heal_memory`, `bp.selector_engine`, `bp.pipeline`,
`bp.sentinel`, `bp.context_rotator`, `bp.retry_policy`, `bp.circuit_breaker`.

## Resilience (Phase 10)

`RetryPolicy` and `CircuitBreaker` are reusable primitives with injectable
sleep/clock/rng for fully deterministic testing:

```python
policy = RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=30.0,
                     multiplier=2.0, jitter=True,          # exp backoff + jitter
                     per_attempt_timeout=5.0,              # timeout awareness
                     on_event=sink.record)                 # observability hook
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0,
                         half_open_max_successes=2, on_event=sink.record)

result = await breaker.execute(lambda: policy.execute(idempotent_read))
```

- **Retry safety contract**: retries apply ONLY where repetition is semantically
  safe. The facade wires them exclusively around read-only paths (`solve`,
  `navigate`); `collect()`/persistence writes are never retried or breaker-gated.
- Classification: only transient failures retry by default (`TimeoutError`,
  `ConnectionError`, `OSError`); anything else is a definite answer.
  `NonRetryableError` forces immediate failure; injectable predicate overrides all.
- Cancellation safety: `asyncio.CancelledError` propagates immediately — never
  swallowed, never counted as a failure.
- Exhaustion re-raises the ORIGINAL last exception; nothing is synthesized.

## Observability (Phase 12)

`ObservabilitySQLiteSink(db_path)` durably journals event dicts (retries,
breaker transitions, custom workflow events) into a stdlib SQLite database:

```python
sink = ObservabilitySQLiteSink("runs.db")
policy = RetryPolicy(on_event=sink.record)
...
sink.count("retry"); sink.recent(20); sink.close()
```

Hook failures are logged and never corrupt protected operations; sink
validation errors raise loudly.

## Self-Healing (Phase 4/9)

`SelfHealingSelectorEngine.resolve_element(page, selector, expected_content, logical_name, heal_memory)`:

1. **MEMORY (S1)** remembered selector tried first; below-threshold entries and
   content-mismatched hits fall through (audit fixes A1/A2)
2. **PRIMARY** — exact selector (confidence 1.00)
3. **L1 Levenshtein** — candidate attributes within threshold similarity (distance capped at 5)
4. **L2 semantic/ARIA** — accessibility attributes matching (confidence 0.90)
5. **L3 spatial/text** — bounding-box geometry + text heuristics (confidence 0.85)
6. **L4 first-button heuristic** — confidence 0.25, deliberately LOW: unreachable at the
   default threshold

Every tier enforces `confidence_threshold ∈ [0.0, 1.0]`. Successful PRIMARY/L1/L2/L3
resolutions feed heal memory through the seven-condition verified write-back contract
(real handle, confidence gate, content verification, provably-stable non-empty selector
that re-resolves on-page, never downgrading stronger entries). L4 never writes back.
First solve = recovery; subsequent solves = cheap memory fast-path.

`SelectorHealMemory`: atomic JSON writes (tmp + os.replace); corrupted files quarantined
as `<path>.corrupt`; capacity-bounded lowest-confidence eviction; stale entries fall
through to the full cascade (S2) and are refreshed. Lookups never invent results.

## Point-in-Time Data Correctness

- `PITQuantEngine.generate_quant_ready_feed(events, cutoff)` — filters rows by
  knowledge-time cutoff, selects the latest **whole row** per ticker (no column-wise
  "Frankenstein" stitching), emits a deterministic synthetic `composite_figi`.
  Malformed timestamps raise `PITimestampError` naming the offending column.
- `EDGARPiTAligner` — filing timestamp validation; raises `FilingTimestampError` on bad input.
- `CapitalMarketEntityResolver` — resolves only curated known entities (token-boundary
  match); unknown names raise `EntityResolutionError`. Never fabricates ISIN/CUSIP/FIGI.
- `QuantDataContractSentinel` — schema validation, null-ratio bound, minimum throughput
  gate; breaches raise.
- `BlockchainLakehouseStreamingPipeline` — z-score anomaly scoring against the
  pre-existing baseline window; absent `tx_hash` values are generated **visibly
  synthetic** (`sim-tx-…`), caller-supplied hashes are never modified.
- `MarketSyntheticGenerator` — GBM-style alternative paths anchored at the seed origin,
  deterministic under `random.seed`. When `event_time=None`, `ingest_market_record`
  invents a bounded extraction-time estimate (≤0.5 s before ingestion); epoch `0.0` is
  always honored exactly.

## Explicitly Unavailable / Experimental Capabilities

These are honest non-implementations; APIs are preserved for future work:

| Component | Status | Behavior |
|-----------|--------|----------|
| `BinaryOLE2REDecoder` | Quarantine | Validates OLE2 magic, counts sectors; returns `status="UNAVAILABLE_NOT_IMPLEMENTED"`, `decompressed_payload=None` |
| `PyarmorCPythonUnpacker.inject_pyeval_hooks` | Quarantine | Raises `NotImplementedError`; previously fabricated `co_names/co_consts` |
| `EDGARBalanceSheetParser.parse_balance_sheet` | Quarantine | Raises `NotImplementedError`; previously returned hardcoded sample figures |
| `SECForm4InsiderTracker.parse_insider_transactions` | Quarantine | Raises `NotImplementedError`; previously fabricated a canned transaction (`compute_risk_shifts_dask` Jaccard audit remains real) |
| Mitmproxy Protobuf/gRPC decode | Not implemented | Raw frames retained; returns `"captured_unprocessed"`; nothing ingested |
| `FridaNativeHookEngine` | Host-dependent | Reports ImportError/unavailability honestly; no payloads fabricated |
| `TLSJA4Spoofer` w/o curl_cffi | Loud failure | Instantiation raises descriptive `RuntimeError` |
| WebRTC IP masking (`StrictContextManager`) | Intentionally absent | Invalid default spoofing removed; contexts created without fake WebRTC init scripts |
| `MicrotaskTimingAligner` Promise patch | Default OFF | Global `Promise.prototype.then` wrapping breaks page timing; opt-in via `enabled=True`, warns when active |
| Crawling / search-engine / site mapping | Not restored | Gen2 implementations were broken (1-page crawl, mapper count bug) and died with that tree; extraction niche covered by `DOMToMarkdownSimplifier` |
| OCR / vision detection | Not restored | Provider-dependent (pytesseract/cv2); Gen1 fallbacks were fabricated detections |
| Webhooks / MCP integrations | Not restored | MCP tools were broken in Gen2; webhook POSTing requires network paths the suite cannot verify honestly |

## Failure Behavior

- Missing dependencies: descriptive errors naming the missing package; no silent fallbacks.
- Selector resolution below threshold: `ElementResolutionError` (never a guessed element).
- Contract violations (schema, null ratio, throughput): raised, not swallowed.
- Persistence errors and storage-state failures surface to the caller (vault protects
  against silent data loss; corrupted heal-memory files are quarantined, not discarded silently).
- All logging goes through the module's child loggers; the **root logger is never mutated**.
  Logging is opt-in via `configure_framework_logging()`. Cascade scan skips are
  debug-logged, never silent.

## Security Boundaries

- Credential sanitization in log formatting (`SanitizedLogFormatter`).
- No secrets, captured traffic, or decrypted payloads are ever synthesized.
- Generated identifiers are visibly synthetic (`sim-tx-…`) or documented as such.
- Browser automation requires caller-supplied handles; the framework cannot spawn
  uncontrolled agents (bounded verbs, explicit capabilities).
- Persistent artifacts: NDJSON output path, optional heal-memory JSON path and optional
  observability DB path — all caller-chosen.

## Testing

```bash
python -m pytest tests -q
# 345 passed
```

Suites:
- `tests/test_phase2_hardening.py` — correctness hardening regressions (log sanitization,
  vault data-loss protection, rotator lifecycle/concurrency, sentinel gates, ITCH zero-share
  removal, PiT normalization, quarantined extractors, streaming pipelines, …)
- `tests/test_phase4_selfhealing.py` — cascade tiers, thresholds, heal memory persistence/
  corruption/eviction/stale handling
- `tests/test_phase5_ux.py` — facade construction, run/solve/collect, browser attachment
- `tests/test_phase8_packaging.py` — release metadata validity + clean-interpreter import
  surface (shim re-export identity, no root-logger mutation, dependency honesty)
- `tests/test_phase9_writeback.py` — verified lower-tier write-back contract
- `tests/test_phase10_resilience.py` — retry/backoff/jitter/classification/timeouts/
  cancellation/breaker FSM/facade wiring
- `tests/test_phase11_ux_orchestration.py` — navigate verb, humanized typing,
  session context manager, end-to-end workflow proofs
- `tests/test_phase12_reconciliation.py` — SQLite sink, reconciliation decision pins
- `tests/test_audit_regressions.py` — A1/A2/A3 audit fixes
- `tests/test_phase13_honesty_audit.py` — visibly-synthetic identifiers, auditable
  skips, simulator-convenience pins, classification guards
- `tests/test_phase14_packaging.py` — real wheel build + contents + metadata
- `tests/test_phase18_healing_lifecycle.py` — full healing lifecycle across
  instances and disk (recovery → cheap memory reuse → staleness → quarantine)
- `tests/fakes.py` — shared Playwright test doubles (no network, fully deterministic)

## Limitations

- Single-module implementation by design; distributed via `pyproject.toml`
  (`behavioral-playwright` 1.1.0). Wheel build verified locally (setuptools 84 /
  wheel 0.48): payload = module + shim only; fresh-venv install + import identity checked.
- Platform status: **Windows verified**; Linux/macOS exercised only via the CI matrix
  definition (no live runner runs observed from this environment).
- iXBRL support is header/narrative-section detection, not full fact extraction.
- Entity resolution covers a curated list only.
- Balance-sheet parsing, Form 4 XML parsing, OLE2 stream extraction, DEFLATE inflation,
  Pyarmor unpacking, Protobuf decoding and real WebRTC masking remain unimplemented (see table above).
- Resilience primitives protect only explicitly wired read paths; arbitrary user actions
  passed to `run()` are never auto-retried (retrying non-idempotent actions is unsafe).
- All self-healing/resilience verification uses deterministic fakes; no live-browser E2E.

## Development History

- Phase 1: engineering audit of legacy patch stack (patches 1–28).
- Phase 2: correctness hardening — removal of all fake-success paths.
- Phase 3: real implementations with explicit unavailability semantics.
- Phase 4: self-healing cascade integration + persistent heal memory.
- Phase 5: `BehavioralPlaywright` orchestration facade.
- Phase 6–7: full regression suite green; documentation.
- Phase 8: packaging metadata + import shim (199 tests).
- Phase 9: verified lower-tier self-healing write-back (230 tests).
- Phase 10: resilience subsystem — retry/backoff/jitter/classification/breaker (273 tests).
- Phase 11: navigate verb, humanized typing, session context manager (300 tests).
- Phase 12: capability reconciliation + SQLite observability sink (313 tests).
- Phase 13: honesty audit — visibly-synthetic ids, auditable skips (323 tests).
- Phase 14: wheel build verified, version 1.1.0 (334 tests).
- Phase 15: CI workflow (py3.9–3.12 × ubuntu/windows, wheel job).
- Phase 16: documentation synchronization.
- Phase 17: final architecture audit (dead-import removal only).
- Phase 18: final self-healing lifecycle audit; absolute-C7 trade-off documented (345 tests).
- Phase 19: final test matrix — 345 passed / 0 failed / 0 skipped / 0 errors.
