"""Unit tests for Behavioral Playwright CLI."""

import pytest
from behavioral_playwright.cli.main import build_parser, main


def test_cli_parser_commands():
    parser = build_parser()
    
    # Scrape args
    parsed = parser.parse_args(["scrape", "https://example.com", "-o", "out.json"])
    assert parsed.command == "scrape"
    assert parsed.url == "https://example.com"
    assert parsed.output == "out.json"

    # Crawl args
    parsed = parser.parse_args(["crawl", "https://example.com", "--max-pages", "10", "--depth", "3"])
    assert parsed.command == "crawl"
    assert parsed.max_pages == 10
    assert parsed.depth == 3

    # Matrix command
    parsed = parser.parse_args(["matrix"])
    assert parsed.command == "matrix"


def test_cli_matrix_execution(capsys):
    ret = main(["matrix"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "PROVIDER MATRIX" in captured.out
    assert "browser/playwright" in captured.out
