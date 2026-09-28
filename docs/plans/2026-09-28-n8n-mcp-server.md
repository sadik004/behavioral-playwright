# n8n MCP Server Implementation Plan (Masterpiece 26-Tool Edition)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-grade, standalone n8n Model Context Protocol (MCP) Server (`n8n.mcp`) with 100% clean 3-tier architecture, Pydantic v2 DTOs, 26 high-performance tools, payload sanitization (avoiding HTTP 400 read-only rejection), diff-based partial node patching (85-90% token savings), 1-click snapshot rollback, anti-hallucination node discovery & schema inspection, LangChain AI agent cluster validation, pin-data testing, autonomous self-healing execution loops, template discovery, and behavioral-playwright stealth scraping integration.

**Architecture:** 3-tier clean architecture separating JSON-RPC 2.0 stdio MCP routing (`server.py`, `tools/registry.py`), domain intelligence & optimization engines (`engine/patcher.py`, `engine/snapshots.py`, `engine/node_catalog.py`, `engine/validator.py`, `engine/diagnostics.py`, `engine/healer.py`, `engine/stealth_bridge.py`, `engine/pindata.py`), and a resilient async REST client with connection pooling, payload sanitization, and AWS full-jitter exponential backoff (`engine/client.py`).

**Tech Stack:** Python 3.10+, Pydantic v2, Pydantic-Settings, httpx, pytest, pytest-asyncio, Rich, behavioral-playwright.

---

## ⚠️ 8 Critical Architectural Invariants & Caveats (Strictly Enforced)

1. **PUT `/api/v1/workflows/{id}` Read-Only Rejection (HTTP 400 Trap)**:
   - n8n `GET /api/v1/workflows/{id}` returns read-only metadata (`id`, `versionId`, `createdAt`, `updatedAt`, `triggerCount`, `tags`, `active`).
   - Resending these in `PUT` triggers `400 Bad Request: Malformed data`.
   - `N8nClient.sanitize_workflow_payload()` MUST whitelist ONLY mutable root fields: `name`, `nodes`, `connections`, `settings`, and optionally `staticData` / `pinData`.

2. **Read-Modify-Write Pattern for `n8n_patch_node`**:
   - n8n REST API v1 lacks native `PATCH /api/v1/workflows/{id}/node`.
   - `WorkflowPatcher` MUST execute: `GET /api/v1/workflows/{id}` -> deep-merge/patch targeted node parameters in-memory -> `sanitize_workflow_payload()` -> `PUT /api/v1/workflows/{id}`.
   - LLMs send only 20-30 token diffs, achieving 85-90% token savings without graph re-emission.

3. **1-Click Local Snapshot & Rollback Safety**:
   - Before any `patch_node` or `update_workflow`, `SnapshotManager` saves the current state to in-memory history and `.snapshots/{workflow_id}_{timestamp}.json`.
   - `n8n_rollback_workflow` restores the previous snapshot instantly if an AI refactor breaks the graph.

4. **Anti-Hallucination Node Discovery & Schema Contract**:
   - LLMs frequently hallucinate parameter names (e.g. `channel` vs `channelId`, `operation: append` vs `operation: create`).
   - `n8n_search_nodes` and `n8n_get_node_schema` provide exact node schemas and property enums from a curated offline catalog of top 100+ n8n nodes.

5. **Strict `pinData` Schema & Node Name Keying**:
   - In n8n, `pinData` is keyed by **Node Name** (human-readable string), NOT by node `id` or `type`.
   - Payload structure MUST strictly conform to: `{"pinData": { "<Node Name>": [ { "json": { ... } } ] }}`.
   - `PinDataManager` automatically wraps raw dicts into `{"json": item}` and validates against the workflow node names.

6. **Docker Networking & Host URL Resolution for Stealth Scraper**:
   - If n8n runs inside Docker and `behavioral-playwright` runs on the host machine, `localhost:8000` fails with Connection Refused.
   - `StealthScraperBridge` and `config.py` default to `http://host.docker.internal:8000` (configurable via `BEHAVIORAL_PLAYWRIGHT_URL`).

7. **Multi-Port DAG Traversal (`main` vs `ai_*` LangChain Ports)**:
   - Standard nodes connect via `connections[sourceNode].main`.
   - LangChain AI Agent nodes connect via specialized ports: `ai_languageModel`, `ai_tool`, `ai_memory`, `ai_outputParser`, `ai_embedding`.
   - `WorkflowValidator` graph traversers (cycle detection, dangling node audits) MUST traverse both `main` and all `ai_*` connection keys.

