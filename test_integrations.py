import sys
import json
import urllib.error
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Stub behavioral_playwright packages if not installed in local environment
class MockProviderUnavailableError(Exception):
    pass

class MockProviderError(Exception):
    pass

class MockInvalidRequestError(Exception):
    pass

for mod in [
    'behavioral_playwright',
    'behavioral_playwright.core',
    'behavioral_playwright.core.config',
    'behavioral_playwright.core.exceptions',
    'behavioral_playwright.core.circuit_breaker',
    'behavioral_playwright.core.v10_core',
    'behavioral_playwright.acquisition',
    'behavioral_playwright.acquisition.exceptions',
    'behavioral_playwright.acquisition.models',
    'behavioral_playwright.acquisition.router',
    'behavioral_playwright.acquisition.handoff',
]:
    if mod not in sys.modules:
        m = MagicMock()
        if mod == 'behavioral_playwright.acquisition.exceptions':
            m.ProviderUnavailableError = MockProviderUnavailableError
            m.InvalidRequestError = MockInvalidRequestError
        elif mod == 'behavioral_playwright.core.exceptions':
            m.ProviderError = MockProviderError
        sys.modules[mod] = m

from bp_facade12 import BP


def test_webhook_invalid_url_raises_valueerror():
    """Verify that an invalid webhook URL raises ValueError."""
    bp = BP()
    with pytest.raises(ValueError, match="Invalid webhook URL schema"):
        bp.integrations.n8n_webhook_trigger("invalid_schema_url", {"data": 123})


def test_n8n_webhook_trigger_success():
    """Verify n8n webhook issues real HTTP POST with json payload."""
    bp = BP()
    mock_resp = MagicMock(status=200)
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    payload = {"event": "crawl_completed", "urls_count": 42}
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        res = bp.integrations.n8n_webhook_trigger("https://n8n.local/webhook/test", payload)
        assert res is True
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.get_method() == "POST"
        assert json.loads(req.data.decode("utf-8")) == payload
        assert req.get_header("Content-type") == "application/json"


def test_slack_webhook_notify_success():
    """Verify Slack webhook formats {'text': message} and posts payload."""
    bp = BP()
    mock_resp = MagicMock(status=200)
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        res = bp.integrations.slack_webhook_notify("https://hooks.slack.com/services/T/B/X", "Crawl Finished")
        assert res is True
        req = mock_urlopen.call_args[0][0]
        assert json.loads(req.data.decode("utf-8")) == {"text": "Crawl Finished"}


def test_discord_webhook_notify_success():
    """Verify Discord webhook formats {'content': message} and posts payload."""
    bp = BP()
    mock_resp = MagicMock(status=204)
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        res = bp.integrations.discord_webhook_notify("https://discord.com/api/webhooks/123/abc", "Alert message")
        assert res is True
        req = mock_urlopen.call_args[0][0]
        assert json.loads(req.data.decode("utf-8")) == {"content": "Alert message"}


def test_webhook_error_propagation():
    """Verify webhook network failure propagates exception."""
    bp = BP()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(urllib.error.URLError):
            bp.integrations.slack_webhook_notify("https://hooks.slack.com/fail", "Test")


@pytest.mark.asyncio
async def test_mcp_call_tool_real_scrape_delegation():
    """Verify mcp_call_tool delegates scrape to bp.web.scrape."""
    bp = BP()
    mock_result = MagicMock(content="<html><body>Scraped content</body></html>")
    bp.web.scrape = AsyncMock(return_value=mock_result)

    res = await bp.integrations.mcp_call_tool_async("scrape", {"url": "https://example.com"})
    assert res["status"] == "success"
    assert res["tool"] == "scrape"
    assert "Scraped content" in res["content"]
    bp.web.scrape.assert_awaited_once_with("https://example.com", options=None)


@pytest.mark.asyncio
async def test_mcp_call_tool_unknown_tool_returns_error():
    """Verify unknown tool name returns structured error dictionary."""
    bp = BP()
    res = await bp.integrations.mcp_call_tool_async("non_existent_tool", {"param": 1})
    assert res["status"] == "error"
    assert "Unknown tool" in res["error"]


def test_generate_mcp_manifest():
    """Verify MCP manifest structure and tools."""
    bp = BP()
    manifest = bp.integrations.generate_mcp_manifest()
    assert manifest["mcp_version"] == "1.0.0"
    tool_names = [t["name"] for t in manifest["tools"]]
    assert "scrape" in tool_names
    assert "crawl" in tool_names


@pytest.mark.asyncio
async def test_top_level_bp_integrations_delegation():
    """Verify top-level BP integration methods delegate cleanly."""
    bp = BP()
    mock_resp = MagicMock(status=200)
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res1 = await bp.slack_webhook_notify("https://hooks.slack.com/test", "Hello")
        assert res1 is True

        res2 = await bp.discord_webhook_notify("https://discord.com/webhook", "Hello")
        assert res2 is True

        res3 = await bp.n8n_webhook_trigger("https://n8n.local/webhook", {"k": "v"})
        assert res3 is True

    mock_scrape_res = MagicMock(content="Hello MCP")
    bp.web.scrape = AsyncMock(return_value=mock_scrape_res)
    mcp_res = await bp.mcp_call_tool("scrape", {"url": "https://mcp.test"})
    assert mcp_res["status"] == "success"
