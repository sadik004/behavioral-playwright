"""Integration extensions: n8n webhooks and MCP tool dispatch.

Real HTTP implementations using urllib; MCP tools delegate to the BP
facade's acquisition methods (scrape/crawl/search/map).
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Optional

_MCP_MANIFEST = {
    "mcp_version": "1.0.0",
    "name": "behavioral-playwright-mcp",
    "tools": [
        {"name": "scrape",
         "description": "Scrapes webpage and extracts clean DOM/content",
         "parameters": {"type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"]}},
        {"name": "crawl",
         "description": "Crawls web domain or URL hierarchy",
         "parameters": {"type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"]}},
        {"name": "search",
         "description": "Performs search query",
         "parameters": {"type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]}},
        {"name": "map",
         "description": "Maps website URL structure",
         "parameters": {"type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"]}},
    ],
}


class IntegrationExtensions:
    """n8n/MCP capabilities mixed into ``bp.integrations``."""

    def __init__(self, bp: Any) -> None:
        self._bp = bp

    # -- webhook dispatch ---------------------------------------------------
    @staticmethod
    def _dispatch_webhook(webhook_url: str, payload: Dict[str, Any],
                          timeout: float = 10.0) -> bool:
        if not str(webhook_url).startswith(("http://", "https://")):
            raise ValueError(f"Invalid webhook URL schema: {webhook_url}")
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "User-Agent": "BehavioralPlaywright-Webhook/1.0"},
            method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300

    def n8n_webhook_trigger(self, webhook_url: str, payload: Dict[str, Any],
                            timeout: float = 10.0) -> bool:
        return self._dispatch_webhook(webhook_url, payload, timeout)

    async def n8n_webhook_trigger_async(self, webhook_url: str,
                                        payload: Dict[str, Any],
                                        timeout: float = 10.0) -> bool:
        return await asyncio.to_thread(
            self._dispatch_webhook, webhook_url, payload, timeout)

    # -- MCP ----------------------------------------------------------------
    async def mcp_call_tool_async(self, tool_name: str,
                                  arguments: Dict[str, Any]) -> Any:
        bp = self._bp
        if tool_name == "scrape":
            url = arguments.get("url") or arguments.get("url_or_html")
            if not url:
                return {"status": "error",
                        "error": "Missing 'url' parameter for scrape tool"}
            result = await bp.web.scrape(url, options=arguments.get("options"))
            content = (getattr(result, "content", None)
                       or getattr(result, "html", None) or str(result))
            return {"status": "success", "tool": tool_name, "content": content}
        if tool_name in ("crawl", "map"):
            url = arguments.get("url")
            if not url:
                return {"status": "error",
                        "error": f"Missing 'url' parameter for {tool_name} tool"}
            fn = bp.web.crawl if tool_name == "crawl" else bp.web.map
            result = await fn(url, options=arguments.get("options"))
            return {"status": "success", "tool": tool_name,
                    "content": str(result)}
        if tool_name == "search":
            query = arguments.get("query")
            if not query:
                return {"status": "error",
                        "error": "Missing 'query' parameter for search tool"}
            result = await bp.web.search(query,
                                         options=arguments.get("options"))
            return {"status": "success", "tool": tool_name,
                    "content": str(result)}
        return {"status": "error", "error": f"Unknown tool: {tool_name}"}

    def mcp_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Sync bridge over :meth:`mcp_call_tool_async`."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.mcp_call_tool_async(tool_name, arguments))
        # Already inside a loop: run in a worker thread with its own loop.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                asyncio.run, self.mcp_call_tool_async(tool_name, arguments)
            ).result()

    @staticmethod
    def generate_mcp_manifest() -> Dict[str, Any]:
        import copy
        return copy.deepcopy(_MCP_MANIFEST)

    @staticmethod
    def integrations_health_check(db_path: str = "bp_tasks.db"
                                  ) -> Dict[str, Any]:
        import os
        import sqlite3
        healthy = True
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("SELECT 1")
            conn.close()
        except sqlite3.Error:
            healthy = False
        return {"mcp_manifest_available": True,
                "sqlite_connections": "healthy" if healthy else "unreachable"}


__all__ = ["IntegrationExtensions"]
