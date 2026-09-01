"""Unit tests for JSON-RPC 2.0 MCP server and tools."""

import json
import pytest
from behavioral_playwright.mcp.server import McpServer
from behavioral_playwright.mcp.tools import MCP_TOOL_DEFINITIONS, McpToolDispatcher


def test_mcp_tool_definitions():
    tool_names = [t["name"] for t in MCP_TOOL_DEFINITIONS]
    assert "scrape_page" in tool_names
    assert "crawl_domain" in tool_names
    assert "take_screenshot" in tool_names
    assert "quant_pit_align" in tool_names
    assert "get_provider_matrix" in tool_names


@pytest.mark.asyncio
async def test_mcp_server_protocol():
    server = McpServer()

    # 1. Initialize
    init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    init_resp = await server.handle_request(init_req)
    assert init_resp["id"] == 1
    assert init_resp["result"]["serverInfo"]["name"] == "behavioral-playwright-mcp"

    # 2. Tools List
    tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    tools_resp = await server.handle_request(tools_req)
    assert len(tools_resp["result"]["tools"]) >= 5

    # 3. Tool Call: quant_pit_align
    call_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "quant_pit_align",
            "arguments": {
                "filing": {
                    "cik": "0000320193",
                    "period_of_report_epoch": 100.0,
                    "sec_dissemination_epoch": 105.0,
                }
            },
        },
    }
    call_resp = await server.handle_request(call_req)
    assert call_resp["id"] == 3
    assert call_resp["result"]["isError"] is False
    content_raw = call_resp["result"]["content"][0]["text"]
    data = json.loads(content_raw)
    assert data["result"]["event_timestamp"] == 100.0

    # 4. Ping
    ping_req = {"jsonrpc": "2.0", "id": 4, "method": "ping", "params": {}}
    ping_resp = await server.handle_request(ping_req)
    assert ping_resp["id"] == 4
    assert ping_resp["result"] == {}

    # 5. Unknown Method (-32601)
    unk_req = {"jsonrpc": "2.0", "id": 5, "method": "resources/list", "params": {}}
    unk_resp = await server.handle_request(unk_req)
    assert unk_resp["id"] == 5
    assert unk_resp["error"]["code"] == -32601

    # 6. Unknown Tool Call (isError: True)
    bad_tool_req = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {"name": "non_existent_tool", "arguments": {}},
    }
    bad_tool_resp = await server.handle_request(bad_tool_req)
    assert bad_tool_resp["id"] == 6
    assert bad_tool_resp["result"]["isError"] is True

    # 7. Generate Claude Desktop Config
    cfg = McpServer.generate_claude_config(python_path="python.exe")
    assert "behavioral-playwright" in cfg["mcpServers"]
