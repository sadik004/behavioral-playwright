"""MCP Tool definitions and execution dispatchers."""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional
from behavioral_playwright.config.settings import AutomationConfig

MCP_TOOL_DEFINITIONS: List[Dict[str, Any]] = [

    {
        "name": "scrape_page",
        "description": "Scrapes a webpage using self-healing browser automation and returns markdown/content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to scrape"},
                "target": {"type": "string", "enum": ["links", "articles", "raw"], "default": "links"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "crawl_domain",
        "description": "Recursively crawls URLs within a domain up to a maximum page count.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Starting URL for crawl"},
                "max_pages": {"type": "integer", "default": 5},
                "depth": {"type": "integer", "default": 2},
            },
            "required": ["url"],
        },
    },
    {
        "name": "take_screenshot",
        "description": "Navigates to a URL and returns a Base64-encoded PNG screenshot for vision analysis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to screenshot"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "quant_pit_align",
        "description": "Aligns a financial SEC filing payload to prevent Point-in-Time look-ahead bias.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filing": {"type": "object", "description": "Filing metadata dictionary"},
            },
            "required": ["filing"],
        },
    },
    {
        "name": "get_provider_matrix",
        "description": "Retrieves the real-time installation and availability status of all browser and network providers.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


class McpToolDispatcher:
    """Dispatches MCP tool calls to the BP engine."""

    def __init__(
        self,
        bp: Optional[Any] = None,
        config: Optional[AutomationConfig] = None,
    ) -> None:
        self._bp = bp
        self._config = config

    def _get_bp(self) -> Any:
        if self._bp is not None:
            return self._bp
        from behavioral_playwright import BP
        return BP(config=self._config)

    async def execute_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            arguments = {}
        bp = self._get_bp()

        try:
            if tool_name == "scrape_page":
                url = arguments.get("url")
                target = arguments.get("target", "links")
                if not url:
                    return {"error": "Missing required argument 'url'"}

                async with bp:
                    await bp.goto(url)
                    if target in ("links", "articles"):
                        records = await bp.extract(target=target)
                        res = [r.to_dict() if hasattr(r, "to_dict") else vars(r) for r in records]
                    else:
                        res = await bp.page.evaluate("() => document.documentElement.outerHTML")
                    return {"status": "success", "result": res}

            elif tool_name == "crawl_domain":
                url = arguments.get("url")
                max_pages = arguments.get("max_pages", 5)
                if not url:
                    return {"error": "Missing required argument 'url'"}

                async with bp:
                    records = await bp.crawl(url, max_pages=max_pages)
                    res = [r.to_dict() if hasattr(r, "to_dict") else vars(r) for r in records]
                    return {"status": "success", "result": res}

            elif tool_name == "take_screenshot":
                url = arguments.get("url")
                if not url:
                    return {"error": "Missing required argument 'url'"}

                async with bp:
                    await bp.goto(url)
                    png_bytes = await bp.screenshot()
                    b64 = base64.b64encode(png_bytes).decode("utf-8")
                    return {
                        "status": "success",
                        "mime_type": "image/png",
                        "data": b64,
                    }

            elif tool_name == "quant_pit_align":
                filing = arguments.get("filing", {})
                aligned = bp.quant.align_edgar_filing(filing)
                return {"status": "success", "result": aligned}

            elif tool_name == "get_provider_matrix":
                matrix = bp.providers.matrix()
                res = {k: {"provider": v.provider, "installed": v.installed} for k, v in matrix.items()}
                return {"status": "success", "result": res}

            return {"error": f"Unknown tool: {tool_name}"}
        except Exception as exc:
            return {"error": str(exc), "status": "failed"}
