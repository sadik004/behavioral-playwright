"""Phase D.5: Independent External Verifier & Trust-Domain Attack Suite.

Validates that:
1. An external verifier running in a decoupled process independently audits runtime evidence.
2. All 22 Phase D.5 adversarial attacks (ATTACK-049 to ATTACK-070) are strictly CAUGHT.
3. Compromised internal probe or Oracle simulations cannot deceive the external verifier.
4. End-to-End Real Chromium execution achieves VERIFIED_REAL_SUCCESS across:
   Real Browser -> Probe -> External Verifier -> Oracle -> Sealed Verdict -> Gate.
5. Corrupted, replayed, or forged variants in the real browser pipeline are all REJECTED.
"""
from __future__ import annotations

import copy
import hashlib
import http.server
import json
import os
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict
import pytest
from playwright.async_api import async_playwright

from harness.external_verifier import ExternalVerificationResult, IndependentExternalVerifier
from harness.gate import verify_runtime_verdict
from harness.oracle import ExecutionStatus, IndependentOracle, OracleVerdict, RuntimeEvidenceContract
from harness.runtime_probe import RuntimeEvidence, TrustedRuntimeProbe


class LocalTestServer:
    """Deterministic local HTTP server serving a test page."""

    HTML_PAGE = """<!DOCTYPE html>
<html>
<head><title>External Verifier Test Page</title></head>
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


def create_sample_evidence_bundle(tmp_path: Path, secret: bytes) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Helper to generate a structurally valid, signed evidence and contract pair."""
    art = tmp_path / "valid_art.png"
    art.write_bytes(b"VALID_IMAGE_DATA_12345")
    art_hash = hashlib.sha256(b"VALID_IMAGE_DATA_12345").hexdigest()

    t_now = time.time()
    exec_id = f"exec-{int(t_now)}"
    sess_id = f"sess-{int(t_now)}"
    ev_id = f"ev-{int(t_now)}"

    digests = {str(art): art_hash}
    dom_state = {"#status-heading": "Action Performed"}

    sig = IndependentExternalVerifier.compute_probe_hmac(
        secret=secret,
        execution_id=exec_id,
        session_id=sess_id,
        evidence_id=ev_id,
        created_at=t_now,
        observed_url="http://127.0.0.1:8080/test",
        observed_title="External Verifier Test Page",
        dom_observed_state=dom_state,
        artifact_digests=digests,
    )

    evidence_dict = {
        "execution_id": exec_id,
        "session_id": sess_id,
        "evidence_id": ev_id,
        "created_at": t_now,
        "observed_url": "http://127.0.0.1:8080/test",
        "observed_title": "External Verifier Test Page",
        "dom_observed_state": dom_state,
        "artifact_digests": digests,
        "browser_pid": os.getpid(),  # Current process is definitely alive
        "probe_signature": sig,
    }

    contract_dict = {
        "execution_id": exec_id,
        "session_id": sess_id,
        "execution_start_time": t_now - 1.0,
        "expected_url": "http://127.0.0.1:8080/test",
        "expected_title": "External Verifier Test Page",
        "expected_dom_selector": "#status-heading",
        "expected_dom_text": "Action Performed",
    }

    return evidence_dict, contract_dict


