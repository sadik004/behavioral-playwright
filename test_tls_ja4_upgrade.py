"""Deterministic Verification Test Suite: TLS/JA4 & HTTP/2 Impersonation Adapter (curl_cffi).

Asserts:
1. When curl_cffi is present (or mocked), CurlCffiProvider.fetch() executes with
   impersonate="chrome124" and returns the normalized payload dictionary:
   {"status", "headers", "body", "body_bytes", "rtt_ms", "impersonate", "engine": "curl_cffi"}.
2. When curl_cffi is absent, it falls back to standard HTTP without raising ModuleNotFoundError,
   returning {"engine": "urllib_fallback", ...}.
3. ClearanceLease correctly binds and forwards tls_impersonate into BrowserClearanceBridge.fetch_with_promotion().
4. bp.providers.create_network("curl_cffi") and bp.network.fetch_stealth() route seamlessly.
"""

import asyncio
import inspect
import sys
import unittest
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from behavioral_playwright.crawling.clearance_bridge import (
    BrowserClearanceBridge,
    ClearanceLease,
)
from behavioral_playwright.facade import BP
from behavioral_playwright.providers.network import (
    CURL_CFFI_AVAILABLE,
    CurlCffiProvider,
)


class TestTLSJA4Upgrade(unittest.IsolatedAsyncioTestCase):
    """Rigorous verification suite for Architectural Upgrade 2."""

    async def test_1_curl_cffi_impersonate_chrome124_payload(self) -> None:
        """Asserts that CurlCffiProvider executes with impersonate='chrome124' and returns normalized payload."""
        provider = CurlCffiProvider()

        # Mock AsyncSession to test exact parameter forwarding & normalized output deterministically
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "application/json", "server": "cloudflare"}
        mock_resp.text = '{"success": true}'
        mock_resp.content = b'{"success": true}'

        session_mock = MagicMock()
        session_mock.get = AsyncMock(return_value=mock_resp)

        session_ctx_mock = MagicMock()
        session_ctx_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_ctx_mock.__aexit__ = AsyncMock(return_value=None)

        with patch("curl_cffi.requests.AsyncSession", return_value=session_ctx_mock) as mock_cls:
            res = await provider.fetch(
                "https://api.example.com/stealth",
                impersonate="chrome124",
                headers={"X-Stealth-Test": "1"},
                cookies={"session_token": "abc123xyz"},
            )

            # Assert AsyncSession instantiated with impersonate="chrome124" and forwarded cookies
            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args[1]
            self.assertEqual(call_kwargs.get("impersonate"), "chrome124")
            self.assertEqual(call_kwargs.get("cookies"), {"session_token": "abc123xyz"})

            # Assert normalized dictionary contract
            self.assertIsInstance(res, dict)
            self.assertEqual(res["status"], 200)
            self.assertEqual(res["headers"], {"content-type": "application/json", "server": "cloudflare"})
            self.assertEqual(res["body"], '{"success": true}')
            self.assertEqual(res["body_bytes"], b'{"success": true}')
            self.assertEqual(res["impersonate"], "chrome124")
            self.assertEqual(res["engine"], "curl_cffi")
            self.assertIn("rtt_ms", res)
            self.assertGreaterEqual(res["rtt_ms"], 0.0)

    async def test_2_graceful_fallback_when_curl_cffi_absent(self) -> None:
        """Asserts that when curl_cffi is absent, standard urllib fallback executes without crashing on import."""
        provider = CurlCffiProvider(fallback=True)

        # Force absent provider state
        with patch("behavioral_playwright.providers.network.CURL_CFFI_AVAILABLE", False):
            with patch.object(provider, "is_available", return_value=False):
                # Mock urllib execution to avoid external network flake during gate check
                mock_urllib_result = {
                    "status": 200,
                    "headers": {"content-type": "text/html"},
                    "body": "<html><body>Fallback OK</body></html>",
                    "body_bytes": b"<html><body>Fallback OK</body></html>",
                    "rtt_ms": 12.5,
                    "impersonate": "urllib_fallback",
                    "engine": "urllib_fallback",
                }
                with patch.object(provider, "_sync_urllib_fetch", return_value=mock_urllib_result):
                    res = await provider.fetch("https://httpbin.org/get")

                    self.assertIsInstance(res, dict)
                    self.assertEqual(res["engine"], "urllib_fallback")
                    self.assertEqual(res["impersonate"], "urllib_fallback")
                    self.assertEqual(res["status"], 200)
                    self.assertEqual(res["body"], "<html><body>Fallback OK</body></html>")

    async def test_3_clearance_lease_binds_and_forwards_tls_impersonate(self) -> None:
        """Asserts that ClearanceLease stores and forwards tls_impersonate to http_fetcher."""
        lease = ClearanceLease(
            domain="protected-target.com",
            cookies={"cf_clearance": "v1.mocked_clearance_secret"},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0"},
            proxy_url="http://sticky-proxy.internal:8080",
            tls_impersonate="chrome124",
        )
        self.assertEqual(lease.tls_impersonate, "chrome124")

        bridge = BrowserClearanceBridge()
        bridge.store_lease(lease)

        received_impersonate: list[Optional[str]] = []

        async def fake_fetcher(
            url: str,
            headers: Dict[str, str],
            proxy: Optional[str] = None,
            tls_impersonate: Optional[str] = None,
        ) -> Dict[str, Any]:
            received_impersonate.append(tls_impersonate)
            return {
                "status": 200,
                "headers": {"cf-ray": "8371902830-DUB"},
                "body": "Passed Cloudflare",
            }

        async def dummy_solver(url: str) -> ClearanceLease:
            return lease

        result = await bridge.fetch_with_promotion(
            "https://protected-target.com/data",
            http_fetcher=fake_fetcher,
            browser_clearance_solver=dummy_solver,
        )

        self.assertEqual(len(received_impersonate), 1)
        self.assertEqual(received_impersonate[0], "chrome124")
        self.assertEqual(result["execution_tier"], "HTTP_WITH_PROMOTED_CLEARANCE")
        self.assertEqual(result["tls_impersonate"], "chrome124")
        self.assertTrue(result["clearance_reused"])

    async def test_4_facade_bp_network_and_providers_integration(self) -> None:
        """Asserts that bp.providers.create_network and bp.network.fetch_stealth are exposed and functioning."""
        bp = BP()

        # 1. bp.providers.create_network("curl_cffi")
        net_provider = bp.providers.create_network("curl_cffi")
        self.assertIsInstance(net_provider, CurlCffiProvider)

        # 2. bp.network.fetch_stealth signature and mock execution
        self.assertTrue(hasattr(bp.network, "fetch_stealth"))
        self.assertTrue(inspect.iscoroutinefunction(bp.network.fetch_stealth))

        mock_payload = {
            "status": 200,
            "headers": {"content-type": "application/json"},
            "body": "{}",
            "body_bytes": b"{}",
            "rtt_ms": 10.0,
            "impersonate": "chrome124",
            "engine": "curl_cffi",
        }
        with patch.object(CurlCffiProvider, "fetch", return_value=mock_payload):
            resp = await bp.network.fetch_stealth("https://api.example.com", impersonate="chrome124")
            self.assertEqual(resp["engine"], "curl_cffi")
            self.assertEqual(resp["impersonate"], "chrome124")


if __name__ == "__main__":
    unittest.main(verbosity=2)

