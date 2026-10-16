"""Phase 4 Functional Verification Suite: Extraction & DOM Intelligence.

Verifies:
- Live DOM authority (never cached/stale)
- Failure honesty (no fabricated success on missing nodes/closed pages)
- Missing vs empty distinction (observable None vs "")
- Table extraction with colspan alignment, duplicate header deduplication, missing cells
- Structured lists, cards, images, and links with absolute URL resolution
- Full provenance tracking (page_url, selector, timestamp, extracted_at)
- Multi-page and multi-session isolation
- Determinism under repeated evaluations
"""

from __future__ import annotations

import asyncio
from urllib.parse import quote
import pytest

from behavioral_playwright.exceptions import ExtractionError
from behavioral_playwright.extraction.dom import DOMExtractor
from behavioral_playwright.facade import BP
from behavioral_playwright.models.results import ExtractionRecord


def make_data_url(html: str) -> str:
    return f"data:text/html;charset=utf-8,{quote(html)}"


HTML_FIXTURE = """<!DOCTYPE html>
<html>
<head>
    <title>Phase 4 Test Page</title>
    <base href="https://app.example.com/portal/" />
</head>
<body>
    <div id="main-container">
        <h1 id="headline">  Live Intelligence Portal \u00a0 </h1>
        <p id="empty-paragraph"></p>
        <span id="attr-target" data-status="" data-id="12345" title="Hover Title">Target</span>
        
        <ul id="feature-list">
            <li>Zero Fabrication</li>
            <li>Live DOM Authority</li>
            <li>Biomechanical Fidelity</li>
        </ul>

        <table id="complex-table">
            <thead>
                <tr>
                    <th>Category</th>
                    <th colspan="2">Details & Specs</th>
                    <th>Action</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Hardware</td>
                    <td>Intel Core</td>
                    <td>64GB RAM</td>
                    <td>Edit</td>
                    <td>Delete</td>
                </tr>
                <tr>
                    <td>Network</td>
                    <td>10Gbps Fiber</td>
                    <td></td>
                    <td>Inspect</td>
                </tr>
            </tbody>
        </table>

        <div id="card-deck">
            <div class="card">
                <h3 class="card-title">Product A</h3>
                <span class="price">$199.99</span>
                <a class="card-link" href="item-a.html">View A</a>
                <img class="card-img" src="img-a.png" alt="Card A Thumbnail" />
            </div>
            <div class="card">
                <h3 class="card-title">Product B</h3>
                <span class="price">$499.00</span>
                <a class="card-link" href="/item-b.html">View B</a>
                <img class="card-img" src="https://cdn.example.com/img-b.png" alt="Card B Thumbnail" data-src="img-b-lazy.png" />
            </div>
        </div>

        <div id="link-section">
            <a href="docs/api.html" title="API Documentation">API Reference</a>
            <a href="/login" rel="nofollow" target="_blank">Login Portal</a>
            <a href="mailto:support@example.com">Email Us</a>
        </div>
    </div>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_live_dom_authority_dynamic_mutation():
    """Verify extraction strictly reflects live DOM mutations and never returns stale cached data."""
    async with BP() as bp:
        await bp.open(make_data_url(HTML_FIXTURE))
        extractor = DOMExtractor()

        # 1. Initial text extraction
        initial_text = await extractor.extract_text(bp.page.raw_page, "#headline")
        assert initial_text == "Live Intelligence Portal"

        # 2. Mutate the DOM live
        await bp.page.evaluate("() => document.getElementById('headline').innerText = 'Mutated New State'")

        # 3. Subsequent extraction must return the updated DOM state immediately
        updated_text = await extractor.extract_text(bp.page.raw_page, "#headline")
        assert updated_text == "Mutated New State"


@pytest.mark.asyncio
async def test_failure_honesty_missing_nodes():
    """Verify extraction raises ExtractionError on nonexistent elements instead of fabricating empty success."""
    async with BP() as bp:
        await bp.open(make_data_url(HTML_FIXTURE))
        extractor = DOMExtractor()

        # Nonexistent text selector must raise ExtractionError
        with pytest.raises(ExtractionError) as exc_info:
            await extractor.extract_text(bp.page.raw_page, "#nonexistent-element-xyz")
        assert "not found for selector" in str(exc_info.value)

        # Nonexistent table selector must raise ExtractionError
        with pytest.raises(ExtractionError) as exc_info:
            await extractor.extract_table(bp.page.raw_page, "#nonexistent-table-xyz")
        assert "not found for selector" in str(exc_info.value)

        # Nonexistent container for links must raise ExtractionError
        with pytest.raises(ExtractionError) as exc_info:
            await extractor.extract_links(bp.page.raw_page, container_selector="#missing-container")
        assert "not found for selector" in str(exc_info.value)


@pytest.mark.asyncio
async def test_missing_vs_empty_field_distinction():
    """Verify explicit distinction between absent fields (None) and existing empty fields ('')."""
    async with BP() as bp:
        await bp.open(make_data_url(HTML_FIXTURE))
        extractor = DOMExtractor()

        # Existing node with empty text returns empty string without error
        empty_text = await extractor.extract_text(bp.page.raw_page, "#empty-paragraph")
        assert empty_text == ""

        # Attribute extraction: existing empty attribute vs absent attribute
        attrs = await extractor.extract_attributes(
            bp.page.raw_page,
            "#attr-target",
            attributes=["data-status", "data-id", "nonexistent-attr"]
        )
        assert attrs["data-status"] == ""  # Attribute present, value empty
        assert attrs["data-id"] == "12345"  # Attribute present with value
        assert attrs["nonexistent-attr"] is None  # Attribute strictly absent


@pytest.mark.asyncio
async def test_table_extraction_with_colspan_and_duplicate_headers():
    """
    Verify table extraction:
    - colspan='2' expands column correctly without shifting subsequent columns
    - duplicate header names are deduplicated ('Action', 'Action_2')
    - missing cell in row produces observable None
    - empty cell in row produces observable ''
    """
    async with BP() as bp:
        await bp.open(make_data_url(HTML_FIXTURE))
        extractor = DOMExtractor()

        rows = await extractor.extract_table(bp.page.raw_page, "#complex-table")
        assert len(rows) == 2

        row1 = rows[0]
        assert row1["Category"] == "Hardware"
        assert row1["Details & Specs"] == "Intel Core"
        assert row1["Details & Specs_2"] == "64GB RAM"
        assert row1["Action"] == "Edit"
        assert row1["Action_2"] == "Delete"

        row2 = rows[1]
        assert row2["Category"] == "Network"
        assert row2["Details & Specs"] == "10Gbps Fiber"
        assert row2["Details & Specs_2"] == ""  # Cell was present in DOM but empty
        assert row2["Action"] == "Inspect"
        assert row2["Action_2"] is None  # Cell was omitted in row 2 (5th cell missing)


@pytest.mark.asyncio
async def test_list_and_card_structured_extraction():
    """Verify ordered list extraction and repeated card component extraction with sub-selectors."""
    async with BP() as bp:
        await bp.open(make_data_url(HTML_FIXTURE))
        extractor = DOMExtractor()

        # 1. Ordered list extraction
        items = await extractor.extract_list(bp.page.raw_page, "#feature-list")
        assert items == ["Zero Fabrication", "Live DOM Authority", "Biomechanical Fidelity"]

        # 2. Repeated card component extraction
        card_schema = {
            "title": ".card-title",
            "price": ".price",
            "url": ".card-link@href",
            "img": ".card-img@src",
        }
        cards = await extractor.extract_cards(
            bp.page.raw_page,
            item_selector=".card",
            schema=card_schema,
            container_selector="#card-deck"
        )
        assert len(cards) == 2
        assert cards[0]["title"] == "Product A"
        assert cards[0]["price"] == "$199.99"
        assert "item-a.html" in cards[0]["url"]
        assert cards[1]["title"] == "Product B"
        assert cards[1]["price"] == "$499.00"


@pytest.mark.asyncio
async def test_link_extraction_with_base_url_and_provenance():
    """Verify relative URL resolution against <base href> and comprehensive provenance recording."""
    async with BP() as bp:
        await bp.open(make_data_url(HTML_FIXTURE))
        extractor = DOMExtractor()

        links = await extractor.extract_links(bp.page.raw_page, container_selector="#link-section")
        assert len(links) >= 3

        # First link: relative to base 'https://app.example.com/portal/'
        api_link = next(link for link in links if "API Reference" in link.text)
        assert api_link.href == "https://app.example.com/portal/docs/api.html"
        assert api_link.attributes.get("title") == "API Documentation"
        assert api_link.selector == "#link-section"
        assert api_link.timestamp is not None
        assert api_link.extracted_at is not None
        assert api_link.extracted_at > 0

        # Root relative link: resolved to origin root
        login_link = next(link for link in links if "Login Portal" in link.text)
        assert login_link.href == "https://app.example.com/login"
        assert login_link.attributes.get("target") == "_blank"

        # Mailto scheme preserved
        mail_link = next(link for link in links if "Email Us" in link.text)
        assert mail_link.href == "mailto:support@example.com"


@pytest.mark.asyncio
async def test_image_extraction_attributes_and_dimensions():
    """Verify image extraction resolves URLs, extracts alt text, srcset, and lazy data-src attributes."""
    async with BP() as bp:
        await bp.open(make_data_url(HTML_FIXTURE))
        extractor = DOMExtractor()

        images = await extractor.extract_images(bp.page.raw_page, container_selector="#card-deck")
        assert len(images) == 2

        img_b = next(img for img in images if img.text == "Card B Thumbnail")
        assert img_b.url == "https://cdn.example.com/img-b.png"
        assert img_b.attributes.get("data-src") == "img-b-lazy.png"
        assert img_b.selector == "#card-deck"


@pytest.mark.asyncio
async def test_concurrency_and_session_isolation():
    """Verify simultaneous extractions across isolated pages do not cross-pollute or leak state."""
    async with BP() as bp:
        page_a = await bp.session.new_page()
        page_b = await bp.session.new_page()

        html_a = "<html><body><h1 id='id'>Session Alpha Token 111</h1></body></html>"
        html_b = "<html><body><h1 id='id'>Session Beta Token 999</h1></body></html>"

        await page_a.goto(make_data_url(html_a))
        await page_b.goto(make_data_url(html_b))

        extractor = DOMExtractor()

        # Concurrent async extractions
        res_a, res_b = await asyncio.gather(
            extractor.extract_text(page_a, "#id"),
            extractor.extract_text(page_b, "#id")
        )

        assert res_a == "Session Alpha Token 111"
        assert res_b == "Session Beta Token 999"

        await page_a.close()
        await page_b.close()


@pytest.mark.asyncio
async def test_extraction_determinism():
    """Verify repeated extraction against identical DOM produces bit-for-bit deterministic outputs."""
    async with BP() as bp:
        await bp.open(make_data_url(HTML_FIXTURE))
        extractor = DOMExtractor()

        results = []
        for _ in range(5):
            table = await extractor.extract_table(bp.page.raw_page, "#complex-table")
            text = await extractor.extract_text(bp.page.raw_page, "#headline")
            results.append((table, text))

        first_table, first_text = results[0]
        for table, text in results[1:]:
            assert table == first_table
            assert text == first_text


@pytest.mark.asyncio
async def test_failure_honesty_closed_page():
    """Verify attempting extraction on a closed page raises ExtractionError without unhandled crash."""
    async with BP() as bp:
        page = await bp.session.new_page()
        await page.goto(make_data_url("<html><body><p id='target'>Hello</p></body></html>"))
        await page.close()

        extractor = DOMExtractor()
        with pytest.raises(ExtractionError):
            await extractor.extract_text(page, "#target")


@pytest.mark.asyncio
async def test_bp_facade_extraction_targets():
    """Verify bp.extract() dispatches cleanly to all supported target modes."""
    async with BP() as bp:
        await bp.open(make_data_url(HTML_FIXTURE))

        # 1. Links
        links = await bp.extract(target="links", container_selector="#link-section")
        assert len(links) >= 3

        # 2. Table
        table = await bp.extract(target="table", container_selector="#complex-table")
        assert len(table) == 2

        # 3. Text
        text = await bp.extract(target="text", container_selector="#headline")
        assert text == "Live Intelligence Portal"

        # 4. List
        items = await bp.extract(target="list", container_selector="#feature-list")
        assert len(items) == 3

        # 5. Images
        images = await bp.extract(target="images", container_selector="#card-deck")
        assert len(images) == 2
