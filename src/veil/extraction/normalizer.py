"""Data normalization and sanitization utilities for extraction."""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Optional
from urllib.parse import urljoin


RE_ZERO_WIDTH = re.compile(r"[\u200B-\u200D\uFEFF\u200E\u200F\u00AD]")
RE_PRICE = re.compile(r"[-+]?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[-+]?[0-9]+(?:\.[0-9]+)?")


def remove_zero_width(text: str) -> str:
    """Removes invisible zero-width spaces, soft hyphens, and directional formatting marks."""
    if not text:
        return ""
    return RE_ZERO_WIDTH.sub("", text)


def normalize_unicode(text: str, form: str = "NFKC") -> str:
    """Normalizes Unicode characters into standard canonical/compatibility form (default NFKC)."""
    if not text:
        return ""
    return unicodedata.normalize(form, text)


def normalize_whitespace(text: str, preserve_newlines: bool = False) -> str:
    """
    Normalizes whitespace across text.
    Replaces non-breaking spaces (\u00a0) with regular spaces.
    If preserve_newlines is True, retains line breaks while collapsing intra-line spaces.
    """
    if not text:
        return ""
    # Replace non-breaking space and other unicode spaces
    s = text.replace("\u00a0", " ").replace("\u202f", " ")
    if preserve_newlines:
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in s.splitlines()]
        # Remove consecutive blank lines
        cleaned_lines = []
        for line in lines:
            if line or (cleaned_lines and cleaned_lines[-1]):
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()
    return re.sub(r"\s+", " ", s).strip()


def clean_text(text: str, preserve_newlines: bool = False) -> str:
    """Full normalization pipeline: removes zero-width characters, normalizes Unicode, and collapses whitespace."""
    if not text:
        return ""
    cleaned = remove_zero_width(text)
    cleaned = normalize_unicode(cleaned, form="NFKC")
    return normalize_whitespace(cleaned, preserve_newlines=preserve_newlines)


def parse_price(text: str) -> Optional[Decimal]:
    """
    Parses currency/price string into an audited Decimal with financial precision.
    Strips currency symbols ($ € £ ৳ ¥ Rs) and thousands commas.
    Returns Decimal with up to 4 decimal places, or None if no valid price pattern is found.
    """
    if not text:
        return None
    cleaned = remove_zero_width(text)
    match = RE_PRICE.search(cleaned)
    if not match:
        return None
    raw_num = match.group(0).replace(",", "")
    try:
        val = Decimal(raw_num)
        return val.quantize(Decimal("0.0001")) if "." in raw_num and len(raw_num.split(".")[1]) > 2 else val.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def parse_numeric(text: str) -> Optional[float]:
    """Extracts first valid floating-point number from text."""
    if not text:
        return None
    match = RE_PRICE.search(remove_zero_width(text))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def resolve_url(base_url: str, url: str) -> str:
    """
    Resolves a relative URL against a base URL.
    Preserves mailto:, tel:, javascript:, and data: schemes as-is.
    """
    if not url:
        return ""
    url_trimmed = url.strip()
    lower = url_trimmed.lower()
    if lower.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return url_trimmed
    if not base_url:
        return url_trimmed
    return urljoin(base_url, url_trimmed)
