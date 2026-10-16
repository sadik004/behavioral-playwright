"""Unit tests for Hydration & Embedded State Extractor and Open Graph mining."""

import json
from unittest.mock import AsyncMock
import pytest

from behavioral_playwright.extraction.dom import (
    DOMExtractor,
    extract_json_ld,
    extract_next_data,
    extract_nuxt_data,
    extract_open_graph,
)
from behavioral_playwright.facade import BP


# ==============================================================================
# 1. Next.js __NEXT_DATA__ Extractor Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_extract_next_data_from_html():
    """Verify Next.js data extraction from static HTML string."""
    payload = {
        "props": {
            "pageProps": {
                "id": "item-123",
                "title": "Quantum Mechanical Scraper",
                "price": 299.99,
            }
        },
        "page": "/products/[id]",
        "query": {"id": "item-123"},
        "buildId": "v6.0.0-quantum",
    }
    html = f"""
    <html>
      <head><title>Test Page</title></head>
      <body>
        <div id="__next">Content</div>
        <script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>
      </body>
    </html>
    """

    res = await extract_next_data(html)
    assert res is not None
    assert res["props"]["pageProps"]["title"] == "Quantum Mechanical Scraper"
    assert res["props"]["pageProps"]["id"] == "item-123"
    assert res["buildId"] == "v6.0.0-quantum"


@pytest.mark.asyncio
async def test_extract_next_data_from_page():
    """Verify Next.js data extraction from live/mock Page evaluation."""
    mock_page = AsyncMock()
    mock_data = {"props": {"pageProps": {"user": "lead_architect"}}}
    mock_page.evaluate = AsyncMock(return_value=json.dumps(mock_data))

    res = await extract_next_data(mock_page)
    assert res is not None
    assert res["props"]["pageProps"]["user"] == "lead_architect"


@pytest.mark.asyncio
async def test_extract_next_data_missing():
    """Verify None is returned when __NEXT_DATA__ is absent."""
    html = "<html><body><h1>Standard HTML</h1></body></html>"
    res = await extract_next_data(html)
    assert res is None


# ==============================================================================
# 2. Nuxt.js State Extractor Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_extract_nuxt_data_from_html():
    """Verify Nuxt 2/3 state extraction from static HTML script."""
    payload = {"data": [{"product": "Stealth Engine", "stock": 42}], "state": {}}
    html = f"""
    <html>
      <body>
        <script id="__NUXT_DATA__" type="application/json">{json.dumps(payload)}</script>
      </body>
    </html>
    """

    res = await extract_nuxt_data(html)
    assert res is not None
    assert res["data"][0]["product"] == "Stealth Engine"


@pytest.mark.asyncio
async def test_extract_nuxt_data_from_page():
    """Verify Nuxt state evaluation on page."""
    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value={"serverRendered": True, "routePath": "/dashboard"})

    res = await extract_nuxt_data(mock_page)
    assert res is not None
    assert res["serverRendered"] is True


# ==============================================================================
# 3. JSON-LD Extractor & @graph Unpacking Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_extract_json_ld_with_graph_unpacking():
    """Verify JSON-LD extraction and unnesting of @graph root arrays."""
    product_schema = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Stealth Crawler 9000",
        "offers": {"@type": "Offer", "price": "149.00", "priceCurrency": "USD"},
    }
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": "Does it bypass Cloudflare?",
                "acceptedAnswer": {"@type": "Answer", "text": "Yes, zero-leak stealth."},
            }
        ],
    }
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Modern Scraping Architecture",
    }

    graph_container = {
        "@context": "https://schema.org",
        "@graph": [product_schema, faq_schema],
    }

    html = f"""
    <html>
      <head>
        <script type="application/ld+json">
          {json.dumps(graph_container)}
        </script>
        <script type="application/ld+json">
          {json.dumps(article_schema)}
        </script>
      </head>
      <body><h1>Store Page</h1></body>
    </html>
    """

    schemas = await extract_json_ld(html)
    assert len(schemas) == 3

    types = [s.get("@type") for s in schemas]
    assert "Product" in types
    assert "FAQPage" in types
    assert "Article" in types

    # Verify unpacked contents
    product = next(s for s in schemas if s.get("@type") == "Product")
    assert product["name"] == "Stealth Crawler 9000"


