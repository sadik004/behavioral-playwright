# Feature Specification: Integrations Namespace (`bp.integrations`)

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Overview & Capabilities
The `IntegrationsNamespace` ([`bp_facade12.py:1266`](file:///c:/Users/User/SAA/bp_facade12.py#L1266)) dispatches real HTTP webhook notifications (Slack, Discord, n8n), exports HAR traces, and bridges tools to AI agents via the Model Context Protocol (MCP).

---

## 2. API Method Reference

### `slack_webhook_notify_async(webhook_url, message, timeout=10.0)`
- **Signature**: `async def slack_webhook_notify_async(self, webhook_url: str, message: str, timeout: float = 10.0) -> bool`
- **Description**: Formats `{"text": message}` payload and dispatches real HTTP POST to Slack.

### `discord_webhook_notify_async(webhook_url, message, timeout=10.0)`
- **Signature**: `async def discord_webhook_notify_async(self, webhook_url: str, message: str, timeout: float = 10.0) -> bool`
- **Description**: Formats `{"content": message}` payload and dispatches real HTTP POST to Discord.

### `n8n_webhook_trigger_async(webhook_url, payload, timeout=10.0)`
- **Signature**: `async def n8n_webhook_trigger_async(self, webhook_url: str, payload: Dict[str, Any], timeout: float = 10.0) -> bool`
- **Description**: Sends custom JSON dictionary payloads to n8n webhook nodes.

### `mcp_call_tool_async(tool_name, arguments)`
- **Signature**: `async def mcp_call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Any`
- **Description**: Dispatches tool invocations (`scrape`, `crawl`, `search`, `map`) directly to `BP.web` methods.

### `generate_mcp_manifest()`
- **Signature**: `def generate_mcp_manifest(self) -> Dict[str, Any]`
- **Description**: Returns standard MCP tool definitions formatted as JSON schema for LLM function calling.
