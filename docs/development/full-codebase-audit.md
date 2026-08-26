# Full Codebase Audit — behavioral-playwright

> Audit date: 2026-08-26. Based on the actual repository history (18 commits,
> tag `v10.0.0`, branches `main`/`refactor/src-layout`) and a line-by-line read
> of every generation. No remote operations were performed.

---

## 1. Repository

| Item | Value |
|------|-------|
| Local path | `D:\behave` |
| Remote | `https://github.com/sadik004/behavioral-playwright.git` |
| Local branch | `main` @ `6f71863` (verified baseline) |
| Remote main | `origin/main` @ `cc6da38` (untouched during audit) |
| Tag | `v10.0.0` → `8e089b6` |
| Test status after audit fixes | **209 passed / 0 failed / 0 skipped / 0 errors** (199 baseline + 10 audit regressions) |

## 2. Historical Evolution (generations)

### Generation 1 — v10.0.0 "Quantum" (`8e089b6`, tagged)
Modular package `src/behavioral_playwright/`: `ai/` (llm, self_healing,
vision/ocr/detector), `behavior/` (BehavioralHumanizer, 430 lines), `math_engine/`
(bezier, chaos/Lorenz, sigmadrift), `navigation/` (circuit breaker, Markov loop
detector), `providers/` (CDP/cloak/playwright/mock factory), `diagnostics/`,
`config/`, `utils/` (clocks/RNG, a genuine mini CSS-selector engine).

**Honesty verdict: ~60% real core wrapped in an inflated shell.**
- REAL: all of `math_engine` (Sigma-lognormal/Fitts/AR(1) tremor), circuit
  breaker, Markov loop detector, retry/backoff navigation, linguistic keystroke
  model, ExploitPoCExporter, CSS engine.
