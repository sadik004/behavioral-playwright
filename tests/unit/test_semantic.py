"""Unit tests for SemanticResolverStrategy."""

import pytest
from behavioral_playwright.models.elements import DOMElement
from behavioral_playwright.models.results import ResolutionStrategy
from behavioral_playwright.selectors.semantic import SemanticResolverStrategy


def test_semantic_scoring_exact_accessible_name():
    strategy = SemanticResolverStrategy()
    el = DOMElement(tag="button", aria_label="Submit Payment", text="Pay Now")
    score = strategy.score_element("Submit Payment", el)
    assert score >= 0.95


def test_semantic_scoring_placeholder():
    strategy = SemanticResolverStrategy()
    el = DOMElement(tag="input", placeholder="Search products, brands...", name="q")
    score = strategy.score_element("Search products", el)
    assert score >= 0.80


def test_semantic_scoring_role_and_tag_boost():
    strategy = SemanticResolverStrategy()
    el = DOMElement(tag="button", role="button", text="Checkout")
    score = strategy.score_element("Checkout", el)
    assert score >= 0.90


@pytest.mark.asyncio
async def test_semantic_resolver_selection():
    strategy = SemanticResolverStrategy(confidence_threshold=0.70)
    candidates = [
        DOMElement(tag="a", text="Home", selector="a.nav-home"),
        DOMElement(tag="button", aria_label="Sign In", selector="button#auth-btn"),
        DOMElement(tag="a", text="About", selector="a.nav-about"),
    ]

    res = await strategy.resolve(page=None, target="Sign In", candidates=candidates)
    assert res is not None
    assert res.success is True
    assert res.strategy == ResolutionStrategy.L2_SEMANTIC
    assert res.matched_element.selector == "button#auth-btn"
    assert res.confidence >= 0.85