8. **Draft Safety & Activation Safeguards**:
   - Workflows can be updated in draft state (`publishIfActive: false`) to avoid crashing live production traffic before pin-data testing passes.

9. **Official MCP Python SDK (`mcp>=1.2.0` / FastMCP)**:
   - Use official `mcp.server.fastmcp.FastMCP` and `mcp.server.stdio` instead of fragile raw stdio loops. Guarantees 100% protocol compliance, seamless Windows stdio buffering, and flawless Claude Desktop / Cursor framing.

10. **Webhook Test vs Production Pathing (`is_test: bool = True`)**:
    - Support `/webhook-test/{path}` (for inactive/testing workflow canvas) and `/webhook/{path}` (for active production workflows) via `is_test: bool = True`.

11. **Zero-Latency Bundled Catalog (`data/nodes_catalog.json`)**:
    - Pre-bundle top 100+ n8n node schemas in `data/nodes_catalog.json` for 0ms offline instant schema inspection without runtime network scraping.

12. **Code Node In-Memory Syntax Validation (`ast.parse`)**:
    - `WorkflowValidator` lints `n8n-nodes-base.code` nodes before saving: Python code is verified via `ast.parse()` and JavaScript code via bracket/syntax matching to prevent syntax crashes.

---

## 🛠️ Complete 26 Production MCP Tools Catalog

| # | Tool Name | Category | Description & Value Proposition |
| :--- | :--- | :--- | :--- |
| 1 | `n8n_list_workflows` | Workflows | List workflows with pagination, active filter, tags, and search query. |
| 2 | `n8n_get_workflow` | Workflows | Retrieve full workflow JSON definition (nodes, connections, settings, pinData). |
| 3 | `n8n_create_workflow` | Workflows | Create a new workflow from structured nodes/connections specification. |
| 4 | `n8n_update_workflow` | Workflows | Replace full workflow definition with sanitized payload. |
| 5 | `n8n_patch_node` | Workflows | **Diff-based partial node updater**: patches specific node parameters in-memory; **85-90% token savings** with auto-snapshot. |
| 6 | `n8n_rollback_workflow` | Safety | **1-click rollback**: restores the previous workflow snapshot if a patch or refactor causes issues. |
| 7 | `n8n_activate_workflow` | Workflows | Toggles workflow active state (`active: true / false`). |
| 8 | `n8n_delete_workflow` | Workflows | Permanently deletes a workflow by ID. |
| 9 | `n8n_search_nodes` | Discovery | **Anti-hallucination discovery**: search n8n node types, descriptions, and categories. |
| 10 | `n8n_get_node_schema` | Discovery | **Parameter contract inspector**: returns exact properties, enums, and operations for any n8n node. |
| 11 | `n8n_validate_workflow` | Validation | DAG cycle detection, dangling nodes check, and n8n expression syntax (`{{ $json... }}`) linter. |
| 12 | `n8n_validate_ai_agent_graph` | Validation | **LangChain AI Agent Validation**: enforces required `ai_languageModel`, `ai_tool`, and `ai_memory` sub-node ports. |
| 13 | `n8n_set_pinned_data` | Testing | **Safe Sandbox Testing**: injects mock test data into trigger nodes (`pinData: { "NodeName": [{"json": ...}] }`). |
| 14 | `n8n_clear_pinned_data` | Testing | Clears pinned data from specific or all nodes before pushing to live production. |
| 15 | `n8n_list_executions` | Executions | Queries execution history with filters (workflowId, status: `success`, `error`, `waiting`). |
| 16 | `n8n_get_execution` | Executions | Inspects full execution data, node-by-node runtime, and I/O records. |
| 17 | `n8n_audit_errors` | Executions | Diagnoses failed executions and generates structured Root Cause Analysis (RCA). |
| 18 | `n8n_retry_execution` | Executions | Retries a failed workflow execution by ID. |
| 19 | `n8n_delete_execution` | Executions | Removes execution records from history. |
| 20 | `n8n_auto_heal_execution` | Self-Healing | **Autonomous self-healing loop**: Inspects failure -> diagnoses RCA -> patches node -> retries execution -> verifies (max 2 attempts). |
| 21 | `n8n_search_templates` | Templates | Searches n8n's 2000+ verified official & community template library by keyword or category. |
| 22 | `n8n_get_template` | Templates | Downloads full workflow template JSON ready for deployment. |
| 23 | `n8n_create_stealth_scraper_node` | Anti-Bot | **behavioral-playwright bridge**: generates pre-configured node to bypass Cloudflare/Turnstile and scrape protected sites. |
| 24 | `n8n_trigger_webhook` | Triggers | Executes test or production webhooks with custom payload, method, and query params. |
| 25 | `n8n_health_check` | System | Checks n8n instance version, public API reachability, and response latency. |
| 26 | `n8n_list_credentials` | System | Lists available credential IDs and types with sensitive secrets masked. |

