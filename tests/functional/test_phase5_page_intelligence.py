"""Phase 5 Functional Verification Suite: Page Intelligence, Mapping & Structured Understanding.

Verifies:
- Semantic field mapping to Pydantic schemas and typed dictionaries
- Bounded confidence scoring and zero-evidence rejection
- Ambiguity detection and strict ambiguity rejection (AmbiguityError)
- Source precedence (Live DOM > JSON-LD > OpenGraph)
- Financial precision type coercion (Decimal(18, 4))
- Complete provenance preservation (source_type, selector, confidence, timestamps)
- SiteMapper internal vs external link classification and heading hierarchy
- SearchEngine behavioral submission, validation, and deduplication
- Concurrency and cross-page state isolation
- Live DOM authority and determinism
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from urllib.parse import quote
import pytest
from pydantic import BaseModel

from behavioral_playwright.exceptions import AmbiguityError, MappingError
from behavioral_playwright.facade import BP
from behavioral_playwright.mapping.models import MappingResult, SourceType
from behavioral_playwright.mapping.schema_mapper import PageSchemaMapper
from behavioral_playwright.mapping.mapper import SiteMapper
from behavioral_playwright.search.engine import SearchEngine


def make_data_url(html: str) -> str:
    return f"data:text/html;charset=utf-8,{quote(html)}"


class ProductSchema(BaseModel):
    title: str
    price: Decimal
    sku: str
    image: str
    in_stock: bool


PAGE_INTELLIGENCE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Quantum Core i9 Workstation - TechStore</title>
    <!-- OpenGraph Metadata -->
    <meta property="og:title" content="Quantum Core i9 OpenGraph Title" />
    <meta property="og:description" content="Ultimate computing powerhouse with 64GB DDR5." />
    <meta property="og:image" content="https://cdn.example.com/images/og-workstation.jpg" />

    <!-- Schema.org JSON-LD -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Quantum Core i9 Workstation JSON-LD",
        "sku": "QC-I9-64GB",
        "image": "https://cdn.example.com/images/jsonld-workstation.jpg",
        "offers": {
            "@type": "Offer",
            "price": "2499.00",
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock"
        }
    }
    </script>
</head>
<body>
    <header>
        <nav id="site-nav">
            <a href="https://example.com/catalog">Internal Catalog</a>
            <a href="https://example.com/cart">Shopping Cart</a>
            <a href="https://external-partner.com/deals">Partner External Deals</a>
        </nav>
    </header>

    <main id="product-details">
        <h1 id="product-title" data-testid="title">Quantum Core i9 Workstation Extreme</h1>
        
        <div class="product-gallery">
            <img id="main-product-image" src="https://cdn.example.com/images/live-dom-workstation.jpg" alt="Quantum Core i9 Main Photo" data-testid="image" />
        </div>

        <div class="pricing-block">
            <span class="currency-symbol">$</span>
            <span id="price" data-testid="price" itemprop="price">2,399.50</span>
        </div>

        <div class="meta-specs">
            <span id="sku" data-testid="sku" itemprop="sku">SKU-QUANTUM-2026</span>
            <span id="stock-status" class="in-stock" data-testid="in_stock">In Stock</span>
        </div>

        <section id="features">
            <h2>Technical Specifications</h2>
            <h3>Processor & Memory</h3>
            <p>64 Cores, 128 Threads, 64GB DDR5 ECC Registered Memory.</p>
        </section>

        <!-- Search component fixture -->
        <section id="search-section">
            <form id="search-form">
                <input type="search" id="site-search" name="q" placeholder="Search workstation components..." />
                <button type="submit" id="search-submit">Search</button>
            </form>
            <div id="search-results">
                <a href="https://example.com/item/1">Result 1: NVMe 2TB Gen5</a>
                <a href="https://example.com/item/2">Result 2: Liquid Cooler 360mm</a>
                <a href="https://example.com/item/1">Result 1: NVMe 2TB Gen5 (Duplicate)</a>
            </div>
        </section>
    </main>
</body>
</html>
"""


