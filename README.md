# Behavioral-Playwright Hardened Engine (v15-Ultimate)

A private behavioral-evasion and point-in-time (PiT) quantitative data framework built
around a single hardened module: `behavioral_evasion_ten_patches_hardened_v15.py`.

The framework's core contract is **honesty**: every capability reports its real status.
Where a capability is not implemented, it is *explicitly* unavailable (raises or returns
`UNAVAILABLE_NOT_IMPLEMENTED` / `captured_unprocessed`). The codebase contains no
fake-success fallbacks, no fabricated financial identifiers, no fabricated HTTP traffic,
and no fabricated decrypted payloads.

## Status

Roadmap phases 1–7 are complete and verified; Phase 8 (final release audit)
completed 2026-08-26. Distribution metadata (`pyproject.toml`) and the
`behavioral_playwright` import surface were added during Phase 8.

| Phase | Scope | State |
|-------|-------|-------|
| 1 | Engineering audit | Complete |
| 2 | Critical correctness hardening | Complete |
| 3 | Real implementations / explicit quarantine | Complete |
| 4 | Self-healing integration + heal memory | Complete |
| 5 | High-level orchestration facade | Complete |
| 6 | Full test suite | 199 passed, 0 failed, 0 skipped (141 phase2 + 27 phase4 + 17 phase5 + 14 phase8) |
| 7 | Documentation | Complete |
| 8 | Final release audit | Complete (2026-08-26; wheel-build verification blocked locally by missing setuptools — see Limitations) |

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
 ├─ SelfHealingSelectorEngine    4-tier selector recovery cascade
 │   └─ SelectorHealMemory       persistent heal memory (JSON, atomic writes)
 ├─ QuantPersistencePipeline     NDJSON persistence + contract sentinel
 │   └─ QuantDataContractSentinel schema/null/throughput gates
 ├─ ContextRotator               bounded context recycling lifecycle
 │   └─ StrictContextManager     isolated contexts (WebRTC spoof intentionally absent)
 ├─ CDPEvasionShield             CDP stack-trace stealth binding
 ├─ HardwareOSSpoofer            WebGL/hardware profile injection
 └─ BiomechanicalInteractionEngine  SigmaDrift mouse trajectories, inertial scroll

Data plane (independent of browser):
 PITQuantEngine · EDGARPiTAligner · CapitalMarketEntityResolver · ITCHParserLOBReconstructor
 MarketSyntheticGenerator · WebSocketDataflowStreamer · BlockchainLakehouseStreamingPipeline
 IXBRLSECParser · EDGARBalanceSheetParser · SECForm4InsiderTracker
 FridaNativeHookEngine · MitmproxyStreamInterceptor · VMASTDeobfuscator
 WasmMemoryInterceptor · MicrotaskTimingAligner · BinaryOLE2REDecoder · PyarmorCPythonUnpacker
```

## High-Level API (Phase 5)

`BehavioralPlaywright` is the single entry point. Three verbs, no autonomous agent:

```python
bp = BehavioralPlaywright(
    region="us-east",
    output_path="bp_output.ndjson",
    min_expected_throughput=0,      # 0 disables the throughput halt (batch mode)
    confidence_threshold=0.80,      # self-healing gate, propagated to the engine
    heal_memory_path="heal.json",   # persistent heal memory (optional)
    recycle_threshold=50,           # context rotation bound (must be >= 1)
)

await bp.attach_browser(browser)            # binds a live handle, enables rotation

element = await bp.solve("button.submit", "Submit order",
                         logical_name="submit-btn", page=page)
