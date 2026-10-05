"""Independent verifier for MUT-005: MCP Unknown Tool Handling."""
import pytest
from behavioral_playwright.mcp.tools import McpToolDispatcher


@pytest.mark.asyncio
async def test_unknown_tool_must_return_error():
    """Executing a non-existent tool must return explicit error and never status='success'."""
    dispatcher = McpToolDispatcher()
    res = await dispatcher.execute_tool("nonexistent_unknown_tool_name", {})
    assert isinstance(res, dict)
    assert "error" in res, f"Expected 'error' in response, got {res}"
    assert res.get("status") != "success", f"Unknown tool returned fake success: {res}"
