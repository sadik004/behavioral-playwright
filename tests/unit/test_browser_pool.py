"""Unit tests for BrowserPoolManager and route interception."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from behavioral_playwright.browser.pool import (
    BrowserPoolManager,
    IMAGE_FONT_EXTENSIONS,
    TRACKING_DOMAINS,
)
from behavioral_playwright.browser.playwright_provider import PlaywrightProvider


class MockRoute:
    def __init__(self, url: str, resource_type: str = "document"):
        self.request = MagicMock()
        self.request.url = url
        self.request.resource_type = resource_type
        self.aborted = False
        self.continued = False

    async def abort(self) -> None:
        self.aborted = True

    async def continue_(self) -> None:
        self.continued = True


@pytest.mark.asyncio
async def test_route_interception_tracking_blocked():
    """Ensure tracking domains are blocked unconditionally."""
    pool = BrowserPoolManager()
    mock_context = MagicMock()
    handler = None

    async def mock_route(pattern, callback):
        nonlocal handler
        handler = callback

    mock_context.route = mock_route
    await pool._setup_route_interception(mock_context, allow_media=True)
    assert handler is not None

    for domain in TRACKING_DOMAINS:
        route = MockRoute(f"https://sub.{domain}/analytics.js", "script")
        await handler(route)
        assert route.aborted is True, f"Failed to abort {domain}"
        assert route.continued is False


@pytest.mark.asyncio
async def test_route_interception_media_blocked_by_default():
    """Ensure images and fonts are aborted when allow_media=False."""
    pool = BrowserPoolManager()
    mock_context = MagicMock()
    handler = None

    async def mock_route(pattern, callback):
        nonlocal handler
        handler = callback

    mock_context.route = mock_route
    await pool._setup_route_interception(mock_context, allow_media=False)
    assert handler is not None

    # Test extensions
    for ext in IMAGE_FONT_EXTENSIONS:
        route = MockRoute(f"https://example.com/asset{ext}")
        await handler(route)
        assert route.aborted is True, f"Failed to abort extension {ext}"

    # Test resource types
    for rtype in ("image", "font", "media"):
        route = MockRoute("https://example.com/dynamic-resource", resource_type=rtype)
        await handler(route)
        assert route.aborted is True, f"Failed to abort resource type {rtype}"

    # Standard document/script should continue
    ok_route = MockRoute("https://example.com/index.html", resource_type="document")
    await handler(ok_route)
    assert ok_route.continued is True
    assert ok_route.aborted is False


@pytest.mark.asyncio
async def test_route_interception_media_allowed_when_flag_true():
    """Ensure images and fonts continue when allow_media=True."""
    pool = BrowserPoolManager()
    mock_context = MagicMock()
    handler = None

    async def mock_route(pattern, callback):
        nonlocal handler
        handler = callback

    mock_context.route = mock_route
    await pool._setup_route_interception(mock_context, allow_media=True)
    assert handler is not None

    img_route = MockRoute("https://example.com/hero.png", resource_type="image")
    await handler(img_route)
    assert img_route.continued is True
    assert img_route.aborted is False


@pytest.mark.asyncio
async def test_browser_pool_lifecycle_and_concurrency():
    """Verify single master browser management and context pooling."""
    mock_browser = AsyncMock()
    mock_browser.is_connected = MagicMock(return_value=True)

    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_page.is_closed = MagicMock(return_value=False)
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_playwright.stop = AsyncMock()

    with patch("behavioral_playwright.browser.pool.async_playwright") as mock_ap:
        pw_context = AsyncMock()
        pw_context.start = AsyncMock(return_value=mock_playwright)
        mock_ap.return_value = pw_context

        pool = BrowserPoolManager(max_concurrent_pages=2)
        assert not pool.is_initialized

        await pool.initialize()
        assert pool.is_initialized
        assert mock_playwright.chromium.launch.call_count == 1

        # Check launch args
        call_kwargs = mock_playwright.chromium.launch.call_args[1]
        assert "--no-sandbox" in call_kwargs["args"]
        assert "--disable-blink-features=AutomationControlled" in call_kwargs["args"]

        # Acquire ephemeral context
        async with pool.get_context(allow_media=False) as ctx:
            assert ctx == mock_context
            assert pool.active_contexts == 1

        # Check context teardown
        mock_context.close.assert_called_once()
        assert pool.active_contexts == 0

        # Acquire ephemeral page
        async with pool.get_page(allow_media=False) as page:
            assert page == mock_page

        mock_page.close.assert_called_once()

        # Shutdown
        await pool.shutdown()
        assert not pool.is_initialized
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()


@pytest.mark.asyncio
async def test_browser_pool_semaphore_limits():
    """Verify that pool limits concurrent contexts to max_concurrency."""
    mock_browser = AsyncMock()
    mock_browser.is_connected = MagicMock(return_value=True)
    mock_context = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

    with patch("behavioral_playwright.browser.pool.async_playwright") as mock_ap:
        pw_context = AsyncMock()
        pw_context.start = AsyncMock(return_value=mock_playwright)
        mock_ap.return_value = pw_context

        pool = BrowserPoolManager(max_concurrent_pages=2)
        await pool.initialize()

        active_count = 0
        max_seen = 0

        async def worker():
            nonlocal active_count, max_seen
            async with pool.get_context():
                active_count += 1
                max_seen = max(max_seen, active_count)
                await asyncio.sleep(0.01)
                active_count -= 1

        await asyncio.gather(worker(), worker(), worker(), worker())
        assert max_seen <= 2
        await pool.shutdown()


@pytest.mark.asyncio
async def test_playwright_provider_ephemeral_context_and_page():
    """Verify PlaywrightProvider ephemeral helpers with route interception."""
    provider = PlaywrightProvider()

    mock_browser = AsyncMock()
    mock_browser.is_connected = MagicMock(return_value=True)
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_page.is_closed = MagicMock(return_value=False)
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    provider._browser = mock_browser

    async with provider.ephemeral_context(allow_media=False) as ctx:
        assert ctx == mock_context
    mock_context.close.assert_called_once()

    async with provider.ephemeral_page(allow_media=False) as page:
        assert page == mock_page
    mock_page.close.assert_called_once()
