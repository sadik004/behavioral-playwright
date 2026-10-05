"""Regression test suite for DEFECT-001: Oracle Fabricated REAL_SUCCESS remediation.

Ensures that:
1. Bare boolean True is never accepted as REAL_SUCCESS.
2. Bare {"status": "success"} without runtime evidence is rejected.
3. Payloads missing runtime artifacts fail live execution evaluation.
4. Literal "dry_run_success" is strictly classified as DRY_RUN.
5. Payloads with dry_run=True are strictly classified as DRY_RUN.
6. Adversarial variants (ATTACK-011, ATTACK-012, ATTACK-013) are strictly caught.
7. Truly verified runtime execution with observables is correctly accepted.
"""
from __future__ import annotations

import pytest
from harness.oracle import ExecutionStatus, IndependentOracle


class TestOracleRemediation:
    """Verifies that IndependentOracle strictly enforces observable runtime evidence."""

    def test_boolean_true_is_not_real_success(self):
        """ATTACK-001 Regression: bare True must not establish REAL_SUCCESS."""
        status = IndependentOracle.classify_status_payload(True)
        assert status != ExecutionStatus.REAL_SUCCESS
        assert status == ExecutionStatus.UNKNOWN

        verdict = IndependentOracle.evaluate_live_execution(True)
        assert verdict.status != ExecutionStatus.REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert any("BARE_BOOLEAN" in v for v in verdict.violations)

    def test_bare_success_payload_is_not_real_success(self):
        """ATTACK-002 Regression: {'status': 'success'} without evidence is not REAL_SUCCESS."""
        payload = {"status": "success"}
        status = IndependentOracle.classify_status_payload(payload)
        assert status != ExecutionStatus.REAL_SUCCESS

        verdict = IndependentOracle.evaluate_live_execution(payload)
        assert verdict.status != ExecutionStatus.REAL_SUCCESS
        assert verdict.is_acceptable is False
        assert any("MISSING_RUNTIME_EVIDENCE" in v or "UNACCEPTABLE_STATUS" in v for v in verdict.violations)

    def test_success_without_runtime_evidence_is_rejected(self):
        """ATTACK-010 Regression: claimed success without browser/DOM/artifacts is rejected."""
        payload = {"status": "success", "mode": "standard", "duration_ms": 120}
        status = IndependentOracle.classify_status_payload(payload)
        assert status != ExecutionStatus.REAL_SUCCESS

        verdict = IndependentOracle.evaluate_live_execution(payload)
        assert verdict.is_acceptable is False
        assert any("MISSING_RUNTIME_EVIDENCE" in v or "UNACCEPTABLE_STATUS" in v for v in verdict.violations)

    def test_dry_run_success_is_never_real_success(self):
        """ATTACK-003 Variant A Regression: literal dry_run_success is DRY_RUN."""
        payload = {"status": "dry_run_success", "trajectory_points": 25}
        status = IndependentOracle.classify_status_payload(payload)
        assert status == ExecutionStatus.DRY_RUN

        verdict = IndependentOracle.evaluate_live_execution(payload)
        assert verdict.status == ExecutionStatus.DRY_RUN
        assert verdict.is_acceptable is False
        assert any("DRY_RUN_DISGUISED_AS_LIVE" in v for v in verdict.violations)

    def test_success_with_dry_run_flag_is_rejected(self):
        """ATTACK-003 Variant B Regression: status='success' with dry_run=True must be DRY_RUN."""
        payload = {"status": "success", "dry_run": True, "title": "Example Domain"}
        status = IndependentOracle.classify_status_payload(payload)
        assert status == ExecutionStatus.DRY_RUN

        verdict = IndependentOracle.evaluate_live_execution(payload)
        assert verdict.status == ExecutionStatus.DRY_RUN
        assert verdict.is_acceptable is False

    def test_attack_011_success_flag_without_evidence_rejected(self):
        """ATTACK-011: {'status': 'success', 'success': True} without evidence must be rejected."""
        payload = {"status": "success", "success": True}
        status = IndependentOracle.classify_status_payload(payload)
        assert status != ExecutionStatus.REAL_SUCCESS

        verdict = IndependentOracle.evaluate_live_execution(payload)
        assert verdict.is_acceptable is False

    def test_attack_012_provider_available_without_browser_evidence_rejected(self):
        """ATTACK-012: {'status': 'ok', 'provider_available': True} without evidence is not REAL_SUCCESS."""
        payload = {"status": "ok", "provider_available": True}
        status = IndependentOracle.classify_status_payload(payload)
        assert status != ExecutionStatus.REAL_SUCCESS

        verdict = IndependentOracle.evaluate_live_execution(payload)
        assert verdict.is_acceptable is False

    def test_attack_013_nested_success_without_evidence_rejected(self):
        """ATTACK-013: {'result': {'status': 'success'}} without evidence must be rejected."""
        payload = {"result": {"status": "success"}}
        status = IndependentOracle.classify_status_payload(payload)
        assert status != ExecutionStatus.REAL_SUCCESS

        verdict = IndependentOracle.evaluate_live_execution(payload)
        assert verdict.is_acceptable is False

    def test_legitimate_live_execution_with_runtime_evidence_accepted(self):
        """Verifies that an execution payload with real observables honestly passes as REAL_SUCCESS."""
        valid_payload = {
            "status": "success",
            "title": "Production Dashboard",
            "url": "https://app.corp.internal/dashboard",
            "artifacts": ["screenshot.png", "network_trace.json"],
            "dry_run": False,
        }
        status = IndependentOracle.classify_status_payload(valid_payload)
        assert status == ExecutionStatus.REAL_SUCCESS

        verdict = IndependentOracle.evaluate_live_execution(valid_payload)
        assert verdict.status == ExecutionStatus.REAL_SUCCESS
        assert verdict.is_acceptable is True
        assert len(verdict.violations) == 0
