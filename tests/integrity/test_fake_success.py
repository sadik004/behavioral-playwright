"""Adversarial Fake-Success & Evasion Integrity Verification Suite.

Tests specifically designed to expose:
1. Dry-run disguised as live success (Rule 10).
2. Swallowed exceptions converted into status: "dry_run_success" (Rule 11).
3. Weak test assertion traps (`assert "success" in status`).
4. Static JavaScript presence mistakenly treated as runtime verification.
5. Simulated hardware/DMA reporting physical execution without hardware.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from harness.oracle import ExecutionStatus, IndependentOracle
from behavioral_evasion_suite.powerhand_master import PowerHandMaster, PowerHandPlaywrightRunner


class TestFakeSuccessDetection:
    """Verifies that the system and oracle strictly detect and reject fake success."""

    def test_dry_run_is_never_classified_as_real_success(self):
        """Rule 10: A successful dry-run must NEVER count as REAL_SUCCESS."""
        dry_run_payload = {
            "status": "dry_run_success",
            "trajectory_points": 25,
            "dma_packets_generated": 25,
            "keystroke_events": 50,
            "stealth_payload_bytes": 1024,
        }

        verdict = IndependentOracle.evaluate_live_execution(dry_run_payload)
        assert verdict.status == ExecutionStatus.DRY_RUN
        assert not verdict.is_acceptable, "Oracle must reject dry_run_success as acceptable live execution"
        assert any("DRY_RUN_DISGUISED_AS_LIVE" in v for v in verdict.violations)

    def test_substring_assertion_weakness_demonstration(self):
        """Demonstrates the fatal flaw in existing test `assert 'success' in res['status']`.

        When live browser execution crashes, the runner returns 'dry_run_success'.
        A naive test checking `'success' in res['status']` evaluates to True,
        falsely certifying broken live automation as working!
        """
        failed_live_result = {"status": "dry_run_success", "error": "Playwright process failed"}

        # Flawed existing assertion pattern passes:
        flawed_check = "success" in failed_live_result["status"]
        assert flawed_check is True, "Demonstrates that naive substring check passes on failure"

        # Independent Oracle correctly falsifies and rejects it:
        verdict = IndependentOracle.evaluate_live_execution(failed_live_result)
        assert verdict.status == ExecutionStatus.DRY_RUN
        assert verdict.is_acceptable is False

    @pytest.mark.asyncio
    async def test_powerhand_runner_catches_browser_crash_and_returns_dry_run(self):
        """Injected Playwright browser failure must be classified as failure, NOT live success."""
        runner = PowerHandPlaywrightRunner(seed=12345)

        # Mock playwright launch to raise an unhandled browser crash
        with patch("playwright.async_api.async_playwright") as mock_playwright:
            mock_playwright.side_effect = RuntimeError("GPU crash / Chromium SIGKILL")

            result = await runner.execute_stealth_session("https://example.com")

            # Implementation now returns status: 'failed' with error details preserved
            assert result.get("status") == "failed"
            assert "GPU crash" in result.get("error", "")

            # Independent Oracle must flag this as REAL_FAILURE and NOT REAL_SUCCESS
            verdict = IndependentOracle.evaluate_live_execution(result)
            assert verdict.status == ExecutionStatus.REAL_FAILURE
            assert verdict.is_acceptable is False, "A crash must fail live integrity gate"

    def test_static_script_presence_is_not_runtime_execution(self):
        """Phase 10: Presence of JS tokens does not prove runtime browser bypass.

        Verifies that get_all_stealth_scripts() is purely a string factory,
        not a validated runtime execution proof.
        """
        master = PowerHandMaster(seed=42)
        scripts = master.get_all_stealth_scripts()

        assert isinstance(scripts, str)
        assert len(scripts) > 0

        # Presence of tokens is purely STATIC
        required_tokens = ["window", "prototype"]
        for token in required_tokens:
            assert token in scripts, f"Missing static token: {token}"

        # Oracle classification: String generation is STATIC_VERIFIED, NOT RUNTIME_VERIFIED
        oracle_status = IndependentOracle.classify_status_payload(
            {"mode": "static_script_bundle", "bytes": len(scripts)}
        )
        assert oracle_status != ExecutionStatus.REAL_SUCCESS

    def test_dma_hardware_bridge_without_pcie_device_is_simulation_only(self):
        """Verifies that FPGAPCIeDMAHardwareBridge does not claim physical kernel execution when /dev/pcie_dma0 is absent."""
        from behavioral_evasion_suite.dma_kernel_bridge import FPGAPCIeDMAHardwareBridge

        bridge = FPGAPCIeDMAHardwareBridge(dma_device_path="/nonexistent/pcie_dma_hardware")
        assert bridge.is_connected is False
        saccade_points = [
            {"x": 100.0, "y": 200.0, "timestamp_ms": 0.0},
            {"x": 110.0, "y": 210.0, "timestamp_ms": 15.0},
        ]
        packets = bridge.inject_hardware_mouse_move(saccade_points)

        # Packets are generated in memory (simulation), not physically sent across PCIe bus
        assert isinstance(packets, list)
        assert len(packets) == 1
        # Bridge must be classified as SIMULATION / FALLBACK
        status = IndependentOracle.classify_status_payload({"simulated": True, "packets": len(packets)})
        assert status == ExecutionStatus.SIMULATION
