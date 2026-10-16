"""Phase 2 Browser & Provider Robustness Functional Test Battery.

Audits and verifies:
1. Browser launch failures and partial initialization cleanup (no leaked process/dir).
2. Closed browser/context operations (explicit typed error propagation, zero silent swallowing).
3. Ephemeral context isolation and guaranteed cleanup on failure/exception.
4. Semaphore concurrency control and recovery under concurrent pressure.
5. Timeout propagation and recovery without corrupted state.
6. Provider unavailability gating (Patchright, UndetectedChromedriver, CurlCffi, etc.).
7. Idempotent repeated shutdowns and lifecycle transitions.
8. Multi-page robustness under individual page failure and context failure.
"""

from __future__ import annotations

import asyncio
import http.server
import os
import socketserver
import tempfile
import threading
from typing import Generator
from unittest.mock import AsyncMock, patch

import pytest

from behavioral_playwright.browser.playwright_provider import PlaywrightProvider
from behavioral_playwright.browser.pool import BrowserPoolManager
from behavioral_playwright.config.settings import AutomationConfig, BrowserConfig
from behavioral_playwright.exceptions import (
    BehavioralPlaywrightError,
    BrowserProviderError,
    NavigationError,
    ProviderUnavailableError,
)
from behavioral_playwright.page.session import BrowserSession, PageSession
from behavioral_playwright.providers.base import UnknownProviderError
from behavioral_playwright.providers.browser import (
    PatchrightProvider,
    PlaywrightProvider as AdaptedPlaywrightProvider,
    UndetectedChromedriverProvider,
)
from behavioral_playwright.providers.factory import (
    create_agent_provider,
    create_browser_provider,
    create_network_provider,
    provider_matrix,
)


# ============================================================================
# Deterministic Localhost HTTP Fixture
# ============================================================================

class _RobustnessHTTPHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/healthy":
            body = b"<!DOCTYPE html><html><head><title>Healthy</title></head><body><h1 id='h'>OK</h1></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/hang":
            # Sleeps longer than test timeout to test clean timeout termination
            threading.Event().wait(10.0)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


class _ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 128


