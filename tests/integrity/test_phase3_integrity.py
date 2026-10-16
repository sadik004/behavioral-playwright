"""Phase 3 Integrity & Regression Tests
Validates fixes for:
- stealth_session.py: human_click and human_type loud failure propagation (eliminating fake success)
- schema_guard.py: verify_page_integrity exception propagation (eliminating silent empty DOM audit)
- dma_kernel_bridge.py: hardware gating contract and simulation fallback validation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from behavioral_evasion_suite.stealth_session import human_click, human_type
from src.behavioral_playwright.powerplay.schema_guard import ResolvedSchemaIntegrityGuard
from behavioral_evasion_suite.dma_kernel_bridge import FPGAPCIeDMAHardwareBridge


class TestPhase3Integrity:
    """Verifies that fake success, silent fallbacks, and swallowed errors are killed."""

    @pytest.mark.asyncio
    async def test_human_click_propagates_click_failure(self):
        """human_click must propagate errors when page.click fails, never swallowing or faking success."""
        mock_page = MagicMock()
        mock_page.click = AsyncMock(side_effect=RuntimeError("Element #missing-btn not found"))

        with pytest.raises(RuntimeError, match="Element #missing-btn not found"):
            await human_click(mock_page, "#missing-btn")

    @pytest.mark.asyncio
    async def test_human_type_propagates_type_failure(self):
        """human_type must propagate errors when page.type fails, never swallowing or faking success."""
        mock_page = MagicMock()
        mock_page.type = AsyncMock(side_effect=ValueError("Input field is disabled"))

        with pytest.raises(ValueError, match="Input field is disabled"):
            await human_type(mock_page, "#disabled-input", "test text")

    @pytest.mark.asyncio
    async def test_verify_page_integrity_propagates_crashed_page_content(self):
        """verify_page_integrity must propagate page crash exceptions instead of auditing empty string."""
        guard = ResolvedSchemaIntegrityGuard()
        mock_page = MagicMock()
        mock_page.content = AsyncMock(side_effect=RuntimeError("Page crashed / CDP session closed"))

        with pytest.raises(RuntimeError, match="Page crashed / CDP session closed"):
            await guard.verify_page_integrity(mock_page)

    def test_dma_hardware_bridge_hardware_gating_simulation_fallback(self):
        """FPGAPCIeDMAHardwareBridge must honestly declare is_connected=False and use simulation fallback."""
        bridge = FPGAPCIeDMAHardwareBridge(dma_device_path="/dev/nonexistent_screamer_pcie")
        assert bridge.is_connected is False, "Bridge must not claim connected status without physical hardware"
        # Trajectory generation in simulation mode must produce valid HID packets
        trajectory = [{"x": 100.0, "y": 100.0}, {"x": 105.0, "y": 108.0}]
        packets = bridge.inject_hardware_mouse_move(trajectory)
        assert len(packets) == 1, "Must generate exactly 1 packet for 2-point trajectory in fallback mode"
        assert len(packets[0]) == 3, "USB HID mouse packet must be 3 bytes"
