"""Tests for Phase 7.2: Shared Authentication and API Resilience Hardening."""

import os
import unittest.mock
import pytest
from behavioral_playwright import BP
from behavioral_playwright.api.client import ApiResponse, AsyncApiClient
from behavioral_playwright.cli.main import build_parser, resolve_cli_config
from behavioral_playwright.config.settings import (
    AuthConfig,
    AutomationConfig,
    CircuitBreakerConfig,
)
from behavioral_playwright.exceptions import CircuitBreakerError
from behavioral_playwright.mcp.server import McpServer
from behavioral_playwright.mcp.tools import McpToolDispatcher
from behavioral_playwright.proxy.models import ProxyNode, ProxyProtocol
from behavioral_playwright.proxy.pool import ProxyPool
from behavioral_playwright.resilience.circuit_breaker import CircuitBreaker, CircuitState


# =====================================================================
# 1. AuthConfig Tests
# =====================================================================

def test_auth_config_default():
    auth = AuthConfig()
    headers = auth.get_headers()
    assert headers == {}


def test_auth_config_explicit_bearer_and_api_key():
    auth = AuthConfig(
        api_key="secret-key-123",
        bearer_token="jwt-token-456",
        custom_headers={"X-Custom-Tenant": "tenant-abc"},
    )
    headers = auth.get_headers()
    assert headers["Authorization"] == "Bearer jwt-token-456"
    assert headers["X-API-Key"] == "secret-key-123"
    assert headers["X-Custom-Tenant"] == "tenant-abc"


def test_auth_config_env_var_resolution(monkeypatch):
    monkeypatch.setenv("BP_API_KEY", "env-api-key")
    monkeypatch.setenv("BP_BEARER_TOKEN", "env-bearer-token")

    auth = AuthConfig()
    resolved = auth.resolve()
    assert resolved.api_key == "env-api-key"
    assert resolved.bearer_token == "env-bearer-token"

    headers = auth.get_headers()
    assert headers["Authorization"] == "Bearer env-bearer-token"
    assert headers["X-API-Key"] == "env-api-key"


def test_auth_config_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("BP_API_KEY", "env-api-key")
    monkeypatch.setenv("BP_BEARER_TOKEN", "env-bearer-token")

    auth = AuthConfig(api_key="explicit-key", bearer_token="explicit-token")
    headers = auth.get_headers()
    assert headers["Authorization"] == "Bearer explicit-token"
    assert headers["X-API-Key"] == "explicit-key"


def test_auth_config_immutability():
    custom = {"X-Trace-ID": "123"}
    auth = AuthConfig(custom_headers=custom, bearer_token="token")
    headers = auth.get_headers()
    headers["Authorization"] = "MUTATED"
    headers["X-Trace-ID"] = "456"
    assert custom["X-Trace-ID"] == "123"
    assert auth.get_headers()["Authorization"] == "Bearer token"


# =====================================================================
# 2. AsyncApiClient Authentication & Headers Tests
# =====================================================================

@pytest.mark.asyncio
async def test_async_api_client_auth_headers_sent():
    auth = AuthConfig(bearer_token="bearer-xyz", custom_headers={"X-Client": "BP"})
    client = AsyncApiClient(auth_config=auth)

    with unittest.mock.patch("urllib.request.build_opener") as mock_opener_builder:
        mock_opener = unittest.mock.MagicMock()
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.read.return_value = b'{"status": "ok"}'
        mock_opener.open.return_value.__enter__.return_value = mock_resp
        mock_opener_builder.return_value = mock_opener

        caller_headers = {"X-Request-ID": "req-999"}
        resp = await client.get("https://api.example.com/data", headers=caller_headers)

        assert resp.status_code == 200
        # Verify request sent to urllib has merged headers
        sent_req = mock_opener.open.call_args[0][0]
        assert sent_req.get_header("Authorization") == "Bearer bearer-xyz"
        assert sent_req.get_header("X-client") == "BP"
        assert sent_req.get_header("X-request-id") == "req-999"
        # Verify caller dictionary was not mutated
        assert "Authorization" not in caller_headers


@pytest.mark.asyncio
async def test_async_api_client_auth_cache_isolation():

    auth1 = AuthConfig(bearer_token="token-user-A")
    auth2 = AuthConfig(bearer_token="token-user-B")

    client1 = AsyncApiClient(auth_config=auth1)
    client2 = AsyncApiClient(auth_config=auth2)

    with unittest.mock.patch("urllib.request.build_opener") as mock_opener_builder:
        mock_opener = unittest.mock.MagicMock()
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.read.return_value = b'{"user": "data"}'
        mock_opener.open.return_value.__enter__.return_value = mock_resp
        mock_opener_builder.return_value = mock_opener

        # User A makes request
        resp1 = await client1.get("https://api.example.com/me")
        assert resp1.status_code == 200
        assert resp1.cached is False

        # User A makes second request -> cached
        resp1_cached = await client1.get("https://api.example.com/me")
        assert resp1_cached.cached is True

        # User B makes request to same URL -> fresh fetch because auth token is different
        resp2 = await client2.get("https://api.example.com/me")
        assert resp2.cached is False


