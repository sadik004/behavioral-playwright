"""DOM Extraction module."""

from behavioral_playwright.extraction.dom import (
    DOMExtractor,
    extract_json_ld,
    extract_next_data,
    extract_nuxt_data,
    extract_open_graph,
)
from behavioral_playwright.extraction.normalizer import (
    clean_text,
    normalize_unicode,
    normalize_whitespace,
    parse_numeric,
    parse_price,
    remove_zero_width,
    resolve_url,
)

__all__ = [
    "DOMExtractor",
    "extract_json_ld",
    "extract_next_data",
    "extract_nuxt_data",
    "extract_open_graph",
    "clean_text",
    "normalize_unicode",
    "normalize_whitespace",
    "parse_numeric",
    "parse_price",
    "remove_zero_width",
    "resolve_url",
]

