"""Automated Regression Battery for all 16 Adversarial Attacks (ATTACK-001 through ATTACK-016).

Authoritative proof that the hardened verification harness strictly catches every attack vector.
"""
from __future__ import annotations

from pathlib import Path
import pytest

from harness.gate import evaluate_gate_verdict, parse_pytest_summary
from harness.mutation import MutationRunner
from harness.oracle import ExecutionStatus, IndependentOracle
from harness.static_integrity import StaticIntegrityAuditor


class TestAttackBattery:
    """Complete 16-point adversarial attack battery."""

    def test_attack_001_boolean_fake_success(self):
        """ATTACK-001: Bare True must NOT be accepted as REAL_SUCCESS."""
        v = IndependentOracle.evaluate_live_execution(True)
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False
        assert any("BARE_BOOLEAN" in item for item in v.violations)

    def test_attack_002_fabricated_success_payload(self):
        """ATTACK-002: Hollow {'status': 'success'} must NOT be accepted as REAL_SUCCESS."""
        v = IndependentOracle.evaluate_live_execution({"status": "success"})
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False
        assert any("MISSING_RUNTIME_EVIDENCE" in item or "UNACCEPTABLE_STATUS" in item for item in v.violations)

    def test_attack_003_dry_run_disguise(self):
        """ATTACK-003: Both literal and flag dry_run payloads must be DRY_RUN and not acceptable."""
        v_a = IndependentOracle.evaluate_live_execution({"status": "dry_run_success"})
        assert v_a.status == ExecutionStatus.DRY_RUN
        assert v_a.is_acceptable is False

        v_b = IndependentOracle.evaluate_live_execution({"status": "success", "dry_run": True})
        assert v_b.status == ExecutionStatus.DRY_RUN
        assert v_b.is_acceptable is False

    def test_attack_004_swallowed_exception(self):
        """ATTACK-004: Swallowed exception returning success must fail failure integrity."""
        def failing():
            try:
                raise RuntimeError("Injected crash")
            except Exception:
                return dict([("status", "success")])

        v = IndependentOracle.evaluate_failure_integrity(failing, (RuntimeError,), "failing_op")
        assert v.is_acceptable is False

    def test_attack_005_and_006_mutation_runner_external_kills(self):
        """ATTACK-005 & ATTACK-006: All mutations must be EXTERNAL_KILLED with zero SELF_KILLED."""
        runner = MutationRunner()
        res = runner.run_all()
        assert res["total_mutations"] == 8
        assert res["external_killed"] == 8
        assert res["self_killed"] == 0
        assert res["survived"] == 0
        assert res["legitimate_score_pct"] == 100.0

    def test_attack_007_gate_bypass(self):
        """ATTACK-007: Runtime verification failure must strictly force gate FAIL."""
        g_status, g_viols = evaluate_gate_verdict(
            static_report={"findings": []},
            existing_res={"failed": 0, "exit_code": 0},
            integrity_res={"failed": 0, "exit_code": 0, "determinism_passed": True, "mcp_passed": True, "provider_passed": True},
            mutation_res={"survived": 0, "self_killed": 0, "legitimate_score_pct": 100.0},
            claim_summary={"CONTRADICTED": 0},
            runtime_status="FAIL (Static scripts masquerading as runtime verification)",
        )
        assert g_status == "FAIL"
        assert any("Runtime Verification Invariant Violated" in v for v in g_viols)

    def test_attack_008_pytest_output_parser(self):
        """ATTACK-008: Subprocess exit code != 0 must force failure regardless of passed count."""
        parsed = parse_pytest_summary("400 passed, 0 failed in 12.0s", returncode=1)
        assert parsed["exit_code"] == 1
        assert parsed["failed"] >= 1
        assert parsed["success"] is False

    def test_attack_009_fake_test_pass(self):
        """ATTACK-009: assert True is strictly detected as P0 by static auditor."""
        auditor = StaticIntegrityAuditor(Path("tests/test_mock.py"), Path("."))
        findings = auditor.audit("def test_mock():\n    assert True\n")
        assert any(f.rule_id == "WEAK-TEST-001" and f.severity == "P0" for f in findings)

    def test_attack_010_missing_runtime_evidence(self):
        """ATTACK-010: Missing runtime evidence flags MISSING_RUNTIME_EVIDENCE."""
        payload = {"status": "success", "mode": "standard", "count": 10}
        v = IndependentOracle.evaluate_live_execution(payload)
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False

    def test_attack_011_success_flag(self):
        """ATTACK-011: {'status': 'success', 'success': True} without observables is rejected."""
        v = IndependentOracle.evaluate_live_execution({"status": "success", "success": True})
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False

    def test_attack_012_provider_available(self):
        """ATTACK-012: {'status': 'ok', 'provider_available': True} without browser evidence is rejected."""
        v = IndependentOracle.evaluate_live_execution({"status": "ok", "provider_available": True})
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False

    def test_attack_013_nested_success(self):
        """ATTACK-013: {'result': {'status': 'success'}} without browser evidence is rejected."""
        v = IndependentOracle.evaluate_live_execution({"result": {"status": "success"}})
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False

    def test_attack_014_indirect_variable_exception(self):
        """ATTACK-014: Indirect variable assignment in except handler is caught as P0 FRAUD-001."""
        code = (
            "def op():\n"
            "    payload = {'status': 'success'}\n"
            "    try:\n"
            "        pass\n"
            "    except Exception:\n"
            "        return payload\n"
        )
        auditor = StaticIntegrityAuditor(Path("src/op.py"), Path("."))
        findings = auditor.audit(code)
        assert any(f.rule_id == "FRAUD-001" and f.severity == "P0" for f in findings)

    def test_attack_015_gate_survived_mutation(self):
        """ATTACK-015: mutation_score=100 with survived=1 must strictly FAIL the gate."""
        g_status, g_viols = evaluate_gate_verdict(
            static_report={"findings": []},
            existing_res={"failed": 0, "exit_code": 0},
            integrity_res={"failed": 0, "exit_code": 0, "determinism_passed": True, "mcp_passed": True, "provider_passed": True},
            mutation_res={"survived": 1, "self_killed": 0, "mutation_score_pct": 100.0, "legitimate_score_pct": 87.5},
            claim_summary={"CONTRADICTED": 0},
            runtime_status="PASS",
        )
        assert g_status == "FAIL"
        assert any("Surviving Mutants Detected" in v for v in g_viols)

    def test_attack_016_subprocess_exit_code_2(self):
        """ATTACK-016: returncode=2 with misleading stdout must strictly FAIL."""
        parsed = parse_pytest_summary("100 passed", returncode=2)
        assert parsed["exit_code"] == 2
        assert parsed["failed"] >= 1
        assert parsed["success"] is False

    def test_attack_017_fake_runtime_artifact(self):
        """ATTACK-017: Fake artifact payload without physical file is strictly rejected."""
        payload = {"status": "success", "title": "Fake Page", "url": "https://fake.example", "artifacts": ["fake.png"]}
        v = IndependentOracle.evaluate_live_execution(payload)
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False
        assert any("FAKE_ARTIFACT_NONEXISTENT" in item for item in v.violations)

    def test_attack_018_fake_url_without_navigation(self):
        """ATTACK-018: URL claimed without browser navigation is strictly rejected."""
        payload = {"status": "success", "url": "https://example.com"}
        v = IndependentOracle.evaluate_live_execution(payload)
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False
        assert any("UNVERIFIED_CLAIMED_NAVIGATION" in item for item in v.violations)

    def test_attack_019_fake_screenshot_path(self):
        """ATTACK-019: Nonexistent screenshot path is strictly rejected."""
        payload = {"status": "success", "artifacts": ["/tmp/fake-screenshot.png"]}
        v = IndependentOracle.evaluate_live_execution(payload)
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False
        assert any("FAKE_ARTIFACT_NONEXISTENT" in item for item in v.violations)

    def test_attack_020_stale_artifact(self, tmp_path):
        """ATTACK-020: Stale artifact from previous execution is strictly rejected."""
        import os, time
        from harness.oracle import RuntimeEvidenceContract
        stale_file = tmp_path / "stale.png"
        stale_file.write_bytes(b"data")
        past = time.time() - 100.0
        os.utime(str(stale_file), (past, past))

        t_now = time.time()
        contract = RuntimeEvidenceContract(session_id="sess_20", execution_start_time=t_now, required_artifacts=[str(stale_file)], post_operation_verified=True)
        v = IndependentOracle.evaluate_live_execution({"status": "success", "artifacts": [str(stale_file)]}, contract=contract)
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False
        assert any("STALE_ARTIFACT_REPLAY" in item for item in v.violations)

    def test_attack_021_wrong_page_evidence(self):
        """ATTACK-021: Evidence from Page A claiming Page B succeeded is rejected."""
        from harness.oracle import RuntimeEvidenceContract
        class MockPageA:
            def is_closed(self): return False
            url = "https://page-a.example"
            def title(self): return "Page A"

        contract = RuntimeEvidenceContract(session_id="sess_21", execution_start_time=100.0, expected_url="https://page-b.example", live_page=MockPageA(), post_operation_verified=True)
        v = IndependentOracle.evaluate_live_execution({"status": "success"}, contract=contract)
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False
        assert any("WRONG_PAGE_EVIDENCE" in item for item in v.violations)

    def test_attack_022_browser_closed_before_verification(self):
        """ATTACK-022: Closed browser before post-op verification is rejected."""
        from harness.oracle import RuntimeEvidenceContract
        class ClosedPage:
            def is_closed(self): return True

        contract = RuntimeEvidenceContract(session_id="sess_22", execution_start_time=100.0, live_page=ClosedPage(), post_operation_verified=True)
        v = IndependentOracle.evaluate_live_execution({"status": "success"}, contract=contract)
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False
        assert any("BROWSER_CLOSED_BEFORE_VERIFICATION" in item for item in v.violations)

    def test_attack_023_navigation_never_happened(self):
        """ATTACK-023: Browser on about:blank with claimed target URL is rejected."""
        from harness.oracle import RuntimeEvidenceContract
        class BlankPage:
            def is_closed(self): return False
            url = "about:blank"
            def title(self): return ""

        contract = RuntimeEvidenceContract(session_id="sess_23", execution_start_time=100.0, expected_url="https://target.corp", live_page=BlankPage(), post_operation_verified=True)
        v = IndependentOracle.evaluate_live_execution({"status": "success", "url": "https://target.corp"}, contract=contract)
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False
        assert any("NAVIGATION_NEVER_HAPPENED" in item for item in v.violations)

    def test_attack_024_dom_evidence_forgery(self):
        """ATTACK-024: Claimed DOM mutation without live DOM element is rejected."""
        from harness.oracle import RuntimeEvidenceContract
        class StaticPage:
            def is_closed(self): return False
            url = "https://app.test"
            def title(self): return "App"
            def query_selector(self, s): return None

        contract = RuntimeEvidenceContract(session_id="sess_24", execution_start_time=100.0, expected_dom_selector="#checkout", live_page=StaticPage(), post_operation_verified=True)
        v = IndependentOracle.evaluate_live_execution({"status": "success", "dom_mutations": 1}, contract=contract)
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False
        assert any("DOM_EVIDENCE_FORGERY" in item for item in v.violations)

    def test_attack_025_cross_session_evidence(self):
        """ATTACK-025: Cross-session evidence injection is rejected."""
        from harness.oracle import RuntimeEvidenceContract
        contract = RuntimeEvidenceContract(session_id="session-B", execution_start_time=100.0, post_operation_verified=True)
        v = IndependentOracle.evaluate_live_execution({"status": "success", "session_id": "session-A"}, contract=contract)
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False
        assert any("CROSS_SESSION_EVIDENCE_LEAK" in item for item in v.violations)

    def test_attack_026_timestamp_replay(self):
        """ATTACK-026: Reusing stale timestamp from past operation is rejected."""
        from harness.oracle import RuntimeEvidenceContract
        contract = RuntimeEvidenceContract(session_id="sess_26", execution_start_time=2000.0, post_operation_verified=True)
        v = IndependentOracle.evaluate_live_execution({"status": "success", "timestamp": 1000.0}, contract=contract)
        assert v.status != ExecutionStatus.REAL_SUCCESS
        assert v.is_acceptable is False
        assert any("TIMESTAMP_REPLAY_DETECTED" in item for item in v.violations)

