import pytest
from unittest.mock import AsyncMock, MagicMock
from veil.automation.mouse import MouseController
from veil.browser.challenge import ChallengeInterceptor


@pytest.mark.asyncio
async def test_mouse_press_and_hold_coordinate():
    page = MagicMock()
    page.mouse = MagicMock()
    page.mouse.move = AsyncMock()
    page.mouse.down = AsyncMock()
    page.mouse.up = AsyncMock()

    mouse = MouseController(page)
    # Fast resolution with mock predicate
    called = []

    def check():
        called.append(True)
        return True

    res = await mouse.press_and_hold(
        100.0,
        200.0,
        min_hold_sec=0.1,
        max_hold_sec=1.0,
        resolve_predicate=check,
        humanize=False,
    )

    assert res is True
    assert len(called) > 0
    page.mouse.down.assert_called_once()
    page.mouse.up.assert_called_once()


@pytest.mark.asyncio
async def test_mouse_press_and_hold_locator():
    page = MagicMock()
    page.mouse = MagicMock()
    page.mouse.move = AsyncMock()
    page.mouse.down = AsyncMock()
    page.mouse.up = AsyncMock()

    locator = MagicMock()
    locator.bounding_box = AsyncMock(return_value={"x": 50, "y": 50, "width": 100, "height": 40})

    mouse = MouseController(page)
    res = await mouse.press_and_hold(
        locator,
        min_hold_sec=0.1,
        max_hold_sec=0.5,
        resolve_predicate=lambda: True,
        humanize=False,
    )

    assert res is True
    page.mouse.down.assert_called_once()
    page.mouse.up.assert_called_once()


@pytest.mark.asyncio
async def test_challenge_interceptor_detection():
    interceptor = ChallengeInterceptor()

    page = MagicMock()
    frame = MagicMock()
    page.frames = [frame]

    # Mock locator returning match for PerimeterX
    loc_px = MagicMock()
    loc_px.count = AsyncMock(return_value=1)
    loc_px.first = loc_px

    def frame_locator(selector):
        if "Human Challenge" in selector:
            return loc_px
        loc_empty = MagicMock()
        loc_empty.count = AsyncMock(return_value=0)
        return loc_empty

    frame.locator = frame_locator

    detection = await interceptor.detect(page)
    assert detection is not None
    assert detection["type"] == "PERIMETER_X"
    assert detection["frame"] is frame


@pytest.mark.asyncio
async def test_challenge_interceptor_resolve_perimeterx():
    interceptor = ChallengeInterceptor()

    page = MagicMock()
    frame = MagicMock()
    page.frames = [frame]

    loc_px = MagicMock()
    loc_px.count = AsyncMock(return_value=1)
    loc_px.first = loc_px

    frame.locator = MagicMock(return_value=loc_px)

    mouse = MagicMock()
    mouse.press_and_hold = AsyncMock(return_value=True)

    res = await interceptor.resolve(page, mouse=mouse)
    assert res is True
    mouse.press_and_hold.assert_called_once()
