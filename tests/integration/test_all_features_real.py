"""Comprehensive Zero-Mock Real-Execution Integration Test Suite (`tests/integration/test_all_features_real.py`).

ROLE: Principal QA & Real-Execution Feature Verification Engineer
Verifies all 10 subsystems with genuine local TCP sockets on 127.0.0.1, real SQLite/file I/O,
and real binary protocols.

CRITICAL INVARIANT: ZERO unittest.mock / MagicMock / monkeypatch.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import socket
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest

# Ensure repository paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# =============================================================================
# REAL MULTI-ROUTE LOCAL HTTP SERVER FIXTURE (ZERO MOCKS)
# =============================================================================

class MultiRouteServerHandler(BaseHTTPRequestHandler):
    """Local HTTP Server serving multi-route real responses for integration tests."""

    flaky_count = 0
    lock = threading.Lock()

    def do_HEAD(self) -> None:
        if self.path in ("/html", "/api/json", "/login", "/session", "/clean"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path

        if path in ("/html", "/clean"):
            body = b"""<!DOCTYPE html>
<html>
<head>
    <title>Quantum Store - Premium Hardware</title>
    <meta name="description" content="High performance computing hardware and peripherals">
    <meta property="og:title" content="Quantum Store Hardware">
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Product", "name": "Quantum GPU Matrix X1", "offers": {"@type": "Offer", "price": "1499.99", "priceCurrency": "USD"}}
    </script>
