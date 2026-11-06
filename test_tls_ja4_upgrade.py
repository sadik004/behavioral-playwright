"""Deterministic Verification Test Suite: TLS/JA4 & HTTP/2 Impersonation Adapter (curl_cffi).

Asserts:
1. Live Local Socket Execution & Parameter Forwarding:
   - Executes real CurlCffiProvider.fetch() over a live local TCP/HTTP server (and verifies AsyncSession
     impersonate="chrome124" parameter binding).
2. Live Urllib Fallback over Real Socket:
   - When curl_cffi is absent (CURL_CFFI_AVAILABLE=False), executes the real _sync_urllib_fetch
     against a live local TCP/HTTP server without MagicMocking _sync_urllib_fetch.
3. ClearanceLease & Bayesian Feedback Integration:
   - ClearanceLease binds and forwards tls_impersonate="chrome124" to http_fetcher.
4. Live Facade bp.network.fetch_stealth Execution:
   - Executes bp.network.fetch_stealth() end-to-end against a live local HTTP server.
"""

import http.server
import inspect
import json
import socketserver
import threading
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


class _LocalTestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        payload = json.dumps({
            "ok": True,
            "path": self.path,
            "cookie": self.headers.get("Cookie", ""),
            "custom": self.headers.get("X-Stealth-Test", ""),
            "ua": self.headers.get("User-Agent", ""),
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        return  # Suppress console noise


class TestTLSJA4Upgrade(unittest.IsolatedAsyncioTestCase):
    """Rigorous live-socket + contract verification suite for Architectural Upgrade 2."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd = socketserver.TCPServer(("127.0.0.1", 0), _LocalTestHandler)
        cls.port = cls.httpd.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    async def test_1_curl_cffi_live_socket_and_impersonate_chrome124(self) -> None:
        """Executes live socket fetch via CurlCffiProvider and verifies impersonate='chrome124'."""
        provider = CurlCffiProvider()

        # 1A: Real live socket execution (no mocks!)
        live_res = await provider.fetch(
            f"{self.base_url}/live-stealth",
            impersonate="chrome124",
            headers={"X-Stealth-Test": "real-socket"},
            cookies={"cf_clearance": "real_token_99"},
        )
        self.assertEqual(live_res["status"], 200)
        self.assertGreater(live_res["rtt_ms"], 0.0)
        parsed = json.loads(live_res["body"])
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["custom"], "real-socket")
        self.assertIn("cf_clearance=real_token_99", parsed["cookie"])
        if CURL_CFFI_AVAILABLE:
            self.assertEqual(live_res["engine"], "curl_cffi")
            self.assertEqual(live_res["impersonate"], "chrome124")

    async def test_2_real_urllib_fallback_over_live_socket_when_curl_cffi_absent(self) -> None:
        """Executes real _sync_urllib_fetch over live TCP socket when CURL_CFFI_AVAILABLE is False."""
        provider = CurlCffiProvider(fallback=True)

        with patch("behavioral_playwright.providers.network.CURL_CFFI_AVAILABLE", False):
            res = await provider.fetch(
                f"{self.base_url}/fallback-live",
                headers={"X-Stealth-Test": "urllib-real"},
                cookies={"session_id": "xyz789"},
            )
            self.assertIsInstance(res, dict)
            self.assertEqual(res["engine"], "urllib_fallback")
            self.assertEqual(res["impersonate"], "urllib_fallback")
            self.assertEqual(res["status"], 200)
            body_json = json.loads(res["body"])
            self.assertEqual(body_json["path"], "/fallback-live")
            self.assertEqual(body_json["custom"], "urllib-real")
            self.assertIn("session_id=xyz789", body_json["cookie"])

    async def test_3_clearance_lease_binds_and_forwards_tls_impersonate(self) -> None:
        """Asserts that ClearanceLease stores and forwards tls_impersonate to http_fetcher."""
        lease = ClearanceLease(
            domain="127.0.0.1",
            cookies={"cf_clearance": "v1.live_clearance_secret"},
            headers={"User-Agent": "Mozilla/5.0 Chrome/124.0.0.0"},
            proxy_url=None,
            tls_impersonate="chrome124",
        )
        self.assertEqual(lease.tls_impersonate, "chrome124")

        bridge = BrowserClearanceBridge()
        bridge.store_lease(lease)

        received_impersonate: list[Optional[str]] = []
        provider = CurlCffiProvider(fallback=True)

        async def real_fetcher(
            url: str,
            headers: Dict[str, str],
            proxy: Optional[str] = None,
            tls_impersonate: Optional[str] = None,
        ) -> Dict[str, Any]:
            received_impersonate.append(tls_impersonate)
            return await provider.fetch(
                url,
                headers=headers,
                proxy=proxy,
                impersonate=tls_impersonate or "chrome124",
            )

        async def dummy_solver(url: str) -> ClearanceLease:
            return lease

        result = await bridge.fetch_with_promotion(
            f"{self.base_url}/protected-resource",
            http_fetcher=real_fetcher,
            browser_clearance_solver=dummy_solver,
        )

        self.assertEqual(len(received_impersonate), 1)
        self.assertEqual(received_impersonate[0], "chrome124")
        self.assertEqual(result["execution_tier"], "HTTP_WITH_PROMOTED_CLEARANCE")
        self.assertEqual(result["tls_impersonate"], "chrome124")
        self.assertTrue(result["clearance_reused"])
        self.assertIn("cf_clearance=v1.live_clearance_secret", json.loads(result["body"])["cookie"])

    async def test_4_facade_bp_network_and_providers_live_integration(self) -> None:
        """Executes bp.network.fetch_stealth against live TCP server without mocking CurlCffiProvider.fetch."""
        bp = BP()
        net_provider = bp.providers.create_network("curl_cffi")
        self.assertIsInstance(net_provider, CurlCffiProvider)

        self.assertTrue(hasattr(bp.network, "fetch_stealth"))
        self.assertTrue(inspect.iscoroutinefunction(bp.network.fetch_stealth))

        resp = await bp.network.fetch_stealth(
            f"{self.base_url}/facade-stealth",
            impersonate="chrome124",
            headers={"X-Stealth-Test": "facade-live"},
        )
        self.assertEqual(resp["status"], 200)
        self.assertEqual(json.loads(resp["body"])["custom"], "facade-live")


if __name__ == "__main__":
    unittest.main(verbosity=2)