class TestPhaseD5Attacks:
    """Attack battery ATTACK-049 through ATTACK-070 for the Independent External Verifier."""

    @pytest.fixture(autouse=True)
    def clean_registries(self):
        IndependentExternalVerifier.reset_consumed_registry()
        IndependentOracle.reset_replay_registry()
        yield

    def test_attack_049_modified_runtime_evidence_after_signing(self, tmp_path: Path):
        """ATTACK-049: Modifying any field in RuntimeEvidence after signing must fail HMAC check."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        # Attacker modifies observed_url
        evidence["observed_url"] = "http://malicious.corp/phish"

        res = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res.is_valid is False
        assert res.status == "REJECTED"
        assert any("INVALID_PROBE_SIGNATURE" in v for v in res.violations)

    def test_attack_050_modified_artifact_after_signing(self, tmp_path: Path):
        """ATTACK-050: Modifying on-disk artifact bytes after signing must fail SHA-256 check."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        # Attacker modifies the file on disk
        art_path = list(evidence["artifact_digests"].keys())[0]
        Path(art_path).write_bytes(b"CORRUPTED_TAMPERED_BYTES")

        res = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res.is_valid is False
        assert res.status == "REJECTED"
        assert any("ARTIFACT_TAMPERED" in v for v in res.violations)

    def test_attack_051_copied_valid_signature_onto_different_evidence(self, tmp_path: Path):
        """ATTACK-051: Pasting valid signature from Evidence A onto Evidence B must fail verification."""
        secret = os.urandom(32)
        ev_a, _ = create_sample_evidence_bundle(tmp_path, secret)
        ev_b, contract_b = create_sample_evidence_bundle(tmp_path, secret)

        # Copy A's signature onto B
        ev_b["probe_signature"] = ev_a["probe_signature"]

        res = IndependentExternalVerifier.verify_evidence(ev_b, contract_b, secret)
        assert res.is_valid is False
        assert any("INVALID_PROBE_SIGNATURE" in v for v in res.violations)

    def test_attack_052_replay_valid_evidence_with_new_execution_id(self, tmp_path: Path):
        """ATTACK-052: Changing contract execution_id while keeping evidence fails execution binding."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        # Contract has new execution_id, evidence has old
        contract["execution_id"] = "brand-new-exec-999"

        res = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res.is_valid is False
        assert any("EXECUTION_ID_MISMATCH" in v for v in res.violations)

    def test_attack_053_replay_valid_evidence_with_old_execution_id(self, tmp_path: Path):
        """ATTACK-053: Replaying identical evidence twice is blocked by consumed registry."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        # First verification succeeds and consumes evidence_id
        res1 = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res1.is_valid is True

        # Second verification of identical evidence fails with EVIDENCE_REPLAY
        res2 = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res2.is_valid is False
        assert res2.status == "REPLAY_DETECTED"
        assert any("EVIDENCE_REPLAY" in v for v in res2.violations)

    def test_attack_054_cross_session_evidence_substitution(self, tmp_path: Path):
        """ATTACK-054: Evidence bound to session X submitted against session Y is rejected."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        contract["session_id"] = "victim-session-target"

        res = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res.is_valid is False
        assert any("SESSION_ID_MISMATCH" in v for v in res.violations)

    def test_attack_055_cross_process_evidence_substitution(self, tmp_path: Path):
        """ATTACK-055: Evidence claiming a PID that does not match OS process table is rejected."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        # Attacker injects a non-existent foreign PID (e.g. 9999999)
        evidence["browser_pid"] = 9999999
        # Recompute signature so HMAC passes, but process check fails
        evidence["probe_signature"] = IndependentExternalVerifier.compute_probe_hmac(
            secret=secret,
            execution_id=evidence["execution_id"],
            session_id=evidence["session_id"],
            evidence_id=evidence["evidence_id"],
            created_at=evidence["created_at"],
            observed_url=evidence["observed_url"],
            observed_title=evidence["observed_title"],
            dom_observed_state=evidence["dom_observed_state"],
            artifact_digests=evidence["artifact_digests"],
        )

        res = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res.is_valid is False
        assert any("DEAD_BROWSER_PROCESS" in v for v in res.violations)

    def test_attack_056_forged_browser_pid(self, tmp_path: Path):
        """ATTACK-056: Negative/zero or non-integer browser PID is rejected."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        evidence["browser_pid"] = -1
        res = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res.is_valid is False
        assert any("DEAD_BROWSER_PROCESS" in v or "INVALID_BROWSER_PID" in v for v in res.violations)

    def test_attack_057_forged_cdp_browser_identity(self, tmp_path: Path):
        """ATTACK-057: Fake CDP/browser identity without running browser is rejected."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)
        evidence["browser_pid"] = 12345678  # Dead PID

        res = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res.is_valid is False
        assert any("DEAD_BROWSER_PROCESS" in v for v in res.violations)

    def test_attack_058_forged_page_identity(self, tmp_path: Path):
        """ATTACK-058: Evidence with mismatched URL or about:blank is rejected."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        # Attacker sets observed_url to about:blank
        evidence["observed_url"] = "about:blank"
        evidence["probe_signature"] = IndependentExternalVerifier.compute_probe_hmac(
            secret=secret,
            execution_id=evidence["execution_id"],
            session_id=evidence["session_id"],
            evidence_id=evidence["evidence_id"],
            created_at=evidence["created_at"],
            observed_url="about:blank",
            observed_title=evidence["observed_title"],
            dom_observed_state=evidence["dom_observed_state"],
            artifact_digests=evidence["artifact_digests"],
        )

        res = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res.is_valid is False
        assert any("NAVIGATION_NEVER_HAPPENED" in v for v in res.violations)

    def test_attack_059_forged_artifact_hash(self, tmp_path: Path):
        """ATTACK-059: Supplying a forged SHA-256 hash that doesn't match disk bytes fails."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        art_path = list(evidence["artifact_digests"].keys())[0]
        evidence["artifact_digests"][art_path] = "0000000000000000000000000000000000000000000000000000000000000000"
        evidence["probe_signature"] = IndependentExternalVerifier.compute_probe_hmac(
            secret=secret,
            execution_id=evidence["execution_id"],
            session_id=evidence["session_id"],
            evidence_id=evidence["evidence_id"],
            created_at=evidence["created_at"],
            observed_url=evidence["observed_url"],
            observed_title=evidence["observed_title"],
            dom_observed_state=evidence["dom_observed_state"],
            artifact_digests=evidence["artifact_digests"],
        )

        res = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res.is_valid is False
        assert any("ARTIFACT_TAMPERED" in v for v in res.violations)

    def test_attack_060_forged_timestamp_freshness(self, tmp_path: Path):
        """ATTACK-060: Future or expired timestamps are rejected by the external verifier."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        # Future timestamp (+100 seconds)
        evidence["created_at"] = time.time() + 100.0
        evidence["probe_signature"] = IndependentExternalVerifier.compute_probe_hmac(
            secret=secret,
            execution_id=evidence["execution_id"],
            session_id=evidence["session_id"],
            evidence_id=evidence["evidence_id"],
            created_at=evidence["created_at"],
            observed_url=evidence["observed_url"],
            observed_title=evidence["observed_title"],
            dom_observed_state=evidence["dom_observed_state"],
            artifact_digests=evidence["artifact_digests"],
        )

        res = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res.is_valid is False
        assert any("FUTURE_TIMESTAMP" in v for v in res.violations)

    def test_attack_061_forged_execution_id_session_id(self, tmp_path: Path):
        """ATTACK-061: Empty execution_id or session_id is rejected."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        evidence["execution_id"] = ""
        res = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res.is_valid is False
        assert any("EMPTY_EXECUTION_ID" in v for v in res.violations)

    def test_attack_062_modified_sealed_oracle_verdict(self):
        """ATTACK-062: Modifying fields on a sealed OracleVerdict invalidates external seal check."""
        secret = os.urandom(32)
        seal = IndependentExternalVerifier.compute_verdict_seal(
            secret=secret,
            status="VERIFIED_REAL_SUCCESS",
            is_acceptable=True,
            execution_id="exec-062",
            evidence_id="ev-062",
            violations=[],
        )

        verdict_dict = {
            "status": "VERIFIED_REAL_SUCCESS",
            "is_acceptable": True,
            "execution_id": "exec-062",
            "evidence_id": "ev-062",
            "violations": [],
            "seal": seal,
        }

        # Valid verdict passes
        res1 = IndependentExternalVerifier.verify_oracle_verdict(verdict_dict, secret)
        assert res1.is_valid is True

        # Attacker tampers with execution_id
        verdict_dict["execution_id"] = "tampered-exec"
        res2 = IndependentExternalVerifier.verify_oracle_verdict(verdict_dict, secret)
        assert res2.is_valid is False
        assert any("FORGED_VERDICT_SEAL" in v for v in res2.violations)

    def test_attack_063_direct_verified_real_success_injection(self):
        """ATTACK-063: Direct injection of unsealed VERIFIED_REAL_SUCCESS is rejected."""
        secret = os.urandom(32)
        unsealed_verdict = {
            "status": "VERIFIED_REAL_SUCCESS",
            "is_acceptable": True,
            "execution_id": "exec-injected",
            "evidence_id": "ev-injected",
            "violations": [],
            "seal": None,
        }

        res = IndependentExternalVerifier.verify_oracle_verdict(unsealed_verdict, secret)
        assert res.is_valid is False
        assert any("UNSEALED_VERDICT" in v for v in res.violations)

    def test_attack_064_dictionary_only_production_result(self):
        """ATTACK-064: Bare production dictionary is rejected as malformed evidence."""
        secret = os.urandom(32)
        prod_dict = {
            "status": "success",
            "title": "Sannysoft Bot Test",
            "dma_packets_sent": 25,
            "dry_run": False,
        }

        res = IndependentExternalVerifier.verify_evidence(prod_dict, {}, secret)
        assert res.is_valid is False
        assert res.status == "INCOMPLETE"
        assert any("INCOMPLETE_EVIDENCE_FIELDS" in v for v in res.violations)

    def test_attack_065_compromised_trusted_runtime_probe_simulation(self, tmp_path: Path):
        """ATTACK-065: Compromised probe creating evidence pointing to non-existent artifacts fails live audit."""
        secret = os.urandom(32)
        ghost_file = tmp_path / "ghost_screenshot.png"
        # File is NOT created on disk

        evidence = {
            "execution_id": "exec-065",
            "session_id": "sess-065",
            "evidence_id": "ev-065",
            "created_at": time.time(),
            "observed_url": "https://secure.corp",
            "observed_title": "Secure",
            "dom_observed_state": {},
            "artifact_digests": {str(ghost_file): "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
            "browser_pid": os.getpid(),
        }
        evidence["probe_signature"] = IndependentExternalVerifier.compute_probe_hmac(
            secret=secret,
            execution_id="exec-065",
            session_id="sess-065",
            evidence_id="ev-065",
            created_at=evidence["created_at"],
            observed_url="https://secure.corp",
            observed_title="Secure",
            dom_observed_state={},
            artifact_digests=evidence["artifact_digests"],
        )

        contract = {
            "execution_id": "exec-065",
            "session_id": "sess-065",
            "execution_start_time": time.time() - 1.0,
            "expected_url": "https://secure.corp",
        }

        # External verifier independently checks disk and catches missing artifact
        res = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res.is_valid is False
        assert any("ARTIFACT_NONEXISTENT" in v for v in res.violations)

    def test_attack_066_compromised_oracle_simulation(self):
        """ATTACK-066: Compromised Oracle creating VERIFIED_REAL_SUCCESS without valid secret is rejected."""
        fake_secret = b"compromised_oracle_wrong_key_12"
        correct_secret = b"master_gate_true_secret_key_123"

        # Compromised oracle seals with its wrong secret
        seal = IndependentExternalVerifier.compute_verdict_seal(
            secret=fake_secret,
            status="VERIFIED_REAL_SUCCESS",
            is_acceptable=True,
            execution_id="exec-066",
            evidence_id="ev-066",
            violations=[],
        )

        verdict_dict = {
            "status": "VERIFIED_REAL_SUCCESS",
            "is_acceptable": True,
            "execution_id": "exec-066",
            "evidence_id": "ev-066",
            "violations": [],
            "seal": seal,
        }

        # Master gate / External verifier audits using correct secret: rejected
        res = IndependentExternalVerifier.verify_oracle_verdict(verdict_dict, correct_secret)
        assert res.is_valid is False
        assert any("FORGED_VERDICT_SEAL" in v for v in res.violations)

    def test_attack_067_verifier_receives_malformed_evidence(self):
        """ATTACK-067: Supplying a string or list instead of dictionary returns MALFORMED."""
        secret = os.urandom(32)
        res = IndependentExternalVerifier.verify_evidence("corrupted_string_payload", {}, secret)
        assert res.is_valid is False
        assert res.status == "MALFORMED"

    def test_attack_068_verifier_process_receives_incomplete_evidence(self):
        """ATTACK-068: Evidence dictionary missing required fields returns INCOMPLETE."""
        secret = os.urandom(32)
        res = IndependentExternalVerifier.verify_evidence({"execution_id": "123"}, {}, secret)
        assert res.is_valid is False
        assert res.status == "INCOMPLETE"

    def test_attack_069_valid_evidence_reused_after_verification(self, tmp_path: Path):
        """ATTACK-069: Reusing evidence after successful verification is caught by replay guard."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        # First verification
        res1 = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res1.is_valid is True

        # Second verification
        res2 = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res2.is_valid is False
        assert res2.status == "REPLAY_DETECTED"

    def test_attack_070_valid_artifact_replaced_after_verification(self, tmp_path: Path):
        """ATTACK-070: Modifying artifact after verification and re-submitting fails byte check."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        art_path = list(evidence["artifact_digests"].keys())[0]

        res1 = IndependentExternalVerifier.verify_evidence(evidence, contract, secret, check_replay=False)
        assert res1.is_valid is True

        # Mutate artifact
        Path(art_path).write_bytes(b"POST_AUDIT_POISONED_BYTES")

        res2 = IndependentExternalVerifier.verify_evidence(evidence, contract, secret, check_replay=False)
        assert res2.is_valid is False
        assert any("ARTIFACT_TAMPERED" in v for v in res2.violations)


class TestRealBrowserPipelineWithExternalVerifier:
    """Real Browser Proof and Negative Pipeline Rejection Tests."""

    @pytest.mark.asyncio
    async def test_real_browser_proof_full_trust_chain(self, tmp_path: Path):
        """Full 13-step trust chain: Browser -> Probe -> Subprocess External Verifier -> Oracle -> Sealed Verdict -> Gate."""
        server = LocalTestServer()
        session_id = f"ext-sess-{int(time.time())}"
        execution_id = f"ext-exec-{int(time.time())}"
        start_time = time.time()
        screenshot_file = tmp_path / "browser_verified.png"

        try:
            async with async_playwright() as p:
                # 1. Real Chromium launch
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # 2. Navigation
                await page.goto(server.base_url)
                title = await page.title()
                assert title == "External Verifier Test Page"

                # 3. Deterministic DOM action
                await page.click("#action-trigger")
                heading_text = await page.inner_text("#status-heading")
                assert heading_text == "Action Performed"

                # 4. Screenshot artifact creation
                await page.screenshot(path=str(screenshot_file))
                assert screenshot_file.exists()
                assert screenshot_file.stat().st_size > 0

                # 5. Capture trusted observation bundle from live engine
                evidence_bundle = await TrustedRuntimeProbe.capture_observation_async(
                    page=page,
                    expected_url=server.base_url,
                    expected_title="External Verifier Test Page",
                    expected_dom_selector="#status-heading",
                    expected_dom_text="Action Performed",
                    artifact_paths=[str(screenshot_file)],
                    execution_id=execution_id,
                    session_id=session_id,
                )

                # 6. Send evidence to the independent external verifier running in a separate subprocess
                evidence_dict = {
                    "execution_id": evidence_bundle.execution_id,
                    "session_id": evidence_bundle.session_id,
                    "evidence_id": evidence_bundle.evidence_id,
                    "created_at": evidence_bundle.created_at,
                    "observed_url": evidence_bundle.observed_url,
                    "observed_title": evidence_bundle.observed_title,
                    "dom_observed_state": evidence_bundle.dom_observed_state,
                    "artifact_digests": evidence_bundle.artifact_digests,
                    "browser_pid": evidence_bundle.browser_pid,
                    "probe_signature": evidence_bundle.probe_signature,
                }

                contract_dict = {
                    "execution_id": execution_id,
                    "session_id": session_id,
                    "execution_start_time": start_time,
                    "expected_url": server.base_url,
                    "expected_title": "External Verifier Test Page",
                    "expected_dom_selector": "#status-heading",
                    "expected_dom_text": "Action Performed",
                }

                ext_result = IndependentExternalVerifier.run_in_subprocess(
                    evidence_dict=evidence_dict,
                    contract_dict=contract_dict,
                    probe_secret=TrustedRuntimeProbe._PROBE_SECRET,
                )
                assert ext_result.is_valid is True
                assert ext_result.status == "VERIFIED"
                assert len(ext_result.violations) == 0

                # 7. Send verified evidence to IndependentOracle
                contract = RuntimeEvidenceContract(
                    session_id=session_id,
                    execution_id=execution_id,
                    execution_start_time=start_time,
                    expected_url=server.base_url,
                    expected_title="External Verifier Test Page",
                    required_artifacts=[str(screenshot_file)],
                    expected_dom_selector="#status-heading",
                    expected_dom_text="Action Performed",
                    evidence=evidence_bundle,
                )

                verdict = IndependentOracle.evaluate_live_execution(
                    {"status": "success", "session_id": session_id, "artifacts": [str(screenshot_file)]},
                    contract=contract,
                )

                # 8. Produce sealed verdict
                assert verdict.status == ExecutionStatus.VERIFIED_REAL_SUCCESS
                assert verdict.is_acceptable is True
                assert verdict.seal is not None
                assert IndependentOracle.is_trusted_success(verdict)

                # 9. Send verdict to Master Gate
                gate_ok, gate_msg = verify_runtime_verdict(verdict, contract)
                assert gate_ok is True
                assert gate_msg == "VERDICT_ACCEPTED_BY_GATE"

                # 10. External verifier independently audits the sealed verdict
                verdict_res = IndependentExternalVerifier.verify_oracle_verdict(
                    verdict=verdict,
                    oracle_secret=IndependentOracle._ORACLE_SECRET,
                    contract=contract_dict,
                )
                assert verdict_res.is_valid is True

                await browser.close()
        finally:
            server.shutdown()

    def test_pipeline_rejects_fake_dictionary(self):
        """Pipeline Rejection 1: Fake dictionary is strictly rejected by both Verifier and Oracle."""
        fake = {"status": "success", "title": "Sannysoft", "dma_packets_sent": 25, "dry_run": False}
        verdict = IndependentOracle.evaluate_live_execution(fake)
        assert verdict.status != ExecutionStatus.VERIFIED_REAL_SUCCESS

        ext_res = IndependentExternalVerifier.verify_evidence(fake, {}, b"dummy")
        assert ext_res.is_valid is False

    def test_pipeline_rejects_fake_artifact(self, tmp_path: Path):
        """Pipeline Rejection 2: Fake artifact path that does not exist is rejected."""
        fake_ev = {
            "execution_id": "e", "session_id": "s", "evidence_id": "ev", "created_at": time.time(),
            "observed_url": "u", "observed_title": "t", "dom_observed_state": {},
            "artifact_digests": {str(tmp_path / "nonexistent.png"): "abc"},
            "probe_signature": "sig",
        }
        res = IndependentExternalVerifier.verify_evidence(fake_ev, {"execution_id": "e", "session_id": "s"}, b"sec")
        assert res.is_valid is False
        assert any("ARTIFACT_NONEXISTENT" in v for v in res.violations)

    def test_pipeline_rejects_modified_artifact(self, tmp_path: Path):
        """Pipeline Rejection 3: Modifying artifact bytes after hashing is rejected."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)
        art_path = list(evidence["artifact_digests"].keys())[0]
        Path(art_path).write_bytes(b"TAMPERED")

        res = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res.is_valid is False
        assert any("ARTIFACT_TAMPERED" in v for v in res.violations)

    def test_pipeline_rejects_replayed_evidence(self, tmp_path: Path):
        """Pipeline Rejection 4: Replaying consumed evidence bundle is rejected."""
        secret = os.urandom(32)
        evidence, contract = create_sample_evidence_bundle(tmp_path, secret)

        res1 = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res1.is_valid is True
        res2 = IndependentExternalVerifier.verify_evidence(evidence, contract, secret)
        assert res2.is_valid is False
        assert res2.status == "REPLAY_DETECTED"

    def test_pipeline_rejects_modified_verdict(self):
        """Pipeline Rejection 5: Modifying fields on a sealed verdict fails Master Gate."""
        forged = OracleVerdict(
            status=ExecutionStatus.VERIFIED_REAL_SUCCESS,
            is_acceptable=True,
            reason="Forged",
            evidence={},
            violations=[],
            execution_id="exec-mod",
            evidence_id="ev-mod",
            seal="fake-seal",
        )
        gate_ok, msg = verify_runtime_verdict(forged)
        assert gate_ok is False
        assert "GATE_REJECT" in msg
