"""Phase C — Runtime Evidence & Browser Reality Test Suite.

Proves that:
1. `REAL_SUCCESS` cannot be claimed or manufactured by self-reported payloads without verifiable runtime evidence.
2. Adversarial attacks ATTACK-017 through ATTACK-026 are strictly caught and rejected.
3. The three-tier taxonomy (CLAIMED_SUCCESS, OBSERVED_SUCCESS, VERIFIED_REAL_SUCCESS) is mathematically enforced.
4. A live Playwright browser interacting with a deterministic local server honestly achieves VERIFIED_REAL_SUCCESS.
"""
from __future__ import annotations

import asyncio
import http.server
import socketserver
import threading
import time
from pathlib import Path
from typing import Any, Generator, Tuple
import pytest
from playwright.async_api import async_playwright

from harness.oracle import ExecutionStatus, IndependentOracle, RuntimeEvidenceContract


class MockPage:
    """Mock page object for simulating specific browser states without starting child processes."""

    def __init__(self, url: str = "about:blank", title_str: str = "", closed: bool = False, dom: dict | None = None) -> None:
        self._url = url
        self._title = title_str
        self._closed = closed
        self._dom = dom or {}

    def is_closed(self) -> bool:
        return self._closed

    @property
    def url(self) -> str:
        return self._url

    def title(self) -> str:
        return self._title

    def query_selector(self, selector: str) -> Any:
        if selector in self._dom:
            text_val = self._dom[selector]
            class MockElement:
                def inner_text(self) -> str:
                    return text_val
            return MockElement()
        return None


class TestTaxonomyDistinction:
    """Verifies that CLAIMED_SUCCESS, OBSERVED_SUCCESS, and VERIFIED_REAL_SUCCESS are strictly segregated."""

    def test_claimed_success_never_qualifies_as_real_success(self) -> None:
        """Rule: CLAIMED_SUCCESS must never equal REAL_SUCCESS or be acceptable."""
        assert ExecutionStatus.CLAIMED_SUCCESS != ExecutionStatus.REAL_SUCCESS
        assert ExecutionStatus.CLAIMED_SUCCESS != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert ExecutionStatus.OBSERVED_SUCCESS != ExecutionStatus.REAL_SUCCESS

        claimed_payload = {
            "status": "success",
            "message": "Self-reported completion",
        }
        verdict = IndependentOracle.evaluate_live_execution(claimed_payload)
        assert verdict.status == ExecutionStatus.CLAIMED_SUCCESS
        assert verdict.status != ExecutionStatus.REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert any("MISSING_RUNTIME_EVIDENCE" in v for v in verdict.violations)


