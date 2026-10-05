"""Independent verifier for MUT-008: Oracle Dry Run Falsification."""
import pytest
from harness.oracle import ExecutionStatus, IndependentOracle


def test_rule_10_dry_run_is_never_real_success():
    """Rule 10 Invariant: Oracle must NEVER classify dry_run_success as REAL_SUCCESS."""
    payload = {"status": "dry_run_success", "dry_run": True}
    status = IndependentOracle.classify_status_payload(payload)
    assert status == ExecutionStatus.DRY_RUN, f"Expected DRY_RUN, got {status}"
    assert status != ExecutionStatus.REAL_SUCCESS

    verdict = IndependentOracle.evaluate_live_execution(payload)
    assert verdict.status == ExecutionStatus.DRY_RUN
    assert verdict.is_acceptable is False
