"""Independent verifier for MUT-003: PowerHand Status Mutation."""
import pytest
from behavioral_evasion_suite.powerhand_master import PowerHandPlaywrightRunner
from harness.oracle import IndependentOracle, ExecutionStatus


@pytest.mark.asyncio
async def test_powerhand_dry_run_must_report_dry_run_success():
    """Dry run execution must return status='dry_run_success' and never claimed live success."""
    runner = PowerHandPlaywrightRunner(seed=42)
    res = await runner.execute_stealth_session("about:blank", dry_run=True)
    assert res.get("status") == "dry_run_success", f"Expected dry_run_success, got {res.get('status')}"
    assert res.get("dry_run") is True
    # Independent oracle contract:
    status = IndependentOracle.classify_status_payload(res)
    assert status == ExecutionStatus.DRY_RUN
    assert status != ExecutionStatus.REAL_SUCCESS