class TestBrowserRealityAttacks:
    """Regression battery for ATTACK-017 through ATTACK-026."""

    def test_attack_017_fake_runtime_artifact(self) -> None:
        """ATTACK-017: Fake result claiming nonexistent artifact must be REJECTED."""
        payload = {
            "status": "success",
            "title": "Fake Page",
            "url": "https://fake.example",
            "artifacts": ["fake.png"],
        }
        verdict = IndependentOracle.evaluate_live_execution(payload)
        assert verdict.status != ExecutionStatus.REAL_SUCCESS
        assert verdict.status == ExecutionStatus.CLAIMED_SUCCESS
        assert verdict.is_acceptable is False
        assert any("FAKE_ARTIFACT_NONEXISTENT" in v for v in verdict.violations)

    def test_attack_018_fake_url_without_navigation(self) -> None:
        """ATTACK-018: URL claimed without browser navigation must be REJECTED."""
        payload = {
            "status": "success",
            "url": "https://example.com",
        }
        verdict = IndependentOracle.evaluate_live_execution(payload)
        assert verdict.status != ExecutionStatus.REAL_SUCCESS
        assert verdict.status == ExecutionStatus.CLAIMED_SUCCESS
        assert verdict.is_acceptable is False
        assert any("UNVERIFIED_CLAIMED_NAVIGATION" in v for v in verdict.violations)

    def test_attack_019_fake_screenshot_path(self) -> None:
        """ATTACK-019: Nonexistent screenshot path must be REJECTED."""
        payload = {
            "status": "success",
            "artifacts": ["/tmp/fake-screenshot.png"],
        }
        verdict = IndependentOracle.evaluate_live_execution(payload)
        assert verdict.status != ExecutionStatus.REAL_SUCCESS
        assert verdict.status == ExecutionStatus.CLAIMED_SUCCESS
        assert verdict.is_acceptable is False
        assert any("FAKE_ARTIFACT_NONEXISTENT" in v for v in verdict.violations)

    def test_attack_020_stale_artifact_replay(self, tmp_path: Path) -> None:
        """ATTACK-020: Stale artifact created prior to execution start must be REJECTED."""
        old_file = tmp_path / "old_artifact.png"
        old_file.write_bytes(b"old-data")

        # Set older timestamp on disk
        past_time = time.time() - 3600.0
        import os
        os.utime(str(old_file), (past_time, past_time))

        t_start = time.time()
        contract = RuntimeEvidenceContract(
            session_id="session-fresh-001",
            execution_start_time=t_start,
            required_artifacts=[str(old_file)],
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "artifacts": [str(old_file)]},
            contract=contract,
        )
        assert verdict.status != ExecutionStatus.REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert any("STALE_ARTIFACT_REPLAY" in v for v in verdict.violations)

    def test_attack_021_wrong_page_evidence(self) -> None:
        """ATTACK-021: Artifact/state from Page A claiming Page B succeeded must be REJECTED."""
        page_a = MockPage(url="https://page-a.example", title_str="Page A")
        t_start = time.time()

        contract = RuntimeEvidenceContract(
            session_id="session-page-b",
            execution_start_time=t_start,
            expected_url="https://page-b.example",
            expected_title="Page B",
            live_page=page_a,
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "url": "https://page-b.example"},
            contract=contract,
        )
        assert verdict.status != ExecutionStatus.REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert any("WRONG_PAGE_EVIDENCE" in v for v in verdict.violations)

    def test_attack_022_browser_closed_before_verification(self) -> None:
        """ATTACK-022: Browser closed before post-op verification must be REJECTED as PARTIAL/FAILURE."""
        closed_page = MockPage(url="https://example.com", closed=True)
        t_start = time.time()

        contract = RuntimeEvidenceContract(
            session_id="session-closed-browser",
            execution_start_time=t_start,
            expected_url="https://example.com",
            live_page=closed_page,
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success"},
            contract=contract,
        )
        assert verdict.status != ExecutionStatus.REAL_SUCCESS
        assert verdict.status in (ExecutionStatus.PARTIAL, ExecutionStatus.CLAIMED_SUCCESS, ExecutionStatus.REAL_FAILURE)
        assert verdict.is_acceptable is False
        assert any("BROWSER_CLOSED_BEFORE_VERIFICATION" in v for v in verdict.violations)

    def test_attack_023_navigation_never_happened(self) -> None:
        """ATTACK-023: Page remaining on about:blank with claimed target URL must be REJECTED."""
        blank_page = MockPage(url="about:blank", title_str="")
        t_start = time.time()

        contract = RuntimeEvidenceContract(
            session_id="session-blank",
            execution_start_time=t_start,
            expected_url="https://target.corp/login",
            live_page=blank_page,
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "url": "https://target.corp/login"},
            contract=contract,
        )
        assert verdict.status != ExecutionStatus.REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert any("NAVIGATION_NEVER_HAPPENED" in v for v in verdict.violations)

    def test_attack_024_dom_evidence_forgery(self) -> None:
        """ATTACK-024: Claimed DOM mutation without observable DOM change must be REJECTED."""
        static_page = MockPage(url="https://app.test", title_str="App", dom={"#unrelated": "text"})
        t_start = time.time()

        contract = RuntimeEvidenceContract(
            session_id="session-dom-forgery",
            execution_start_time=t_start,
            expected_url="https://app.test",
            expected_dom_selector="#checkout-success-banner",
            live_page=static_page,
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "dom_mutations": 1},
            contract=contract,
        )
        assert verdict.status != ExecutionStatus.REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert any("DOM_EVIDENCE_FORGERY" in v for v in verdict.violations)

    def test_attack_025_cross_session_evidence(self) -> None:
        """ATTACK-025: Injecting Session A evidence into Session B must be REJECTED."""
        t_start = time.time()
        contract_b = RuntimeEvidenceContract(
            session_id="session-B-target",
            execution_start_time=t_start,
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "session-A-injected"},
            contract=contract_b,
        )
        assert verdict.status != ExecutionStatus.REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert any("CROSS_SESSION_EVIDENCE_LEAK" in v for v in verdict.violations)

    def test_attack_026_timestamp_replay(self) -> None:
        """ATTACK-026: Reusing old timestamp from past operation must be REJECTED."""
        t_start = time.time()
        old_replay_timestamp = t_start - 3600.0

        contract = RuntimeEvidenceContract(
            session_id="session-anti-replay",
            execution_start_time=t_start,
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "timestamp": old_replay_timestamp},
            contract=contract,
        )
        assert verdict.status != ExecutionStatus.REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert any("TIMESTAMP_REPLAY_DETECTED" in v for v in verdict.violations)


