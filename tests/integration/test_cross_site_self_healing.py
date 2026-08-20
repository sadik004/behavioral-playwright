"""
Integration tests: Cross-Site Self-Healing Element Recovery.
Demonstrates:
  Site A (E-Commerce / Content Portal with mutated class):
    Fixed selector fails -> Semantic resolver recovers.
  Site B (News Forum with mutated IDs):
    Fixed selector fails -> Fuzzy/Semantic resolver recovers.
"""

import pytest
from behavioral_playwright.browser.mock_provider import MockBrowserProvider
from behavioral_playwright.config.settings import AutomationConfig, BrowserConfig
from behavioral_playwright.models.results import ResolutionStrategy
from behavioral_playwright.page.session import BrowserSession


@pytest.mark.asyncio
async def test_site_a_semantic_self_healing():
    """
    Scenario: E-Commerce store mutated its button class from .btn-add-cart to .v2-cart-btn-98.
    Fixed selector fails -> Self-Healing L2 Semantic recovers via aria-label.
    """
    config = AutomationConfig(browser=BrowserConfig(headless=True))
    mock_provider = MockBrowserProvider(config.browser)

    async with BrowserSession(config=config, provider=mock_provider) as session:
        page = await session.new_page()
        await page.goto("https://store-a.example.com/item")

        # Configure mock page DOM snapshot simulating mutated layout
        page.raw_page.register_eval_result("const query =", [
            {
                "tag": "button",
                "id": "",
                "class_name": "v2-cart-btn-98 dynamic-hash-3a",
                "text": "Buy Item",
                "role": "button",
                "aria_label": "Add to Cart",
                "is_visible": True,
                "selector": "button.v2-cart-btn-98.dynamic-hash-3a"
            }
        ])

        # Phase 1: Fixed fragile selector fails
        fixed_selector = "button.btn-add-cart"
        res_fixed = await page.resolve(fixed_selector)
        # Because fixed selector does not match the DOM, resolver cascades to healing
        assert res_fixed.is_healed is True
        assert res_fixed.strategy == ResolutionStrategy.L2_SEMANTIC
        assert "v2-cart-btn-98" in res_fixed.selector

        # Phase 2: Resolving by accessible intention directly
        res_semantic = await page.resolve("Add to Cart")
        assert res_semantic.success is True
        assert res_semantic.strategy == ResolutionStrategy.L2_SEMANTIC
        assert res_semantic.confidence >= 0.85
        assert "v2-cart-btn-98" in res_semantic.selector


@pytest.mark.asyncio
async def test_site_b_fuzzy_self_healing():
    """
    Scenario: News forum mutated its story submit button ID from #submit-link to #post-story-v4.
    Fixed selector fails -> Self-Healing L3 Fuzzy recovers via text similarity.
    """
    config = AutomationConfig(browser=BrowserConfig(headless=True))
    mock_provider = MockBrowserProvider(config.browser)

    async with BrowserSession(config=config, provider=mock_provider) as session:
        page = await session.new_page()
        await page.goto("https://news-b.example.com")

        # Configure mock page DOM snapshot simulating mutated layout
        page.raw_page.register_eval_result("const query =", [
            {
                "tag": "a",
                "id": "post-story-v4",
                "class_name": "nav-link",
                "text": "Submit New Story",
                "is_visible": True,
                "selector": "a#post-story-v4"
            }
        ])

        # Phase 1: Fixed fragile selector fails
        fixed_selector = "a#submit-link"
        res_fixed = await page.resolve(fixed_selector)
        assert res_fixed.is_healed is True
        assert "post-story-v4" in res_fixed.selector

        # Phase 2: Resolving by approximate text intention
        res_fuzzy = await page.resolve("Submit Story")
        assert res_fuzzy.success is True
        assert res_fuzzy.strategy in [ResolutionStrategy.L2_SEMANTIC, ResolutionStrategy.L3_FUZZY]
        assert res_fuzzy.selector == "a#post-story-v4"
