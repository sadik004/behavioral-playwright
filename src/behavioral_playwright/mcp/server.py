"""Standard JSON-RPC 2.0 Model Context Protocol (MCP) Server."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict, Optional

from behavioral_playwright.mcp.tools import MCP_TOOL_DEFINITIONS, McpToolDispatcher


class McpServer:
    """Stdio-based JSON-RPC 2.0 server for Claude Desktop, Cursor, and AI Agents."""

    def __init__(self) -> None:
        self.dispatcher = McpToolDispatcher()

    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "behavioral-playwright-mcp", "version": "10.0.0"},
                },
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": MCP_TOOL_DEFINITIONS},
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = await self.dispatcher.execute_tool(tool_name, arguments)
            
            is_error = "error" in result
            content_text = json.dumps(result, indent=2)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": content_text}],
                    "isError": is_error,
                },
            }

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        # Notification or unknown method
        if req_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        return None

    async def run_stdio(self) -> None:
        """Reads JSON-RPC lines from stdin and writes responses to stdout."""
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line = await reader.readline()
            if not line:
                break
            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            try:
                req = json.loads(line_str)
                resp = await self.handle_request(req)
                if resp:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
            except Exception as exc:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(exc)}"},
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()

    @staticmethod
    def generate_claude_config(python_path: str = "python") -> Dict[str, Any]:
        """Generates standard claude_desktop_config.json entry."""
        return {
            "mcpServers": {
                "behavioral-playwright": {
                    "command": python_path,
                    "args": ["-m", "behavioral_playwright.mcp.server"],
                }
            }
        }


def main() -> None:
    server = McpServer()
    asyncio.run(server.run_stdio())


if __name__ == "__main__":
    main()
