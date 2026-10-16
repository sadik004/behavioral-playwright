"""Phase 1 Core Correctness & Runtime Foundation Test Battery.

Audits and verifies:
1. Page / Session isolation (Page A vs Page B on shared context)
2. Lifecycle state transitions and invalid state transition handling
3. Navigation correctness (valid, invalid, timeout, failure honesty)
4. Evaluation correctness (values, DOM mutations, JS exceptions, closed page)
5. Screenshot correctness (active page, file existence, PNG header, closed page)
6. Provider abstraction (availability honesty, factory, unknown providers)
7. Exception hierarchy and error contracts
8. Timeout propagation
9. Resource cleanup and idempotency
10. Deterministic replay and RNG isolation
11. Concurrent access on independent pages
"""

from __future__ import annotations

import asyncio
import http.server
import os
import random
import socketserver
import tempfile
import threading
from typing import Generator

import pytest

from behavioral_playwright.browser.playwright_provider import PlaywrightProvider
from behavioral_playwright.browser.pool import BrowserPoolManager
from behavioral_playwright.config.settings import AutomationConfig, BrowserConfig
from behavioral_playwright.exceptions import (
    BehavioralPlaywrightError,
    BrowserProviderError,
    ElementResolutionError,
    NavigationError,
    ProviderUnavailableError,
)
from behavioral_playwright.facade import BP
from behavioral_playwright.page.session import BrowserSession, PageSession
from behavioral_playwright.providers.base import UnknownProviderError
from behavioral_playwright.providers.factory import (
    create_agent_provider,
    create_browser_provider,
    create_network_provider,
    provider_matrix,
)


# ============================================================================
# Deterministic Localhost HTTP Fixture
# ============================================================================

class _DeterministicHTTPHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/page_a":
            body = b"<!DOCTYPE html><html><head><title>Page A</title></head><body style='background-color:red;'><h1 id='title'>Alpha</h1><p id='desc'>Content A</p></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/page_b":
            body = b"<!DOCTYPE html><html><head><title>Page B</title></head><body style='background-color:blue;'><h1 id='title'>Beta</h1><p id='desc'>Content B</p></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/slow":
            # Sleep 3 seconds to test timeout propagation
            time_to_sleep = 3.0
            threading.Event().wait(time_to_sleep)
            body = b"<!DOCTYPE html><html><head><title>Slow Page</title></head><body>Delayed</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass  # Suppress console logging during test runs


