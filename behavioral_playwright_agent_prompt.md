# AI Coding Agent Master Prompt — `sadik004/behavioral-playwright` (90-Bug Zero-Regression Remediation)

 নিচে দুটি রেডি-টু-ইউএস (Copy-Pasteable) প্রম্পট দেওয়া হলো। আপনি যেকোনো AI Coding Agent (যেমন: **Claude Code**, **Cursor Agent**, **Windsurf**, **Cline**, অথবা **GitHub Copilot Workspace**)-কে সরাসরি কপি-পেস্ট করে দিতে পারেন।

* **Prompt 1 (Standalone Full-Context Prompt):** এজেন্টের কাছে যদি কোনো বাইরের স্ক্রিপ্ট না থাকে, তবে এই প্রম্পটটি দিন—এতে ৯০টি বাগের প্রতিটি রুট কজ, ফাইল-বাই-ফাইল সমাধান এবং ভেরিফিকেশন কমান্ড দেওয়া আছে।
* **Prompt 2 (Fast-Track Script Prompt):** আপনি যদি রিপোজিটরির রুটে `fix_all_behavioral_playwright_bugs.py` ফাইলটি রাখেন, তবে এই ছোট প্রম্পটটি দিলেই এজেন্ট এক কমান্ডে সব ফিক্স ও ভেরিফাই করে ফেলবে।

---

## Prompt 1: Standalone Master Prompt (Copy & Paste to Coding Agent)

