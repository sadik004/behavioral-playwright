"""
Unit tests for Vision, Virtual OCR, and Coordinate mapping.
"""

import pytest

from behavioral_playwright import (
    AIConfig,
    AutomationConfig,
    BehavioralHumanizer,
    DeterministicRandomSource,
    MockPage,
    VirtualTestClock,
    VisualElement,
)


@pytest.mark.asyncio
async def test_ai_cv_ocr(mock_page: MockPage, test_clock: VirtualTestClock) -> None:
    config = AutomationConfig(ai=AIConfig(enabled=True, ocr_cv_enabled=True))
    humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=test_clock)
    assert humanizer.vision_engine is not None

    elements = await humanizer.vision_engine.capture_and_analyze(mock_page)
    assert len(elements) > 0
    texts = [e.text for e in elements]
    assert "Login" in texts or "Submit" in texts
    assert elements[0].confidence > 0.80


def test_ai_coordinate_mapping() -> None:
    ve = VisualElement(
        text="ClickMe",
        bounding_box={"x": 150.0, "y": 250.0, "width": 100.0, "height": 50.0},
        confidence=0.99,
    )
    cx = ve.bounding_box["x"] + ve.bounding_box["width"] / 2.0
    cy = ve.bounding_box["y"] + ve.bounding_box["height"] / 2.0
    assert cx == 200.0
    assert cy == 275.0