@pytest.fixture(scope="module")
def local_server() -> Generator[str, None, None]:
    """Spins up a lightweight in-process HTTP server on an ephemeral port."""
    server = socketserver.TCPServer(("127.0.0.1", 0), _DeterministicHTTPHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


# ============================================================================
# 1. Page / Session Isolation Tests
# ============================================================================

class TestPageSessionIsolation:
    """Verifies strict state and resource isolation between independent PageSessions."""

    @pytest.mark.asyncio
    async def test_page_isolation_independent_navigation_and_dom(self, local_server: str):
        """Operations on Page A must never cross-contaminate Page B."""
        async with BrowserSession() as session:
            page_a = await session.new_page()
            page_b = await session.new_page()

            await page_a.goto(f"{local_server}/page_a")
            await page_b.goto(f"{local_server}/page_b")

            # Check URLs and titles
            assert await page_a.get_url() == f"{local_server}/page_a"
            assert await page_b.get_url() == f"{local_server}/page_b"
            assert await page_a.get_title() == "Page A"
            assert await page_b.get_title() == "Page B"

            # Check DOM content
            h1_a = await page_a.evaluate("() => document.getElementById('title').innerText")
            h1_b = await page_b.evaluate("() => document.getElementById('title').innerText")
            assert h1_a == "Alpha"
            assert h1_b == "Beta"

            # Mutate Page A's DOM; verify Page B is completely unaffected
            await page_a.evaluate("() => { document.getElementById('title').innerText = 'Mutated Alpha'; }")
            h1_a_after = await page_a.evaluate("() => document.getElementById('title').innerText")
            h1_b_after = await page_b.evaluate("() => document.getElementById('title').innerText")
            assert h1_a_after == "Mutated Alpha"
            assert h1_b_after == "Beta"

            # Mutate Page B's DOM; verify Page A is unaffected
            await page_b.evaluate("() => { document.getElementById('title').innerText = 'Mutated Beta'; }")
            assert await page_a.evaluate("() => document.getElementById('title').innerText") == "Mutated Alpha"
            assert await page_b.evaluate("() => document.getElementById('title').innerText") == "Mutated Beta"

            await page_a.close()
            await page_b.close()

    @pytest.mark.asyncio
    async def test_page_isolation_screenshots_are_distinct(self, local_server: str):
        """Screenshots of Page A (red background) and Page B (blue background) must differ."""
        async with BrowserSession() as session:
            page_a = await session.new_page()
            page_b = await session.new_page()

            await page_a.goto(f"{local_server}/page_a")
            await page_b.goto(f"{local_server}/page_b")

            bytes_a = await page_a.screenshot()
            bytes_b = await page_b.screenshot()

            assert len(bytes_a) > 0
            assert len(bytes_b) > 0
            assert bytes_a != bytes_b  # Visual difference must be captured in byte content

            await page_a.close()
            await page_b.close()

    @pytest.mark.asyncio
    async def test_closing_page_a_does_not_invalidate_page_b(self, local_server: str):
        """Closing Page A must leave Page B fully operational and responsive."""
        async with BrowserSession() as session:
            page_a = await session.new_page()
            page_b = await session.new_page()

            await page_a.goto(f"{local_server}/page_a")
            await page_b.goto(f"{local_server}/page_b")

            # Close Page A
            await page_a.close()

            # Page B must still function perfectly
            title_b = await page_b.get_title()
            assert title_b == "Page B"
            eval_b = await page_b.evaluate("() => 10 + 20")
            assert eval_b == 30

            # Navigate Page B again
            await page_b.goto(f"{local_server}/page_a")
            assert await page_b.get_title() == "Page A"

            await page_b.close()


# ============================================================================
# 2. Lifecycle State & Invalid Transition Tests
# ============================================================================

class TestLifecycleTransitions:
    """Verifies valid lifecycle progression and explicit errors on invalid transitions."""

    @pytest.mark.asyncio
    async def test_closed_page_goto_raises_explicit_exception(self, local_server: str):
        """Navigating a closed page must raise NavigationError, not succeed silently."""
        async with BrowserSession() as session:
            page = await session.new_page()
            await page.close()

            with pytest.raises(NavigationError) as exc_info:
                await page.goto(f"{local_server}/page_a")
            assert "Failed to navigate" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_closed_page_evaluate_raises_exception(self):
        """Evaluating on a closed page must raise an exception, not return dummy data."""
        async with BrowserSession() as session:
            page = await session.new_page()
            await page.close()

            with pytest.raises(Exception):
                await page.evaluate("() => document.title")

    @pytest.mark.asyncio
    async def test_closed_page_screenshot_raises_exception(self):
        """Taking a screenshot of a closed page must raise an exception."""
        async with BrowserSession() as session:
            page = await session.new_page()
            await page.close()

            with pytest.raises(Exception):
                await page.screenshot()

    @pytest.mark.asyncio
    async def test_uninitialized_browser_new_page_raises_error(self):
        """Spawning a page before calling session.start() must raise BrowserProviderError."""
        session = BrowserSession()
        assert session._is_active is False
        with pytest.raises(BrowserProviderError) as exc_info:
            await session.new_page()
        assert "not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_closed_browser_new_page_raises_error(self):
        """Spawning a page after session.close() must raise BrowserProviderError."""
        session = BrowserSession()
        await session.start()
        await session.close()
        assert session._is_active is False

        with pytest.raises(BrowserProviderError) as exc_info:
            await session.new_page()
        assert "not initialized" in str(exc_info.value)


# ============================================================================
# 3. Navigation Correctness Tests
# ============================================================================

class TestNavigationCorrectness:
    """Verifies navigation guarantees, URL fidelity, and error propagation."""

    @pytest.mark.asyncio
    async def test_navigation_to_unreachable_endpoint_raises_navigation_error(self):
        """Navigating to an unbound local port must raise NavigationError."""
        async with BrowserSession() as session:
            page = await session.new_page()
            with pytest.raises(NavigationError) as exc_info:
                # Port 1 is reserved and guaranteed not listening
                await page.goto("http://127.0.0.1:1", timeout_ms=3000)
            assert "Failed to navigate" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_navigation_timeout_propagates_cleanly(self, local_server: str):
        """A timeout of 500ms on a 3-second endpoint must raise NavigationError."""
        async with BrowserSession() as session:
            page = await session.new_page()
            start = asyncio.get_event_loop().time()
            with pytest.raises(NavigationError) as exc_info:
                await page.goto(f"{local_server}/slow", timeout_ms=500)
            elapsed = asyncio.get_event_loop().time() - start
            # Must abort close to 500ms, not wait the full 3 seconds
            assert elapsed < 2.0
            assert "Timeout" in str(exc_info.value) or "Failed to navigate" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_navigation_state_tracker_records_transitions(self, local_server: str):
        """StateTracker must record each navigation step with title and URL."""
        async with BrowserSession() as session:
            page = await session.new_page()
            await page.goto(f"{local_server}/page_a")
            await page.goto(f"{local_server}/page_b")

            history = page.state_tracker.history
            assert len(history) == 2
            assert history[0].url == f"{local_server}/page_a"
            assert history[0].title == "Page A"
            assert history[1].url == f"{local_server}/page_b"
            assert history[1].title == "Page B"


# ============================================================================
# 4. Evaluation Correctness Tests
# ============================================================================

class TestEvaluationCorrectness:
    """Verifies JavaScript evaluation behavior, return fidelity, and error bubbling."""

    @pytest.mark.asyncio
    async def test_evaluate_primitives_and_complex_data(self, local_server: str):
        """Evaluation must faithfully return strings, numbers, booleans, lists, and dicts."""
        async with BrowserSession() as session:
            page = await session.new_page()
            await page.goto(f"{local_server}/page_a")

            assert await page.evaluate("() => 42") == 42
            assert await page.evaluate("() => 'hello world'") == "hello world"
            assert await page.evaluate("() => true") is True
            assert await page.evaluate("() => [1, 2, 3]") == [1, 2, 3]
            assert await page.evaluate("() => ({key: 'value', num: 100})") == {"key": "value", "num": 100}

    @pytest.mark.asyncio
    async def test_evaluate_javascript_exception_bubbles(self, local_server: str):
        """A JavaScript runtime error must raise a Python exception, not return None or fake success."""
        async with BrowserSession() as session:
            page = await session.new_page()
            await page.goto(f"{local_server}/page_a")

            with pytest.raises(Exception) as exc_info:
                await page.evaluate("() => { throw new Error('Simulated JS Failure'); }")
            assert "Simulated JS Failure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_evaluate_missing_element_returns_null(self, local_server: str):
        """Querying a non-existent element in JS must return None."""
        async with BrowserSession() as session:
            page = await session.new_page()
            await page.goto(f"{local_server}/page_a")

            res = await page.evaluate("() => document.getElementById('non_existent_id_xyz')")
            assert res is None


# ============================================================================
# 5. Screenshot Correctness Tests
# ============================================================================

class TestScreenshotCorrectness:
    """Verifies screenshot creation, filesystem persistence, and PNG valid bytes."""

    @pytest.mark.asyncio
    async def test_screenshot_persists_valid_png_to_disk(self, local_server: str):
        """Screenshot with path parameter must create a valid non-empty PNG file."""
        async with BrowserSession() as session:
            page = await session.new_page()
            await page.goto(f"{local_server}/page_a")

            with tempfile.TemporaryDirectory() as tmp_dir:
                shot_path = os.path.join(tmp_dir, "test_shot.png")
                raw_bytes = await page.screenshot(path=shot_path)

                assert os.path.exists(shot_path)
                assert os.path.getsize(shot_path) > 0
                assert len(raw_bytes) == os.path.getsize(shot_path)

                # Verify PNG magic header: \x89PNG\r\n\x1a\n
                with open(shot_path, "rb") as f:
                    header = f.read(8)
                assert header == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.asyncio
    async def test_screenshot_invalid_path_raises_exception(self, local_server: str):
        """Writing a screenshot to an invalid path (e.g. directory path where file expected) must raise an exception."""
        async with BrowserSession() as session:
            page = await session.new_page()
            await page.goto(f"{local_server}/page_a")

            with tempfile.TemporaryDirectory() as tmp_dir:
                with pytest.raises(Exception):
                    await page.screenshot(path=tmp_dir)


# ============================================================================
# 6. Provider Abstraction Tests
# ============================================================================

class TestProviderAbstraction:
    """Verifies provider matrix integrity, honest capability detection, and factory routing."""

    def test_provider_matrix_reports_truthful_installed_status(self):
        """provider_matrix() must report installed=True only for genuinely importable packages."""
        matrix = provider_matrix()
        assert "browser/playwright" in matrix
        assert matrix["browser/playwright"].installed is True

        # Check patchright: installed flag must match is_available() dynamically
        patch_info = matrix.get("browser/patchright")
        assert patch_info is not None
        from behavioral_playwright.providers.browser import PatchrightProvider
        assert patch_info.installed is PatchrightProvider().is_available()

    def test_create_browser_provider_factory(self):
        """create_browser_provider returns configured provider instance or raises UnknownProviderError."""
        pw_prov = create_browser_provider("playwright")
        assert pw_prov.display_name == "playwright"

        with pytest.raises(UnknownProviderError):
            create_browser_provider("nonexistent_phantom_engine")

    def test_require_available_raises_on_uninstalled_provider(self):
        """Calling require_available() on an uninstalled provider must raise ProviderUnavailableError."""
        from behavioral_playwright.providers.browser import PatchrightProvider
        prov = PatchrightProvider()
        if not prov.is_available():
            with pytest.raises(ProviderUnavailableError) as exc_info:
                prov.require_available()
            assert "UNAVAILABLE" in str(exc_info.value)
            assert "pip install" in str(exc_info.value)


# ============================================================================
# 7. Exception Contract Tests
# ============================================================================

class TestExceptionContract:
    """Verifies canonical exception inheritance and error semantics."""

    def test_exception_inheritance_hierarchy(self):
        """All domain exceptions must inherit from BehavioralPlaywrightError."""
        assert issubclass(NavigationError, BehavioralPlaywrightError)
        assert issubclass(BrowserProviderError, BehavioralPlaywrightError)
        assert issubclass(ElementResolutionError, BehavioralPlaywrightError)
        assert issubclass(ProviderUnavailableError, BehavioralPlaywrightError)
        assert issubclass(ProviderUnavailableError, RuntimeError)  # Dual inheritance invariant

    def test_exception_details_formatting(self):
        """Exception details dictionary must format cleanly into the message string."""
        err = NavigationError("Failed to load page", details={"code": 404, "host": "127.0.0.1"})
        assert "Failed to load page" in str(err)
        assert "Details:" in str(err)
        assert "'code': 404" in str(err)


# ============================================================================
# 8. Resource Cleanup & Idempotency Tests
# ============================================================================

class TestResourceCleanup:
    """Verifies resource teardown, double-close idempotency, and pool disposal."""

    @pytest.mark.asyncio
    async def test_page_and_session_double_close_idempotent(self):
        """Calling close() repeatedly on page and session must succeed without crashing."""
        session = BrowserSession()
        await session.start()
        page = await session.new_page()

        # First close
        await page.close()
        await session.close()
        assert session._is_active is False

        # Second close (must be completely idempotent)
        await page.close()
        await session.close()
        assert session._is_active is False

    @pytest.mark.asyncio
    async def test_browser_pool_ephemeral_context_cleanup(self, local_server: str):
        """Ephemeral contexts in BrowserPoolManager must close on context manager exit."""
        pool = BrowserPoolManager(max_concurrent_pages=4)
        try:
            await pool.initialize()
            assert pool.is_initialized is True
            assert pool.active_contexts == 0

            async with pool.get_context() as ctx:
                assert pool.active_contexts == 1
                page = await ctx.new_page()
                await page.goto(f"{local_server}/page_a")
                assert await page.title() == "Page A"

            # Context must be automatically closed and active count decremented
            assert pool.active_contexts == 0
        finally:
            await pool.shutdown()
            assert pool.is_initialized is False


# ============================================================================
# 9. Determinism Tests
# ============================================================================

class TestDeterminism:
    """Verifies deterministic generation and isolation from global PRNG mutations."""

    def test_keystroke_dynamics_deterministic_replay(self):
        """Same input text with seeded PRNG produces identical keystroke sequences."""
        from behavioral_playwright.powerplay.keystrokes import LinguisticKeystrokeDynamicsEngine

        engine = LinguisticKeystrokeDynamicsEngine()

        random.seed(42)
        seq1 = engine.generate_typing_sequence("test deterministic sequence")

        # Mutate global random
        for _ in range(50):
            random.random()

        # Reset seed and re-generate
        random.seed(42)
        seq2 = engine.generate_typing_sequence("test deterministic sequence")

        assert len(seq1) == len(seq2)
        assert seq1 == seq2


# ============================================================================
# 10. Concurrency Tests
# ============================================================================

class TestConcurrency:
    """Verifies concurrent execution safety across independent PageSessions."""

    @pytest.mark.asyncio
    async def test_concurrent_page_operations_on_shared_session(self, local_server: str):
        """Multiple concurrent tasks operating on separate pages must not interfere."""
        async with BrowserSession() as session:
            page_a = await session.new_page()
            page_b = await session.new_page()

            async def _task_a():
                await page_a.goto(f"{local_server}/page_a")
                for _ in range(5):
                    await page_a.evaluate("() => 1 + 1")
                    await asyncio.sleep(0.01)
                return await page_a.get_title()

            async def _task_b():
                await page_b.goto(f"{local_server}/page_b")
                for _ in range(5):
                    await page_b.evaluate("() => 2 + 2")
                    await asyncio.sleep(0.01)
                return await page_b.get_title()

            title_a, title_b = await asyncio.gather(_task_a(), _task_b())
            assert title_a == "Page A"
            assert title_b == "Page B"

            await page_a.close()
            await page_b.close()
