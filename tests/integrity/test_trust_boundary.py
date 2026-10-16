"""Phase D Remediation — Runtime Provenance & Trust Boundary Verification Suite.

Validates that:
1. All 14 Phase D regression attacks (ATTACK-027 to ATTACK-040) are strictly CAUGHT.
2. All 8 new remediation attacks (ATTACK-041 to ATTACK-048) are strictly CAUGHT.
3. The Critical Architectural Test cleanly separates fake dictionary metadata from real Chromium runtime evidence.
4. Master Gate independently verifies verdict seals and execution binding.
"""
from __future__ import annotations

import hashlib
import http.server
import os
import socketserver
import threading
import time
from pathlib import Path
from typing import Any
import pytest
from playwright.async_api import async_playwright

from harness.gate import verify_runtime_verdict
from harness.oracle import ExecutionStatus, IndependentOracle, OracleVerdict, RuntimeEvidenceContract
from harness.runtime_probe import ProvenanceError, RuntimeEvidence, TrustedRuntimeProbe


class EvilDuckPage:
    """Attacker-crafted duck-typed Page object mimicking Playwright Page interface."""

    def __init__(self, url: str = "https://target.example", title_str: str = "Target", closed: bool = False):
        self._url = url
        self._title = title_str
        self._closed = closed

    def is_closed(self) -> bool:
        return self._closed

    @property
    def url(self) -> str:
        return self._url

    def title(self) -> str:
        return self._title

    def query_selector(self, selector: str) -> Any:
        class FakeElement:
            def inner_text(self) -> str:
                return "Target Element"
        return FakeElement()


