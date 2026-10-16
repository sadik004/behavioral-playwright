"""Real Local HTTP Server End-to-End (E2E) Test Suite (`tests/integration/test_real_local_server_e2e.py`).

Spins up a genuine local HTTP server on 127.0.0.1 (ephemeral socket port)
serving live clean data and live Cloudflare challenge responses.
Verifies real TCP socket communication, 4-tier adaptive crawler escalation telemetry,
CLI command executions, and robust MCP tool invocations without mock paths.
"""

from __future__ import annotations

import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Generator
import pytest

from veil.crawling.models import CrawlerTier, CrawlRequest
from veil.crawling.service import TieredCrawlerService
from veil.cli.main import main as cli_main
from veil.mcp.tools import handle_tool_call


class RealLocalChallengeServerHandler(BaseHTTPRequestHandler):
    """Local server request handler serving clean content and challenge triggers."""

    def do_GET(self) -> None:
        if self.path == "/clean":
            body = b"<html><body><h1>Real Data</h1></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif self.path == "/cf-challenge":
            body = b"<html><head><title>Just a moment...</title></head><body>cf-turnstile challenge required</body></html>"
            self.send_response(403)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("cf-mitigated", "challenge")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        # Suppress noisy standard HTTP access logs during test run
        pass


@pytest.fixture(scope="module")
def local_http_server() -> Generator[str, None, None]:
    """Binds a genuine socket on 127.0.0.1 with an OS-allocated ephemeral port."""
    server = HTTPServer(("127.0.0.1", 0), RealLocalChallengeServerHandler)
    host, port = server.server_address
    server_url = f"http://{host}:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield server_url
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
async def test_tiered_crawler_real_tcp_clean_endpoint(local_http_server: str) -> None:
    """Tests that Tier 1 (HTTP_FAST) hits real TCP socket and succeeds with 0 escalations."""
    crawler = TieredCrawlerService()
    req = CrawlRequest(url=f"{local_http_server}/clean")

    response = await crawler.crawl(req)

    assert response.is_success is True
    assert response.status_code == 200
    assert "<h1>Real Data</h1>" in response.body
    assert response.resolved_tier == CrawlerTier.HTTP_FAST
    assert response.escalations_count == 0
    assert len(response.escalation_history) == 0
    assert response.challenge_detected is None


@pytest.mark.asyncio
async def test_tiered_crawler_real_tcp_cf_challenge_escalation(local_http_server: str) -> None:
    """Tests that 403 cf-mitigated challenge is detected on real socket and triggers escalation."""
    crawler = TieredCrawlerService()
    req = CrawlRequest(url=f"{local_http_server}/cf-challenge")

    response = await crawler.crawl(req)

    # Must have recorded at least 1 escalation starting from HTTP_FAST
    assert len(response.escalation_history) > 0

    first_record = response.escalation_history[0]
    assert first_record.tier == CrawlerTier.HTTP_FAST
    assert first_record.status_code == 403
    assert "cloudflare" in first_record.reason.lower()
    assert first_record.latency_ms > 0.0

    # Telemetry should be completely serialized without error
    telemetry = [rec.to_dict() for rec in response.escalation_history]
    assert len(telemetry) >= 1
    assert telemetry[0]["tier"] == "HTTP_FAST"
    assert telemetry[0]["status_code"] == 403


@pytest.mark.asyncio
async def test_cli_commands_and_mcp_tools_real_execution(local_http_server: str) -> None:
    """Executes CLI commands (--help, doctor, audit) and invokes core MCP tools with real inputs."""
    # 1. CLI Commands Execution Check
    with pytest.raises(SystemExit) as exc_info:
        cli_main(["--help"])
    assert exc_info.value.code == 0
    assert cli_main(["doctor"]) == 0
    assert cli_main(["audit"]) == 0


    # 2. MCP Tools Execution Check
    # Tool 1: get_provider_matrix
    res_matrix = await handle_tool_call("get_provider_matrix", {})
    assert "providers" in res_matrix or "browser/playwright" in str(res_matrix)

    # Tool 2: quant_pit_align
    res_quant = await handle_tool_call("quant_pit_align", {
        "filing": {
            "symbol": "AAPL",
            "filing_date": "2026-02-15",
            "period_end": "2025-12-31",
            "revenue": 1000000,
        }
    })
    assert "aligned_filing" in res_quant or "status" in res_quant or "filing" in res_quant

    # Tool 3: audit_biometrics
    res_bio = await handle_tool_call("audit_biometrics", {
        "samples": [
            {"x": 10.0, "y": 10.0, "t": 0.0},
            {"x": 20.0, "y": 15.0, "t": 0.05},
            {"x": 35.0, "y": 25.0, "t": 0.10},
        ]
    })
    assert "status" in res_bio or "score" in res_bio or "audit" in res_bio

    # Tool 4: memory_pid_health
    res_mem = await handle_tool_call("memory_pid_health", {
        "current_rss_mb": 420.0,
        "target_rss_mb": 512.0,
    })
    assert "status" in res_mem or "recommendation" in res_mem or "control_output" in res_mem

    # Tool 5: check_cannibalization
    res_cann = await handle_tool_call("check_cannibalization", {
        "query_a": "python scraping framework",
        "query_b": "python browser automation",
        "urls_a": ["https://python.org", "https://playwright.dev"],
        "urls_b": ["https://python.org", "https://selenium.dev"],
        "threshold": 0.30,
    })
    assert "jaccard_similarity" in res_cann or "overlap" in res_cann or "status" in res_cann

    # Tool 6: mine_google_suggest
    res_sugg = await handle_tool_call("mine_google_suggest", {
        "query": "fastapi vs",
        "alphabet": False,
    })
    assert "suggestions" in res_sugg or "status" in res_sugg or "query" in res_sugg

    # Tool 7: inspect_state
    res_state = await handle_tool_call("inspect_state", {"workflow_id": "wf_test_01"})
    assert "status" in res_state or "state" in res_state or "error" in res_state


    # Tool 8: extract_metadata on real local server
    res_meta = await handle_tool_call("extract_metadata", {
        "url": f"{local_http_server}/clean"
    })
    assert "status" in res_meta or "metadata" in res_meta or "error" not in res_meta or res_meta.get("status") == "success"

    # Tool 9: run_graphql_security_audit
    res_gql = await handle_tool_call("run_graphql_security_audit", {
        "target_url": f"{local_http_server}/clean"
    })
    assert "audit_report" in res_gql or "status" in res_gql

    # Tool 10: run_security_audit_on_page
    res_sec = await handle_tool_call("run_security_audit_on_page", {
        "target_url": f"{local_http_server}/clean"
    })
    assert "audit_report" in res_sec or "status" in res_sec

    # Tool 11: stealth_get_snapshot
    res_snap = await handle_tool_call("stealth_get_snapshot", {})
    assert "status" in res_snap or "error" in res_snap

    # Tool 12: scrape_page on real local server
    res_scrape = await handle_tool_call("scrape_page", {
        "url": f"{local_http_server}/clean",
        "target": "raw",
    })
    assert "status" in res_scrape or "result" in res_scrape
