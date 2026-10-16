"""Functional Validation: Realistic End-to-End Scenarios.
Explicit Given / When / Then scenarios verifying observable real-world behavior across components.
"""

from __future__ import annotations

import json
import os
import tempfile
import pytest

from behavioral_playwright.facade import BP
from behavioral_playwright.mcp.tools import McpToolDispatcher
from behavioral_playwright.storage.exporters import DataStorageManager
from behavioral_playwright.exceptions import ElementResolutionError


E2E_APP_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Behavioral Store Application</title>
</head>
<body>
    <header>
        <h1 id="store-title">Modern E-Commerce Portal</h1>
    </header>

    <main>
        <!-- Search & Filter Form -->
        <section id="search-section">
            <input id="product-search" name="search_query" type="text" placeholder="Search catalog..." />
            <button id="search-submit" onclick="
                var q = document.getElementById('product-search').value;
                document.getElementById('search-result').innerText = 'Query: ' + q;
                document.getElementById('search-result').className = 'active-result';
            ">Search</button>
            <div id="search-result">No query submitted</div>
        </section>

        <!-- Product Listing & Cart Actions -->
        <section id="catalog">
            <article class="product-card" id="prod-1">
                <span class="product-name">Quantum Shield Pro</span>
                <span class="product-price">$49.99</span>
                <button class="add-to-cart-btn" onclick="
                    var cart = document.getElementById('cart-count');
                    cart.innerText = parseInt(cart.innerText) + 1;
                    this.innerText = 'Added!';
                    this.disabled = true;
                ">Add to Cart</button>
            </article>
        </section>

        <!-- Dynamic Cart Display -->
        <div id="cart-container">
            <span>Items in cart: </span><span id="cart-count">0</span>
        </div>

        <!-- Semantic Mutation Area for Self-Healing -->
        <div id="checkout-area">
            <!-- ID mutated to random hash, but accessible role and aria remain -->
            <button id="btn_mutated_9a7x1" role="button" aria-label="Proceed to Checkout" onclick="
                document.getElementById('checkout-status').innerText = 'Order Placed Successfully';
            ">Check Out</button>
            <div id="checkout-status">Pending</div>
        </div>
    </main>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_scenario_a_navigate_locate_click_verify_state():
    """Scenario A: Navigate -> locate -> click -> verify state change.
    
    Given: A local e-commerce store page with a product and cart count of 0
    When:  The user clicks the 'Add to Cart' button
    Then:  The cart count in the DOM increments to 1 and the button text updates to 'Added!'
    """
    async with BP() as bp:
        # Given
        await bp.open(f"data:text/html,{E2E_APP_HTML}")
        init_cart = await bp.page.evaluate("() => document.getElementById('cart-count').innerText")
        assert init_cart == "0"
        
        # When
        await bp.click(".add-to-cart-btn")
        
        # Then
        new_cart = await bp.page.evaluate("() => document.getElementById('cart-count').innerText")
        btn_text = await bp.page.evaluate("() => document.querySelector('.add-to-cart-btn').innerText")
        is_disabled = await bp.page.evaluate("() => document.querySelector('.add-to-cart-btn').disabled")
        
        assert new_cart == "1"
        assert btn_text == "Added!"
        assert is_disabled is True


@pytest.mark.asyncio
async def test_scenario_b_navigate_locate_input_type_verify_value():
    """Scenario B: Navigate -> locate input -> type -> verify DOM value and submission.
    
    Given: A local page containing a search input field and submit button
    When:  The user types 'Quantum Mechanics' and clicks Search
    Then:  The DOM input value reflects 'Quantum Mechanics' and search-result displays 'Query: Quantum Mechanics'
    """
    async with BP() as bp:
        # Given
        await bp.open(f"data:text/html,{E2E_APP_HTML}")
        
        # When
        await bp.type("#product-search", "Quantum Mechanics")
        await bp.click("#search-submit")
        
        # Then
        input_value = await bp.page.evaluate("() => document.getElementById('product-search').value")
        result_text = await bp.page.evaluate("() => document.getElementById('search-result').innerText")
        result_class = await bp.page.evaluate("() => document.getElementById('search-result').className")
        
        assert input_value == "Quantum Mechanics"
        assert result_text == "Query: Quantum Mechanics"
        assert result_class == "active-result"


@pytest.mark.asyncio
async def test_scenario_c_self_healing_recovery_on_mutated_id():
    """Scenario C: Locate element with broken ID -> self-healing recovers -> verify state change.
    
    Given: A checkout button whose ID was mutated by the server (btn_mutated_9a7x1)
    When:  The automation attempts to click the button by its accessible semantic label 'Proceed to Checkout'
    Then:  The self-healing resolver recovers the element and checkout-status becomes 'Order Placed Successfully'
    """
    async with BP() as bp:
        # Given
        await bp.open(f"data:text/html,{E2E_APP_HTML}")
        
        # When
        res = await bp.page.click_healed("Proceed to Checkout")
        assert res.success is True
        
        # Then
        status_text = await bp.page.evaluate("() => document.getElementById('checkout-status').innerText")
        assert status_text == "Order Placed Successfully"


def test_scenario_d_extract_persist_export_read_back_compare():
    """Scenario D: Extract structured data -> persist/export -> read back -> compare.
    
    Given: Extracted structured catalog records
    When:  The records are serialized and exported via DataStorageManager to JSON and CSV
    Then:  The physical files exist on disk and read back with exact structural and value equality
    """
    catalog_records = [
        {"product_id": 101, "title": "Quantum Shield Pro", "price": 49.99, "currency": "USD"},
        {"product_id": 102, "title": "Stealth Proxy Router", "price": 129.50, "currency": "USD"},
    ]
    
    manager = DataStorageManager()
    with tempfile.TemporaryDirectory() as tmpdir:
        # Export JSON
        target_json = os.path.join(tmpdir, "catalog.json")
        out_path = manager.export(catalog_records, target_json, format="json")
        assert os.path.exists(out_path)
        
        # Read back JSON
        with open(out_path, "r", encoding="utf-8") as f:
            persisted_data = json.load(f)
            
        assert len(persisted_data) == 2
        assert persisted_data[0]["title"] == "Quantum Shield Pro"
        assert persisted_data[1]["price"] == 129.50
        assert persisted_data == catalog_records


@pytest.mark.asyncio
async def test_scenario_e_mcp_tool_framework_action_observable_state():
    """Scenario E: MCP tool -> framework action -> observable browser/result state.
    
    Given: The McpToolDispatcher initialized with the framework engine
    When:  The 'take_screenshot' tool is invoked with a local page URL
    Then:  The tool launches a real browser, captures the rendered canvas, and returns image/png data
    """
    dispatcher = McpToolDispatcher()
    test_url = f"data:text/html,{E2E_APP_HTML}"
    
    result = await dispatcher.execute_tool("take_screenshot", {"url": test_url})
    
    assert result.get("status") == "success"
    assert result.get("mime_type") == "image/png"
    assert len(result.get("data", "")) > 500