class LocalTestServer:
    """Threaded local HTTP server serving a deterministic test page."""

    HTML_PAGE = """<!DOCTYPE html>
<html>
<head><title>Sannysoft Test</title></head>
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


class TestTrustBoundaryAttacks:
    """Regression battery for ATTACK-027 through ATTACK-040: All must be CAUGHT."""

    def test_attack_027_forged_page_object_is_caught(self):
        """ATTACK-027: Mock/fake EvilDuckPage must be REJECTED by Oracle and Gate."""
        t_start = time.time()
        fake_page = EvilDuckPage(url="https://bank.example/transfer", title_str="Transfer Complete")

        contract = RuntimeEvidenceContract(
            session_id="evil-sess-027",
            execution_start_time=t_start,
            expected_url="https://bank.example/transfer",
            expected_title="Transfer Complete",
            live_page=fake_page,
            expected_dom_selector="#status",
            expected_dom_text="Target Element",
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "evil-sess-027"},
            contract=contract,
        )

        # Attack must be CAUGHT
        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert not IndependentOracle.is_trusted_success(verdict)
        assert any("FORGED_PAGE_OBJECT" in v for v in verdict.violations)

    def test_attack_028_forged_browser_context_is_caught(self):
        """ATTACK-028: Duck-typed context without real browser process must be REJECTED."""
        fake_context = EvilDuckPage(url="https://secure.internal/dashboard", title_str="Dashboard")
        t_start = time.time()

        contract = RuntimeEvidenceContract(
            session_id="ctx-forgery-028",
            execution_start_time=t_start,
            expected_url="https://secure.internal/dashboard",
            expected_title="Dashboard",
            live_page=fake_context,
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "ctx-forgery-028"},
            contract=contract,
        )

        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert not IndependentOracle.is_trusted_success(verdict)
        assert any("FORGED_PAGE_OBJECT" in v for v in verdict.violations)

    def test_attack_029_forged_runtime_evidence_contract_is_caught(self):
        """ATTACK-029: Fabricated contract with no operation or probe evidence must be REJECTED."""
        t_start = time.time()
        contract = RuntimeEvidenceContract(
            session_id="fabricated-contract-029",
            execution_start_time=t_start,
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "fabricated-contract-029"},
            contract=contract,
        )

        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert not IndependentOracle.is_trusted_success(verdict)
        assert any("MISSING_TRUSTED_PROBE_EVIDENCE" in v for v in verdict.violations)

    def test_attack_030_post_operation_verified_boolean_ignored(self):
        """ATTACK-030: Caller setting post_operation_verified=True without probe evidence is REJECTED."""
        contract = RuntimeEvidenceContract(
            session_id="bool-forgery-030",
            execution_start_time=time.time(),
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "bool-forgery-030"},
            contract=contract,
        )

        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert not IndependentOracle.is_trusted_success(verdict)

    def test_attack_031_session_id_spoofing_without_probe_is_caught(self):
        """ATTACK-031: Session ID spoofing without cryptographic probe evidence is REJECTED."""
        target_session = "victim-session-id"
        contract = RuntimeEvidenceContract(
            session_id=target_session,
            execution_start_time=time.time(),
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": target_session},
            contract=contract,
        )

        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert not IndependentOracle.is_trusted_success(verdict)

    def test_attack_032_artifact_mtime_forgery_is_caught(self, tmp_path: Path):
        """ATTACK-032: os.utime modification alone cannot achieve VERIFIED_REAL_SUCCESS."""
        stale_file = tmp_path / "stale_screenshot.png"
        stale_file.write_bytes(b"old stale image data")

        t_start = time.time()
        os.utime(str(stale_file), (t_start + 5.0, t_start + 5.0))

        contract = RuntimeEvidenceContract(
            session_id="mtime-forge-032",
            execution_start_time=t_start,
            required_artifacts=[str(stale_file)],
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "mtime-forge-032", "artifacts": [str(stale_file)]},
            contract=contract,
        )

        # Without trusted probe signed hash binding, mtime alone does not grant VERIFIED_REAL_SUCCESS
        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert not IndependentOracle.is_trusted_success(verdict)

    def test_attack_033_artifact_content_replacement_is_caught(self, tmp_path: Path):
        """ATTACK-033: Modifying artifact content post-capture triggers ARTIFACT_TAMPERED."""
        art = tmp_path / "screenshot.png"
        art.write_bytes(b"LEGITIMATE INITIAL SCREENSHOT")
        digest = hashlib.sha256(b"LEGITIMATE INITIAL SCREENSHOT").hexdigest()

        t_now = time.time()
        # Create signed probe bundle recording initial digest
        evidence = RuntimeEvidence(
            execution_id="exec-033",
            session_id="sess-033",
            evidence_id="ev-033",
            created_at=t_now,
            observed_url="https://app.test",
            observed_title="App",
            dom_observed_state={},
            artifact_digests={str(art): digest},
            browser_pid=None,
            probe_signature=TrustedRuntimeProbe._compute_evidence_mac(
                execution_id="exec-033",
                session_id="sess-033",
                evidence_id="ev-033",
                created_at=t_now,
                observed_url="https://app.test",
                observed_title="App",
                dom_observed_state={},
                artifact_digests={str(art): digest},
            ),
        )

        contract = RuntimeEvidenceContract(
            session_id="sess-033",
            execution_id="exec-033",
            execution_start_time=t_now,
            required_artifacts=[str(art)],
            evidence=evidence,
        )

        # Attacker replaces content prior to verification
        art.write_bytes(b"TAMPERED POISONED SCREENSHOT")

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "sess-033", "artifacts": [str(art)]},
            contract=contract,
        )

        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert any("ARTIFACT_TAMPERED" in v for v in verdict.violations)

    def test_attack_034_wrong_execution_evidence_reuse_is_caught(self, tmp_path: Path):
        """ATTACK-034: Evidence bound to Execution A is REJECTED when submitted to Execution B."""
        art = tmp_path / "exec_a_screen.png"
        art.write_bytes(b"Execution A Data")
        digest = hashlib.sha256(b"Execution A Data").hexdigest()

        t_now = time.time()
        evidence_a = RuntimeEvidence(
            execution_id="exec-A",
            session_id="sess-A",
            evidence_id="ev-034-A",
            created_at=t_now,
            observed_url="https://app.test",
            observed_title="App",
            dom_observed_state={},
            artifact_digests={str(art): digest},
            browser_pid=None,
            probe_signature=TrustedRuntimeProbe._compute_evidence_mac(
                execution_id="exec-A",
                session_id="sess-A",
                evidence_id="ev-034-A",
                created_at=t_now,
                observed_url="https://app.test",
                observed_title="App",
                dom_observed_state={},
                artifact_digests={str(art): digest},
            ),
        )

        # Execution B attempts to use evidence_a
        contract_b = RuntimeEvidenceContract(
            session_id="sess-B",
            execution_id="exec-B",
            execution_start_time=t_now,
            required_artifacts=[str(art)],
            evidence=evidence_a,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "sess-B", "artifacts": [str(art)]},
            contract=contract_b,
        )

        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert any("WRONG_EXECUTION_EVIDENCE" in v for v in verdict.violations)

    def test_attack_035_pre_operation_evidence_is_caught(self, tmp_path: Path):
        """ATTACK-035: Pre-operation evidence with true past mtime is CAUGHT by freshness check."""
        old_file = tmp_path / "past_artifact.png"
        old_file.write_bytes(b"past evidence")
        t_past = time.time() - 3600.0
        os.utime(str(old_file), (t_past, t_past))

        contract = RuntimeEvidenceContract(
            session_id="sess-035",
            execution_start_time=time.time(),
            required_artifacts=[str(old_file)],
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "sess-035", "artifacts": [str(old_file)]},
            contract=contract,
        )

        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert any("STALE_ARTIFACT_REPLAY" in v for v in verdict.violations)

    def test_attack_036_cross_process_evidence_without_binding_is_caught(self, tmp_path: Path):
        """ATTACK-036: Unbound cross-process file without probe provenance is REJECTED."""
        proc_a_file = tmp_path / "proc_a_dump.json"
        proc_a_file.write_text('{"from": "foreign_process"}')

        contract = RuntimeEvidenceContract(
            session_id="proc-B",
            execution_start_time=time.time(),
            required_artifacts=[str(proc_a_file)],
            post_operation_verified=True,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "proc-B", "artifacts": [str(proc_a_file)]},
            contract=contract,
        )

        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert not IndependentOracle.is_trusted_success(verdict)

    def test_attack_037_production_api_fake_evidence_is_caught(self):
        """ATTACK-037: Production dictionary format alone NEVER produces VERIFIED_REAL_SUCCESS."""
        prod_format_result = {
            "status": "success",
            "title": "Bot Detection Page",
            "dma_packets_sent": 25,
            "dry_run": False,
        }

        verdict = IndependentOracle.evaluate_live_execution(prod_format_result)

        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert verdict.status == ExecutionStatus.CLAIMED_SUCCESS
        assert verdict.is_acceptable is False
        assert not IndependentOracle.is_trusted_success(verdict)

    def test_attack_038_direct_verified_real_success_forgery_is_caught(self):
        """ATTACK-038: Manually constructed OracleVerdict without valid seal is REJECTED by Master Gate."""
        forged = OracleVerdict(
            status=ExecutionStatus.VERIFIED_REAL_SUCCESS,
            is_acceptable=True,
            reason="I am an attacker forging a passing verdict",
            evidence={},
            violations=[],
        )

        # Oracle and Gate both reject unsealed verdict
        assert not IndependentOracle.is_trusted_success(forged)
        is_accepted, msg = verify_runtime_verdict(forged)
        assert is_accepted is False
        assert "GATE_REJECT" in msg

    def test_attack_039_oracle_verdict_replay_is_caught(self):
        """ATTACK-039: Replayed verdict without matching execution binding is REJECTED by Master Gate."""
        captured_verdict = OracleVerdict(
            status=ExecutionStatus.VERIFIED_REAL_SUCCESS,
            is_acceptable=True,
            reason="Legitimate execution from run #1",
            evidence={"session_id": "run-1"},
            violations=[],
            execution_id="run-1-exec",
            evidence_id="run-1-ev",
            seal="arbitrary-or-replayed-seal",
        )

        # Verification must reject replayed/forged seal
        assert not IndependentOracle.is_trusted_success(captured_verdict)
        is_accepted, msg = verify_runtime_verdict(captured_verdict)
        assert is_accepted is False

    def test_attack_040_evidence_mutation_after_verification_is_caught(self, tmp_path: Path):
        """ATTACK-040: Modifying artifact post-verification is CAUGHT upon re-evaluation."""
        screenshot = tmp_path / "shot.png"
        screenshot.write_bytes(b"INITIAL VALID SCREENSHOT")
        digest = hashlib.sha256(b"INITIAL VALID SCREENSHOT").hexdigest()

        t_now = time.time()
        evidence = RuntimeEvidence(
            execution_id="exec-040",
            session_id="mutation-040",
            evidence_id="ev-040",
            created_at=t_now,
            observed_url="https://app.test",
            observed_title="App",
            dom_observed_state={},
            artifact_digests={str(screenshot): digest},
            browser_pid=None,
            probe_signature=TrustedRuntimeProbe._compute_evidence_mac(
                execution_id="exec-040",
                session_id="mutation-040",
                evidence_id="ev-040",
                created_at=t_now,
                observed_url="https://app.test",
                observed_title="App",
                dom_observed_state={},
                artifact_digests={str(screenshot): digest},
            ),
        )

        contract = RuntimeEvidenceContract(
            session_id="mutation-040",
            execution_id="exec-040",
            execution_start_time=t_now,
            required_artifacts=[str(screenshot)],
            evidence=evidence,
        )

        v1 = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "mutation-040", "artifacts": [str(screenshot)]},
            contract=contract,
        )
        assert v1.status == ExecutionStatus.VERIFIED_REAL_SUCCESS

        # Attacker mutates the artifact on disk
        screenshot.write_bytes(b"POISONED MODIFIED CONTENT")

        # Second verification: Live SHA-256 re-hashing MUST catch the mutation
        v2 = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "mutation-040", "artifacts": [str(screenshot)]},
            contract=contract,
        )
        assert v2.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert v2.is_acceptable is False
        assert any("ARTIFACT_TAMPERED" in v for v in v2.violations)


class TestRemediationAttacks:
    """New Remediation Attacks ATTACK-041 through ATTACK-048: All must be CAUGHT."""

    def test_attack_041_forge_execution_id_is_caught(self, tmp_path: Path):
        """ATTACK-041: Modifying execution_id in evidence invalidates probe HMAC signature."""
        art = tmp_path / "art41.png"
        art.write_bytes(b"data41")
        digest = hashlib.sha256(b"data41").hexdigest()

        t_now = time.time()
        valid_sig = TrustedRuntimeProbe._compute_evidence_mac(
            execution_id="legit-exec-41",
            session_id="sess-41",
            evidence_id="ev-41",
            created_at=t_now,
            observed_url="https://test.com",
            observed_title="Test",
            dom_observed_state={},
            artifact_digests={str(art): digest},
        )

        # Attacker injects forged execution_id while keeping old signature
        forged_evidence = RuntimeEvidence(
            execution_id="forged-exec-41",
            session_id="sess-41",
            evidence_id="ev-41",
            created_at=t_now,
            observed_url="https://test.com",
            observed_title="Test",
            dom_observed_state={},
            artifact_digests={str(art): digest},
            browser_pid=None,
            probe_signature=valid_sig,
        )

        contract = RuntimeEvidenceContract(
            session_id="sess-41",
            execution_id="forged-exec-41",
            execution_start_time=t_now,
            required_artifacts=[str(art)],
            evidence=forged_evidence,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "sess-41", "artifacts": [str(art)]},
            contract=contract,
        )

        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert any("FORGED_EVIDENCE_SIGNATURE" in v for v in verdict.violations)

    def test_attack_042_forge_evidence_id_is_caught(self, tmp_path: Path):
        """ATTACK-042: Modifying evidence_id invalidates probe HMAC signature."""
        art = tmp_path / "art42.png"
        art.write_bytes(b"data42")
        digest = hashlib.sha256(b"data42").hexdigest()

        t_now = time.time()
        valid_sig = TrustedRuntimeProbe._compute_evidence_mac(
            execution_id="exec-42",
            session_id="sess-42",
            evidence_id="orig-ev-42",
            created_at=t_now,
            observed_url="https://test.com",
            observed_title="Test",
            dom_observed_state={},
            artifact_digests={str(art): digest},
        )

        forged_evidence = RuntimeEvidence(
            execution_id="exec-42",
            session_id="sess-42",
            evidence_id="forged-ev-42",
            created_at=t_now,
            observed_url="https://test.com",
            observed_title="Test",
            dom_observed_state={},
            artifact_digests={str(art): digest},
            browser_pid=None,
            probe_signature=valid_sig,
        )

        contract = RuntimeEvidenceContract(
            session_id="sess-42",
            execution_id="exec-42",
            execution_start_time=t_now,
            required_artifacts=[str(art)],
            evidence=forged_evidence,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "sess-42", "artifacts": [str(art)]},
            contract=contract,
        )

        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert any("FORGED_EVIDENCE_SIGNATURE" in v for v in verdict.violations)

    def test_attack_043_modify_artifact_after_hash_capture_is_caught(self, tmp_path: Path):
        """ATTACK-043: Modifying artifact bytes after hash capture triggers ARTIFACT_TAMPERED."""
        art = tmp_path / "art43.png"
        art.write_bytes(b"initial bytes")
        digest = hashlib.sha256(b"initial bytes").hexdigest()

        t_now = time.time()
        evidence = RuntimeEvidence(
            execution_id="exec-43",
            session_id="sess-43",
            evidence_id="ev-43",
            created_at=t_now,
            observed_url="https://test.com",
            observed_title="Test",
            dom_observed_state={},
            artifact_digests={str(art): digest},
            browser_pid=None,
            probe_signature=TrustedRuntimeProbe._compute_evidence_mac(
                execution_id="exec-43",
                session_id="sess-43",
                evidence_id="ev-43",
                created_at=t_now,
                observed_url="https://test.com",
                observed_title="Test",
                dom_observed_state={},
                artifact_digests={str(art): digest},
            ),
        )

        contract = RuntimeEvidenceContract(
            session_id="sess-43",
            execution_id="exec-43",
            execution_start_time=t_now,
            required_artifacts=[str(art)],
            evidence=evidence,
        )

        # Attacker writes modified content
        art.write_bytes(b"modified bytes")

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "sess-43", "artifacts": [str(art)]},
            contract=contract,
        )

        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert any("ARTIFACT_TAMPERED" in v for v in verdict.violations)

    def test_attack_044_replay_consumed_evidence_is_caught(self, tmp_path: Path):
        """ATTACK-044: Replaying a consumed evidence bundle in a subsequent execution is CAUGHT."""
        art = tmp_path / "art44.png"
        art.write_bytes(b"data44")
        digest = hashlib.sha256(b"data44").hexdigest()

        t_now = time.time()
        evidence = RuntimeEvidence(
            execution_id="exec-44",
            session_id="sess-44",
            evidence_id="ev-44-unique",
            created_at=t_now,
            observed_url="https://test.com",
            observed_title="Test",
            dom_observed_state={},
            artifact_digests={str(art): digest},
            browser_pid=None,
            probe_signature=TrustedRuntimeProbe._compute_evidence_mac(
                execution_id="exec-44",
                session_id="sess-44",
                evidence_id="ev-44-unique",
                created_at=t_now,
                observed_url="https://test.com",
                observed_title="Test",
                dom_observed_state={},
                artifact_digests={str(art): digest},
            ),
        )

        contract1 = RuntimeEvidenceContract(
            session_id="sess-44",
            execution_id="exec-44",
            execution_start_time=t_now,
            required_artifacts=[str(art)],
            evidence=evidence,
        )

        # First verification succeeds and consumes evidence_id
        v1 = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "sess-44", "artifacts": [str(art)]},
            contract=contract1,
        )
        assert v1.status == ExecutionStatus.VERIFIED_REAL_SUCCESS

        # Attacker replays evidence in a second contract/execution
        contract2 = RuntimeEvidenceContract(
            session_id="sess-44",
            execution_id="exec-44",
            execution_start_time=t_now,
            required_artifacts=[str(art)],
            evidence=evidence,
        )

        v2 = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "sess-44", "artifacts": [str(art)]},
            contract=contract2,
        )

        assert v2.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert any("EVIDENCE_REPLAY_DETECTED" in v for v in v2.violations)

    def test_attack_045_fake_playwright_like_object_is_caught(self):
        """ATTACK-045: Mock object with synthetic methods is rejected by TrustedRuntimeProbe."""
        class FakePlaywrightDouble:
            def __init__(self):
                self.url = "https://legit.example"
                self.context = self
                self.browser = self
            def is_closed(self):
                return False
            def is_connected(self):
                return True
            def title(self):
                return "Legit"
            def query_selector(self, s):
                return None

        fake = FakePlaywrightDouble()
        is_valid, reason = TrustedRuntimeProbe.validate_playwright_page(fake)
        assert is_valid is False
        assert "FORGED_PAGE_OBJECT" in reason

    def test_attack_046_call_oracle_with_valid_dict_no_probe_is_caught(self):
        """ATTACK-046: Valid-looking dictionary without runtime probe returns CLAIMED_SUCCESS."""
        payload = {
            "status": "success",
            "url": "https://production.internal/portal",
            "title": "Portal Home",
            "dma_packets_sent": 100,
            "dry_run": False,
        }

        verdict = IndependentOracle.evaluate_live_execution(payload)
        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert verdict.status == ExecutionStatus.CLAIMED_SUCCESS
        assert verdict.is_acceptable is False
        assert not IndependentOracle.is_trusted_success(verdict)

    def test_attack_047_manually_constructed_verdict_rejected_by_gate(self):
        """ATTACK-047: Manually constructed verdict with fake seal is REJECTED by Master Gate."""
        forged_verdict = OracleVerdict(
            status=ExecutionStatus.VERIFIED_REAL_SUCCESS,
            is_acceptable=True,
            reason="Attacker claimed success",
            evidence={},
            violations=[],
            execution_id="forged-exec",
            evidence_id="forged-ev",
            seal="fake-hmac-seal-0000000000000000000000000000000000000000000000000000000000000000",
        )

        assert not IndependentOracle.is_trusted_success(forged_verdict)
        accepted, reason = verify_runtime_verdict(forged_verdict)
        assert accepted is False
        assert "GATE_REJECT" in reason

    def test_attack_048_modify_verdict_after_sealing_is_caught(self, tmp_path: Path):
        """ATTACK-048: Modifying any field on a legitimately sealed verdict invalidates its seal."""
        art = tmp_path / "art48.png"
        art.write_bytes(b"data48")
        digest = hashlib.sha256(b"data48").hexdigest()

        t_now = time.time()
        evidence = RuntimeEvidence(
            execution_id="exec-48",
            session_id="sess-48",
            evidence_id="ev-48-seal",
            created_at=t_now,
            observed_url="https://test.com",
            observed_title="Test",
            dom_observed_state={},
            artifact_digests={str(art): digest},
            browser_pid=None,
            probe_signature=TrustedRuntimeProbe._compute_evidence_mac(
                execution_id="exec-48",
                session_id="sess-48",
                evidence_id="ev-48-seal",
                created_at=t_now,
                observed_url="https://test.com",
                observed_title="Test",
                dom_observed_state={},
                artifact_digests={str(art): digest},
            ),
        )

        contract = RuntimeEvidenceContract(
            session_id="sess-48",
            execution_id="exec-48",
            execution_start_time=t_now,
            required_artifacts=[str(art)],
            evidence=evidence,
        )

        verdict = IndependentOracle.evaluate_live_execution(
            {"status": "success", "session_id": "sess-48", "artifacts": [str(art)]},
            contract=contract,
        )
        assert verdict.status == ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert IndependentOracle.is_trusted_success(verdict)

        # Attacker tampers with execution_id or violations on the sealed verdict
        verdict.execution_id = "tampered-exec-48"
        assert not IndependentOracle.is_trusted_success(verdict)
        accepted, msg = verify_runtime_verdict(verdict)
        assert accepted is False
        assert "GATE_REJECT" in msg


class TestCriticalArchitecturalProof:
    """Critical architectural proof: fake dictionary vs real Chromium execution."""

    def test_critical_architectural_fake_dictionary_rejected(self):
        """Proof A: Exact fake dictionary payload MUST produce CLAIMED_SUCCESS, NOT VERIFIED_REAL_SUCCESS."""
        fake_payload = {
            "status": "success",
            "title": "Sannysoft Test",
            "dma_packets_sent": 25,
            "dry_run": False,
        }

        verdict = IndependentOracle.evaluate_live_execution(fake_payload)

        # Assert mathematically that fake metadata != runtime proof
        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS
        assert verdict.status == ExecutionStatus.CLAIMED_SUCCESS
        assert verdict.is_acceptable is False
        assert not IndependentOracle.is_trusted_success(verdict)
        accepted, msg = verify_runtime_verdict(verdict)
        assert accepted is False
        assert "GATE_REJECT" in msg

    @pytest.mark.asyncio
    async def test_critical_architectural_real_chromium_verified(self, tmp_path: Path):
        """Proof B: Real Chromium execution with TrustedRuntimeProbe MUST produce sealed VERIFIED_REAL_SUCCESS."""
        server = LocalTestServer()
        session_id = f"arch-sess-{int(time.time())}"
        execution_id = f"arch-exec-{int(time.time())}"
        start_time = time.time()
        screenshot_file = tmp_path / "sannysoft_real.png"

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # 1. Real Chromium navigation
                await page.goto(server.base_url)
                title = await page.title()
                assert title == "Sannysoft Test"

                # 2. Real DOM mutation
                await page.click("#action-trigger")
                heading_text = await page.inner_text("#status-heading")
                assert heading_text == "Action Performed"

                # 3. Real screenshot artifact
                await page.screenshot(path=str(screenshot_file))
                assert screenshot_file.exists()
                assert screenshot_file.stat().st_size > 0

                # 4. Capture trusted observation via TrustedRuntimeProbe
                evidence = await TrustedRuntimeProbe.capture_observation_async(
                    page=page,
                    expected_url=server.base_url,
                    expected_title="Sannysoft Test",
                    expected_dom_selector="#status-heading",
                    expected_dom_text="Action Performed",
                    artifact_paths=[str(screenshot_file)],
                    execution_id=execution_id,
                    session_id=session_id,
                )

                # 5. Build strict contract bound to this execution and evidence
                contract = RuntimeEvidenceContract(
                    session_id=session_id,
                    execution_id=execution_id,
                    execution_start_time=start_time,
                    expected_url=server.base_url,
                    expected_title="Sannysoft Test",
                    required_artifacts=[str(screenshot_file)],
                    expected_dom_selector="#status-heading",
                    expected_dom_text="Action Performed",
                    evidence=evidence,
                )

                result_payload = {
                    "status": "success",
                    "session_id": session_id,
                    "execution_id": execution_id,
                    "url": server.base_url,
                    "title": title,
                    "artifacts": [str(screenshot_file)],
                    "timestamp": time.time(),
                }

                # 6. Oracle evaluation
                verdict = IndependentOracle.evaluate_live_execution(result_payload, contract=contract)

                # Assert that real runtime evidence = verified runtime proof
                assert verdict.status == ExecutionStatus.VERIFIED_REAL_SUCCESS
                assert verdict.is_acceptable is True
                assert verdict.seal is not None
                assert len(verdict.violations) == 0
                assert IndependentOracle.is_trusted_success(verdict)

                # 7. Master Gate independent verification
                accepted, msg = verify_runtime_verdict(verdict, contract)
                assert accepted is True
                assert msg == "VERDICT_ACCEPTED_BY_GATE"

                await browser.close()
        finally:
            server.shutdown()