---

## 🗓️ 10-Task Implementation Roadmap (Strict TDD Methodology)

### Task 1: Scaffolding, Packaging & Configuration Architecture
**Files:**
- Create: `e:/Bug/n8n.mcp/pyproject.toml`
- Create: `e:/Bug/n8n.mcp/requirements.txt`
- Create: `e:/Bug/n8n.mcp/.env.example`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/__init__.py`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/config.py`
- Test: `e:/Bug/n8n.mcp/tests/unit/test_config.py`

**Step 1: Write failing test (`test_config.py`)**:
Test default configuration, environment variable overrides (`N8N_HOST`, `N8N_API_KEY`, `N8N_TIMEOUT_SECONDS`, `N8N_MAX_RETRIES`, `BEHAVIORAL_PLAYWRIGHT_URL`), URL normalization (stripping trailing slashes), and snapshot directory configuration.

**Step 2: Run test to verify it fails**:
Run: `pytest n8n.mcp/tests/unit/test_config.py -v` (Expected: FAIL).

**Step 3: Implement minimal code**:
Implement `config.py` using `pydantic_settings.BaseSettings`.

**Step 4: Verify test passes**:
Run: `pytest n8n.mcp/tests/unit/test_config.py -v` (Expected: PASS).

**Step 5: Git commit**:
`git -C e:/Bug/n8n.mcp commit -m "feat(n8n-mcp): scaffold project and configuration layer"`

---

### Task 2: Pydantic v2 Models & DTOs
**Files:**
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/models/__init__.py`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/models/workflow.py`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/models/execution.py`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/models/node.py`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/models/diagnostics.py`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/models/template.py`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/models/snapshot.py`
- Test: `e:/Bug/n8n.mcp/tests/unit/test_models.py`

**Step 1: Write failing test (`test_models.py`)**:
Test serialization/deserialization, aliasing, and strict validation of:
- `WorkflowDTO`, `WorkflowCreateRequest`, `WorkflowUpdateRequest`, `WorkflowSanitizedPayload`
- `NodeDTO`, `NodeConnectionDTO`, `PinDataDTO`, `NodePatchRequest`, `NodeSchemaDTO`
- `ExecutionDTO`, `ExecutionDetailDTO`, `DiagnosticsReportDTO`, `SelfHealingReportDTO`
- `SnapshotDTO`, `TemplateSummaryDTO`, `TemplateDetailDTO`

**Step 2: Run test to verify it fails**:
Run: `pytest n8n.mcp/tests/unit/test_models.py -v` (Expected: FAIL).

**Step 3: Implement minimal code**:
Implement all Pydantic v2 models with field aliases and default factories.

**Step 4: Verify test passes**:
Run: `pytest n8n.mcp/tests/unit/test_models.py -v` (Expected: PASS).

**Step 5: Git commit**:
`git -C e:/Bug/n8n.mcp commit -m "feat(n8n-mcp): implement Pydantic v2 DTOs and domain models"`

---

### Task 3: Resilient n8n Async REST Client with Payload Sanitization & Full-Jitter Backoff
**Files:**
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/engine/__init__.py`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/engine/client.py`
- Test: `e:/Bug/n8n.mcp/tests/unit/test_client.py`

**Step 1: Write failing test (`test_client.py`)**:
Test:
- `sanitize_workflow_payload()` correctly strips `id`, `versionId`, `createdAt`, `updatedAt`, `triggerCount`, `tags`, etc., preventing HTTP 400.
- Workflow CRUD methods (`list_workflows`, `get_workflow`, `create_workflow`, `update_workflow`, `delete_workflow`, `activate_workflow`).
- Execution methods (`list_executions`, `get_execution`, `retry_execution`, `delete_execution`).
- Webhook trigger calls (`trigger_webhook`).
- Template search and download (`search_templates`, `get_template`).
- AWS Full-Jitter Exponential Backoff on HTTP 429 and 503.

**Step 2: Run test to verify it fails**:
Run: `pytest n8n.mcp/tests/unit/test_client.py -v` (Expected: FAIL).

**Step 3: Implement minimal code**:
Implement `N8nClient` with `httpx.AsyncClient`, connection pooling, payload sanitization, and jittered retries.

**Step 4: Verify test passes**:
Run: `pytest n8n.mcp/tests/unit/test_client.py -v` (Expected: PASS).

**Step 5: Git commit**:
`git -C e:/Bug/n8n.mcp commit -m "feat(n8n-mcp): implement resilient REST client with payload sanitization and backoff"`

---

### Task 4: Diff-Based Node Patcher, Snapshot Rollback & Pin Data Engine
**Files:**
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/engine/patcher.py`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/engine/snapshots.py`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/engine/pindata.py`
- Test: `e:/Bug/n8n.mcp/tests/unit/test_patcher.py`
- Test: `e:/Bug/n8n.mcp/tests/unit/test_snapshots.py`
- Test: `e:/Bug/n8n.mcp/tests/unit/test_pindata.py`