result  = await bp.run(my_action)           # action(page) behind the stealth stack
status  = await bp.collect(record, MySchema, event_time=...)   # PiT ingest
await bp.close()                            # flush buffer + save heal memory
```

Pipeline semantics per verb:

- **run** → acquire healthy context → geo-align → CDP shield → hardware spoof → execute → verify/cleanup
- **solve** → heal-memory fast-path → exact → Levenshtein → semantic/ARIA → spatial/heuristic,
  each tier gated by `confidence_threshold`; raises `ElementResolutionError` instead of guessing
- **collect** → entity resolution → dual-timestamp PiT validation → schema contract → buffered
  NDJSON persistence; contract breaches raise loudly

Power users can reach `bp.heal_memory`, `bp.selector_engine`, `bp.pipeline`, `bp.sentinel`, `bp.context_rotator`.

## Self-Healing (Phase 4)

`SelfHealingSelectorEngine.resolve_element(page, selector, expected_content, logical_name, heal_memory)`:

1. **S1 memory fast-path** — remembered selector tried first on a hit
2. **PRIMARY** — exact selector (confidence 1.00)
3. **L1 Levenshtein** — candidate attributes within threshold similarity (distance capped at 5)
4. **L2 semantic/ARIA** — role/label/text matching (confidence 0.90)
5. **L3 spatial/text** — bounding-box geometry + text heuristics (confidence 0.85)
6. **L4 first-button heuristic** — confidence 0.25, deliberately LOW: unreachable at the
   default threshold; becomes reachable only when a caller explicitly lowers it below 0.25

Every tier enforces `confidence_threshold ∈ [0.0, 1.0]` (constructor validates); low-confidence
results never pass. On success through the cascade, the resolution is **remembered**
(logical name → selector, tier, confidence, UTC timestamp).

`SelectorHealMemory` records target name, healed selector, strategy tier, confidence and
update time; persists to JSON via atomic write (`tmp` + `os.replace`); a corrupted file is
quarantined as `<path>.corrupt` and memory rebuilds empty (recovery never crashes the host);
capacity-bounded with lowest-confidence/oldest eviction; stale entries fall through to the
full cascade and are overwritten (`S2`). Lookups never invent results.

## Point-in-Time Data Correctness

- `PITQuantEngine.generate_quant_ready_feed(events, cutoff)` — filters rows by
  `event_time ≤ cutoff < knowledge_time` semantics, selects the latest **whole row**
  per ticker (no column-wise "Frankenstein" stitching), emits a deterministic
  `composite_figi` derived via stable hash (no invented identifiers). Malformed or
  missing timestamps raise `PITimestampError` naming the offending column.
- `EDGARPiTAligner` — filing timestamp validation; raises `FilingTimestampError` on bad input.
- `CapitalMarketEntityResolver` — resolves only curated known entities (case-insensitive,
  embedded matches supported); unknown names raise `EntityResolutionError`. Never fabricates ISIN/CUSIP/FIGI.
- `QuantDataContractSentinel` — schema validation, null-ratio bound (`max_null_ratio`),
  and minimum throughput gate (`min_expected_throughput` ≥ 0); breaches raise.
- `BlockchainLakehouseStreamingPipeline` — z-score anomaly scoring against the
  **pre-existing baseline window** (the newcomer is scored before admission), preventing
  self-masking of extreme transactions; warm-up (< 2 baseline points) yields `z_score = 0`.
- `MarketSyntheticGenerator` — GBM-style alternative paths anchored at the seed origin
  (`series[0] == seed_series[0]`), drift/vol from the seed path, deterministic under `random.seed`.

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

## Failure Behavior

- Missing dependencies: descriptive errors naming the missing package; no silent fallbacks.
- Selector resolution below threshold: `ElementResolutionError` (never a guessed element).
- Contract violations (schema, null ratio, throughput): raised, not swallowed.
- Persistence errors and storage-state failures surface to the caller (vault protects
  against silent data loss; corrupted heal-memory files are quarantined, not discarded silently).
- All logging goes through the module's child loggers; the **root logger is never mutated**.
  Logging is opt-in via `configure_framework_logging()`.

## Security Boundaries

- Credential sanitization in log formatting (`SanitizedLogFormatter`).
- No secrets, captured traffic, or decrypted payloads are ever synthesized.
- Browser automation requires caller-supplied handles; the framework cannot spawn
  uncontrolled agents (bounded verbs, explicit capabilities).
- Persistent artifacts: NDJSON output path and optional heal-memory JSON path — both caller-chosen.

## Testing

```bash
python -m pytest tests -q
# 199 passed
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
- `tests/fakes.py` — shared Playwright test doubles (no network, fully deterministic)

## Limitations

- Single-module implementation by design; distributed via `pyproject.toml`
  (`behavioral-playwright`) with a thin `behavioral_playwright` import surface.
  Wheel-build verification was blocked in the audit environment (setuptools/wheel absent);
  metadata is tomllib-validated and the import surface is subprocess-tested.
- Platform status: **Windows verified**; Linux/macOS unverified (pure-Python, but unexercised).
- iXBRL support is header/narrative-section detection, not full fact extraction.
- Entity resolution covers a curated list only.
- Balance-sheet parsing, Form 4 XML parsing, OLE2 stream extraction, DEFLATE inflation,
  Pyarmor unpacking, Protobuf decoding and real WebRTC masking remain unimplemented (see table above).
- Lower-tier heal write-back: only PRIMARY-tier resolutions persist to heal memory;
  lower tiers return raw element handles (stable-selector extraction pending).

## Development History

- Phase 1: engineering audit of legacy patch stack (patches 1–28).
- Phase 2: correctness hardening — removal of all fake-success paths (fabricated HTTP
  responses, decrypted payloads, unpacked bytecode, WebRTC spoofing defaults), root-logger
  isolation, sentinel/throughput gates, PiT row-consistency, baseline-window anomaly scoring,
  origin-anchored synthetic series generation.
- Phase 3: real implementations with explicit unavailability semantics where genuine work
  remains (OLE2, Pyarmor, Protobuf decode).
- Phase 4: self-healing cascade integration + persistent heal memory.
- Phase 5: `BehavioralPlaywright` orchestration facade (plan→execute→heal→verify→persist).
- Phase 6: full regression suite green (185 tests).
- Phase 7: this document.
