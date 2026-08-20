"""
Pytest configuration and shared fixtures.
"""

import pytest

from behavioral_playwright import (
    AIConfig,
    AutomationConfig,
    DeterministicRandomSource,
    MockPage,
    VirtualTestClock,
)


@pytest.fixture
def mock_page() -> MockPage:
    return MockPage()


@pytest.fixture
def test_clock() -> VirtualTestClock:
    return VirtualTestClock()


@pytest.fixture
def test_rng() -> DeterministicRandomSource:
    return DeterministicRandomSource(42)


@pytest.fixture
def default_config() -> AutomationConfig:
    return AutomationConfig(ai=AIConfig(enabled=True, self_healing_enabled=True, ocr_cv_enabled=True))
