"""Unit tests for DOMExtractor."""

import pytest
from behavioral_playwright.browser.mock_provider import MockPage
from behavioral_playwright.extraction.dom import DOMExtractor
from behavioral_playwright.models.results import ExtractionRecord


@pytest.mark.asyncio
async def test_extract_links():
    extractor = DOMExtractor()
    page = MockPage()

    page.register_eval_result("Array.from(root.querySelectorAll('a[href]'))", [
        {
            "text": "Product 1",
            "href": "https://store.com/item1",
            "attributes": {"title": "View Item 1", "target": "_blank"},
            "metadata": {"id": "link-1"}
        },
        {
            "text": "Product 2",
            "href": "https://store.com/item2",
            "attributes": {"title": "View Item 2"},
            "metadata": {"id": "link-2"}
        }
    ])

    links = await extractor.extract_links(page)
    assert len(links) == 2
    assert isinstance(links[0], ExtractionRecord)
    assert links[0].text == "Product 1"
    assert links[0].href == "https://store.com/item1"
    assert links[0].attributes.get("title") == "View Item 1"


@pytest.mark.asyncio
async def test_extract_articles():
    extractor = DOMExtractor()
    page = MockPage()

    page.register_eval_result("Array.from(root.querySelectorAll('article", [
        {
            "text": "Breaking Tech News Headline",
            "href": "https://news.com/article-1",
            "attributes": {"summary": "A detailed summary of the news article..."},
            "metadata": {"tag": "article"}
        }
    ])

    articles = await extractor.extract_articles(page)
    assert len(articles) == 1
    assert articles[0].text == "Breaking Tech News Headline"
    assert articles[0].href == "https://news.com/article-1"
    assert articles[0].attributes.get("summary") == "A detailed summary of the news article..."
