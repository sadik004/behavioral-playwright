"""Independent MCP Contract Verification Suite.

Tests:
1. Tool list integrity and valid schema structure.
2. Unknown tool invocation error handling.
3. Missing mandatory arguments error response.
4. Provider matrix retrieval via MCP.
5. Error code and serialization integrity.
"""
from __future__ import annotations

import pytest

from behavioral_playwright.mcp.tools import MCP_TOOL_DEFINITIONS, McpToolDispatcher


class TestMcpContractsIntegrity:
    """Independent verification of MCP contracts and schema invariants."""

    def test_mcp_tool_definitions_schema_compliance(self):
        """Every tool definition must adhere to standard JSON schema contracts."""
        assert isinstance(MCP_TOOL_DEFINITIONS, list)
        assert len(MCP_TOOL_DEFINITIONS) >= 15, f"Expected at least 15 tools, found {len(MCP_TOOL_DEFINITIONS)}"

        tool_names = set()
        for tool in MCP_TOOL_DEFINITIONS:
            assert "name" in tool, "Tool missing 'name' field"
            assert "description" in tool, f"Tool {tool.get('name')} missing 'description'"
            assert "inputSchema" in tool, f"Tool {tool.get('name')} missing 'inputSchema'"

            schema = tool["inputSchema"]
            assert schema.get("type") == "object", f"Tool {tool['name']} schema type must be 'object'"
            assert "properties" in schema, f"Tool {tool['name']} missing 'properties'"

            name = tool["name"]
            assert name not in tool_names, f"Duplicate tool registered: {name}"
            tool_names.add(name)

    @pytest.mark.asyncio
    async def test_mcp_unknown_tool_returns_error(self):
        """Calling an unregistered tool must return explicit error dictionary."""
        dispatcher = McpToolDispatcher()
        res = await dispatcher.execute_tool("phantom_unregistered_tool", {})

        assert isinstance(res, dict)
        assert "error" in res, f"Expected 'error' in response, got: {res}"
        assert "Unknown tool" in res["error"]
        assert res.get("status") != "success"

    @pytest.mark.asyncio
    async def test_mcp_missing_arguments_returns_error(self):
        """Calling tools with missing mandatory arguments must return explicit error."""
        dispatcher = McpToolDispatcher()

        # scrape_page requires 'url'
        res = await dispatcher.execute_tool("scrape_page", {})
        assert isinstance(res, dict)
        # Should return error without crashing
        assert "error" in res or res.get("status") in ("failed", "error")

    @pytest.mark.asyncio
    async def test_mcp_get_provider_matrix_returns_data(self):
        """get_provider_matrix tool must return provider dictionary with installed booleans."""
        dispatcher = McpToolDispatcher()
        res = await dispatcher.execute_tool("get_provider_matrix", {})

        assert isinstance(res, dict)
        assert res.get("status") == "success"
        assert "result" in res
        providers_dict = res["result"]
        assert "browser/playwright" in providers_dict
