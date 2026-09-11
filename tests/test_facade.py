import pytest
from unittest.mock import AsyncMock, patch
from behavioral_playwright import BP
from behavioral_playwright.config.settings import AutomationConfig

@pytest.fixture
def mock_session():
    session = AsyncMock()
    page = AsyncMock()
    
    page.click_healed = AsyncMock(return_value="clicked")
    page.type_healed = AsyncMock(return_value="typed")
    page.scroll = AsyncMock()
    page.scroll.down = AsyncMock()
    page.screenshot = AsyncMock(return_value=b"image_data")
    page.extract_links = AsyncMock(return_value=[{"link": "test"}])
    page.extract_articles = AsyncMock(return_value=[{"article": "test"}])
    page.goto = AsyncMock()
    page.close = AsyncMock()
    
    session.start = AsyncMock()
    session.new_page = AsyncMock(return_value=page)
    session.close = AsyncMock()
    
    return session, page

@pytest.mark.asyncio
async def test_bp_import_and_initialization():
    bp = BP()
    assert bp.config is not None
    assert bp.session is None
    assert bp.page is None
    
    config = AutomationConfig()
    bp2 = BP(config=config)
    assert bp2.config is config

@pytest.mark.asyncio
@patch("behavioral_playwright.facade.BrowserSession")
async def test_bp_boot(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    bp = BP()
    await bp.boot()
    
    session.start.assert_called_once()
    session.new_page.assert_called_once()
    assert bp.session is session
    assert bp.page is page

@pytest.mark.asyncio
@patch("behavioral_playwright.facade.BrowserSession")
async def test_bp_async_context_manager(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    async with BP() as bp:
        assert bp.session is session
        assert bp.page is page
        session.start.assert_called_once()
        session.new_page.assert_called_once()
        
    page.close.assert_called_once()
    session.close.assert_called_once()

@pytest.mark.asyncio
@patch("behavioral_playwright.facade.BrowserSession")
async def test_bp_goto_open(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    bp = BP()
    await bp.open("https://example.com")
    page.goto.assert_called_with("https://example.com")
    
    await bp.goto("https://test.com")
    page.goto.assert_called_with("https://test.com")

@pytest.mark.asyncio
@patch("behavioral_playwright.facade.BrowserSession")
async def test_bp_click_delegation(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    async with BP() as bp:
        res = await bp.click("#button")
        assert res == "clicked"
        page.click_healed.assert_called_with("#button")

@pytest.mark.asyncio
@patch("behavioral_playwright.facade.BrowserSession")
async def test_bp_type_fill_delegation(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    async with BP() as bp:
        res1 = await bp.type("#input", "hello")
        assert res1 == "typed"
        page.type_healed.assert_called_with("#input", "hello")
        
        res2 = await bp.fill("#input2", "world")
        assert res2 == "typed"
        page.type_healed.assert_called_with("#input2", "world")

@pytest.mark.asyncio
@patch("behavioral_playwright.facade.BrowserSession")
async def test_bp_scroll_delegation(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    async with BP() as bp:
        await bp.scroll(distance_y=300)
        page.scroll.down.assert_called_with(distance=300)
        
        await bp.scroll()
        page.scroll.down.assert_called_with(distance=500)

@pytest.mark.asyncio
@patch("behavioral_playwright.facade.BrowserSession")
async def test_bp_screenshot_delegation(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    async with BP() as bp:
        res = await bp.screenshot(path="test.png")
        assert res == b"image_data"
        page.screenshot.assert_called_with(path="test.png")

@pytest.mark.asyncio
@patch("behavioral_playwright.facade.BrowserSession")
async def test_bp_extract_delegation(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    async with BP() as bp:
        res = await bp.extract(target="links", container_selector="div")
        assert res == [{"link": "test"}]
        page.extract_links.assert_called_with("div")
        
        res2 = await bp.extract(target="articles")
        assert res2 == [{"article": "test"}]
        page.extract_articles.assert_called_with(None)
        
        with pytest.raises(ValueError):
            await bp.extract(target="unknown")

@pytest.mark.asyncio
@patch("behavioral_playwright.facade.BrowserSession")
async def test_bp_close(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    bp = BP()
    await bp.boot()
    await bp.close()
    
    page.close.assert_called_once()
    session.close.assert_called_once()
    assert bp.page is None
    assert bp.session is None
    
    # Check repeated close is safe
    await bp.close()

@pytest.mark.asyncio
async def test_bp_error_handling_unbooted():
    bp = BP()
    with pytest.raises(RuntimeError, match="BP is not booted"):
        await bp.click("#btn")
        
    with pytest.raises(RuntimeError, match="BP is not booted"):
        await bp.type("#inp", "text")
        
    with pytest.raises(RuntimeError, match="BP is not booted"):
        await bp.scroll()
        
    with pytest.raises(RuntimeError, match="BP is not booted"):
        await bp.screenshot()
        
    with pytest.raises(RuntimeError, match="BP is not booted"):
        await bp.extract()

@pytest.mark.asyncio
@patch('behavioral_playwright.facade.BrowserSession')
async def test_bp_crawl_delegation(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    async with BP() as bp:
        with patch('behavioral_playwright.crawling.crawler.Crawler.crawl', new_callable=AsyncMock) as mock_crawl:
            mock_crawl.return_value = [{'link': 'crawled'}]
            res = await bp.crawl('https://example.com')
            assert res == [{'link': 'crawled'}]
            mock_crawl.assert_called_with('https://example.com', 5)

@pytest.mark.asyncio
@patch('behavioral_playwright.facade.BrowserSession')
async def test_bp_search_delegation(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    async with BP() as bp:
        with patch('behavioral_playwright.search.engine.SearchEngine.search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [{'link': 'result'}]
            res = await bp.search('query')
            assert res == [{'link': 'result'}]
            mock_search.assert_called_with('query', "input[type='search'], input[name='q']", "button[type='submit']")

@pytest.mark.asyncio
@patch('behavioral_playwright.facade.BrowserSession')
async def test_bp_map_delegation(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    async with BP() as bp:
        with patch('behavioral_playwright.mapping.mapper.SiteMapper.map', new_callable=AsyncMock) as mock_map:
            mock_map.return_value = {'url': 'map'}
            res = await bp.map('https://example.com')
            assert res == {'url': 'map'}
            mock_map.assert_called_with('https://example.com')

@pytest.mark.asyncio
@patch('behavioral_playwright.facade.BrowserSession')
async def test_bp_handoff_delegation(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    async with BP() as bp:
        with patch('behavioral_playwright.handoff.session_handoff.SessionHandoff.handoff', new_callable=AsyncMock) as mock_handoff:
            mock_handoff.return_value = {'cookies': []}
            res = await bp.handoff()
            assert res == {'cookies': []}
            mock_handoff.assert_called_with(None)

@pytest.mark.asyncio
@patch('behavioral_playwright.facade.BrowserSession')
async def test_bp_verify_delegation(mock_browser_session_cls, mock_session):
    session, page = mock_session
    mock_browser_session_cls.return_value = session
    
    async with BP() as bp:
        with patch('behavioral_playwright.verification.verifier.StateVerifier.verify', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {'verified': True}
            res = await bp.verify(expected_title='Test')
            assert res == {'verified': True}
            mock_verify.assert_called_with(None, 'Test', None, None, None)

