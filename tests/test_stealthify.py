"""
Unit and Integration Tests for Universal Stealthify & Autonomous Challenge Solver
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from behavioral_evasion_suite import (
    stealthify,
    AutonomousChallengeSolver,
    Preset,
    StealthPage
)


@pytest.mark.asyncio
async def test_stealthify_wrapper_and_delegation():
    """Verify stealthify patches page, injects shields, and binds helpers."""
    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.goto = AsyncMock(return_value=None)
    mock_page.title = AsyncMock(return_value="Protected Portal")
    mock_page.add_init_script = AsyncMock(return_value=None)
    mock_page.query_selector = AsyncMock(return_value=None)

    # Apply stealthify
    stealth_page = await stealthify(mock_page, preset=Preset.MAX_QUANTUM)

    assert isinstance(stealth_page, StealthPage)
    assert stealth_page.url == "https://example.com"
    title = await stealth_page.title()
    assert title == "Protected Portal"

    # Verify custom methods exist
    assert hasattr(stealth_page, "human_click")
    assert hasattr(stealth_page, "human_type")
    assert hasattr(stealth_page, "human_scroll")
    assert hasattr(stealth_page, "auto_resolve_challenge")
    assert hasattr(stealth_page, "detect_challenge")


@pytest.mark.asyncio
async def test_autonomous_challenge_detection_and_resolution():
    """Verify autonomous detection and neuromuscular solver for Turnstile."""
    mock_page = AsyncMock()
    mock_element = AsyncMock()
    mock_element.bounding_box = AsyncMock(return_value={"x": 100, "y": 200, "width": 300, "height": 65})

    async def mock_query_selector(sel):
        if "turnstile" in sel:
            return mock_element
        return None

    mock_page.query_selector = mock_query_selector

    solver = AutonomousChallengeSolver(facade=AsyncMock())
    solver.facade.kinematics.human_click_coords = AsyncMock(return_value=None)

    # 1. Test challenge detection
    detected = await solver.detect_challenge(mock_page)
    assert detected is not None
    assert detected["type"] == "turnstile"
    assert detected["box"]["width"] == 300

    # 2. Test auto_resolve
    with patch("behavioral_evasion_suite.stealthify.cognitive_reading_pause", new_callable=AsyncMock):
        # Emulate resolved on second poll
        call_count = 0
        async def mock_query_disappearing(sel):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return mock_element
            return None
        mock_page.query_selector = mock_query_disappearing

        res = await solver.auto_resolve(mock_page)
        assert res is True
        solver.facade.kinematics.human_click_coords.assert_awaited()
