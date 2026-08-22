import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

# Stub behavioral_playwright packages if not installed in local environment
class MockProviderUnavailableError(Exception):
    pass

class MockProviderError(Exception):
    pass

class MockInvalidRequestError(Exception):
    pass

for mod in [
    'behavioral_playwright',
    'behavioral_playwright.core',
    'behavioral_playwright.core.config',
    'behavioral_playwright.core.exceptions',
    'behavioral_playwright.core.circuit_breaker',
    'behavioral_playwright.core.v10_core',
    'behavioral_playwright.acquisition',
    'behavioral_playwright.acquisition.exceptions',
    'behavioral_playwright.acquisition.models',
    'behavioral_playwright.acquisition.router',
    'behavioral_playwright.acquisition.handoff',
]:
    if mod not in sys.modules:
        m = MagicMock()
        if mod == 'behavioral_playwright.acquisition.exceptions':
            m.ProviderUnavailableError = MockProviderUnavailableError
            m.InvalidRequestError = MockInvalidRequestError
        elif mod == 'behavioral_playwright.core.exceptions':
            m.ProviderError = MockProviderError
        sys.modules[mod] = m

from bp_facade12 import BP


@pytest.fixture
def mock_bp(tmp_path):
    bp = BP()
    db_file = str(tmp_path / "test_crawl.db")
    return bp, db_file


@pytest.mark.asyncio
async def test_crawl_recursive_real_links_extraction(mock_bp):
    """Verify that root URL is acquired, real HTML links are extracted and recursively processed."""
    bp, db_path = mock_bp

    pages = {
        "https://example.com": MagicMock(
            html='<html><body><a href="/about">About</a><a href="/products">Products</a><a href="https://external.com/page">Ext</a></body></html>',
            content=None
        ),
        "https://example.com/about": MagicMock(
            html='<html><body><a href="/team">Team</a><a href="/about#team">Anchor</a></body></html>',
            content=None
        ),
        "https://example.com/products": MagicMock(
            html='<html><body><a href="/pricing">Pricing</a></body></html>',
            content=None
        ),
        "https://example.com/team": MagicMock(
            html='<html><body>No links</body></html>',
            content=None
        ),
        "https://example.com/pricing": MagicMock(
            html='<html><body>No links</body></html>',
            content=None
        ),
    }

    async def mock_scrape(url, options=None):
        if url in pages:
            return pages[url]
        raise RuntimeError(f"404 Not Found: {url}")

    bp.web.scrape = AsyncMock(side_effect=mock_scrape)

    visited = await bp.web.crawl_recursive("https://example.com", max_depth=3, db_path=db_path)

    # Verify root was crawled
    assert "https://example.com" in visited
    # Verify discovered internal links were crawled
    assert "https://example.com/about" in visited
    assert "https://example.com/products" in visited
    assert "https://example.com/team" in visited
    assert "https://example.com/pricing" in visited

    # Verify external links were excluded
    assert "https://external.com/page" not in visited
    # Verify simulated/fake placeholder links were NOT used
    assert "https://example.com/contact" not in visited

    # Verify bp.web.scrape was actually called with discovered URLs
    scraped_urls = [call.args[0] for call in bp.web.scrape.call_args_list]
    assert "https://example.com" in scraped_urls
    assert "https://example.com/about" in scraped_urls
    assert "https://example.com/products" in scraped_urls