**Step 1: Write failing tests**:
- `test_patcher.py`: Read-Modify-Write pattern, parameter deep-merge, token-efficient diff output, preserves graph integrity.
- `test_snapshots.py`: Creating snapshots before updates, listing snapshots, restoring snapshot via `rollback()`.
- `test_pindata.py`: Keying by Node Name, wrapping into `{"json": ...}`, clearing pin data.

**Step 2: Run tests to verify they fail**:
Run: `pytest n8n.mcp/tests/unit/test_patcher.py n8n.mcp/tests/unit/test_snapshots.py n8n.mcp/tests/unit/test_pindata.py -v` (Expected: FAIL).

**Step 3: Implement minimal code**:
Implement `WorkflowPatcher`, `SnapshotManager`, and `PinDataManager`.

**Step 4: Verify tests pass**:
Run: `pytest n8n.mcp/tests/unit/test_patcher.py n8n.mcp/tests/unit/test_snapshots.py n8n.mcp/tests/unit/test_pindata.py -v` (Expected: PASS).

**Step 5: Git commit**:
`git -C e:/Bug/n8n.mcp commit -m "feat(n8n-mcp): implement diff-based patcher, snapshot rollback, and pin-data engine"`

---

### Task 5: Anti-Hallucination Node Discovery & Schema Catalog
**Files:**
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/engine/node_catalog.py`
- Test: `e:/Bug/n8n.mcp/tests/unit/test_node_catalog.py`

**Step 1: Write failing test (`test_node_catalog.py`)**:
Test:
- Searching nodes by keyword, category, or package (`slack`, `httpRequest`, `postgres`, `openAi`, `code`).
- Retrieving exact schema, required properties, operations, and credentials for target node types.
- Fallback fuzzy search for misspelled node names.

**Step 2: Run test to verify it fails**:
Run: `pytest n8n.mcp/tests/unit/test_node_catalog.py -v` (Expected: FAIL).

**Step 3: Implement minimal code**:
Implement `NodeCatalogEngine` with curated offline schema definitions for top 100+ n8n nodes.

**Step 4: Verify test passes**:
Run: `pytest n8n.mcp/tests/unit/test_node_catalog.py -v` (Expected: PASS).

**Step 5: Git commit**:
`git -C e:/Bug/n8n.mcp commit -m "feat(n8n-mcp): implement anti-hallucination node discovery and schema catalog"`

---

### Task 6: DAG Validator & LangChain AI Agent Cluster Linter
**Files:**
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/engine/validator.py`
- Test: `e:/Bug/n8n.mcp/tests/unit/test_validator.py`

**Step 1: Write failing test (`test_validator.py`)**:
Test:
- DFS cycle detection across standard and `ai_*` connections.
- Dangling nodes detection (isolated nodes).
- Expression syntax linter (`{{ $json.key }}`).
- **LangChain AI Agent Validation**: Detecting `@n8n/n8n-nodes-langchain.agent` missing `ai_languageModel`, invalid `main` connections on tools, missing tool names.

**Step 2: Run test to verify it fails**:
Run: `pytest n8n.mcp/tests/unit/test_validator.py -v` (Expected: FAIL).

**Step 3: Implement minimal code**:
Implement `WorkflowValidator` with multi-port graph traversal algorithms.

**Step 4: Verify test passes**:
Run: `pytest n8n.mcp/tests/unit/test_validator.py -v` (Expected: PASS).

**Step 5: Git commit**:
`git -C e:/Bug/n8n.mcp commit -m "feat(n8n-mcp): implement DAG validator with LangChain AI agent validation"`

---

### Task 7: Execution Diagnostics & Autonomous Self-Healing Engine
**Files:**
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/engine/diagnostics.py`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/engine/healer.py`
- Test: `e:/Bug/n8n.mcp/tests/unit/test_diagnostics.py`
- Test: `e:/Bug/n8n.mcp/tests/unit/test_healer.py`

