"""Model Context Protocol (MCP) server & tool dispatch subsystem."""

from behavioral_playwright.mcp.server import McpServer
from behavioral_playwright.mcp.tools import MCP_TOOL_DEFINITIONS, McpToolDispatcher

__all__ = [
    "McpServer",
    "McpToolDispatcher",
    "MCP_TOOL_DEFINITIONS",
]
