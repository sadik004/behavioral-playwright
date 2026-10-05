"""Unit tests for extraction normalizer utilities."""

from decimal import Decimal
import pytest

from behavioral_playwright.extraction.normalizer import (
    clean_text,
    normalize_unicode,
    normalize_whitespace,
    parse_numeric,
    parse_price,
    remove_zero_width,
    resolve_url,
)


def test_remove_zero_width():
    # Zero width space \u200b and byte order mark \ufeff
    raw = "P\u200br\u200do\ufeffd\u200eu\u200fc\u00adt"
    assert remove_zero_width(raw) == "Product"
    assert remove_zero_width("") == ""


def test_normalize_whitespace():
    # Collapses multiple spaces, tabs, and non-breaking spaces
    raw = "  Hello \t\t  World\u00a0\u00a0! \n  Next  "
    assert normalize_whitespace(raw, preserve_newlines=False) == "Hello World ! Next"

    # Preserves single paragraph break when requested
    multiline = "Line 1   \t\n\n\n  Line   2  \n"
    res = normalize_whitespace(multiline, preserve_newlines=True)
    assert res == "Line 1\n\nLine 2"



def test_normalize_unicode():
    # NFKC normalizes fullwidth characters and ligatures
    fullwidth = "Ｈｅｌｌｏ"
    assert normalize_unicode(fullwidth, form="NFKC") == "Hello"


def test_clean_text_combined():
    raw = "\u200b  A\u00a0B   \u200dC  \ufeff"
    assert clean_text(raw) == "A B C"


def test_parse_price_financial_precision():
    # Strict Decimal(18, 4) or Decimal(18, 2) financial precision
    assert parse_price("$1,299.99") == Decimal("1299.99")
    assert parse_price("€ 45.5000") == Decimal("45.5000")
    assert parse_price("£10") == Decimal("10.00")
    assert parse_price("৳ 500.25") == Decimal("500.25")
    assert parse_price("Free") is None
    assert parse_price("") is None


def test_parse_numeric():
    assert parse_numeric("Stock: 1,450 units") == 1450.0
    assert parse_numeric("Score: 98.6%") == 98.6
    assert parse_numeric("No numbers here") is None


def test_resolve_url():
    base = "https://example.com/catalog/items/"
    assert resolve_url(base, "details.html") == "https://example.com/catalog/items/details.html"
    assert resolve_url(base, "/about") == "https://example.com/about"
    assert resolve_url(base, "https://other.com/api") == "https://other.com/api"
    # Protocol schemes preserved as-is
    assert resolve_url(base, "mailto:support@example.com") == "mailto:support@example.com"
    assert resolve_url(base, "javascript:void(0)") == "javascript:void(0)"
    assert resolve_url(base, "tel:+1234567890") == "tel:+1234567890"
