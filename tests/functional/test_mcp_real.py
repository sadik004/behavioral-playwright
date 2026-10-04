"""Functional Validation: MCP Tools & Dispatcher Execution.
Tests MCP tool invocations against real browser/runtime and verifies observable tool results.
"""

from __future__ import annotations

import base64
import pytest
from behavioral_playwright.mcp.tools import McpToolDispatcher


@pytest.mark.asyncio
async def test_mcp_get_provider_matrix():
    """Verify get_provider_matrix tool returns live honest matrix with playwright installed."""
    dispatcher = McpToolDispatcher()
    res = await dispatcher.execute_tool("get_provider_matrix", {})
    
    assert res.get("status") == "success"
    assert "result" in res
    result_map = res["result"]
    assert "browser/playwright" in result_map
    assert result_map["browser/playwright"]["installed"] is True
    assert result_map["browser/patchright"]["installed"] is False


@pytest.mark.asyncio
async def test_mcp_take_screenshot_real_png():
    """Verify take_screenshot navigates to page, captures real image, and returns valid base64 PNG."""
    dispatcher = McpToolDispatcher()
    url = "data:text/html,<html><head><title>MCP Screenshot</title></head><body style='background: blue;'><h1>Captured</h1></body></html>"
    
    res = await dispatcher.execute_tool("take_screenshot", {"url": url})
    
    assert res.get("status") == "success"
    assert res.get("mime_type") == "image/png"
    assert "data" in res
    
    # Decode base64 and verify real PNG signature bytes (\x89PNG\r\n\x1a\n)
    raw_png = base64.b64decode(res["data"])
    assert raw_png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(raw_png) > 1000  # Genuine non-empty image


@pytest.mark.asyncio
async def test_mcp_scrape_page_real_links():
    """Verify scrape_page executes browser automation and extracts links."""
    dispatcher = McpToolDispatcher()
    url = "data:text/html,<html><body><a href='https://openai.com/research'>Research</a><a href='https://anthropic.com/claude'>Claude</a></body></html>"
    
    res = await dispatcher.execute_tool("scrape_page", {"url": url, "target": "links"})
    
    assert res.get("status") == "success"
    links = res.get("result", [])
    assert len(links) == 2
    assert links[0]["text"] == "Research"
    assert links[0]["href"] == "https://openai.com/research"
    assert links[1]["text"] == "Claude"
    assert links[1]["href"] == "https://anthropic.com/claude"


@pytest.mark.asyncio
async def test_mcp_unknown_tool_rejection():
    """Verify invoking an unknown tool fails honestly without fake success."""
    dispatcher = McpToolDispatcher()
    res = await dispatcher.execute_tool("nonexistent_fake_tool_999", {})
    
    assert "error" in res
    assert "Unknown tool" in res["error"]
    assert res.get("status") != "success"


@pytest.mark.asyncio
async def test_mcp_missing_required_arguments():
    """Verify tool execution fails gracefully when required inputs are omitted."""
    dispatcher = McpToolDispatcher()
    res = await dispatcher.execute_tool("take_screenshot", {})
    
    assert "error" in res
    assert "Missing required argument" in res["error"]
    assert res.get("status") != "success"
