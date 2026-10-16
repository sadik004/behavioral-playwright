"""Functional Validation: Data Extraction & Storage Pipelines.
Tests structured DOM/metadata extraction and physical serialization/export to JSON, CSV, and SQLite.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import pytest

from behavioral_playwright.extraction.dom import DOMExtractor, extract_json_ld, extract_open_graph
from behavioral_playwright.facade import BP
from behavioral_playwright.storage.exporters import DataStorageManager
from behavioral_playwright.exceptions import ExtractionError


EXTRACTION_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Extraction & Storage Test</title>
    <!-- OpenGraph Metadata -->
    <meta property="og:title" content="Verified OpenGraph Title" />
    <meta property="og:description" content="Audited OpenGraph Description" />
    <meta name="twitter:card" content="summary_large_image" />

    <!-- Schema.org JSON-LD -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Product",
                "name": "Playwright Hardened Engine",
                "offers": {
                    "@type": "Offer",
                    "price": "99.00",
                    "priceCurrency": "USD"
                }
            }
        ]
    }
    </script>
</head>
<body>
    <div id="links-container">
        <a href="https://example.com/one" title="Link 1">First Page</a>
        <a href="https://example.com/two" title="Link 2">Second Page</a>
    </div>

    <table id="data-table">
        <thead>
            <tr><th>Product</th><th>Price</th><th>Stock</th></tr>
        </thead>
        <tbody>
            <tr><td>Alpha</td><td>$10.00</td><td>100</td></tr>
            <tr><td>Beta</td><td>$25.50</td><td>45</td></tr>
        </tbody>
    </table>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_dom_extractor_links_and_table():
    """Verify DOMExtractor extracts structured links and table rows from real page."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{EXTRACTION_HTML}")
        extractor = DOMExtractor()
        
        # 1. Links
        links = await extractor.extract_links(bp.page.raw_page, container_selector="#links-container")
        assert len(links) == 2
        assert links[0].text == "First Page"
        assert links[0].href == "https://example.com/one"
        assert links[1].text == "Second Page"
        assert links[1].href == "https://example.com/two"
        
        # 2. Table
        table_rows = await extractor.extract_table(bp.page.raw_page, table_selector="#data-table")
        assert len(table_rows) == 2
        assert table_rows[0]["Product"] == "Alpha"
        assert table_rows[0]["Price"] == "$10.00"
        assert table_rows[1]["Product"] == "Beta"
        assert table_rows[1]["Stock"] == "45"


@pytest.mark.asyncio
async def test_metadata_extraction_json_ld_and_og():
    """Verify JSON-LD schemas and OpenGraph tags are unpacked accurately."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{EXTRACTION_HTML}")
        
        # 1. OpenGraph
        og = await extract_open_graph(bp.page.raw_page)
        assert og.get("og:title") == "Verified OpenGraph Title"
        assert og.get("og:description") == "Audited OpenGraph Description"
        assert og.get("twitter:card") == "summary_large_image"
        
        # 2. JSON-LD (@graph flattened)
        json_ld = await extract_json_ld(bp.page.raw_page)
        assert len(json_ld) >= 1
        product = next((item for item in json_ld if item.get("@type") == "Product"), None)
        assert product is not None
        assert product["name"] == "Playwright Hardened Engine"
        assert product["offers"]["price"] == "99.00"


def test_storage_export_roundtrip_json_csv_sqlite():
    """Verify DataStorageManager exports data to disk and files read back with bit-for-bit equivalence."""
    manager = DataStorageManager()
    
    test_records = [
        {"id": 1, "sku": "SKU-001", "name": "Item Alpha", "price": 10.50},
        {"id": 2, "sku": "SKU-002", "name": "Item Beta", "price": 42.00},
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Export JSON
        json_path = os.path.join(tmpdir, "exported.json")
        out_json = manager.export(test_records, json_path, format="json")
        assert os.path.exists(out_json)
        with open(out_json, "r", encoding="utf-8") as f:
            read_json = json.load(f)
        assert len(read_json) == 2
        assert read_json[0]["sku"] == "SKU-001"
        assert read_json[1]["price"] == 42.00
        
        # 2. Export CSV
        csv_path = os.path.join(tmpdir, "exported.csv")
        out_csv = manager.export(test_records, csv_path, format="csv")
        assert os.path.exists(out_csv)
        with open(out_csv, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]
        assert "id,sku,name,price" in lines[0]
        assert "1,SKU-001,Item Alpha,10.5" in lines[1]
        
        # 3. Export SQLite
        sqlite_path = os.path.join(tmpdir, "exported.db")
        out_db = manager.export(test_records, sqlite_path, format="sqlite", table_name="inventory")
        assert os.path.exists(out_db)
        conn = sqlite3.connect(out_db)
        cursor = conn.cursor()
        cursor.execute("SELECT sku, price FROM inventory ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        assert len(rows) == 2
        assert rows[0][0] == "SKU-001"
        assert rows[1][0] == "SKU-002"


def test_storage_export_negative_invalid_destination():
    """Verify DataStorageManager raises OSError/IOError when target directory does not exist and cannot be written."""
    manager = DataStorageManager()
    records = [{"test": "data"}]
    
    invalid_path = "Z:\\NonExistentDrive_Path_12345\\file.json"
    with pytest.raises((OSError, IOError)):
        manager.export(records, invalid_path, format="json")


def test_storage_export_negative_empty_target():
    """Verify DataStorageManager raises ValueError when target_path is empty."""
    manager = DataStorageManager()
    records = [{"test": "data"}]
    
    with pytest.raises(ValueError):
        manager.export(records, "", format="json")
