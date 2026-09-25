"""
End-to-End Real-World Live Mining & Verification Suite.
Validates Google Suggest drilldown, CSR rendering drift auditing, SERP overlap cannibalization,
and MCP JSON-RPC tool dispatchers across the unified BP architecture.
"""

from unittest.mock import AsyncMock, patch
import pytest

from behavioral_playwright import BP
from behavioral_playwright.mcp.tools import MCP_TOOL_DEFINITIONS, McpToolDispatcher
from behavioral_playwright.mining import (
    CSRRenderingDriftAuditor,
    GoogleSuggestMiner,
    PAAMiner,
    SEOMiningEngine,
    SERPCannibalizationEngine,
)
from behavioral_playwright.models.seo_dtos import (
    CannibalizationReport,
    CSRDriftReport,
    SuggestResult,
)


@pytest.mark.asyncio
async def test_facade_suggest_miner_integration():
    """Verify bp.mining.mine_suggest executes and returns valid SuggestResult."""
    bp = BP()
    mock_res = SuggestResult(
        query="fastapi vs",
        suggestions=["fastapi vs flask", "fastapi vs django"],
        alphabet_tree={"f": ["fastapi vs flask"]},
        total_unique=2,
    )

    with patch("behavioral_playwright.mining.suggest_miner.GoogleSuggestMiner.mine", new=AsyncMock(return_value=mock_res)):
        res = await bp.mining.mine_suggest("fastapi vs", alphabet=True)
        assert isinstance(res, SuggestResult)
        assert res.query == "fastapi vs"
        assert res.total_unique == 2
        assert "f" in res.alphabet_tree


@pytest.mark.asyncio
async def test_facade_csr_drift_auditor_integration():
    """Verify bp.mining.audit_csr_drift executes and returns valid CSRDriftReport."""
    bp = BP()

    raw_html = "<html><head><title>Raw Page</title></head><body><p>Server content</p></body></html>"
    rendered_html = """
    <html>
      <head><title>CSR Page</title></head>
      <body>
        <h1>Injected Heading</h1>
        <p>Server content</p>
        <a href="/link1">1</a><a href="/link2">2</a><a href="/link3">3</a><a href="/link4">4</a>
      </body>
    </html>
    """

    report = await bp.mining.audit_csr_drift(raw_html=raw_html, rendered_html=rendered_html)
    assert isinstance(report, CSRDriftReport)
    assert report.raw_html_bytes > 0
    assert report.rendered_html_bytes > 0
    assert "H1 headings rendered exclusively via CSR" in report.missing_in_raw
    assert report.hydration_drift_detected is True


@pytest.mark.asyncio
async def test_facade_check_overlap_integration():
    """Verify bp.mining.check_overlap computes cannibalization report."""
    bp = BP()
    report = await bp.mining.check_overlap(
        query_a="scraping",
        query_b="crawling",
        urls_a=["https://example.com/guide", "https://example.com/docs"],
        urls_b=["https://example.com/guide", "https://example.com/api"],
        threshold=0.30,
    )
    assert isinstance(report, CannibalizationReport)
    assert "https://example.com/guide" in report.common_urls
    assert report.recommendation == "MERGE_INTO_SINGLE_CANONICAL"


def test_mcp_tool_definitions_presence():
    """Verify all new mining and verification tools are registered in MCP_TOOL_DEFINITIONS."""
    tool_names = [t["name"] for t in MCP_TOOL_DEFINITIONS]
    assert "mine_google_suggest" in tool_names
    assert "audit_csr_drift" in tool_names
    assert "mine_paa" in tool_names
    assert "check_cannibalization" in tool_names
    assert "extract_metadata" in tool_names
    assert "sniff_api_responses" in tool_names


@pytest.mark.asyncio
async def test_mcp_dispatcher_mine_google_suggest():
    """Verify MCP tool dispatcher executes mine_google_suggest."""
    mock_res = SuggestResult(
        query="python",
        suggestions=["python download", "python tutorial"],
        total_unique=2,
    )

    dispatcher = McpToolDispatcher()
    with patch("behavioral_playwright.mining.suggest_miner.GoogleSuggestMiner.mine", new=AsyncMock(return_value=mock_res)):
        resp = await dispatcher.execute_tool(
            "mine_google_suggest",
            {"query": "python", "alphabet": False},
        )
        assert resp["status"] == "success"
        assert resp["result"]["query"] == "python"
        assert resp["result"]["total_unique"] == 2


@pytest.mark.asyncio
async def test_mcp_dispatcher_audit_csr_drift():
    """Verify MCP tool dispatcher executes audit_csr_drift."""
    dispatcher = McpToolDispatcher()
    raw = "<html><body><p>Static</p></body></html>"
    csr = "<html><body><h1>Dynamic</h1><p>Static</p></body></html>"

    resp = await dispatcher.execute_tool(
        "audit_csr_drift",
        {"raw_html": raw, "rendered_html": csr},
    )
    assert resp["status"] == "success"
    assert "drift_ratio" in resp["result"]
    assert "seo_indexation_risk" in resp["result"]


@pytest.mark.asyncio
async def test_mcp_dispatcher_check_cannibalization():
    """Verify MCP tool dispatcher executes check_cannibalization."""
    dispatcher = McpToolDispatcher()
    resp = await dispatcher.execute_tool(
        "check_cannibalization",
        {
            "query_a": "q1",
            "query_b": "q2",
            "urls_a": ["https://site.com/a"],
            "urls_b": ["https://site.com/a"],
            "threshold": 0.40,
        },
    )
    assert resp["status"] == "success"
    assert resp["result"]["jaccard_score"] == 1.0
    assert resp["result"]["recommendation"] == "MERGE_INTO_SINGLE_CANONICAL"


@pytest.mark.asyncio
async def test_mcp_dispatcher_mine_paa():
    """Verify MCP tool dispatcher executes mine_paa with mock HTML."""
    dispatcher = McpToolDispatcher()
    mock_serp = """
    <div class="related-question-pair">
      <div role="button"><div>How does Playwright work?</div></div>
      <div>
        <div>Playwright controls browser instances via CDP.</div>
        <a href="https://playwright.dev"><span>Docs</span></a>
      </div>
    </div>
    """
    resp = await dispatcher.execute_tool(
        "mine_paa",
        {"html": mock_serp, "depth": 1},
    )
    assert resp["status"] == "success"
    assert resp["count"] == 1
    assert resp["nodes"][0]["question"] == "How does Playwright work?"
