"""Unit tests for BrowserSession and PageSession."""

import pytest
from behavioral_playwright.browser.mock_provider import MockBrowserProvider
from behavioral_playwright.config.settings import AutomationConfig, BrowserConfig
from behavioral_playwright.page.session import BrowserSession, PageSession


@pytest.mark.asyncio
async def test_browser_session_context_manager():
    config = AutomationConfig(browser=BrowserConfig(headless=True))
    mock_provider = MockBrowserProvider(config.browser)

    async with BrowserSession(config=config, provider=mock_provider) as session:
        page = await session.new_page()
        assert isinstance(page, PageSession)

        await page.goto("https://session.example.com")
        assert await page.get_url() == "https://session.example.com"
        assert page.state_tracker.transition_count == 1

    assert mock_provider.is_launched is False


@pytest.mark.asyncio
async def test_page_session_controllers():
    config = AutomationConfig()
    mock_provider = MockBrowserProvider(config.browser)
    await mock_provider.launch()

    page = PageSession(
        raw_page=mock_provider.active_page,
        provider=mock_provider,
        config=config
    )

    # Verify controllers are cleanly bound
    assert page.mouse is not None
    assert page.keyboard is not None
    assert page.scroll is not None
    assert page.resolver is not None
    assert page.extractor is not None

    await mock_provider.close()
