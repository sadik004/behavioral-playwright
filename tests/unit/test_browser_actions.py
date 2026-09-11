import pytest

from unittest.mock import AsyncMock, MagicMock

# Legacy sys.modules stub block removed during src-layout refactor.

from behavioral_playwright import BP
from behavioral_playwright.exceptions import ProviderUnavailableError


@pytest.fixture
def unbooted_bp():
    return BP()


@pytest.fixture
def booted_bp():
    bp = BP()
    mock_humanizer = MagicMock()
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock(return_value=None)
    mock_page.query_selector = AsyncMock(return_value=None)
    mock_page.hover = AsyncMock(return_value=None)
    mock_page.drag_and_drop = AsyncMock(return_value=None)
    mock_page.check = AsyncMock(return_value=None)
    mock_page.uncheck = AsyncMock(return_value=None)
    mock_page.select_option = AsyncMock(return_value=None)
    mock_page.press = AsyncMock(return_value=None)
    mock_page.screenshot = AsyncMock(return_value=b"fake_bytes")

    bp._humanizer = mock_humanizer
    bp._page = mock_page
    return bp


@pytest.mark.asyncio
async def test_preboot_guards(unbooted_bp):
    """Verify that calling browser methods before boot raises ProviderUnavailableError."""
    with pytest.raises(ProviderUnavailableError):
        await unbooted_bp.browser.hover("#target")

    with pytest.raises(ProviderUnavailableError):
        await unbooted_bp.browser.drag_and_drop("#src", "#dst")

    with pytest.raises(ProviderUnavailableError):
        await unbooted_bp.browser.check_checkbox("#chk")

    with pytest.raises(ProviderUnavailableError):
        await unbooted_bp.browser.select_option("#sel", "val")

    with pytest.raises(ProviderUnavailableError):
        await unbooted_bp.browser.keyboard_press("#input", "Enter")


@pytest.mark.asyncio
async def test_humanizer_delegation_when_methods_exist(booted_bp):
    """When humanizer implements specialized methods, facade must delegate to humanizer."""
    humanizer = booted_bp._humanizer
    humanizer.execute_safe_hover = AsyncMock(return_value=True)
    humanizer.execute_safe_drag_and_drop = AsyncMock(return_value=True)
    humanizer.execute_safe_check = AsyncMock(return_value=True)
    humanizer.execute_safe_select_option = AsyncMock(return_value=True)
    humanizer.execute_safe_keyboard_press = AsyncMock(return_value=True)

    assert await booted_bp.browser.hover("#btn") is True
    humanizer.execute_safe_hover.assert_awaited_once_with("#btn")
    booted_bp._page.hover.assert_not_awaited()

    assert await booted_bp.browser.drag_and_drop("#src", "#dst") is True
    humanizer.execute_safe_drag_and_drop.assert_awaited_once_with("#src", "#dst")
    booted_bp._page.drag_and_drop.assert_not_awaited()

    assert await booted_bp.browser.check_checkbox("#chk", checked=True) is True
    humanizer.execute_safe_check.assert_awaited_once_with("#chk", True)
    booted_bp._page.check.assert_not_awaited()

    assert await booted_bp.browser.select_option("#dropdown", "opt1") is True
    humanizer.execute_safe_select_option.assert_awaited_once_with("#dropdown", "opt1")
    booted_bp._page.select_option.assert_not_awaited()

    assert await booted_bp.browser.keyboard_press("#inp", "Escape") is True
    humanizer.execute_safe_keyboard_press.assert_awaited_once_with("#inp", "Escape")
    booted_bp._page.press.assert_not_awaited()