@pytest.mark.asyncio
async def test_crawl_recursive_respects_max_depth(mock_bp):
    """Verify crawler respects max_depth limit."""
    bp, db_path = mock_bp

    pages = {
        "https://test.org": MagicMock(html='<a href="/d1">D1</a>'),
        "https://test.org/d1": MagicMock(html='<a href="/d2">D2</a>'),
        "https://test.org/d2": MagicMock(html='<a href="/d3">D3</a>'),
        "https://test.org/d3": MagicMock(html='<a href="/d4">D4</a>'),
    }
    bp.web.scrape = AsyncMock(side_effect=lambda u, **kw: pages.get(u, MagicMock(html="")))

    # Depth 1: Only root URL (depth 0)
    visited_d1 = await bp.web.crawl_recursive("https://test.org", max_depth=1, db_path=db_path + "_d1")
    assert visited_d1 == ["https://test.org"]

    # Depth 2: Root (0) + D1 (1)
    visited_d2 = await bp.web.crawl_recursive("https://test.org", max_depth=2, db_path=db_path + "_d2")
    assert "https://test.org" in visited_d2
    assert "https://test.org/d1" in visited_d2
    assert "https://test.org/d2" not in visited_d2


@pytest.mark.asyncio
async def test_crawl_recursive_respects_max_pages(mock_bp):
    """Verify crawler stops when max_pages limit is reached."""
    bp, db_path = mock_bp

    pages = {
        "https://site.com": MagicMock(html='<a href="/p1">1</a><a href="/p2">2</a><a href="/p3">3</a><a href="/p4">4</a>'),
        "https://site.com/p1": MagicMock(html=''),
        "https://site.com/p2": MagicMock(html=''),
        "https://site.com/p3": MagicMock(html=''),
        "https://site.com/p4": MagicMock(html=''),
    }
    bp.web.scrape = AsyncMock(side_effect=lambda u, **kw: pages.get(u, MagicMock(html="")))

    visited = await bp.web.crawl_recursive("https://site.com", max_depth=3, max_pages=2, db_path=db_path)
    assert len(visited) == 2


@pytest.mark.asyncio
async def test_crawl_recursive_error_resilience(mock_bp):
    """Verify that a failure on one page does not abort the entire crawl."""
    bp, db_path = mock_bp

    async def mock_scrape(url, options=None):
        if url == "https://robust.com/fail":
            raise ConnectionError("Timeout")
        return MagicMock(html='<a href="/fail">Fail</a><a href="/ok">Ok</a>')

    bp.web.scrape = AsyncMock(side_effect=mock_scrape)

    visited = await bp.web.crawl_recursive("https://robust.com", max_depth=2, db_path=db_path)
    assert "https://robust.com" in visited
    assert "https://robust.com/ok" in visited
    assert "https://robust.com/fail" not in visited


@pytest.mark.asyncio
async def test_url_normalization_and_filtering(mock_bp):
    """Verify relative resolution, fragment stripping, asset extension filtering, and domain safety."""
    bp, _ = mock_bp

    html = """
    <div>
        <a href="/path/page">Relative</a>
        <a href="https://example.com/section#heading">Fragment</a>
        <a href="https://example.com/image.png">Image</a>
        <a href="https://example.com/style.css">CSS</a>
        <a href="https://otherdomain.com/docs">External</a>
        <a href="javascript:void(0)">JS</a>
        <a href="mailto:info@example.com">Email</a>
    </div>
    """
    links = bp.web.extract_links("https://example.com", html)
    filtered = bp.web.filter_crawl_links("https://example.com", links)

    assert "https://example.com/path/page" in filtered
    assert "https://example.com/section" in filtered
    assert not any(l.endswith(".png") for l in filtered)
    assert not any(l.endswith(".css") for l in filtered)
    assert not any("otherdomain.com" in l for l in filtered)
    assert not any("javascript:" in l for l in filtered)
    assert not any("mailto:" in l for l in filtered)


@pytest.mark.asyncio
async def test_top_level_bp_crawl_recursive_delegation(mock_bp):
    """Verify bp.crawl_recursive delegates to bp.web.crawl_recursive."""
    bp, db_path = mock_bp
    bp.web.scrape = AsyncMock(return_value=MagicMock(html='<a href="/sub">Sub</a>'))

    visited = await bp.crawl_recursive("https://delegate.com", max_depth=2, db_path=db_path)
    assert "https://delegate.com" in visited
    assert "https://delegate.com/sub" in visited
