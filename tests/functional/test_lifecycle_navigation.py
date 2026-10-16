"""Functional Validation: Browser/Context Lifecycle & Real Navigation.
Tests real observable browser behavior, page lifecycle, and URL navigation.
"""

from __future__ import annotations

import pytest
from playwright.async_api import Error as PlaywrightError

from behavioral_playwright.config.settings import AutomationConfig, BrowserConfig
from behavioral_playwright.exceptions import NavigationError
from behavioral_playwright.facade import BP
from behavioral_playwright.page.session import BrowserSession


@pytest.mark.asyncio
async def test_browser_session_lifecycle():
    """Verify BrowserSession launches a real browser, spawns a page, and terminates cleanly."""
    config = AutomationConfig(browser=BrowserConfig(headless=True))
    session = BrowserSession(config=config)
    
    # 1. State before start
    assert session._is_active is False
    
    # 2. Launch
    await session.start()
    assert session._is_active is True
    
    # 3. New page creation
    page = await session.new_page()
    assert page.raw_page is not None
    
    # 4. Observable page navigation
    html = "<html><head><title>Lifecycle Test</title></head><body><div id='app'>Active</div></body></html>"
    await page.goto(f"data:text/html,{html}")
    title = await page.get_title()
    assert title == "Lifecycle Test"
    
    # 5. Clean teardown
    await page.close()
    await session.close()
    assert session._is_active is False


@pytest.mark.asyncio
async def test_bp_context_manager_lifecycle():
    """Verify BP async context manager boots and shuts down the browser cleanly."""
    async with BP() as bp:
        assert bp.session is not None
        assert bp.page is not None
        assert bp.session._is_active is True
        
        # Navigate and observe title
        html = "<html><head><title>BP Booted Page</title></head><body><h1>Hello BP</h1></body></html>"
        await bp.goto(f"data:text/html,{html}")
        title = await bp.page.get_title()
        assert title == "BP Booted Page"
        
        heading_text = await bp.page.evaluate("() => document.querySelector('h1').innerText")
        assert heading_text == "Hello BP"
        
    # After exit, session is closed
    assert bp.session is None
    assert bp.page is None


@pytest.mark.asyncio
async def test_real_navigation_and_state_tracking():
    """Verify navigation to local HTML fixture correctly tracks state and URL."""
    async with BP() as bp:
        fixture = (
            "data:text/html,"
            "<!DOCTYPE html><html><head><title>Nav Target</title></head>"
            "<body><p id='content'>Navigation Succeeded</p></body></html>"
        )
        await bp.open(fixture)
        
        url = await bp.page.get_url()
        assert "data:text/html" in url
        
        title = await bp.page.get_title()
        assert title == "Nav Target"
        
        # Verify StateTracker recorded this
        history = bp.page.state_tracker.history
        assert len(history) >= 1
        assert history[-1].title == "Nav Target"


@pytest.mark.asyncio
async def test_multi_page_isolation_defect():
    """DEFECT-001 REGRESSION: Multiple pages on same PlaywrightProvider clobber _current_page.
    
    Verifies that Page A and Page B maintain strict, bidirectional state isolation.
    Mutating Page A does not affect Page B, and mutating Page B does not affect Page A.
    """
    async with BrowserSession() as session:
        page_a = await session.new_page()
        page_b = await session.new_page()

        html_a = "<html><head><title>Title A</title></head><body><span id='target'>State A</span></body></html>"
        html_b = "<html><head><title>Title B</title></head><body><span id='target'>State B</span></body></html>"

        await page_a.goto(f"data:text/html,{html_a}")
        await page_b.goto(f"data:text/html,{html_b}")

        # Page A -> State A, Page B -> State B
        val_a = await page_a.evaluate("() => document.getElementById('target').innerText")
        val_b = await page_b.evaluate("() => document.getElementById('target').innerText")
        assert val_a == "State A"
        assert val_b == "State B"

        title_a = await page_a.get_title()
        title_b = await page_b.get_title()
        assert title_a == "Title A"
        assert title_b == "Title B"

        # Mutate Page A -> Verify Page B remains unchanged
        await page_a.evaluate("() => { document.getElementById('target').innerText = 'State A Mutated'; }")
        val_b_after_a_mut = await page_b.evaluate("() => document.getElementById('target').innerText")
        assert val_b_after_a_mut == "State B"
        val_a_current = await page_a.evaluate("() => document.getElementById('target').innerText")
        assert val_a_current == "State A Mutated"

        # Mutate Page B -> Verify Page A remains unchanged
        await page_b.evaluate("() => { document.getElementById('target').innerText = 'State B Mutated'; }")
        val_a_after_b_mut = await page_a.evaluate("() => document.getElementById('target').innerText")
        assert val_a_after_b_mut == "State A Mutated"
        val_b_current = await page_b.evaluate("() => document.getElementById('target').innerText")
        assert val_b_current == "State B Mutated"

        await page_a.close()
        await page_b.close()
