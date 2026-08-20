"""Unit tests for SelfHealingResolver cascading resolution engine."""

import pytest
from behavioral_playwright.browser.mock_provider import MockElementHandle, MockPage
from behavioral_playwright.config.settings import ResolverConfig
from behavioral_playwright.models.results import ResolutionStrategy
from behavioral_playwright.selectors.resolver import SelfHealingResolver


@pytest.mark.asyncio
async def test_resolver_l1_exact_match():
    resolver = SelfHealingResolver()
    page = MockPage()
    # Add element so query_selector_all matches immediately
    page._elements = [
        MockElementHandle(tag="button", attributes={"id": "login-btn"}, text="Login")
    ]

    result = await resolver.resolve(page, "#login-btn")
    assert result.success is True
    assert result.strategy == ResolutionStrategy.L1_EXACT
    assert result.selector == "#login-btn"


@pytest.mark.asyncio
async def test_resolver_l2_semantic_cascade():
    resolver = SelfHealingResolver()
    page = MockPage()
    page._elements = []  # L1 fails

    # Register DOM snapshot with mutated button having aria-label="Login"
    page.register_eval_result("const query =", [
        {
            "tag": "button",
            "id": "new-auth-id-99",
            "aria_label": "Login",
            "text": "Sign In to Account",
            "is_visible": True,
            "selector": "button#new-auth-id-99"
        }
    ])

    result = await resolver.resolve(page, "Login")
    assert result.success is True
    assert result.strategy == ResolutionStrategy.L2_SEMANTIC
    assert result.is_healed is True
    assert result.selector == "button#new-auth-id-99"


@pytest.mark.asyncio
async def test_resolver_l3_fuzzy_cascade():
    resolver = SelfHealingResolver()
    page = MockPage()
    page._elements = []

    # Register DOM snapshot with text
    page.register_eval_result("const query =", [
        {
            "tag": "a",
            "id": "btn-docs",
            "text": "ComprehensiveDocumentation",
            "is_visible": True,
            "selector": "a#btn-docs"
        }
    ])

    # Target with typo and distance
    result = await resolver.resolve(page, "ComprehensivDocumntation")
    assert result.success is True
    assert result.strategy == ResolutionStrategy.L3_FUZZY
    assert result.is_healed is True
    assert result.selector == "a#btn-docs"


@pytest.mark.asyncio
async def test_resolver_exhaustion_failure():
    resolver = SelfHealingResolver()
    page = MockPage()
    page._elements = []

    page.register_eval_result("const query =", [
        {"tag": "div", "text": "Unrelated content", "is_visible": True, "selector": "div.unrelated"}
    ])

    result = await resolver.resolve(page, "CompletelyNonExistentTargetElement")
    assert result.success is False
    assert result.selector is None
