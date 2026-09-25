"""MCP Tool definitions and execution dispatchers."""

from __future__ import annotations

import base64
import os
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
    {
        "name": "stealth_click",
        "description": "Performs an undetectable, human-mimetic click on a selector or (x, y) coordinates using Costello saccades, Harris-Wolpert noise, and subpixel targeting.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector to click"},
                "x": {"type": "number", "description": "X coordinate"},
                "y": {"type": "number", "description": "Y coordinate"},
                "url": {"type": "string", "description": "Optional URL to navigate to first"},
            },
        },
    },
    {
        "name": "stealth_type",
        "description": "Simulates human typing into an input element using physical QWERTY Euclidean distances and Weibull latency distributions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector to type into"},
                "text": {"type": "string", "description": "Text to type"},
            },
            "required": ["selector", "text"],
        },
    },
    {
        "name": "stealth_navigate",
        "description": "Navigates to URL with automated 3-state CAPTCHA loop protection and Shannon entropy content validation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target URL to navigate to"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "audit_biometrics",
        "description": "Evaluates kinematic or timing trajectories against empirical human reference baselines using Two-Sample KS-test, Mann-Whitney U, and Wasserstein distance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "samples": {"type": "array", "items": {"type": "number"}, "description": "Array of velocities or keystroke latencies"},
                "modality": {"type": "string", "enum": ["mouse", "keystroke"], "default": "mouse"},
            },
            "required": ["samples"],
        },
    },
    {
        "name": "memory_pid_health",
        "description": "Checks Chromium browser memory usage and calculates closed-loop PID regulation recommendations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "current_rss_mb": {"type": "number", "description": "Current process RSS in MB (optional)"},
                "target_rss_mb": {"type": "number", "default": 512.0},
            },
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
        res: Any = None

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

            elif tool_name == "stealth_click":
                selector = arguments.get("selector")
                x = arguments.get("x")
                y = arguments.get("y")
                url = arguments.get("url")

                async with bp:
                    if url:
                        await bp.goto(url)
                    if y is not None and x is not None:
                        await bp.click(x, y=y, humanize=True)
                        return {"status": "success", "action": "coordinate_click", "x": x, "y": y}
                    elif selector:
                        await bp.click(selector, humanize=True)
                        return {"status": "success", "action": "selector_click", "selector": selector}
                    return {"error": "Must provide selector or both x and y"}

            elif tool_name == "stealth_type":
                selector = arguments.get("selector")
                text = arguments.get("text", "")
                if not selector or not text:
                    return {"error": "Missing required arguments 'selector' and 'text'"}

                async with bp:
                    await bp.click(selector, humanize=True)
                    await bp.type(text, humanize=True)
                    return {"status": "success", "action": "typed", "chars": len(text)}

            elif tool_name == "stealth_navigate":
                url = arguments.get("url")
                if not url:
                    return {"error": "Missing required argument 'url'"}

                async with bp:
                    await bp.goto(url)
                    title = await bp.page.get_title()
                    loop_eval = bp.powerplay.loop_detector.record_navigation(url)
                    audit_res = bp.powerplay.audit_content_entropy(title)
                    return {
                        "status": "success",
                        "url": url,
                        "title": title,
                        "loop_evaluation": loop_eval,
                        "content_audit": audit_res,
                    }

            elif tool_name == "audit_biometrics":
                samples = arguments.get("samples", [])
                modality = arguments.get("modality", "mouse")
                if modality == "keystroke":
                    res = bp.validator.validate_keystroke_latencies(samples)
                else:
                    res = bp.validator.validate_mouse_kinematics(samples)
                return {"status": "success", "result": res}

            elif tool_name == "memory_pid_health":
                target_mb = float(arguments.get("target_rss_mb", 512.0))
                current_mb = arguments.get("current_rss_mb")
                if current_mb is None:
                    try:
                        import psutil
                        process = psutil.Process(os.getpid())
                        current_mb = float(process.memory_info().rss) / (1024.0 * 1024.0)
                    except Exception:
                        current_mb = 250.0  # Fallback nominal RSS
                else:
                    current_mb = float(current_mb)

                correction = bp.powerplay.compute_memory_adjustment(current_rss_mb=current_mb, target_rss_mb=target_mb)
                return {
                    "status": "success",
                    "current_rss_mb": round(current_mb, 2),
                    "target_rss_mb": round(target_mb, 2),
                    "regulation": correction,
                }

            return {"error": f"Unknown tool: {tool_name}"}
        except Exception as exc:
            return {"error": str(exc), "status": "failed"}
