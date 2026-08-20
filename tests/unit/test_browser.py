"""Unit tests for BrowserProvider implementations."""

import pytest
from behavioral_playwright.browser.mock_provider import MockBrowserProvider, MockPage
from behavioral_playwright.config.settings import BrowserConfig
from behavioral_playwright.exceptions import BrowserProviderError, NavigationError


@pytest.mark.asyncio
async def test_mock_browser_lifecycle():
    provider = MockBrowserProvider(BrowserConfig(headless=True))
    assert provider.is_launched is False

    await provider.launch()
    assert provider.is_launched is True

    page = await provider.new_page()
    assert isinstance(page, MockPage)

    await provider.goto("https://test.example.com")
    assert await provider.get_url() == "https://test.example.com"

    await provider.close()
    assert provider.is_launched is False


@pytest.mark.asyncio
async def test_mock_browser_unlaunched_error():
    provider = MockBrowserProvider()
    with pytest.raises(BrowserProviderError):
        await provider.new_page()


@pytest.mark.asyncio
async def test_mock_browser_navigation_failure():
    provider = MockBrowserProvider()
    await provider.launch()
    with pytest.raises(NavigationError):
        await provider.goto("https://fail.example.com")
    await provider.close()


@pytest.mark.asyncio
async def test_mock_page_evaluation():
    provider = MockBrowserProvider()
    await provider.launch()
    provider.active_page.register_eval_result("return 42", 42)

    val = await provider.evaluate("return 42")
    assert val == 42
    await provider.close()
