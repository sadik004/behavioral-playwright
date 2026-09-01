"""Unit tests for FuzzyResolverStrategy and Levenshtein similarity metric."""

import pytest
from behavioral_playwright.models.elements import DOMElement
from behavioral_playwright.models.results import ResolutionStrategy
from behavioral_playwright.selectors.fuzzy import (
    FuzzyResolverStrategy,
    calculate_levenshtein_distance,
    calculate_similarity_ratio,
    normalize_text,
)


def test_normalize_text():
    assert normalize_text("  Sign-In / Login  ") == "sign in login"
    assert normalize_text("RTX 4060 Ti (8GB)!") == "rtx 4060 ti 8gb"


def test_levenshtein_distance():
    assert calculate_levenshtein_distance("kitten", "sitting") == 3
    assert calculate_levenshtein_distance("login", "login") == 0
    assert calculate_levenshtein_distance("search", "searche") == 1


def test_similarity_ratio():
    assert calculate_similarity_ratio("Sign In", "Sign In") == 1.0
    assert calculate_similarity_ratio("Search bar", "Search") >= 0.70
    assert calculate_similarity_ratio("Apple", "Banana") < 0.30


@pytest.mark.asyncio
async def test_fuzzy_resolver_selection():
    strategy = FuzzyResolverStrategy(similarity_threshold=0.60)
    candidates = [
        DOMElement(tag="button", text="Continue Shopping", selector="button.continue"),
        DOMElement(tag="button", text="Proceed to Checkout", selector="button.checkout-btn"),
        DOMElement(tag="a", text="Privacy Policy", selector="a.privacy"),
    ]

    res = await strategy.resolve(page=None, target="Proceed Checkout", candidates=candidates)
    assert res is not None
    assert res.success is True
    assert res.strategy == ResolutionStrategy.L3_FUZZY
    assert res.matched_element.selector == "button.checkout-btn"
    assert res.confidence >= 0.65