```markdown
You are an autonomous Principal Python & Browser-Automation Systems Engineer tasked with executing a complete, zero-regression remediation of all 90 bugs across the `sadik004/behavioral-playwright` repository (`veil` v6.0.0 / `behavioral_playwright` / `behavioral_evasion_suite`).

### 1. HARD CONSTRAINTS & ANTI-GAMING RULES
1. **Respect `LOCK.json`**: Before modifying any file, read `LOCK.json` at the repository root (if present) and NEVER modify or overwrite any file listed in `LOCK.json`.
2. **Zero Syntax Errors**: Every `.py` file in `src/`, `behavioral_evasion_suite/`, `providers/`, `scripts/`, `tests/`, and the root directory must pass `ast.parse()` cleanly.
3. **No Mock-Only Shortcuts or Hardcoded Test Return Values**: All fixes must pass `scripts/ast_anti_gaming.py` and `scripts/audit_architecture.py` (100% score, 0 violations). Never use bare `pass`, `...`, `TODO`, `FIXME`, or `NotImplementedError` in production modules.
4. **Dual-Namespace Parity**: Keep `src/veil/` and `src/behavioral_playwright/` 100% synchronized so imports from either namespace behave identically.

---

### 2. COMPLETE FILE-BY-FILE REMEDIATION SPECIFICATION (ALL 90 BUGS)

#### A. Critical Syntax & Core Facade (`src/veil/facade.py` — Bugs #1–#16)
- **Bug #1 (Line 665 SyntaxError)**: Fix the broken `import re as _re` statement that was concatenated onto the end of a regex raw string (`r"..."import re as _re`). Move `import re as _re` onto its own properly indented line.
- **Bugs #2–#4 (`Veil.crawl`, `Veil.map`, `Veil.search`)**:
  - Ensure `Veil.crawl(url, max_pages=..., max_depth=...)` normalizes URLs, discovers child `<a href="...">` links across pages up to `max_pages`/`max_depth`, and returns a consistent dictionary/object containing `pages` (list of page dicts with `url`, `markdown`, `html`, `title`, `links`, `status_code`), `visited_urls`, and `total_pages`.
  - Ensure `Veil.map(url)` extracts and normalizes all unique in-domain and discovered links into a deduplicated list of absolute URLs.
  - Ensure `Veil.search(query, ...)` works deterministically offline/online and returns structured search results without raising unhandled network exceptions when offline.
- **Bugs #5–#8 (`ObservabilityNamespace._ensure_legacy_db`)**:
  - Fix SQLite connection leaks in `ObservabilityNamespace._ensure_legacy_db` and metrics logging by using `contextlib.closing(sqlite3.connect(...))` and `with conn:` blocks so file descriptors are never leaked.
- **Bugs #9–#12 (`AINamespace.extract` & `SchemaNamespace`)**:
  - Provide a deterministic heuristic/DOM fallback in `AINamespace.extract(html_or_url, schema=...)` when no external LLM API key is configured or when offline, extracting fields matching the requested Pydantic/dict schema (`title`, `price`, `items`, `links`, `headings`, `summary`).
- **Bugs #13–#16 (`AuditNamespace` & `SecurityNamespace`)**:
  - Wire `Veil.audit.security(url_or_html, ...)` and `Veil.security.audit_graphql(...)` / `audit_web_security(...)` so they return normalized reports containing `vulnerabilities`, `findings`, `risk_score`, `passed`, and `recommendations`.

#### B. CLI Entrypoint (`src/veil/cli/main.py` — Bugs #17–#22)
- **Bug #17**: Define and export `_rec_to_dict(rec)` at module level in `src/veil/cli/main.py` (handling dataclasses, Pydantic models via `model_dump()`/`dict()`, dicts, and general objects via `__dict__`) so CLI JSON serialization and unit tests importing `_rec_to_dict` never raise `NameError` or `ImportError`.
- **Bugs #18–#22**: Ensure `build_parser()`, `run_doctor()`, `run_audit()`, `run_crawl()`, and `main(argv)` handle all subcommands (`crawl`, `map`, `extract`, `audit`, `doctor`, `mcp`) cleanly and return integer exit codes (`0` on success).

#### C. DOM Extraction, Price Normalizer, Auto-Schema & RAG (`src/veil/extraction/` — Bugs #23–#34)
- **`src/veil/extraction/dom.py` (Bugs #23–#27)**:
  - Make `DOMExtractor.extract_links`, `extract_tables`, `extract_hydration_state`, `extract_by_selectors`, and `extract_structured` callable both as `@staticmethod` / `@classmethod` and on instances.
  - Support nested selector specs in `extract_by_selectors(html, selectors)` (e.g., `{"title": "h1", "meta": {"author": ".author"}}` or list specs) without raising `TypeError: unhashable type: 'dict'`.
  - Gracefully handle malformed JSON inside `<script id="__NEXT_DATA__">` in `extract_hydration_state(html)` by returning `{}` (or partial recovered state) instead of crashing with `json.JSONDecodeError`.
- **`src/veil/extraction/normalizer.py` (Bugs #28–#30)**:
  - In `PriceDecimal` (or currency normalizer return type), implement `__eq__`, `__float__`, and comparison operators so `PriceDecimal("1299.99") == Decimal("1299.99")`, `PriceDecimal("1299.99") == 1299.99`, and `PriceDecimal("1299.99") == "1299.99"` all evaluate to `True`.
- **`src/veil/extraction/auto_schema.py`, `markdown.py`, `quarantine.py`, `rag_chunker_exporter.py` (Bugs #31–#34)**:
  - Ensure `AutoSchemaExtractor` infers repeating item lists and key-value pairs accurately, `MarkdownConverter` preserves headings/tables/links cleanly, `PromptInjectionQuarantine` sanitizes hidden prompt-injection payloads while preserving legitimate content, and `RAGChunkerExporter` chunks documents with accurate token/character overlap and metadata.

#### D. Crawling Engine, Checkpoints, Recovery & Proxy Rotation (`src/veil/crawling/` & `src/veil/resilience/` — Bugs #35–#48)
- **`src/veil/crawling/checkpoint.py` & `src/veil/resilience/recovery.py` (Bugs #35–#40)**:
  - Unify the SQLite schema for `crawl_checkpoints` across both `CrawlCheckpointStore` (`checkpoint.py`) and `recover_crawl_session` (`recovery.py`).
  - Fix `fail_task(task_id, error=...)` so it increments `attempt = attempt + 1` in SQLite, re-queues tasks (`status = 'pending'`) when `attempt < max_retries`, and marks them `'failed'` (or `'dead_letter'`) once `attempt >= max_retries`.
  - Use `BEGIN IMMEDIATE` transactions in `pop_task()` so concurrent workers never pop the same URL task twice.
  - Always close SQLite connections in `CrawlCheckpointStore` and `recover_crawl_session()` using context managers.
- **`src/veil/crawling/service.py`, `crawler.py`, `firecrawl.py` (Bugs #41–#45)**:
  - Fix `CrawlingService.escalate_and_fetch(url, ...)` so it returns actual fetched/rendered HTML content (and status metadata) rather than a placeholder string.
  - Ensure `FirecrawlBlueprint.crawl(url, max_pages=...)` and `Crawler.crawl(...)` follow discovered links and populate `pages` and `links`.
- **`src/veil/crawling/bandit_proxy_rotator.py` & `src/veil/proxy/pool.py` (Bugs #46–#48)**:
  - Synchronize `ProxyPool` and `BanditProxyRotator` method signatures (`select_proxy`, `report_success`, `report_failure`, `get_proxy`, `record_outcome`) so Thompson Sampling / UCB1 proxy selection works seamlessly with both URL strings and `ProxyEntry` objects.

#### E. Kinematics, Keystrokes, Gaze Physics & NLP Intent Parser (`src/veil/kinematics/` & `behavioral_evasion_suite/` — Bugs #49–#68)
- **`src/veil/kinematics/tracking.py`, `validator.py`, `schema_guard.py` (Bugs #49–#55)**:
  - Ensure trajectory points support both attribute access (`pt.x`, `pt.y`, `pt.t`) and tuple/dict unpacking (`x, y = pt[:2]`) via a `MousePoint` object, with deterministic seeded generation when `seed` is provided and realistic Fitts's Law sub-movement overshoot and bell-shaped velocity profiles (`KinematicsValidator.validate_trajectory`).
- **`behavioral_evasion_suite/keystroke_engine.py` (Bugs #56–#61)**:
  - Fix `_char_to_keycode(ch)` so uppercase/lowercase letters map to their standard DOM virtual `keyCode` (`ord(ch.upper())` for `'a'`–`'z'`), digits map to `48`–`57`, space to `32`, Enter to `13`, Backspace to `8`, Tab to `9`, and punctuation to standard US-QWERTY virtual key codes (`;` -> `186`, `=` -> `187`, `,` -> `188`, `-` -> `189`, `.` -> `190`, `/` -> `191`, `` ` `` -> `192`, `[` -> `219`, `\` -> `220`, `]` -> `221`, `'` -> `222`).
  - Scale inter-key flight and dwell times inversely with `wpm` so higher WPM (`120 WPM`) is deterministically faster than lower WPM (`40 WPM`), while respecting `typo_rate=0.0` (emitting exact characters with zero backspaces) and `typo_rate>0` (emitting realistic neighbor-key typos followed by `Backspace` recovery).