@pytest.mark.asyncio
async def test_extract_json_ld_malformed_ignored():
    """Verify malformed JSON-LD scripts are skipped gracefully."""
    html = """
    <html>
      <head>
        <script type="application/ld+json">NOT VALID JSON {{{</script>
        <script type="application/ld+json">{"@type": "Organization", "name": "Acme Corp"}</script>
      </head>
    </html>
    """
    schemas = await extract_json_ld(html)
    assert len(schemas) == 1
    assert schemas[0]["@type"] == "Organization"
    assert schemas[0]["name"] == "Acme Corp"


# ==============================================================================
# 4. OpenGraph & Twitter Card Extractor Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_extract_open_graph_tags():
    """Verify extraction of og:* and twitter:* tags into normalized dictionary."""
    html = """
    <html>
      <head>
        <meta property="og:title" content="Stealth Browser Automation Engine" />
        <meta property="og:description" content="Subpixel precision and anti-detection automation." />
        <meta property="og:image" content="https://example.com/banner.png" />
        <meta property="og:url" content="https://example.com/engine" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:creator" content="@architect" />
        <meta name="description" content="Ignored standard description meta" />
      </head>
    </html>
    """

    og_data = await extract_open_graph(html)
    assert og_data["og:title"] == "Stealth Browser Automation Engine"
    assert og_data["og:description"] == "Subpixel precision and anti-detection automation."
    assert og_data["og:image"] == "https://example.com/banner.png"
    assert og_data["twitter:card"] == "summary_large_image"
    assert og_data["twitter:creator"] == "@architect"
    assert "description" not in og_data


# ==============================================================================
# 5. DOMExtractor & Facade Delegation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_dom_extractor_class_methods():
    """Verify DOMExtractor instance exposes all new extraction helpers."""
    extractor = DOMExtractor()
    html = """
    <html>
      <head>
        <meta property="og:site_name" content="Enterprise Playwright" />
        <script type="application/ld+json">{"@type": "WebSite", "url": "https://test.com"}</script>
      </head>
      <body>
        <script id="__NEXT_DATA__" type="application/json">{"props": {"pageProps": {}}}</script>
      </body>
    </html>
    """
    next_d = await extractor.extract_next_data(html)
    assert next_d == {"props": {"pageProps": {}}}

    json_ld = await extractor.extract_json_ld(html)
    assert len(json_ld) == 1
    assert json_ld[0]["@type"] == "WebSite"

    og = await extractor.extract_open_graph(html)
    assert og["og:site_name"] == "Enterprise Playwright"


@pytest.mark.asyncio
async def test_facade_mining_hydration_delegation():
    """Verify BP facade bp.mining delegations for hydration and metadata extraction."""
    bp = BP()
    html = """
    <html>
      <head>
        <meta property="og:title" content="BP Facade Test" />
        <script type="application/ld+json">{"@type": "BreadcrumbList"}</script>
      </head>
      <body>
        <script id="__NEXT_DATA__" type="application/json">{"page": "/facade"}</script>
      </body>
    </html>
    """

    res_next = await bp.mining.extract_next_data(page_or_html=html)
    assert res_next == {"page": "/facade"}

    res_jsonld = await bp.mining.extract_json_ld(page_or_html=html)
    assert len(res_jsonld) == 1
    assert res_jsonld[0]["@type"] == "BreadcrumbList"

    res_og = await bp.mining.extract_open_graph(page_or_html=html)
    assert res_og["og:title"] == "BP Facade Test"
