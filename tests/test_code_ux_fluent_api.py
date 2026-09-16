"""
Unit and Integration Tests for Code UX, Presets, and Fluent Developer API (v6.0.0 Level 5 Quantum Edition)
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from behavioral_evasion_suite import (
    Preset,
    StealthConfig,
    StealthBrowser,
    StealthPage,
    UnifiedQuantumFacade
)


def test_presets_initialization():
    """Verify presets factory and overrides."""
    cfg_max = StealthConfig.from_preset(Preset.MAX_QUANTUM)
    assert cfg_max.enable_worker_shield is True
    assert cfg_max.use_kernel_input is True
    assert cfg_max.enable_subpixel_font_shield is True

    cfg_fast = StealthConfig.from_preset(Preset.FAST_BYPASS, proxy="socks5://localhost:1080")
    assert cfg_fast.enable_worker_shield is False
    assert cfg_fast.use_kernel_input is False
    assert cfg_fast.proxy == "socks5://localhost:1080"

    cfg_headless = StealthConfig.from_preset(Preset.HEADLESS_UNDETECTABLE)
    assert cfg_headless.headless is True
    assert cfg_headless.enable_v8_shield is True

    cfg_custom = StealthConfig.from_preset("balanced", custom_flag=True)
    assert cfg_custom.custom_options.get("custom_flag") is True


@pytest.mark.asyncio
async def test_stealth_page_delegation_and_kinematics():
    """Verify that StealthPage proxies native methods and provides human actions."""
    mock_raw_page = AsyncMock()
    mock_raw_page.url = "https://example.com"
    mock_raw_page.title = AsyncMock(return_value="Example Domain")
    mock_raw_page.goto = AsyncMock(return_value=None)
    mock_raw_page.content = AsyncMock(return_value="<html><body><h1>Test</h1></body></html>")
    mock_raw_page.evaluate = AsyncMock(return_value={"title": "Test", "elements": []})

    facade = UnifiedQuantumFacade()
    config = StealthConfig.from_preset(Preset.MAX_QUANTUM)

    page = StealthPage(mock_raw_page, facade, config)

    # 1. Test attribute delegation
    assert page.url == "https://example.com"
    await page.goto("https://example.com")
    mock_raw_page.goto.assert_awaited_once_with("https://example.com")

    title = await page.title()
    assert title == "Example Domain"

    # 2. Test raw_page accessor
    assert page.raw_page is mock_raw_page

    # 3. Test human_scroll
    with patch("behavioral_evasion_suite.stealth_browser.human_scroll", new_callable=AsyncMock) as mock_scroll:
        await page.human_scroll(delta_y=400, duration_s=0.5)
        mock_scroll.assert_awaited_once_with(mock_raw_page, delta_y=400, duration_s=0.5)

    # 4. Test cognitive_pause
    with patch("behavioral_evasion_suite.stealth_browser.cognitive_reading_pause", new_callable=AsyncMock) as mock_pause:
        await page.cognitive_pause(min_seconds=0.1, max_seconds=0.2)
        mock_pause.assert_awaited_once_with(0.1, 0.2)

    # 5. Test extract_compact_dom
    tree = await page.extract_compact_dom()
    assert isinstance(tree, dict)
    assert "elements" in tree


def test_stealth_browser_factory():
    """Verify that StealthBrowser initializes with fluent parameters."""
    browser = StealthBrowser.launch(preset=Preset.MAX_QUANTUM, headless=True)
    assert browser.config.preset == Preset.MAX_QUANTUM
    assert browser.config.headless is True
    assert isinstance(browser.facade, UnifiedQuantumFacade)