- MOCK-THEATER on error/fallback paths: fabricated LLM JSON responses
  (`provider.py:79-108`), fake vision detections ("Login"/"Submit"/"Enter
  Username" at fixed boxes, `engine.py:102-117`), canned DOM candidates in the
  healing resolver (`resolver.py:45-51`), `b"mock_png"` screenshots, default
  captcha solver that sleeps and returns True, hardcoded OTP `"729481"`,
  TPM signature fabrication, eBPF/JA4/trust-score props (~12 decorative
  diagnostics classes). Verification OR'd four success signals so failure was
  nearly unreportable; provider cascade silently ended in MockBrowserProvider.

### Generation 2 — v1.0.0 reboot + BP facade (`381be14` … `bdfbb3d`)
Legacy v10 source deleted (`e1731aa`); new flat package:
automation/browser/config/extraction/models/page/resilience/selectors, then
facade.py (`BP` with boot/open/goto/click/type/fill/scroll/screenshot/
extract/crawl/search/map/handoff/verify + web/infrastructure/observability/
network/integrations namespaces), crawler, search engine, site mapper, session
handoff, state verifier. De-mocking campaign visible in
`docs/debugging/known-problems.md`.

**Verdict: good real core, frayed edges at `cc6da38`:**
- Latent bugs shipped live: `bp.crawl()` crawled exactly 1 page (metadata key
  mismatch `crawler.py:46` vs `dom.py:34-36`); `SiteMapper.map()` always
  reported 0 external links (same mismatch); 3 of 4 MCP tools raised
  AttributeError (called nonexistent `bp.web.crawl/map/search`); `boot()`
  returned None against its own annotation; humanizer sentinel `object()`
  made "humanized" actions permanently raise or degrade to raw Playwright.
- `_legacy_facade12.py` (1,978 lines) was dead, unimportable code still shipped
  in the wheel, containing fabricated "evasion probability" theater.
- `dist/` shipped a THIRD architecture whose offline LLM returned silent mocks.
- Docs corpus advertised ai/intelligence/humanization/PDF/DOCX/cache/proxy/HAR
  capabilities that did not exist in the live tree ("Last Verified Against
  Commit 68a3d1e", two generations stale).
- Real and honest: resolver cascade L1→L2→L3, resilience primitives with
  injectable clocks, SQLite observability, OCR raising ProviderUnavailableError
  instead of faking, mock provider explicit opt-in only.

### Generation 3 — current baseline (`6f71863`, local)
The entire 114-file `src/` tree, examples, docs knowledge base and old tests
were replaced by the single hardened module
`behavioral_evasion_ten_patches_hardened_v15.py` (3,085 lines) + 4 phase test
suites + thin `behavioral_playwright` re-export shim + pyproject. This is the
"patches 1–28 → phases 1–8" lineage documented in README/current-checkpoint.

## 3. Current Architecture

Single module, three planes:

- **Browser plane**: SanitizedLogFormatter, CDPEvasionShield, TLSJA4Spoofer,
  BiomechanicalInteractionEngine (WindMouse), HardwareOSSpoofer, ContextRotator
  (new-before-old rotation under asyncio.Lock), DynamicUSGeoIPAligner,
  SessionStateVault (atomic writes), DOMToMarkdownSimplifier, QualitySentinel,
  PassiveOSFingerprintTuner, StrictContextManager (WebRTC masking honestly
  absent), SelectorHealMemory + SelfHealingSelectorEngine.
- **Data plane** (browser-independent): EDGARPiTAligner, MarketSyntheticGenerator,
  CapitalMarketEntityResolver, QuantDataContractSentinel, QuantPersistencePipeline,
  FridaNativeHookEngine, MitmproxyStreamInterceptor, WebSocketDataflowStreamer,
  BlockchainLakehouseStreamingPipeline, IXBRLSECParser, EDGARBalanceSheetParser,
  SECForm4InsiderTracker, BinaryOLE2REDecoder, PyarmorCPythonUnpacker,
  PITQuantEngine (+ parse_pit_timestamp, _stable_composite_figi).
- **Orchestration**: ElementResolutionError + `BehavioralPlaywright` facade
  (`run` / `solve` / `collect` / `close` / `attach_browser`).

Ownership is clear; no circular imports (one module); pydantic is the only
module-level third-party dependency (AST-enforced by tests).

## 4. Capability Matrix

| Capability | Gen1 (v10 Quantum) | Gen2 (BP facade) | Current (v15) | Status | Tests |
|---|---|---|---|---|---|
| Self-healing selector cascade | Levenshtein healer w/ canned fallbacks | L1→L2→L3 real resolver | MEMORY→PRIMARY→L1→L2→L3→L4, threshold-gated every tier | **PRESERVED+IMPROVED** (fake paths removed; persistent heal memory added) | 27+10 ✅ |
| Heal memory persistence | — | — | SelectorHealMemory: atomic JSON, corrupt quarantine `.corrupt`, bounded eviction | **NEW** | ✅ |
| Confidence gating | decorative constants | fixed per-tier | enforced ∈[0,1] on EVERY tier incl. MEMORY (audit fix A1) | **PRESERVED+HARDENED** | ✅ |
| Humanized interaction (mouse/typing math) | REAL math_engine + humanizer | absent (sentinel object) | BiomechanicalInteractionEngine (WindMouse + inertial scroll) | typing dynamics **REMOVED**, mouse/scroll PRESERVED | partial |
| Stealth JS injection (toString/WebGL/platform) | providers init script | absent | CDPEvasionShield + HardwareOSSpoofer | PRESERVED (real injection) | smoke via run() |
| Geo/locale alignment | — | — | DynamicUSGeoIPAligner | PRESERVED | ✅ |
| Session persistence | — | handoff/storage_state | SessionStateVault (anti-data-loss atomic) | PRESERVED+HARDENED | ✅ |
| Circuit breaker / retry / Markov loop detection | REAL | REAL | **REMOVED** (not carried into v15) | **LOST** (rotator lock partially covers lifecycle) | — |
| Crawling (BFS crawler, sitemap, robots) | — | real but broken (1-page bug) | **REMOVED** | **LOST** (was broken anyway) | — |
| Search engine / site mapping / extraction targets | — | real (mapper external-count bug) | DOMToMarkdownSimplifier covers extraction niche | **LOST/TRANSFORMED** | ✅ (markdown) |
| OCR / vision detection | provider-dependent + fake fallbacks | honest pytesseract wrapper | **REMOVED** | **LOST** | — |
| LLM integration | PROVIDER-DEPENDENT + fabricated offline mocks | removed | **REMOVED** (fabrication never re-added) | **LOST by design** | — |
| Webhooks/MCP/n8n integrations | — | real webhooks; MCP broken | **REMOVED** | **LOST** | — |
| SQLite observability/metrics/queue | — | real | **REMOVED** | **LOST** | — |
| Network latency probe / TLS spoofing | JA4 theater (decorative) | HEAD probes only | TLSJA4Spoofer via curl_cffi, loud RuntimeError without it | **PRESERVED as honest stub** | absence-path ✅ |
| Native hooks (frida) | — | — | FridaNativeHookEngine, reports unavailability, fabricates nothing | PRESERVED (honest) | absence-path ✅ |
| PiT quant engine (no look-ahead) | — | — | PITQuantEngine whole-row selection, deterministic composite_figi | **CURRENT OWNERSHIP** | ✅ |
| Entity resolution | — | — | curated registry, token-boundary match, raises on unknown | CURRENT (fabricated ISINs removed in Ph2) | ✅ |
| Data contract sentinel / NDJSON pipeline | — | — | schema/null-ratio/throughput gates | CURRENT | ✅ |
| ITCH LOB / dollar bars | — | — | real reconstruction incl. zero-share removal fix | CURRENT | ✅ |
| iXBRL / balance sheet / Form 4 parsers | — | — | header detection real; narrative/XML parsing quarantined (NotImplementedError) | EXPERIMENTAL/QUARANTINED | ✅ |
| OLE2 decode / Pyarmor unpack / protobuf decode | — | — | honest UNAVAILABLE_NOT_IMPLEMENTED / raw retention | QUARANTINED (honest) | ✅ |
| WebRTC IP masking | fake SDP shim | — | intentionally absent (documented) | REMOVED by design (was fake) | n/a |
| Microtask timing patch | global Promise wrap | — | default OFF quarantine, opt-in | PRESERVED as opt-in experimental | ✅ |

## 5. Lost-Capability Detail (deleted in `6f71863`, not restored)

Per instructions nothing was auto-restored. Gaps identified:

1. **Resilience primitives** (circuit breaker, retry policy, Markov loop
   detector) — genuinely real in Gen2, gone now. The v15 module has no retry
   anywhere; transient page failures propagate raw.
2. **Crawling/search/mapping** — real-but-buggy in Gen2; deleted rather than
   fixed. The 1-page-crawl bug and mapper metadata bug died with them.
3. **OCR/vision** — honest pytesseract/cv2 wrappers lost.
4. **Integrations & observability** — real webhook POSTing, SQLite metrics,
   WAL task queue lost (MCP path was broken anyway).
5. **Typing humanization** (keystroke gauss delays, typo simulation) — the
   mouse has WindMouse; typing has nothing.

## 6. Self-Healing Audit (deep)

Verified semantics (all source-read, then test-pinned):

- Cascade order: S1 MEMORY fast-path → PRIMARY (1.0) → L1 normalized
  Levenshtein (distance ≤ 5, similarity ≥ threshold) → L2 aria/title (0.90) →
  L3 spatial geometry + text (0.85) → L4 first-button (0.25, deliberately
  unreachable at default 0.80).
- Threshold validated in constructor; enforced on L2/L3/L4 explicitly.
- Heal memory: remember/lookup/forget/stats; capacity-bounded lowest-confidence
  eviction; atomic save (tmp + os.replace); missing file = silent no-op;
  corrupted file quarantined as `<path>.corrupt`; invalid entries skipped.
- Stale memory (S2): wait_for_selector failure falls through to full cascade;
  PRIMARY success refreshes the entry.
- Facade integration: `heal_memory_path=` param; solve uses + fills memory;
  close() persists; end-to-end disk round-trip across instances tested.
- Failure honesty: below-threshold ⇒ ElementResolutionError; never a guess.

**Defects found & FIXED in this audit (regression-tested in
`tests/test_audit_regressions.py`):**

| ID | Severity | Defect | Fix |
|----|----------|--------|-----|
| A1 | HIGH | MEMORY tier bypassed `confidence_threshold`: a remembered entry loaded from a legacy/hand-edited file with low confidence was returned unconditionally, violating the documented "enforced on every tier" contract | Memory hits below threshold now fall through to the cascade (S2-style); boundary `== threshold` stays accepted; facade-level test proves solve() raises instead of returning the weak hit |
| A2 | MEDIUM | MEMORY fast-path ignored `expected_content`: if the page changed such that the old selector resolves a *different* element, the wrong element was trusted | When expected content is supplied and the element text lacks it, entry treated as stale → full cascade recovers (test shows L2 recovery). Unverifiable handles keep the hit rather than inventing failure |
| A3 | LOW | `event_time=0.0` discarded by truthiness check in `ingest_market_record`; epoch 0 silently replaced by an invented jittered timestamp | `is not None` check; regression tests pin exact 0.0 persistence through pipeline and facade |

Remaining documented limitations (NOT hidden, NOT faked): only PRIMARY-tier
resolutions are written back automatically (lower tiers return raw handles —
stable-selector extraction pending); MEMORY-hit refresh does not bump the
entry's timestamp.

## 7. UX Audit

`BehavioralPlaywright` achieves "minimal user code" for its three verbs
(run/solve/collect ≈ 3–5 lines per workflow) without being a god object:
five components wired, power-user escape hatches preserved
(`bp.heal_memory/selector_engine/pipeline/sentinel/context_rotator`).

Code-reduction opportunities identified (NOT implemented — need direction):
1. `solve`+`click`: solve returns a handle; callers still write click code.
   A `solve_and_perform` verb would remove boilerplate but starts duplicating
   Gen2's action namespace — keep out until needed.
2. No batch API for collect (loop required). Low value; sentinel semantics get
   murky for batches.
3. Historical BP facade had 15 verbs; current 3-verb design is deliberately
   narrower and healthier. Do not grow back toward the Gen2 god-facade.

## 8. Real-Implementation Classification (current module)

- **REAL**: logging sanitizer, CDP shield JS, hardware spoof JS, geo aligner,
  biomechanical trajectories/scroll, rotator, vault, markdown simplifier,
  quality sentinel, self-healing stack, VM AST deobfuscator (regex-based,
  honest failures), WASM hook injection, both persistence pipelines, entity
  resolver, contract sentinel, ITCH LOB, EDGAR aligner, synthetic generator,
  websocket sentiment, blockchain z-score pipeline, PIT engine.
- **PROVIDER-DEPENDENT**: TLSJA4Spoofer (curl_cffi), FridaNativeHookEngine
  (frida + device), live Playwright behavior (fakes in tests).
- **EXPERIMENTAL**: MicrotaskTimingAligner (opt-in), WasmMemoryInterceptor,
  VMASTDeobfuscator scope, L4 tier below 0.25.
- **UNAVAILABLE (honest)**: BinaryOLE2REDecoder payload, PyarmorCPythonUnpacker,
  iXBRL narratives, balance-sheet DataFrame, Form4 XML parsing, mitmproxy
  protobuf/gRPC decode, WebRTC masking.
- **Flagged, left unchanged (documented simulator defaults)**:
  `BlockchainLakehouseStreamingPipeline` generates a random 64-hex `tx_hash`
  when input omits it — pinned by existing test as simulator output format;
  `ingest_market_record` invents event_time = now−jitter when None (bounded,
  documented, knowledge_timestamp stays authoritative). Both are simulator
  conveniences inside clearly-labeled simulation classes, not fake-success
  paths; changing them would alter pinned public behavior without user
  direction.

## 9. Problems Found (summary)

- CRITICAL: none open (Gen1/Gen2 theater never carried into v15).
- HIGH: A1 memory-tier gate bypass (fixed).
- MEDIUM: A2 memory content verification gap (fixed); Gen2 latent bugs
  (crawl/mapper/MCP/boot) — died with the deleted tree, recorded here so they
  are not reintroduced.
- LOW: A3 falsy epoch trap (fixed); L3 rejection logs per-element (noise);
  MEMORY-hit doesn't refresh timestamp.
- DOC: checkpoint §1 claims "NOT A GIT REPO" — stale (repo exists since the
  baseline commit); README phase table says 199 tests (now 209).

## 10. Fixes Made

| File | Change |
|------|--------|
| `behavioral_evasion_ten_patches_hardened_v15.py` | A1: MEMORY-tier threshold gate + fall-through; A2: expected_content verification on memory hits; A3: `event_time is not None`; docstrings updated |
| `tests/test_audit_regressions.py` | NEW: 10 regression tests covering A1 (4), A2 (3), A3 (3) |
| `docs/development/full-codebase-audit.md` | this document |

Suite: **209 passed / 0 failed / 0 skipped / 0 errors** (was 199 before audit).

## 11. Remaining Work (prioritized)

1. Lower-tier heal write-back: extract stable selectors from L1–L3 handles
   (unlocks full memory utility; documented limitation today).
2. Reintroduce resilience primitives (retry/backoff) from Gen2 — they were
   real and are genuinely missing.
3. Wheel-build verification once setuptools/wheel available in env.
4. Decide fate of simulator-default identifiers (tx_hash) — make visibly
   synthetic or require caller-supplied IDs.
5. Quarantined capabilities (iXBRL narrative, balance sheet, Form4 XML,
   protobuf decode, OLE2) — real implementations or keep honest stubs.
6. CI workflow (none exists for the v15 tree; Gen1 had one).
7. Update README/checkpoint counts (199→209) and checkpoint §1 VCS claim.

## 12. Git

- Working tree changes: 1 modified (module), 2 new files (regression suite,
  this doc). Nothing staged/committed unless explicitly requested.
- Local commits: none created during audit.
- Remote: untouched. No push, no force-push, no merge, no PR, no branch
  changes. Remote main remains `cc6da38`.

REMOTE MODIFIED: NO
PUSH PERFORMED: NO
