"""Functional Validation: Negative Testing Suite.
Tests that the framework fails honestly, predictively, and with exact domain exceptions when given invalid inputs.
"""

from __future__ import annotations

import pytest
from behavioral_playwright.exceptions import (
    BrowserProviderError,
    ElementResolutionError,
    NavigationError,
    ProviderUnavailableError,
)
from behavioral_playwright.facade import BP
from behavioral_playwright.page.session import BrowserSession
from behavioral_playwright.providers import create_browser_provider
from behavioral_playwright.storage.exporters import DataStorageManager


@pytest.mark.asyncio
async def test_negative_invalid_css_selector_syntax():
    """Verify malformed CSS selector syntax cascades to self-healing or raises resolution error on action."""
    async with BP() as bp:
        await bp.open("data:text/html,<html><body><button>Test</button></body></html>")
        
        # Malformed selector syntax: unclosed bracket
        with pytest.raises(ElementResolutionError):
            await bp.page.click_healed("button[unclosed-attribute=")


@pytest.mark.asyncio
async def test_negative_missing_element_resolution():
    """Verify attempting to interact with non-existent element raises ElementResolutionError."""
    async with BP() as bp:
        await bp.open("data:text/html,<html><body><h1>Title</h1></body></html>")
        
        with pytest.raises(ElementResolutionError) as exc_info:
            await bp.page.click_healed("#non-existent-button-12345")
            
        assert "could not be resolved" in str(exc_info.value)


@pytest.mark.asyncio
async def test_negative_invalid_url_navigation():
    """Verify navigation to invalid or unreachable URL raises NavigationError."""
    async with BP() as bp:
        # Invalid host that cannot be reached
        with pytest.raises(NavigationError) as exc_info:
            await bp.page.goto("http://127.0.0.1:59999/unreachable_path")
            
        assert "Failed to navigate" in str(exc_info.value)


@pytest.mark.asyncio
async def test_negative_closed_context_interaction():
    """Verify attempting to interact with a session after closing it raises BrowserProviderError or Exception."""
    session = BrowserSession()
    await session.start()
    page = await session.new_page()
    await page.goto("data:text/html,<html><body><h1>Active</h1></body></html>")
    
    # Close the session entirely
    await session.close()
    
    # Interacting with page whose session/provider is closed must raise
    with pytest.raises((BrowserProviderError, Exception)):
        await page.evaluate("() => document.title")


@pytest.mark.asyncio
async def test_negative_malformed_extraction_target():
    """Verify bp.extract() raises ValueError when given an unsupported extraction target."""
    async with BP() as bp:
        await bp.open("data:text/html,<html><body><p>Text</p></body></html>")
        
        with pytest.raises(ValueError) as exc_info:
            await bp.extract(target="unsupported_quantum_target_xyz")
            
        assert "not supported by DOMExtractor" in str(exc_info.value)


def test_negative_unavailable_provider():
    """Verify launching an uninstalled provider raises ProviderUnavailableError."""
    provider = create_browser_provider("patchright")
    with pytest.raises(ProviderUnavailableError) as exc_info:
        provider.launch()
        
    assert "patchright" in str(exc_info.value).lower()


def test_negative_invalid_storage_destination():
    """Verify DataStorageManager raises OSError/IOError when destination path cannot be written."""
    manager = DataStorageManager()
    with pytest.raises((OSError, IOError)):
        manager.export([{"k": "v"}], "Z:\\NonExistent_Drive_123\\target.json", format="json")