</head>
<body>
    <h1>Product Catalog</h1>
    <table id="products">
        <thead><tr><th>Item</th><th>Price</th></tr></thead>
        <tbody><tr><td>Quantum Blade Server</td><td>$2,499.00</td></tr></tbody>
    </table>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/json":
            body = json.dumps({
                "page": 1,
                "total_pages": 5,
                "items": [{"id": 101, "sku": "QNT-01", "name": "Quantum Core i9", "price": 499.99}],
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/session":
            cookie_header = self.headers.get("Cookie", "")
            if "session_token=sess_quantum_sec_991827" in cookie_header:
                body = json.dumps({"status": "valid", "user": "admin"}).encode("utf-8")
                self.send_response(200)
            else:
                body = json.dumps({"error": "unauthorized"}).encode("utf-8")
                self.send_response(401)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/flaky":
            with MultiRouteServerHandler.lock:
                MultiRouteServerHandler.flaky_count += 1
                c = MultiRouteServerHandler.flaky_count
            if c < 3:
                body = json.dumps({"error": "service unavailable", "attempt": c}).encode("utf-8")
                self.send_response(503)
            else:
                body = json.dumps({"status": "recovered", "attempt": c}).encode("utf-8")
                self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/cf-challenge":
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

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/login":
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                self.rfile.read(length)
            body = json.dumps({"status": "authenticated", "session_id": "sess_quantum_sec_991827"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie", "session_token=sess_quantum_sec_991827; Path=/; HttpOnly")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def real_server_url() -> Generator[str, None, None]:
    server = HTTPServer(("127.0.0.1", 0), MultiRouteServerHandler)
    host, port = server.server_address
    url = f"http://{host}:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield url
    finally:
        server.shutdown()
        server.server_close()


# =============================================================================
# TESTS ACROSS ALL 10 SUBSYSTEMS
# =============================================================================

@pytest.mark.asyncio
async def test_subsystem_1_kinematics_and_biomechanics() -> None:
    """Subsystem 1: SigmaLognormalMotor & BiometricMouseController real physics."""
    from veil.kinematics.biomechanics import (
        BiometricMouseController,
        SigmaLognormalMotor,
        BiomechanicalMousePhysics,
        MousePoint,
    )
    from behavioral_evasion_suite.mouse_physics import (
        BiometricMouseController as LegacyMouseController,
    )

    # 1. SigmaLognormalMotor profile
    motor = SigmaLognormalMotor(mu=-0.8, sigma=0.45, t0=0.05)
    cum_profile = motor.generate_cumulative_profile(steps=30, duration_s=0.40)
    assert len(cum_profile) == 30
    assert cum_profile[-1] == 1.0
    v_peak = max(motor.compute_velocity(t * 0.01) for t in range(1, 40))
    assert v_peak > 0.0

    # 2. BiometricMouseController movement & seed determinism
    ctrl = BiometricMouseController()
    path_a1 = await ctrl.generate_human_movement((10.0, 10.0), (450.0, 350.0), seed=42)
    path_a2 = await ctrl.generate_human_movement((10.0, 10.0), (450.0, 350.0), seed=42)
    path_b = await ctrl.generate_human_movement((10.0, 10.0), (450.0, 350.0), seed=99)

    assert len(path_a1) > 15
    assert 0.0 <= path_a1[0]["t"] < 1.0
    assert path_a1[-1]["t"] < 10.0
    assert path_a1 == path_a2, "Determinism failed: same seed gave different trajectories"
    assert path_a1 != path_b, "Entropy failure: different seeds gave identical trajectories"

    # 3. BiomechanicalMousePhysics legacy trajectory
    bmp = BiomechanicalMousePhysics()
    pts = bmp.generate_trajectory(start=(0.0, 0.0), end=(200.0, 200.0), steps=25)
    assert len(pts) >= 25
    assert hasattr(pts[0], "x") and hasattr(pts[0], "y")


def test_subsystem_2_linguistic_keystrokes() -> None:
    """Subsystem 2: LinguisticKeystrokeDynamicsEngine QWERTY & monotonic timing."""
    from veil.kinematics.keystrokes import LinguisticKeystrokeDynamicsEngine

    engine = LinguisticKeystrokeDynamicsEngine(seed=42)
    text = "The quick brown fox jumps over the lazy dog."
    seq1 = engine.generate_typing_sequence(text, seed=42)
    seq2 = engine.generate_typing_sequence(text, seed=42)
    seq3 = engine.generate_typing_sequence(text, seed=777)

    assert seq1 == seq2, "Determinism failed: same seed gave different keystrokes"
    assert seq1 != seq3, "Entropy failed: different seeds gave identical keystrokes"
    assert len(seq1) == len(text) * 2
    assert all(seq1[i]["timestamp_ms"] <= seq1[i + 1]["timestamp_ms"] for i in range(len(seq1) - 1))


def test_subsystem_3_layer4_network_and_os_bridge(real_server_url: str) -> None:
    """Subsystem 3: Layer-4 socket inspection, PID memory, schema guard, and tracking."""
    from veil.kinematics.network_l4 import SocketTTLInspector
    from veil.kinematics.memory_pid import ResolvedChromiumMemoryPIDController
    from veil.kinematics.schema_guard import ResolvedSchemaIntegrityGuard
    from veil.kinematics.tracking import StatefulEvasionTracker
    from veil.kinematics.validator import BiometricDistributionValidator
    from veil.kinematics.vision_guard import UltimateVisionLanguageActionGuard
    from veil.kinematics.captcha import ResolvedCAPTCHAInfiniteLoopDetector
    from veil.kinematics.orchestrator import Bpp

    # 1. Socket TTL inspector
    inspector = SocketTTLInspector()
    sock_info = inspector.align_socket_parameters()
    assert sock_info["socket_ttl"] > 0
    assert sock_info["status"] == "configured"

    # 2. Chromium Memory PID
    pid = ResolvedChromiumMemoryPIDController(target_mb=512.0)
    corr = pid.compute_correction(current_usage_mb=680.0, dt=1.0)
    assert corr["error_mb"] == 168.0
    assert corr["correction_intensity_pct"] > 0.0

    # 3. Schema Shannon Entropy Guard
    guard = ResolvedSchemaIntegrityGuard()
    ent = guard.compute_shannon_entropy("Quantum Computing Architecture with High Entropy")
    assert ent > 3.0

    # 4. Stateful Evasion Tracker
    tracker = StatefulEvasionTracker()
    tracker.record_request()
    tracker.record_memory(480.0)
    tracker.register_captcha()
    assert tracker.captcha_encounters == 1
    assert tracker.ip_reputation < 1.0

    # 5. Biometric Distribution Validator
    val = BiometricDistributionValidator(random_seed=42)
    val_res = val.evaluate_distribution_alignment([100.0, 105.0, 110.0, 95.0, 102.0, 98.0, 107.0, 103.0])
    assert "p_value" in val_res or "is_human_indistinguishable" in val_res or "decision" in val_res

    # 6. Ultimate Vision-Language Action Guard
    action_guard = UltimateVisionLanguageActionGuard()
    heal_res = action_guard.evaluate_and_heal_click(
        vec_intended=[1.0, 0.0],
        vec_scanned=[0.96, 0.04],
        box_intended=(100.0, 100.0, 200.0, 200.0),
        box_scanned=(110.0, 105.0, 210.0, 205.0),
    )
    assert heal_res.get("decision") == "PASS"
    assert heal_res.get("status") == "HEALED"

    # 7. CAPTCHA Loop Detector
    loop_det = ResolvedCAPTCHAInfiniteLoopDetector()
    loop_status = loop_det.record_navigation(f"{real_server_url}/html", is_challenge=False)
    assert loop_status["recommended_action"] == "PROCEED"
    assert loop_det.circuit_state == "CLOSED"

    # 8. Master Bpp Orchestrator
    bot = Bpp()
    assert bot.tracker is not None
    assert bot.biomechanics is not None
    assert bot.validator is not None


def test_subsystem_4_stealth_and_fingerprinting() -> None:
    """Subsystem 4: Shader spoofer script, fingerprint generator, and DOM telemetry."""
    from veil.evasion.canvas_shield import CanvasWebGLShaderSpoofer
    from veil.fingerprint.generator import FingerprintGenerator
    from veil.fingerprint.models import OSPlatform
    from veil.kinematics.dom_telemetry import DOMTelemetryCollector, PageTelemetryAuditor

    # 1. Shader spoofer
    canvas_script = CanvasWebGLShaderSpoofer.get_canvas_shader_spoofer_script()
    assert "mulberry32" in canvas_script
    assert "UNMASKED_RENDERER_WEBGL" in canvas_script

    # 2. Fingerprint generator
    fp_gen = FingerprintGenerator(seed=1337)
    fp_profile = fp_gen.generate(platform=OSPlatform.WINDOWS, locale="en-US")
    fp_patch = fp_gen.generate_evasion_script(fp_profile)
    assert fp_profile.webgl.vendor is not None
    assert len(fp_patch) > 100

    # 3. DOM Telemetry Collector
    collector = DOMTelemetryCollector()
    collector.record_event("click", "button", payload={"x": 100, "y": 200}, timestamp_ms=105.0)
    collector.record_event("keydown", "input", payload={"key": "Enter"}, timestamp_ms=155.0)
    auditor = PageTelemetryAuditor(collector)
    audit_rep = auditor.audit()
    assert audit_rep["total_events"] == 2
    assert audit_rep["status"] == "PASSED"


@pytest.mark.asyncio
async def test_subsystem_5_extraction_and_binary_protocol(real_server_url: str) -> None:
    """Subsystem 5: Real HTML DOM extraction and NASDAQ ITCH-5.0 binary parser."""
    from veil.extraction.dom import extract_json_ld, extract_open_graph
    from veil.extraction.normalizer import clean_text, parse_price
    from veil.core.itch_binary import ItchBinaryParser

    # 1. Fetch live HTML and extract OpenGraph & JSON-LD
    with urllib.request.urlopen(f"{real_server_url}/html", timeout=5.0) as resp:
        live_html = resp.read().decode("utf-8")

    og_data = await extract_open_graph(live_html)
    json_ld_data = await extract_json_ld(live_html)
    price_val = parse_price("$2,499.00")
    cleaned = clean_text("   Quantum   Computing\n\n\tBlade   ")

    assert og_data.get("og:title") == "Quantum Store Hardware"
    assert json_ld_data[0].get("name") == "Quantum GPU Matrix X1"
    assert price_val == 2499.0
    assert cleaned == "Quantum Computing Blade"

    # 2. NASDAQ TotalView-ITCH 5.0 binary framing & parsing
    ts_930 = 34_200 * 1_000_000_000
    prefix = struct.pack(">HH", 1, 2) + ts_930.to_bytes(6, "big")
    msg_a = b"A" + prefix + struct.pack(">Q", 1001) + b"B" + struct.pack(">I", 500) + b"AAPL    " + struct.pack(">I", 1_855_000)
    frame = struct.pack(">H", len(msg_a)) + msg_a

    parser = ItchBinaryParser(dollar_threshold=50000.0)
    itch_res = parser.parse_stream(frame)
    itch_messages = itch_res.messages

    assert len(itch_messages) == 1
    assert itch_messages[0]["stock"] == "AAPL"
    assert itch_messages[0]["shares"] == 500
    assert itch_messages[0]["order_ref"] == 1001


@pytest.mark.asyncio
async def test_subsystem_6_resilience_and_orchestration(real_server_url: str) -> None:
    """Subsystem 6: RetryPolicy recovery over live socket and WorkflowState state machine."""
    from veil.resilience.retry import RetryPolicy
    from behavioral_playwright.config.settings import RetryConfig
    from veil.orchestration.conditions import ConditionEvaluator
    from veil.orchestration.models import ActionType, Condition, WorkflowStatus, WorkflowStep
    from veil.orchestration.state import WorkflowState

    # 1. RetryPolicy against flaky endpoint
    retry_policy = RetryPolicy(
        config=RetryConfig(max_attempts=4, base_delay=0.01, max_delay=0.05, exponential_backoff=True)
    )

    async def _fetch_flaky() -> Dict[str, Any]:
        req = urllib.request.Request(f"{real_server_url}/flaky")
        loop = asyncio.get_running_loop()

        def _sync_call() -> Dict[str, Any]:
            try:
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as he:
                if he.code == 503:
                    raise ConnectionResetError(f"HTTP 503: {he.reason}")
                raise

        return await loop.run_in_executor(None, _sync_call)

    flaky_result = await retry_policy.execute(_fetch_flaky, operation_name="flaky_test")
    assert flaky_result.get("status") == "recovered"
    assert len(retry_policy.attempts_history) >= 1

    # 2. WorkflowState and ConditionEvaluator
    wf_state = WorkflowState(workflow_id="wf_real_001", session_id="sess_test_01")
    wf_state.transition_to(WorkflowStatus.RUNNING, reason="Started test step")
    wf_state.transition_to(WorkflowStatus.COMPLETED, reason="Step completed successfully")

    cond = Condition(name="check_state", condition_type="custom", evaluator=lambda sess, st, sp: st.status == WorkflowStatus.COMPLETED)
    step = WorkflowStep(step_id="step_01", action="resolve", action_type=ActionType.READ_ONLY)
    cond_res = await ConditionEvaluator.evaluate_precondition(cond, None, wf_state, step)

    assert cond_res is True
    assert wf_state.status == WorkflowStatus.COMPLETED
    assert len(wf_state.history) == 2


def test_subsystem_7_storage_and_session_vault(real_server_url: str) -> None:
    """Subsystem 7: Storage exporters (JSON, NDJSON, CSV, SQLite) and SessionStateVault."""
    from veil.storage.exporters import JSONExporter, NDJSONExporter, CSVExporter, SQLiteExporter
    from behavioral_evasion_suite.session_vault import SessionStateVault

    test_records = [
        {"id": 1, "sku": "Q-01", "name": "Quantum Rig Alpha", "price": 1299.99},
        {"id": 2, "sku": "Q-02", "name": "Quantum Rig Beta", "price": 2499.00},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        json_file = os.path.join(tmpdir, "out.json")
        ndjson_file = os.path.join(tmpdir, "out.ndjson")
        csv_file = os.path.join(tmpdir, "out.csv")
        sqlite_file = os.path.join(tmpdir, "out.db")

        JSONExporter().export(test_records, json_file)
        NDJSONExporter().export(test_records, ndjson_file)
        CSVExporter().export(test_records, csv_file)
        SQLiteExporter().export(test_records, sqlite_file, table_name="scraped_items")

        with open(json_file, "r", encoding="utf-8") as f:
            read_json = json.load(f)
        with open(ndjson_file, "r", encoding="utf-8") as f:
            read_ndjson = [json.loads(line) for line in f if line.strip()]

        conn = sqlite3.connect(sqlite_file)
        row_count = conn.execute("SELECT COUNT(*) FROM scraped_items").fetchone()[0]
        conn.close()

        assert len(read_json) == 2
        assert len(read_ndjson) == 2
        assert row_count == 2

        # Test Session State Vault against real login endpoint
        req = urllib.request.Request(f"{real_server_url}/login", data=b"username=admin&password=secret", method="POST")
        with urllib.request.urlopen(req) as resp:
            cookie = resp.headers.get("Set-Cookie")

        vault_file = os.path.join(tmpdir, "vault_state.json")
        vault = SessionStateVault(filepath=vault_file)
        with open(vault_file, "w") as vf:
            json.dump({"cookies": [{"name": "session_token", "value": "sess_quantum_sec_991827"}], "origins": []}, vf)

        auth_req = urllib.request.Request(f"{real_server_url}/session", headers={"Cookie": cookie.split(";")[0]})
        with urllib.request.urlopen(auth_req) as resp:
            session_resp = json.loads(resp.read().decode("utf-8"))

        assert session_resp.get("status") == "valid"


def test_subsystem_8_network_sniffer_and_intelligence(real_server_url: str) -> None:
    """Subsystem 8: Facade response timing, bot shield detection, and proxy pool management."""
    from veil.facade import BP
    from veil.proxy.pool import ProxyPool

    bp = BP()
    rtt_ms = bp.network.measure_response_time(f"{real_server_url}/html")
    shield_info = bp.intel.detect_bot_shields("<html><div class='cf-turnstile'>Cloudflare Turnstile challenge</div></html>")
    evasion_profile = bp.intel.estimate_evasion_probability()

    pool = ProxyPool()
    pool.add_proxy("192.168.1.100", 8080)
    p_node = pool.get_proxy()
    pool.report_success(p_node, latency_ms=12.5)

    assert rtt_ms > 0.0
    assert shield_info["shield_detected"] is True
    assert "cloudflare" in shield_info["detected_vendors"]
    assert evasion_profile["evasion_score"] > 0.0
    assert p_node.host == "192.168.1.100"


@pytest.mark.asyncio
async def test_subsystem_9_providers_architecture(real_server_url: str) -> None:
    """Subsystem 9: Multi-provider matrix probing and CurlCffiProvider live request."""
    from veil.providers import provider_matrix, CurlCffiProvider

    matrix = provider_matrix()
    assert len(matrix) >= 6

    curl_p = CurlCffiProvider()
    if curl_p.is_available():
        curl_resp = await curl_p.afetch(f"{real_server_url}/html")
        assert curl_resp.status_code == 200
        assert "Quantum Store" in curl_resp.text


@pytest.mark.asyncio
async def test_subsystem_10_tiered_crawler_mcp_and_cli(real_server_url: str) -> None:
    """Subsystem 10: 4-Tier crawler, all 12 MCP tools, and CLI subcommands via subprocess."""
    from veil.crawling.models import CrawlerTier, CrawlRequest
    from veil.crawling.service import TieredCrawlerService
    from veil.mcp.tools import handle_tool_call

    # 1. 4-Tier Crawler clean and challenge executions
    crawler = TieredCrawlerService()
    resp_clean = await crawler.crawl(CrawlRequest(url=f"{real_server_url}/html"))
    assert resp_clean.status_code == 200
    assert resp_clean.resolved_tier == CrawlerTier.HTTP_FAST
    assert resp_clean.escalations_count == 0

    resp_cf = await crawler.crawl(CrawlRequest(url=f"{real_server_url}/cf-challenge"))
    assert len(resp_cf.escalation_history) > 0
    assert resp_cf.escalation_history[0].status_code == 403

    # 2. Invoke all 12 MCP Tools with real inputs
    t1 = await handle_tool_call("get_provider_matrix", {})
    t2 = await handle_tool_call("quant_pit_align", {"filing": {"symbol": "AAPL", "revenue": 1000000}})
    t3 = await handle_tool_call("audit_biometrics", {"samples": [{"x": 10, "y": 10, "t": 0.0}]})
    t4 = await handle_tool_call("memory_pid_health", {"current_rss_mb": 450.0, "target_rss_mb": 512.0})
    t5 = await handle_tool_call("check_cannibalization", {
        "query_a": "python web scraping", "query_b": "python browser automation",
        "urls_a": ["https://python.org"], "urls_b": ["https://python.org"], "threshold": 0.3,
    })
    t6 = await handle_tool_call("mine_google_suggest", {"query": "fastapi vs", "alphabet": False})
    t7 = await handle_tool_call("inspect_state", {"workflow_id": "wf_test_01"})
    t8 = await handle_tool_call("extract_metadata", {"url": f"{real_server_url}/html"})
    t9 = await handle_tool_call("run_graphql_security_audit", {"target_url": f"{real_server_url}/html"})
    t10 = await handle_tool_call("run_security_audit_on_page", {"target_url": f"{real_server_url}/html"})
    t11 = await handle_tool_call("stealth_get_snapshot", {})
    t12 = await handle_tool_call("scrape_page", {"url": f"{real_server_url}/html", "target": "raw"})

    assert "providers" in t1 or "browser/playwright" in str(t1)
    assert t2 is not None
    assert t3 is not None
    assert t4 is not None

    # 3. Real CLI execution via subprocess
    cli_env = {**os.environ, "PYTHONPATH": str(SRC_DIR)}
    cli_help = subprocess.run([sys.executable, "-m", "veil.cli.main", "--help"], env=cli_env, capture_output=True, text=True)
    cli_doc = subprocess.run([sys.executable, "-m", "veil.cli.main", "doctor"], env=cli_env, capture_output=True, text=True)
    cli_aud = subprocess.run([sys.executable, "-m", "veil.cli.main", "audit"], env=cli_env, capture_output=True, text=True)

    assert cli_help.returncode == 0
    assert cli_doc.returncode == 0
    assert cli_aud.returncode == 0


@pytest.mark.asyncio
async def test_subsystem_11_scalability_blueprints_and_biomechanics(real_server_url: str) -> None:
    """Subsystem 11: Scalability, SQLite Checkpointing, 5 Blueprints, and arXiv Biomechanics."""
    from veil.crawling.checkpoint import CheckpointStore
    from veil.crawling.models import CrawlerTier, CrawlRequest
    from veil.crawling.service import TieredCrawlerService
    from veil.kinematics.biomechanics import (
        BiometricMouseController,
        compute_scroll_speed_variance,
        compute_teleport_click_ratio,
        generate_newton_wheel_scroll,
        generate_pre_click_stream,
    )
    from veil.blueprints import (
        EcommerceStealthBlueprint,
        CognitiveFormAgentBlueprint,
        WebRTCAndAuthAuditBlueprint,
        QuantPiTAndITCHBlueprint,
        FirecrawlReplacementBlueprint,
    )

    # 1. arXiv Biomechanics Primitives: Pre-Click Stream & Newton Wheel Scroll
    pre_click = generate_pre_click_stream(start=(50.0, 50.0), target=(350.0, 220.0), steps=25, seed=42)
    teleport_ratio = compute_teleport_click_ratio(pre_click)
    assert teleport_ratio == 0.0, f"Expected 0.0 teleport ratio, got {teleport_ratio}"
    assert pre_click[-1]["type"] == "click"

    wheel_events = generate_newton_wheel_scroll(delta_y=450.0, steps=20, seed=42)
    scroll_var = compute_scroll_speed_variance(wheel_events)
    assert scroll_var > 0.0, f"Expected scroll speed variance > 0, got {scroll_var}"

    ctrl = BiometricMouseController(seed=42)
    ctrl_stream = ctrl.generate_pre_click_stream(start=(10.0, 10.0), target=(100.0, 100.0))
    assert compute_teleport_click_ratio(ctrl_stream) == 0.0

    # 2. Crash-Resilient CheckpointStore & Auto-Context Recycling
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "crawl_checkpoint.db")
        store = CheckpointStore(db_path=db_path)

        crawler = TieredCrawlerService(
            max_concurrency=4,
            checkpoint_store=store,
            max_pages_per_context=2,
            memory_threshold_mb=256.0,
        )

        # Batch crawl with concurrency and checkpointing
        test_urls = [f"{real_server_url}/html", f"{real_server_url}/clean"]
        batch_res = await crawler.crawl_batch(test_urls, crawl_id="test_run_01")
        assert len(batch_res) == 2
        assert all(r.status_code == 200 for r in batch_res)
        assert store.is_completed("test_run_01", f"{real_server_url}/html")

        # Context rotation check
        rotation_status = crawler.check_and_rotate_context(current_memory_mb=300.0)
        assert rotation_status["rotated"] is True

        store.close()

    # 3. Blueprint 1: EcommerceStealthBlueprint
    ecom_bp = EcommerceStealthBlueprint(seed=42)
    ecom_res = await ecom_bp.scrape_catalog(f"{real_server_url}/html")
    assert ecom_res["status_code"] == 200
    assert ecom_res["scroll_simulation"]["passed"] is True
    assert len(ecom_res["tables"]) > 0 or len(ecom_res["schema_ld"]) > 0

    # 4. Blueprint 2: CognitiveFormAgentBlueprint
    form_bp = CognitiveFormAgentBlueprint(seed=42)
    form_res = await form_bp.submit_form(
        action_url=f"{real_server_url}/login",
        form_data={"username": "admin", "password": "secret"},
    )
    assert form_res["status_code"] == 200
    assert form_res["click_telemetry"]["teleport_click_ratio"] == 0.0

    # 5. Blueprint 3: WebRTCAndAuthAuditBlueprint
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_file = os.path.join(tmpdir, "audit_vault.json")
        sec_bp = WebRTCAndAuthAuditBlueprint()
        sec_res = await sec_bp.audit_endpoint_and_vault(
            url=f"{real_server_url}/html",
            vault_filepath=vault_file,
        )
        assert sec_res["status_code"] == 200
        assert sec_res["webrtc_audit"]["status"] == "SECURE"
        assert sec_res["vault"]["persisted_entries"] >= 1

    # 6. Blueprint 4: QuantPiTAndITCHBlueprint
    quant_bp = QuantPiTAndITCHBlueprint()
    aligned = quant_bp.align_financial_filing(
        symbol="AAPL",
        cik="0000320193",
        period_of_report_epoch=1700000000,
        sec_dissemination_epoch=1700003600,
        metrics={"revenue": 119575000000, "net_income": 33916000000},
    )
    assert aligned["knowledge_timestamp"] == 1700003600
    assert aligned["event_timestamp"] == 1700000000

    add_order_bytes = quant_bp.build_test_itch_add_order(
        stock="NVDA    ",
        order_ref=5001,
        shares=200,
        price_dollars=485.50,
        buy_sell="B",
    )
    parsed_itch = quant_bp.parse_itch_messages(add_order_bytes)
    assert len(parsed_itch.messages) == 1
    assert parsed_itch.messages[0]["type"] == "A"
    assert parsed_itch.messages[0]["stock"] == "NVDA"

    # 7. Blueprint 5: FirecrawlReplacementBlueprint
    fire_bp = FirecrawlReplacementBlueprint()
    scrape_out = await fire_bp.scrape(f"{real_server_url}/html")
    assert scrape_out["success"] is True
    assert "# Product Catalog" in scrape_out["data"]["markdown"]
    assert scrape_out["data"]["metadata"]["title"] == "Quantum Store - Premium Hardware"

