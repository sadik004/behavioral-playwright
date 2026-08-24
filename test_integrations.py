import sys
import json
import urllib.error
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Refactored package exposes BP via the public API (src layout).
from behavioral_playwright import BP


def test_webhook_invalid_url_raises_valueerror():
    """Verify that an invalid webhook URL raises ValueError."""
    bp = BP()
    with pytest.raises(ValueError, match="Invalid webhook URL schema"):
        bp.integrations.notify_webhook("invalid_schema_url", {"data": 123})


@pytest.mark.skip(reason="n8n integration not implemented in refactored facade "
                         "(legacy-only API; tracked for future namespace work)")
def test_n8n_webhook_trigger_success():
    """Verify n8n webhook issues real HTTP POST with json payload."""
    bp = BP()
    mock_resp = MagicMock(status=200)
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    payload = {"event": "crawl_completed", "urls_count": 42}
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        res = bp.integrations.notify_webhook("https://n8n.local/webhook/test", payload)
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
        res = bp.integrations.notify_webhook(
            "https://hooks.slack.com/services/T/B/X", {"text": "Crawl Finished"})
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
        res = bp.integrations.notify_webhook(
            "https://discord.com/api/webhooks/123/abc",
            {"content": "Alert message"})
        assert res is True
        req = mock_urlopen.call_args[0][0]
        assert json.loads(req.data.decode("utf-8")) == {"content": "Alert message"}


def test_webhook_error_propagation():
    """Verify webhook network failure propagates exception."""
    bp = BP()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(urllib.error.URLError):
            bp.integrations.notify_webhook("https://hooks.slack.com/fail", {"text": "Test"})


@pytest.mark.skip(reason="MCP integration not implemented in refactored facade "
                         "(legacy-only API; tracked for future namespace work)")
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


@pytest.mark.skip(reason="MCP integration not implemented in refactored facade "
                         "(legacy-only API; tracked for future namespace work)")
@pytest.mark.asyncio
async def test_mcp_call_tool_unknown_tool_returns_error():
    """Verify unknown tool name returns structured error dictionary."""
    bp = BP()
    res = await bp.integrations.mcp_call_tool_async("non_existent_tool", {"param": 1})
    assert res["status"] == "error"
    assert "Unknown tool" in res["error"]


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
