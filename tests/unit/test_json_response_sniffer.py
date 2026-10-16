"""Unit tests for JSONResponseSniffer and MCP intelligence mining tools."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from behavioral_playwright.facade import BP
from behavioral_playwright.mcp.tools import McpToolDispatcher
from behavioral_playwright.network.sniffer import JSONResponseSniffer


class MockPlaywrightResponse:
    def __init__(self, url: str, status: int, data: dict, content_type: str = "application/json"):
        self.url = url
        self.status = status
        self._data = data
        self.headers = {"content-type": content_type}

    async def json(self) -> dict:
        return self._data

    async def text(self) -> str:
        import json
        return json.dumps(self._data)


class MockPlaywrightPage:
    def __init__(self):
        self._handlers = {}

    def on(self, event: str, handler):
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def remove_listener(self, event: str, handler):
        if event in self._handlers and handler in self._handlers[event]:
            self._handlers[event].remove(handler)

    async def emit_response(self, response):
        for h in self._handlers.get("response", []):
            await h(response)


@pytest.mark.asyncio
async def test_json_response_sniffer_intercept_and_buffer():
    """Verify JSONResponseSniffer captures matching background JSON payloads."""
    page = MockPlaywrightPage()
    sniffer = JSONResponseSniffer(page)

    resp1 = MockPlaywrightResponse(
        url="https://api.example.com/v1/products?page=1",
        status=200,
        data={"items": [{"id": 101, "sku": "STEALTH-X"}]},
    )
    resp2 = MockPlaywrightResponse(
        url="https://tracking.com/beacon",
        status=200,
        data={"tracked": True},
        content_type="text/plain",
    )

    await page.emit_response(resp1)
    await page.emit_response(resp2)

    # Filter by pattern
    payloads = await sniffer.intercept_json(url_patterns=["*products*"], timeout=0.5)
    assert len(payloads) == 1
    assert payloads[0]["items"][0]["sku"] == "STEALTH-X"

    # Verify captured buffer
    captured = sniffer.captured_responses
    assert len(captured) == 1
    assert captured[0]["url"] == "https://api.example.com/v1/products?page=1"

    # Test clear
    sniffer.clear()
    assert len(sniffer.captured_responses) == 0

    sniffer.detach()


@pytest.mark.asyncio
async def test_json_response_sniffer_async_context_manager():
    """Verify async context manager auto-detaches handler on exit."""
    page = MockPlaywrightPage()

    async with JSONResponseSniffer(page) as sniffer:
        assert len(page._handlers.get("response", [])) == 1
        resp = MockPlaywrightResponse(
            url="https://api.example.com/data.json",
            status=200,
            data={"status": "ok"},
        )
        await page.emit_response(resp)
        results = await sniffer.intercept_json(url_patterns=["*.json"])
        assert results == [{"status": "ok"}]

    # Handler should be removed after context exit
    assert len(page._handlers.get("response", [])) == 0


@pytest.mark.asyncio
async def test_facade_sniffer_creation():
    """Verify sniffer factory on bp.network and bp.mining."""
    page = MockPlaywrightPage()
    bp = BP()
    sniffer = bp.network.create_sniffer(page)
    assert isinstance(sniffer, JSONResponseSniffer)
    sniffer.detach()


@pytest.mark.asyncio
async def test_mcp_extract_metadata_and_sniff_tools():
    """Verify MCP tools for metadata extraction and API sniffing."""
    mock_bp = MagicMock()
    mock_bp.page = AsyncMock()
    mock_bp.page.url = "https://example.com"
    mock_bp.goto = AsyncMock()
    mock_bp.boot = AsyncMock()

    mock_bp.mining = AsyncMock()
    mock_bp.mining.extract_next_data = AsyncMock(return_value={"page": "/home"})
    mock_bp.mining.extract_nuxt_data = AsyncMock(return_value=None)
    mock_bp.mining.extract_json_ld = AsyncMock(return_value=[{"@type": "WebSite"}])
    mock_bp.mining.extract_open_graph = AsyncMock(return_value={"og:title": "Test"})

    mock_sniffer = AsyncMock()
    mock_sniffer.intercept_json = AsyncMock(return_value=[{"data": [1, 2, 3]}])
    mock_sniffer.detach = MagicMock()
    mock_bp.network = MagicMock()
    mock_bp.network.create_sniffer = MagicMock(return_value=mock_sniffer)

    mock_bp.__aenter__ = AsyncMock(return_value=mock_bp)
    mock_bp.__aexit__ = AsyncMock(return_value=None)

    dispatcher = McpToolDispatcher(bp=mock_bp)

    # 1. Test extract_metadata tool
    meta_res = await dispatcher.execute_tool("extract_metadata", {"url": "https://test.com"})
    assert meta_res["status"] == "success"
    assert meta_res["next_data"] == {"page": "/home"}
    assert meta_res["json_ld"] == [{"@type": "WebSite"}]
    assert meta_res["open_graph"] == {"og:title": "Test"}

    # 2. Test sniff_api_responses tool
    sniff_res = await dispatcher.execute_tool(
        "sniff_api_responses",
        {"url_patterns": ["/api/*"], "timeout": 2.0},
    )
    assert sniff_res["status"] == "success"
    assert sniff_res["matched_payloads_count"] == 1
    assert sniff_res["payloads"] == [{"data": [1, 2, 3]}]