**Step 1: Write failing tests**:
- `test_diagnostics.py`: Parsing execution failure traces, identifying crashed node, categorizing error code (401 auth, 404 not found, syntax error), generating actionable RCA report.
- `test_healer.py`: Bounded self-healing execution loop (inspect failure -> patch node -> retry execution -> verify status, capped at 2 attempts).

**Step 2: Run tests to verify they fail**:
Run: `pytest n8n.mcp/tests/unit/test_diagnostics.py n8n.mcp/tests/unit/test_healer.py -v` (Expected: FAIL).

**Step 3: Implement minimal code**:
Implement `ExecutionDiagnosticsEngine` and `AutonomousSelfHealer`.

**Step 4: Verify tests pass**:
Run: `pytest n8n.mcp/tests/unit/test_diagnostics.py n8n.mcp/tests/unit/test_healer.py -v` (Expected: PASS).

**Step 5: Git commit**:
`git -C e:/Bug/n8n.mcp commit -m "feat(n8n-mcp): implement execution diagnostics and autonomous self-healing loop"`

---

### Task 8: behavioral-playwright Stealth Scraper Bridge Node Generator
**Files:**
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/engine/stealth_bridge.py`
- Test: `e:/Bug/n8n.mcp/tests/unit/test_stealth_bridge.py`

**Step 1: Write failing test (`test_stealth_bridge.py`)**:
Test generating pre-configured n8n HTTP Request node pointing to `http://host.docker.internal:8000/scrape` with URL, selector, biometric tremor flags, and structured output parsing.

**Step 2: Run test to verify it fails**:
Run: `pytest n8n.mcp/tests/unit/test_stealth_bridge.py -v` (Expected: FAIL).

**Step 3: Implement minimal code**:
Implement `StealthScraperBridgeBuilder`.

**Step 4: Verify test passes**:
Run: `pytest n8n.mcp/tests/unit/test_stealth_bridge.py -v` (Expected: PASS).

**Step 5: Git commit**:
`git -C e:/Bug/n8n.mcp commit -m "feat(n8n-mcp): implement behavioral-playwright stealth scraper bridge"`

---

### Task 9: Tool Registry Exposing 26 Production MCP Tools
**Files:**
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/tools/__init__.py`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/tools/registry.py`
- Test: `e:/Bug/n8n.mcp/tests/unit/test_tool_registry.py`

**Step 1: Write failing test (`test_tool_registry.py`)**:
Verify registration, JSON Schema manifests, parameter validation, and execution routing for all 26 tools.

**Step 2: Run test to verify it fails**:
Run: `pytest n8n.mcp/tests/unit/test_tool_registry.py -v` (Expected: FAIL).

**Step 3: Implement minimal code**:
Implement `ToolRegistry` with all 26 tool schemas and async execution dispatchers.

**Step 4: Verify test passes**:
Run: `pytest n8n.mcp/tests/unit/test_tool_registry.py -v` (Expected: PASS).

**Step 5: Git commit**:
`git -C e:/Bug/n8n.mcp commit -m "feat(n8n-mcp): register 26 production MCP tools in registry"`

---

### Task 10: JSON-RPC 2.0 Stdio Server, Integration Suite, Docs & Remote Push
**Files:**
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/server.py`
- Create: `e:/Bug/n8n.mcp/src/n8n_mcp/__main__.py`
- Create: `e:/Bug/n8n.mcp/tests/integration/test_mcp_e2e.py`
- Create: `e:/Bug/n8n.mcp/README.md`
- Create: `e:/Bug/n8n.mcp/PLAYBOOK.md`
- Create: `e:/Bug/n8n.mcp/LICENSE`
- Modify: `e:/Bug/ROADMAP.md`

**Step 1: Implement `server.py` and `__main__.py`**:
Windows `ProactorEventLoop` safe async stdio stream reader/writer.

**Step 2: Write integration tests & verify 100% test suite**:
Run: `pytest n8n.mcp/tests/ -v` (Expected: Exit code 0, 100% pass).

**Step 3: Create documentation (`README.md`, `PLAYBOOK.md`, `LICENSE`)**:
Full architecture diagram, 26-tool reference, Claude Desktop & Cursor config JSONs, token savings analysis, pin-data testing guide.

**Step 4: Push to GitHub**:
`git -C e:/Bug/n8n.mcp push -u origin main`
Verify remote push on [sadik004/n8n.mcp](https://github.com/sadik004/n8n.mcp).