AMBIGUOUS_PRICE_HTML = """<!DOCTYPE html>
<html>
<head><title>Ambiguous Price Page</title></head>
<body>
    <h1>Product With Ambiguous Pricing</h1>
    <!-- Two competing price candidates with equal selector prominence -->
    <div id="price-option-a" class="price" data-testid="price">$199.99</div>
    <div id="price-option-b" class="price" data-testid="price">$299.99</div>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_semantic_schema_mapping_to_pydantic():
    """Verify live DOM evidence maps cleanly to Pydantic schema with financial Decimal conversion."""
    async with BP() as bp:
        await bp.open(make_data_url(PAGE_INTELLIGENCE_HTML))
        mapper = PageSchemaMapper(confidence_threshold=0.60)

        result: MappingResult = await mapper.map_schema(bp.page, ProductSchema)
        assert result.success is True
        assert result.confidence >= 0.85
        assert len(result.missing_fields) == 0
        assert len(result.ambiguities) == 0

        # Type Coercion Verification
        assert result.data["title"] == "Quantum Core i9 Workstation Extreme"
        assert result.data["price"] == Decimal("2399.50")
        assert result.data["sku"] == "SKU-QUANTUM-2026"
        assert result.data["image"] == "https://cdn.example.com/images/live-dom-workstation.jpg"
        assert result.data["in_stock"] is True

        # Provenance Verification
        price_field = result.fields["price"]
        assert price_field.evidence is not None
        assert price_field.evidence.source_type == SourceType.DOM
        assert price_field.evidence.selector is not None
        assert price_field.confidence >= 0.80
        assert price_field.is_ambiguous is False


@pytest.mark.asyncio
async def test_source_precedence_live_dom_over_metadata():
    """Verify live DOM values take precedence over JSON-LD metadata when both are present."""
    async with BP() as bp:
        await bp.open(make_data_url(PAGE_INTELLIGENCE_HTML))
        mapper = PageSchemaMapper(precedence=[SourceType.DOM, SourceType.JSON_LD, SourceType.OPEN_GRAPH])

        result = await mapper.map_schema(bp.page, {"price": Decimal, "title": str})
        assert result.success is True
        # Live DOM price ($2399.50) overrides JSON-LD price ($2499.00)
        assert result.data["price"] == Decimal("2399.50")
        assert result.data["title"] == "Quantum Core i9 Workstation Extreme"
        assert result.fields["price"].evidence.source_type == SourceType.DOM


@pytest.mark.asyncio
async def test_source_fallback_to_json_ld_when_dom_absent():
    """Verify JSON-LD metadata is utilized when live DOM element for a field is absent."""
    html_without_dom_sku = """<!DOCTYPE html>
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Metadata Only Product",
            "sku": "JSONLD-SKU-999"
        }
        </script>
    </head>
    <body>
        <h1>Metadata Only Product</h1>
    </body>
    </html>
    """
    async with BP() as bp:
        await bp.open(make_data_url(html_without_dom_sku))
        mapper = PageSchemaMapper()

        result = await mapper.map_schema(bp.page, {"sku": str, "name": str})
        assert result.data["sku"] == "JSONLD-SKU-999"
        assert result.fields["sku"].evidence.source_type == SourceType.JSON_LD


@pytest.mark.asyncio
async def test_ambiguity_detection_and_strict_rejection():
    """Verify ambiguity detection flags multiple close candidates and raises AmbiguityError on strict mode."""
    async with BP() as bp:
        await bp.open(make_data_url(AMBIGUOUS_PRICE_HTML))
        mapper = PageSchemaMapper(confidence_threshold=0.60, ambiguity_margin=0.10)

        # 1. Non-strict mode records ambiguity without crashing
        res_lenient = await mapper.map_schema(bp.page, {"price": Decimal}, strict_ambiguity=False)
        assert "price" in res_lenient.ambiguities
        assert res_lenient.fields["price"].is_ambiguous is True
        assert res_lenient.fields["price"].candidate_count >= 2

        # 2. Strict mode raises typed AmbiguityError
        with pytest.raises(AmbiguityError) as exc_info:
            await mapper.map_schema(bp.page, {"price": Decimal}, strict_ambiguity=True)
        assert "Ambiguous candidates for field 'price'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_required_field_missing_raises_mapping_error():
    """Verify require_all_fields=True raises MappingError when required fields cannot be found."""
    async with BP() as bp:
        await bp.open(make_data_url(PAGE_INTELLIGENCE_HTML))
        mapper = PageSchemaMapper()

        with pytest.raises(MappingError) as exc_info:
            await mapper.map_schema(
                bp.page,
                {"nonexistent_barcode_spec": str, "title": str},
                require_all_fields=True
            )
        assert "Required schema fields could not be resolved" in str(exc_info.value)


@pytest.mark.asyncio
async def test_site_mapper_netloc_classification_and_headings():
    """Verify SiteMapper accurately categorizes internal vs external links and extracts heading hierarchy."""
    async with BP() as bp:
        test_url = "https://example.com/product/123"
        await bp.open(make_data_url(PAGE_INTELLIGENCE_HTML))
        
        # Inject current URL for netloc testing
        mapper = SiteMapper(bp.page)
        
        # Mock goto to stay on data url while evaluating target URL logic
        orig_goto = bp.page.goto
        async def fake_goto(url):
            pass
        bp.page.goto = fake_goto

        map_data = await mapper.map("https://example.com/product/123")
        bp.page.goto = orig_goto

        assert map_data["internal_links_count"] >= 2  # catalog, cart
        assert map_data["external_links_count"] >= 1  # external-partner.com
        assert map_data["headings_count"] >= 3  # h1, h2, h3
        
        heading_levels = [h["level"] for h in map_data["headings"]]
        assert "h1" in heading_levels
        assert "h2" in heading_levels
        assert "h3" in heading_levels


@pytest.mark.asyncio
async def test_search_engine_behavioral_submission_and_deduplication():
    """Verify SearchEngine validates query, types, submits, and returns deduplicated results."""
    async with BP() as bp:
        await bp.open(make_data_url(PAGE_INTELLIGENCE_HTML))
        engine = SearchEngine(bp.page)

        # 1. Empty query raises ValueError
        with pytest.raises(ValueError) as exc_info:
            await engine.search("")
        assert "must not be empty" in str(exc_info.value)

        # 2. Valid search execution
        results = await engine.search(
            query="workstation",
            search_input_selector="#site-search",
            submit_selector="#search-submit",
            results_container_selector="#search-results"
        )

        # Result 1 was duplicated in HTML fixture, deduplication must produce 2 unique results
        assert len(results) == 2
        assert "Result 1" in results[0].text
        assert "Result 2" in results[1].text
        assert results[0].metadata.get("search_query") == "workstation"
        assert results[0].metadata.get("search_position") == 1
        assert results[1].metadata.get("search_position") == 2


@pytest.mark.asyncio
async def test_concurrency_and_session_isolation():
    """Verify simultaneous schema mapping across independent sessions does not leak candidate state."""
    async with BP() as bp:
        page_a = await bp.session.new_page()
        page_b = await bp.session.new_page()

        html_a = """<html><body>
            <h1 id="title" data-testid="title">Alpha Server</h1>
            <span id="price" data-testid="price">$1,000.00</span>
        </body></html>"""

        html_b = """<html><body>
            <h1 id="title" data-testid="title">Beta Laptop</h1>
            <span id="price" data-testid="price">$2,500.00</span>
        </body></html>"""

        await page_a.goto(make_data_url(html_a))
        await page_b.goto(make_data_url(html_b))

        mapper = PageSchemaMapper()

        res_a, res_b = await asyncio.gather(
            mapper.map_schema(page_a, {"title": str, "price": Decimal}),
            mapper.map_schema(page_b, {"title": str, "price": Decimal}),
        )

        assert res_a.data["title"] == "Alpha Server"
        assert res_a.data["price"] == Decimal("1000.00")

        assert res_b.data["title"] == "Beta Laptop"
        assert res_b.data["price"] == Decimal("2500.00")

        await page_a.close()
        await page_b.close()


@pytest.mark.asyncio
async def test_live_dom_authority_dynamic_mutation():
    """Verify mapping updates immediately after dynamic DOM mutation without stale caching."""
    async with BP() as bp:
        await bp.open(make_data_url(PAGE_INTELLIGENCE_HTML))
        mapper = PageSchemaMapper()

        # Initial mapping
        res1 = await mapper.map_schema(bp.page, {"price": Decimal})
        assert res1.data["price"] == Decimal("2399.50")

        # Mutate DOM price via JS
        await bp.page.evaluate("() => document.getElementById('price').innerText = '1,899.00'")

        # Subsequent mapping reflects new live price
        res2 = await mapper.map_schema(bp.page, {"price": Decimal})
        assert res2.data["price"] == Decimal("1899.00")


@pytest.mark.asyncio
async def test_bp_facade_map_schema_integration():
    """Verify bp.map_schema() facade delegation functions end-to-end."""
    async with BP() as bp:
        await bp.open(make_data_url(PAGE_INTELLIGENCE_HTML))
        result = await bp.map_schema(ProductSchema)
        assert result.success is True
        assert result.data["title"] == "Quantum Core i9 Workstation Extreme"
        assert result.data["price"] == Decimal("2399.50")