# =====================================================================
# 3. ProxyPool Integration Tests
# =====================================================================


@pytest.mark.asyncio
async def test_async_api_client_proxy_pool_integration():
    pool = ProxyPool()
    node = pool.add_proxy(host="10.0.0.1", port=8080, protocol=ProxyProtocol.HTTP)

    client = AsyncApiClient(proxy_pool=pool)

    with unittest.mock.patch("urllib.request.build_opener") as mock_opener_builder:
        mock_opener = unittest.mock.MagicMock()
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status = 200
        mock_resp.headers = {}
        mock_resp.read.return_value = b'{"success": true}'
        mock_opener.open.return_value.__enter__.return_value = mock_resp
        mock_opener_builder.return_value = mock_opener

        resp = await client.get("https://api.example.com/proxy-test")
        assert resp.status_code == 200
        assert node.total_requests == 1
        assert node.failed_requests == 0


@pytest.mark.asyncio
async def test_async_api_client_proxy_pool_failure_recording():
    pool = ProxyPool()
    node = pool.add_proxy(host="10.0.0.1", port=8080, protocol=ProxyProtocol.HTTP)
    client = AsyncApiClient(proxy_pool=pool)

    with unittest.mock.patch("urllib.request.build_opener") as mock_opener_builder:
        mock_opener = unittest.mock.MagicMock()
        mock_opener.open.side_effect = Exception("Connection refused")
        mock_opener_builder.return_value = mock_opener

        with pytest.raises(Exception, match="Connection refused"):
            await client.get("https://api.example.com/fail-test")

        assert node.failed_requests == 1


# =====================================================================
# 4. CircuitBreaker Integration Tests
# =====================================================================

@pytest.mark.asyncio
async def test_async_api_client_circuit_breaker_open_rejection():
    cb_cfg = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60.0)
    cb = CircuitBreaker(config=cb_cfg)
    client = AsyncApiClient(circuit_breaker=cb)

    with unittest.mock.patch("urllib.request.build_opener") as mock_opener_builder:
        mock_opener = unittest.mock.MagicMock()
        mock_opener.open.side_effect = Exception("Service unavailable")
        mock_opener_builder.return_value = mock_opener

        # 1st failure
        with pytest.raises(Exception):
            await client.get("https://api.example.com/fail")

        # 2nd failure -> trips to OPEN
        with pytest.raises(Exception):
            await client.get("https://api.example.com/fail")

        assert cb.state == CircuitState.OPEN

        # 3rd attempt must be rejected immediately by CircuitBreakerError
        with pytest.raises(CircuitBreakerError, match="CircuitBreaker is OPEN"):
            await client.get("https://api.example.com/fail")


# =====================================================================
# 5. CLI Shared Authentication & Parser Tests
# =====================================================================

def test_cli_parser_auth_flags():
    parser = build_parser()
    parsed = parser.parse_args(["--api-key", "cli-key", "--token", "cli-jwt", "matrix"])
    assert parsed.api_key == "cli-key"
    assert parsed.token == "cli-jwt"
    assert parsed.command == "matrix"

    config = resolve_cli_config(parsed)
    assert config.auth.api_key == "cli-key"
    assert config.auth.bearer_token == "cli-jwt"


def test_cli_parser_env_fallback(monkeypatch):
    monkeypatch.setenv("BP_API_KEY", "env-cli-key")
    monkeypatch.setenv("BP_BEARER_TOKEN", "env-cli-jwt")

    parser = build_parser()
    parsed = parser.parse_args(["matrix"])
    config = resolve_cli_config(parsed)
    assert config.auth.api_key == "env-cli-key"
    assert config.auth.bearer_token == "env-cli-jwt"


# =====================================================================
# 6. MCP Server & Tool Shared Authentication Tests
# =====================================================================

def test_mcp_server_shared_config():
    auth = AuthConfig(api_key="mcp-api-key", bearer_token="mcp-token")
    auto_cfg = AutomationConfig(auth=auth)
    server = McpServer(config=auto_cfg)

    dispatcher_bp = server.dispatcher._get_bp()
    assert dispatcher_bp.config.auth.api_key == "mcp-api-key"
    assert dispatcher_bp.config.auth.bearer_token == "mcp-token"
    assert dispatcher_bp.api.client.auth_config.api_key == "mcp-api-key"