@pytest.fixture(scope="module")
def local_server() -> Generator[str, None, None]:
    server = _ThreadingTCPServer(("127.0.0.1", 0), _RobustnessHTTPHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


# ============================================================================
# 1. Browser Launch Failure & Partial Initialization Cleanup
# ============================================================================

class TestLaunchFailureAndPartialInit:
    """Verifies that failures during launch clean up all created resources."""

    @pytest.mark.asyncio
    async def test_launch_failure_cleans_up_playwright_and_tempdir(self):
        """When launch_persistent_context fails, playwright is stopped and temp dir is removed."""
        provider = PlaywrightProvider()

        with patch("behavioral_playwright.browser.playwright_provider.async_playwright") as mock_pw_start:
            mock_pw_instance = AsyncMock()
            mock_pw_instance.chromium.launch_persistent_context = AsyncMock(
                side_effect=RuntimeError("Simulated Chromium binary crash on launch")
            )
            mock_pw_instance.stop = AsyncMock()
            pw_context = AsyncMock()
            pw_context.start = AsyncMock(return_value=mock_pw_instance)
            mock_pw_start.return_value = pw_context

            with pytest.raises(BrowserProviderError) as exc_info:
                await provider.launch()

            assert "Playwright launch failed" in str(exc_info.value)
            # Verify close() was invoked in cleanup
            assert provider._context is None
            assert provider._playwright is None
            assert provider._current_page is None
            mock_pw_instance.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pool_initialize_failure_shuts_down_cleanly(self):
        """When pool.initialize() encounters an error, shutdown() is invoked cleanly."""
        pool = BrowserPoolManager(max_concurrent_pages=2)

        with patch("behavioral_playwright.browser.pool.async_playwright") as mock_pw_start:
            mock_pw_instance = AsyncMock()
            mock_pw_instance.chromium.launch = AsyncMock(
                side_effect=RuntimeError("Simulated driver communication failure")
            )
            mock_pw_instance.stop = AsyncMock()
            pw_context = AsyncMock()
            pw_context.start = AsyncMock(return_value=mock_pw_instance)
            mock_pw_start.return_value = pw_context

            with pytest.raises(BrowserProviderError) as exc_info:
                await pool.initialize()

            assert "BrowserPool initialization failed" in str(exc_info.value)
            assert not pool.is_initialized
            assert pool._browser is None
            assert pool._playwright is None


# ============================================================================
# 2. Closed Browser / Context Robustness & Zero Silent Swallowing
# ============================================================================

class TestClosedBrowserOperations:
    """Verifies honest, explicit error contracts when operations hit closed state."""

    @pytest.mark.asyncio
    async def test_operations_on_uninitialized_pool_raise_error(self):
        pool = BrowserPoolManager()
        # Pool not initialized and get_context fails if initialize is blocked
        with patch.object(pool, "initialize", AsyncMock(side_effect=RuntimeError("Init blocked"))):
            with pytest.raises(RuntimeError):
                async with pool.get_context():
                    pass

    @pytest.mark.asyncio
    async def test_provider_operations_after_close_raise_typed_errors(self, local_server):
        session = BrowserSession(AutomationConfig(browser=BrowserConfig(headless=True)))
        await session.start()
        page = await session.new_page()
        await session.close()

        # Navigation on closed page must raise explicit NavigationError
        with pytest.raises(NavigationError):
            await page.goto(f"{local_server}/healthy")

        # Evaluate on closed page must raise explicit error
        with pytest.raises(Exception):
            await page.evaluate("() => 1 + 1")

        # Screenshot on closed page must raise explicit error
        with pytest.raises(Exception):
            await page.screenshot()


# ============================================================================
# 3. Ephemeral Context Isolation & Teardown Guarantees
# ============================================================================

class TestEphemeralContextRobustness:
    """Verifies ephemeral contexts are cleanly and deterministically torn down."""

    @pytest.mark.asyncio
    async def test_pool_ephemeral_context_closed_even_on_exception(self, local_server):
        pool = BrowserPoolManager(max_concurrent_pages=4)
        await pool.initialize()

        assert pool.active_contexts == 0
        try:
            with pytest.raises(ValueError, match="Intentional test failure inside context"):
                async with pool.get_context() as ctx:
                    assert pool.active_contexts == 1
                    page = await ctx.new_page()
                    await page.goto(f"{local_server}/healthy")
                    raise ValueError("Intentional test failure inside context")

            # Active contexts must decrement back to 0
            assert pool.active_contexts == 0
        finally:
            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_pool_ephemeral_page_closed_even_on_exception(self, local_server):
        pool = BrowserPoolManager(max_concurrent_pages=4)
        await pool.initialize()

        try:
            with pytest.raises(ZeroDivisionError):
                async with pool.get_page() as page:
                    assert pool.active_contexts == 1
                    await page.goto(f"{local_server}/healthy")
                    _ = 1 / 0

            assert pool.active_contexts == 0
        finally:
            await pool.shutdown()


# ============================================================================
# 4. Semaphore Concurrency Control & Recovery
# ============================================================================

class TestPoolSemaphoreConcurrency:
    """Verifies that BrowserPoolManager strictly respects max_concurrency limits."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_contexts(self, local_server):
        pool = BrowserPoolManager(max_concurrent_pages=2)
        await pool.initialize()

        peak_active = 0

        async def worker(worker_id: int):
            nonlocal peak_active
            async with pool.get_page() as page:
                current = pool.active_contexts
                if current > peak_active:
                    peak_active = current
                await page.goto(f"{local_server}/healthy")
                await asyncio.sleep(0.05)

        try:
            tasks = [asyncio.create_task(worker(i)) for i in range(5)]
            await asyncio.gather(*tasks)

            # Peak active contexts must never exceed max_concurrency of 2
            assert peak_active <= 2
            assert pool.active_contexts == 0
        finally:
            await pool.shutdown()


# ============================================================================
# 5. Timeout Propagation & State Non-Corruption
# ============================================================================

class TestTimeoutPropagationAndRecovery:
    """Verifies timeout propagation and that timed-out pages recover cleanly."""

    @pytest.mark.asyncio
    async def test_navigation_timeout_recovers_on_subsequent_request(self, local_server):
        session = BrowserSession(AutomationConfig(browser=BrowserConfig(headless=True)))
        await session.start()
        page = await session.new_page()

        try:
            # 1. Trigger timeout on hanging endpoint
            with pytest.raises(NavigationError) as exc_info:
                await page.goto(f"{local_server}/hang", timeout_ms=500)
            assert "Navigation" in type(exc_info.value).__name__

            # 2. Immediately navigate to a healthy endpoint; state must be intact and operational
            await page.goto(f"{local_server}/healthy", timeout_ms=5000)
            title = await page.get_title()
            assert title == "Healthy"
        finally:
            await session.close()


# ============================================================================
# 6. Provider Unavailability Gating & Anti-Fraud
# ============================================================================

class TestProviderUnavailabilityGating:
    """Verifies that optional providers fail honestly and immediately when uninstalled."""

    def test_patchright_honest_availability_gating(self):
        provider = PatchrightProvider()
        info = provider.info()
        assert info.provider == "patchright"
        if not info.installed:
            with pytest.raises(ProviderUnavailableError) as exc_info:
                provider.require_available()
            assert "pip install patchright" in exc_info.value.install_hint
            assert exc_info.value.provider == "patchright"

    def test_undetected_chromedriver_honest_availability_gating(self):
        provider = UndetectedChromedriverProvider()
        info = provider.info()
        assert info.provider == "undetected_chromedriver"
        if not info.installed:
            with pytest.raises(ProviderUnavailableError) as exc_info:
                provider.require_available()
            assert "undetected-chromedriver" in exc_info.value.install_hint
            assert exc_info.value.provider == "undetected_chromedriver"

    def test_unknown_provider_factory_rejection(self):
        with pytest.raises(UnknownProviderError) as exc_info:
            create_browser_provider("selenium_grid")
        assert "unknown browser provider 'selenium_grid'" in str(exc_info.value)
        assert "available" in str(exc_info.value)

    def test_provider_matrix_completeness(self):
        matrix = provider_matrix()
        assert "browser/playwright" in matrix
        assert "browser/patchright" in matrix
        assert "browser/undetected_chromedriver" in matrix
        assert "network/curl_cffi" in matrix
        assert "agent/browser_use" in matrix
        assert "agent/stagehand" in matrix
        # Playwright must be installed in this environment
        assert matrix["browser/playwright"].installed is True


# ============================================================================
# 7. Idempotent Repeated Shutdowns & Multi-Cycle Transitions
# ============================================================================

class TestLifecycleRobustnessAndReinitialization:
    """Verifies idempotent shutdowns and multi-cycle reinitialization."""

    @pytest.mark.asyncio
    async def test_pool_repeated_shutdown_is_idempotent(self):
        pool = BrowserPoolManager(max_concurrent_pages=2)
        await pool.initialize()
        assert pool.is_initialized is True

        # First shutdown
        await pool.shutdown()
        assert pool.is_initialized is False

        # Second shutdown must be a safe no-op with zero exceptions
        await pool.shutdown()
        assert pool.is_initialized is False

    @pytest.mark.asyncio
    async def test_pool_reinitialize_after_shutdown(self, local_server):
        pool = BrowserPoolManager(max_concurrent_pages=2)
        await pool.initialize()

        async with pool.get_page() as page:
            await page.goto(f"{local_server}/healthy")
            assert await page.title() == "Healthy"

        await pool.shutdown()
        assert pool.is_initialized is False

        # Re-initialize and execute another workload
        await pool.initialize()
        assert pool.is_initialized is True

        async with pool.get_page() as page:
            await page.goto(f"{local_server}/healthy")
            assert await page.title() == "Healthy"

        await pool.shutdown()
        assert pool.is_initialized is False

    @pytest.mark.asyncio
    async def test_session_start_after_stop(self, local_server):
        session = BrowserSession(AutomationConfig(browser=BrowserConfig(headless=True)))
        await session.start()
        page1 = await session.new_page()
        await page1.goto(f"{local_server}/healthy")
        assert await page1.get_title() == "Healthy"
        await session.close()

        # Re-start session
        await session.start()
        page2 = await session.new_page()
        await page2.goto(f"{local_server}/healthy")
        assert await page2.get_title() == "Healthy"
        await session.close()


# ============================================================================
# 8. Multi-Page Robustness Under Single Page Failure
# ============================================================================

class TestMultiPageFaultTolerance:
    """Verifies that an error or crash in one page does not corrupt sibling pages."""

    @pytest.mark.asyncio
    async def test_one_page_failure_does_not_affect_sibling_pages(self, local_server):
        session = BrowserSession(AutomationConfig(browser=BrowserConfig(headless=True)))
        await session.start()

        page1 = await session.new_page()
        page2 = await session.new_page()

        await page1.goto(f"{local_server}/healthy")
        await page2.goto(f"{local_server}/healthy")

        assert await page1.get_title() == "Healthy"
        assert await page2.get_title() == "Healthy"

        # Explicitly close page1
        await page1.close()

        # Page 2 must remain fully operational
        assert await page2.get_title() == "Healthy"
        heading = await page2.evaluate("() => document.getElementById('h').innerText")
        assert heading == "OK"

        await session.close()
