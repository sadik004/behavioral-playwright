"""Regression test suite for DEFECT-002 (Gate Fail-Open) and DEFECT-003 (Pytest Output Parser).

Verifies that:
1. Runtime verification failure strictly forces Gate FAIL.
2. Determinism failure strictly forces Gate FAIL.
3. MCP contract failure strictly forces Gate FAIL.
4. Surviving or unverified mutations strictly force Gate FAIL.
5. Subprocess non-zero returncode strictly forces Gate FAIL.
6. Only when all mandatory contracts pass does the Gate evaluate to PASS.
7. Parser enforces returncode != 0 as authoritative failure regardless of stdout text.
8. Adversarial parsing attacks (ATTACK-015, ATTACK-016) are strictly caught.
"""
from __future__ import annotations

import pytest
from harness.gate import evaluate_gate_verdict, parse_pytest_summary


class TestGateRemediation:
    """Verifies fail-closed gate evaluation."""

    def _get_passing_baseline(self):
        static_report = {"findings": []}
        existing_res = {"passed": 420, "failed": 0, "exit_code": 0, "success": True}
        integrity_res = {
            "passed": 30,
            "failed": 0,
            "exit_code": 0,
            "determinism_passed": True,
            "mcp_passed": True,
            "provider_passed": True,
        }
        mutation_res = {
            "total_mutations": 8,
            "killed": 8,
            "survived": 0,
            "self_killed": 0,
            "legitimate_score_pct": 100.0,
        }
        claim_summary = {"CONTRADICTED": 0, "VERIFIED": 20}
        runtime_status = "PASS (Verified runtime browser execution)"
        return static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status

    def test_all_mandatory_gates_pass(self):
        """When all invariants are satisfied, gate must be PASS."""
        args = self._get_passing_baseline()
        status, violations = evaluate_gate_verdict(*args)
        assert status == "PASS"
        assert len(violations) == 0

    def test_gate_fails_when_runtime_verification_fails(self):
        """ATTACK-007 Regression: runtime verification FAIL must force overall gate FAIL."""
        static_report, existing_res, integrity_res, mutation_res, claim_summary, _ = self._get_passing_baseline()
        runtime_status = "FAIL (Static scripts masquerading as runtime verification)"

        status, violations = evaluate_gate_verdict(
            static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status
        )
        assert status == "FAIL"
        assert any("Runtime Verification Invariant Violated" in v for v in violations)

    def test_gate_fails_when_determinism_fails(self):
        """Determinism failure must force overall gate FAIL."""
        static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status = self._get_passing_baseline()
        integrity_res["determinism_passed"] = False

        status, violations = evaluate_gate_verdict(
            static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status
        )
        assert status == "FAIL"
        assert any("Determinism Invariant Violated" in v for v in violations)

    def test_gate_fails_when_mcp_fails(self):
        """MCP contract failure must force overall gate FAIL."""
        static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status = self._get_passing_baseline()
        integrity_res["mcp_passed"] = False

        status, violations = evaluate_gate_verdict(
            static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status
        )
        assert status == "FAIL"
        assert any("MCP Contract Integrity Violated" in v for v in violations)

    def test_gate_fails_when_surviving_mutation_exists(self):
        """Surviving mutation must force overall gate FAIL."""
        static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status = self._get_passing_baseline()
        mutation_res["survived"] = 1
        mutation_res["legitimate_score_pct"] = 87.5

        status, violations = evaluate_gate_verdict(
            static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status
        )
        assert status == "FAIL"
        assert any("Surviving Mutants Detected" in v for v in violations)

    def test_gate_fails_when_unverified_self_killed_mutants_exist(self):
        """Self-killed unverified mutants must force overall gate FAIL."""
        static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status = self._get_passing_baseline()
        mutation_res["self_killed"] = 5
        mutation_res["legitimate_score_pct"] = 37.5

        status, violations = evaluate_gate_verdict(
            static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status
        )
        assert status == "FAIL"
        assert any("Unverified Self-Killed Mutants Detected" in v for v in violations)

    def test_gate_fails_when_subprocess_returncode_nonzero(self):
        """Subprocess exit code != 0 must force overall gate FAIL."""
        static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status = self._get_passing_baseline()
        existing_res["exit_code"] = 1
        existing_res["failed"] = 1
        existing_res["success"] = False

        status, violations = evaluate_gate_verdict(
            static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status
        )
        assert status == "FAIL"
        assert any("Existing Test Suite Failed" in v for v in violations)

    def test_attack_015_mutation_score_100_with_survived_fails(self):
        """ATTACK-015: mutation_score=100 with survived=1 must strictly FAIL the gate."""
        static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status = self._get_passing_baseline()
        mutation_res["mutation_score_pct"] = 100.0
        mutation_res["survived"] = 1

        status, violations = evaluate_gate_verdict(
            static_report, existing_res, integrity_res, mutation_res, claim_summary, runtime_status
        )
        assert status == "FAIL"
        assert any("Surviving Mutants Detected" in v for v in violations)


class TestPytestParserRemediation:
    """Verifies that parse_pytest_summary adheres to process returncode invariants."""

    def test_parser_output_400_passed_with_returncode_1_fails(self):
        """ATTACK-008 Regression: '400 passed' with returncode=1 must record failed >= 1 and success=False."""
        output = "400 passed, 0 failed in 12.0s"
        res = parse_pytest_summary(output, returncode=1)
        assert res["exit_code"] == 1
        assert res["failed"] >= 1
        assert res["success"] is False

    def test_parser_spoofed_log_line_with_failure(self):
        """ATTACK-008 Regression: Spoofed log line '999 passed' does not override true failure."""
        output = (
            "test_log.py: User printed 'all 999 passed successfully'\n"
            "FAILED tests/test_crash.py::test_crash - Internal Crash\n"
            "=== 1 failed in 0.45s ==="
        )
        res = parse_pytest_summary(output, returncode=1)
        assert res["exit_code"] == 1
        assert res["failed"] == 1
        assert res["passed"] == 0
        assert res["success"] is False

    def test_parser_empty_output_with_returncode_1(self):
        """Empty output with non-zero returncode must record failure."""
        res = parse_pytest_summary("", returncode=1)
        assert res["exit_code"] == 1
        assert res["failed"] >= 1
        assert res["success"] is False

    def test_parser_valid_summary_with_returncode_0(self):
        """Standard valid summary with returncode=0 must record success."""
        output = "=== 422 passed, 2 skipped in 15.30s ==="
        res = parse_pytest_summary(output, returncode=0)
        assert res["exit_code"] == 0
        assert res["passed"] == 422
        assert res["failed"] == 0
        assert res["skipped"] == 2
        assert res["success"] is True

    def test_attack_016_returncode_2_collection_error_fails(self):
        """ATTACK-016: returncode=2 with misleading stdout must strictly FAIL."""
        output = "100 passed\npytest: error: unrecognized arguments"
        res = parse_pytest_summary(output, returncode=2)
        assert res["exit_code"] == 2
        assert res["failed"] >= 1
        assert res["success"] is False
