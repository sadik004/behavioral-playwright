"""
Unit tests verifying MCP Nuclear & Stealth Tool dispatching for AI Agents.
Validates stealth_click, stealth_type, stealth_navigate, audit_biometrics, and memory_pid_health.
"""

import json
import pytest
import numpy as np
from behavioral_playwright.mcp.server import McpServer
from behavioral_playwright.mcp.tools import MCP_TOOL_DEFINITIONS


def test_mcp_nuclear_tool_definitions_present():
    names = [t["name"] for t in MCP_TOOL_DEFINITIONS]
    assert "stealth_click" in names
    assert "stealth_type" in names
    assert "stealth_navigate" in names
    assert "audit_biometrics" in names
    assert "memory_pid_health" in names


@pytest.mark.asyncio
async def test_mcp_audit_biometrics_tool_dispatch():
    server = McpServer()

    # Synthetic lognormal mouse velocities
    rng = np.random.default_rng(42)
    synthetic_velocities = rng.lognormal(mean=-0.35, sigma=0.28, size=150).tolist()

    req = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {
            "name": "audit_biometrics",
            "arguments": {
                "samples": synthetic_velocities,
                "modality": "mouse"
            }
        }
    }
    resp = await server.handle_request(req)
    assert resp["id"] == 10
    assert resp["result"]["isError"] is False

    data = json.loads(resp["result"]["content"][0]["text"])
    assert data["status"] == "success"
    assert "ks_statistic" in data["result"]
    assert "p_value" in data["result"]
    assert "is_human_indistinguishable" in data["result"]


@pytest.mark.asyncio
async def test_mcp_memory_pid_health_tool_dispatch():
    server = McpServer()

    req = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "memory_pid_health",
            "arguments": {
                "current_rss_mb": 750.0,
                "target_rss_mb": 512.0
            }
        }
    }
    resp = await server.handle_request(req)
    assert resp["id"] == 11
    assert resp["result"]["isError"] is False

    data = json.loads(resp["result"]["content"][0]["text"])
    assert data["status"] == "success"
    assert data["current_rss_mb"] == 750.0
    assert data["target_rss_mb"] == 512.0
    assert "error_mb" in data["regulation"]
    assert data["regulation"]["error_mb"] == 238.0