@pytest.mark.asyncio
async def test_playwright_page_fallback_when_humanizer_methods_absent(booted_bp):
    """When humanizer lacks specialized methods, facade must fall back to real Playwright page execution."""
    humanizer = booted_bp._humanizer
    for attr in [
        "execute_safe_hover",
        "execute_safe_drag_and_drop",
        "execute_safe_check",
        "execute_safe_select_option",
        "execute_safe_keyboard_press",
    ]:
        if hasattr(humanizer, attr):
            delattr(humanizer, attr)

    # Hover fallback
    res = await booted_bp.browser.hover("#menu")
    assert res is True
    booted_bp._page.hover.assert_awaited_once_with("#menu")

    # Drag and drop fallback
    res = await booted_bp.browser.drag_and_drop("#item1", "#dropzone")
    assert res is True
    booted_bp._page.drag_and_drop.assert_awaited_once_with("#item1", "#dropzone")

    # Check / uncheck fallback
    res = await booted_bp.browser.check_checkbox("#agree", checked=True)
    assert res is True
    booted_bp._page.check.assert_awaited_once_with("#agree")

    res = await booted_bp.browser.check_checkbox("#agree", checked=False)
    assert res is True
    booted_bp._page.uncheck.assert_awaited_once_with("#agree")

    # Check / uncheck aliases
    res = await booted_bp.browser.check("#box1")
    assert res is True
    booted_bp._page.check.assert_awaited_with("#box1")

    res = await booted_bp.browser.uncheck("#box2")
    assert res is True
    booted_bp._page.uncheck.assert_awaited_with("#box2")

    # Select option fallback
    res = await booted_bp.browser.select_option("#countries", "CA")
    assert res is True
    booted_bp._page.select_option.assert_awaited_once_with("#countries", "CA")

    # Keyboard press fallback
    res = await booted_bp.browser.keyboard_press("#search", "Enter")
    assert res is True
    booted_bp._page.press.assert_awaited_once_with("#search", "Enter")

    # Press alias
    res = await booted_bp.browser.press("#search2", "Tab")
    assert res is True
    booted_bp._page.press.assert_awaited_with("#search2", "Tab")


@pytest.mark.asyncio
async def test_top_level_bp_delegates(booted_bp):
    """Verify top-level BP convenience methods delegate cleanly to browser namespace."""
    humanizer = booted_bp._humanizer
    for attr in [
        "execute_safe_hover",
        "execute_safe_drag_and_drop",
        "execute_safe_check",
        "execute_safe_select_option",
        "execute_safe_keyboard_press",
    ]:
        if hasattr(humanizer, attr):
            delattr(humanizer, attr)

    await booted_bp.hover("#top-menu")
    booted_bp._page.hover.assert_awaited_with("#top-menu")

    await booted_bp.drag_and_drop("#drag", "#drop")
    booted_bp._page.drag_and_drop.assert_awaited_with("#drag", "#drop")

    await booted_bp.check_checkbox("#chk1", checked=True)
    booted_bp._page.check.assert_awaited_with("#chk1")

    await booted_bp.check("#chk2")
    booted_bp._page.check.assert_awaited_with("#chk2")

    await booted_bp.uncheck("#chk3")
    booted_bp._page.uncheck.assert_awaited_with("#chk3")

    await booted_bp.select_option("#opt", "val1")
    booted_bp._page.select_option.assert_awaited_with("#opt", "val1")

    await booted_bp.keyboard_press("#press1", "Enter")
    booted_bp._page.press.assert_awaited_with("#press1", "Enter")

    await booted_bp.press("#press2", "Backspace")
    booted_bp._page.press.assert_awaited_with("#press2", "Backspace")


@pytest.mark.asyncio
async def test_error_propagation_from_playwright(booted_bp):
    """Verify exceptions from underlying page interactions are not swallowed."""
    humanizer = booted_bp._humanizer
    for attr in ["execute_safe_hover", "execute_safe_select_option"]:
        if hasattr(humanizer, attr):
            delattr(humanizer, attr)

    booted_bp._page.hover = AsyncMock(side_effect=RuntimeError("Element not visible"))
    with pytest.raises(RuntimeError, match="Element not visible"):
        await booted_bp.browser.hover("#hidden")

    booted_bp._page.select_option = AsyncMock(side_effect=ValueError("Option not found"))
    with pytest.raises(ValueError, match="Option not found"):
        await booted_bp.browser.select_option("#select", "invalid_val")


@pytest.mark.asyncio
async def test_part1_regressions_intact(booted_bp):
    """Verify Part 1 fixes remain intact (async type, scroll, console.debug in JS)."""
    humanizer = booted_bp._humanizer
    humanizer.execute_safe_type = AsyncMock(return_value=True)
    humanizer.human_scroll = AsyncMock(return_value=True)

    await booted_bp.browser.type("#input", "hello")
    assert humanizer.execute_safe_type.call_count == 5

    await booted_bp.browser.scroll(50.0)
    assert humanizer.human_scroll.call_count == 5

    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    legacy_path = repo_root / "src" / "behavioral_playwright" / "_legacy_facade12.py"
    with open(legacy_path, "r", encoding="utf-8") as f:
        code = f.read()
    assert "console.debug('Virtual speech synthesized.');" in code