- **`behavioral_evasion_suite/nlp_intent_parser.py` & `nlp_executor.py` (Bugs #62–#65)**:
  - Fix multi-clause command splitting in `NLPIntentParser.parse(prompt)` so compound instructions separated by `, then`, `and then`, `;`, or `and <action_verb>` (e.g., `"Go to https://example.com and click #login and type 'admin' into #user and wait 500ms"`) split into distinct sequential steps (`navigate`, `click`, `type`, `wait`).
  - Fix duration unit parsing in wait clauses so `"500ms"` or `"500 milliseconds"` parses as `500.0` ms (`0.5` seconds) whereas `"2s"` or `"2 seconds"` parses as `2000.0` ms (`2.0` seconds) — never multiplying millisecond values by `1000`.
- **`behavioral_evasion_suite/cognitive_gaze_physics.py`, `circuit_breaker.py`, `satellite_field_verifier.py`, `stealth_session.py`, `worker_universal_shield.py` (Bugs #66–#68)**:
  - Ensure gaze saccades/fixations, circuit breaker state transitions (`CLOSED` -> `OPEN` -> `HALF_OPEN` -> `CLOSED`), satellite field verification, stealth session lifecycle, and worker universal shield script injection all operate without runtime errors.

#### F. MCP Server & All 34 MCP Tools (`src/veil/mcp/tools.py` & `mcp_server.py` — Bugs #69–#80)
- Implement real, functional dispatch for all 34 registered MCP tools in `src/veil/mcp/tools.py` and `mcp_server.py` (including `navigate_stealth`, `click_human`, `type_human`, `scroll_human`, `extract_dom`, `extract_structured_data`, `extract_markdown`, `extract_tables`, `extract_links`, `extract_hydration`, `quarantine_prompt_injection`, `export_rag_chunks`, `crawl_domain`, `map_domain`, `solve_captcha`, `bypass_cloudflare`, `rotate_identity`, `generate_fingerprint`, `handoff_session`, `audit_graphql`, `audit_web_security`, `audit_aio_visibility`, `mine_paa`, `mine_autocomplete`, `detect_rendering_drift`, `detect_cannibalization`, `parse_itch_stream`, `compute_orderbook_imbalance`, `verify_rendering`, `ocr_document`, `get_Stealth_metrics`, `reset_circuit_breaker`, `execute_nlp_intent`, `run_blueprint`).
- Ensure every MCP tool returns a JSON-serializable `dict` with `status: "ok"` (or tool-specific structured payload) and never raises `NotImplementedError` or `KeyError`.

#### G. Security Auditors, Mining, Quant ITCH & Providers (`src/veil/security/`, `src/veil/mining/`, `src/veil/core/`, `src/veil/providers/`, `providers/` — Bugs #81–#90)
- **`src/veil/security/graphql_auditor.py`, `web_security_auditor.py`, `behavioral_evasion_suite/unified_security_auditor_v5.py` (Bugs #81–#84)**:
  - Ensure GraphQL depth/introspection/batching checks and web security header/CORS/CSP/cookie checks return complete structured audit results and work both offline (analyzing provided HTML/headers/schema) and online.
- **`src/veil/mining/aio_auditor.py`, `paa_miner.py`, `rendering_drift.py` (Bugs #85–#87)**:
  - Ensure `AIOAuditor`, `PAAMiner`, and `RenderingDriftDetector` compute deterministic scores and structured diffs without division-by-zero on empty inputs.
- **`src/veil/core/quant_engine.py`, `itch_binary.py`, `src/veil/providers/`, `providers/` (Bugs #88–#90)**:
  - Guard `QuantEngine` orderbook imbalance, VWAP, and micro-price calculations against zero-volume books, and keep `providers/` at the repo root synchronized with `src/veil/providers/`.

---

### 3. MANDATORY VERIFICATION PROTOCOL
After applying all fixes, run the following commands in order and do not stop until every single command exits with code `0`:

```bash
# 1. Verify zero syntax errors across the entire repository
python3 -c '
import ast, pathlib
for p in pathlib.Path(".").rglob("*.py"):
    ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
print("AST syntax check passed for all Python files!")
'

# 2. Run architectural & AST anti-gaming audits
PYTHONPATH=src:. python3 scripts/audit_architecture.py
PYTHONPATH=src:. python3 scripts/ast_anti_gaming.py

# 3. Run the real feature verification script
PYTHONPATH=src:. python3 scripts/verify_all_features_real.py

# 4. Run the full pytest suite (including the 90-bug master regression suite)
PYTHONPATH=src:. pytest -q
```
```

---

## Prompt 2: Fast-Track Auto-Patcher Prompt (If Using `fix_all_behavioral_playwright_bugs.py`)

আপনি যদি আমাদের তৈরি করা `fix_all_behavioral_playwright_bugs.py` ফাইলটি আপনার প্রজেক্টের রুট ফোল্ডারে রাখেন, তাহলে এজেন্টকে শুধু নিচের প্রম্পটটি দিন:

```markdown
I have placed `fix_all_behavioral_playwright_bugs.py` in the root of this repository (`sadik004/behavioral-playwright`).

Please execute the following steps:
1. Run `python3 fix_all_behavioral_playwright_bugs.py --repo-root . --apply --verify` to remediate all 90 bugs across the codebase while respecting `LOCK.json`.
2. Run the full verification & anti-gaming test suites to confirm 100% pass rate and zero regressions:
   - `PYTHONPATH=src:. python3 scripts/audit_architecture.py`
   - `PYTHONPATH=src:. python3 scripts/ast_anti_gaming.py`
   - `PYTHONPATH=src:. python3 scripts/verify_all_features_real.py`
   - `PYTHONPATH=src:. pytest -q`
3. Show me the `git status` and a summary of the test results. Do not delete `LOCK.json`.
```