class LocalTestServer:
    """Threaded local HTTP server serving a deterministic test page."""

    HTML_PAGE = """<!DOCTYPE html>
<html>
<head><title>Deterministic Local Verification</title></head>
<body>
    <h1 id="status-heading">Initial State</h1>
    <button id="action-trigger" onclick="
        document.getElementById('status-heading').innerText='Action Performed';
        document.getElementById('status-heading').setAttribute('data-verified', 'true');
    ">Execute Action</button>
</body>
</html>"""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(LocalTestServer.HTML_PAGE.encode("utf-8"))

        def log_message(self, format: str, *args: Any) -> None:
            pass

    def __init__(self) -> None:
        self.server = socketserver.TCPServer(("127.0.0.1", 0), self.Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.port}/"

    def shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()


class TestLiveBrowserProof:
    """End-to-End Live Browser Proof on deterministic localhost environment."""

    @pytest.mark.asyncio
    async def test_live_browser_navigation_action_and_verification(self, tmp_path: Path) -> None:
        """Proves that a real Playwright session satisfies all 7 contract pillars for VERIFIED_REAL_SUCCESS."""
        server = LocalTestServer()
        session_id = f"live-sess-{int(time.time())}"
        start_time = time.time()
        screenshot_file = tmp_path / "verified_page.png"

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # 1. Real navigation
                await page.goto(server.base_url)
                title = await page.title()
                assert title == "Deterministic Local Verification"

                # 2. Perform deterministic harmless action
                await page.click("#action-trigger")
                heading_text = await page.inner_text("#status-heading")
                assert heading_text == "Action Performed"

                # 3. Create fresh screenshot artifact
                await page.screenshot(path=str(screenshot_file))
                assert screenshot_file.exists()
                assert screenshot_file.stat().st_size > 0

                # 4. Synchronous verification while browser is live
                # Wrap live page in a synchronous inspection adapter for IndependentOracle
                class LivePageAdapter:
                    def is_closed(self) -> bool:
                        return page.is_closed()
                    @property
                    def url(self) -> str:
                        return page.url
                    def title(self) -> str:
                        return title
                    def query_selector(self, selector: str) -> Any:
                        if selector == "#status-heading":
                            class HeaderElement:
                                def inner_text(self) -> str:
                                    return heading_text
                            return HeaderElement()
                        return None

                contract = RuntimeEvidenceContract(
                    session_id=session_id,
                    execution_start_time=start_time,
                    execution_end_time=time.time(),
                    expected_url=server.base_url,
                    expected_title="Deterministic Local Verification",
                    required_artifacts=[str(screenshot_file)],
                    live_page=LivePageAdapter(),
                    expected_dom_selector="#status-heading",
                    expected_dom_text="Action Performed",
                    post_operation_verified=True,
                )

                result_payload = {
                    "status": "success",
                    "session_id": session_id,
                    "url": server.base_url,
                    "title": title,
                    "artifacts": [str(screenshot_file)],
                    "timestamp": time.time(),
                    "dom_mutations": 1,
                }

                # Independent Oracle Verification
                verdict = IndependentOracle.evaluate_live_execution(result_payload, contract=contract)

                assert verdict.status == ExecutionStatus.VERIFIED_REAL_SUCCESS
                assert verdict.status == ExecutionStatus.REAL_SUCCESS
                assert verdict.is_acceptable is True
                assert len(verdict.violations) == 0
                assert verdict.evidence["observed_url"] == server.base_url

                await browser.close()

        finally:
            server.shutdown()
