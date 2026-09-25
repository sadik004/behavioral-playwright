"""Unit tests for Behavioral Playwright CLI Mining Subcommands."""

import json
from unittest.mock import AsyncMock, patch
import pytest

from behavioral_playwright.cli.main import build_parser, main
from behavioral_playwright.models.seo_dtos import (
    CannibalizationReport,
    CSRDriftReport,
    PAANode,
    SuggestResult,
)


def test_cli_mining_subparser_arguments():
    """Verify argument parsing for all mining CLI commands."""
    parser = build_parser()

    # 1. extract-meta
    parsed_meta = parser.parse_args(["extract-meta", "https://example.com", "-o", "meta.json"])
    assert parsed_meta.command == "extract-meta"
    assert parsed_meta.url == "https://example.com"
    assert parsed_meta.output == "meta.json"

    # 2. mine-paa
    parsed_paa = parser.parse_args(["mine-paa", "fastapi tutorial", "--depth", "3", "-o", "paa.json"])
    assert parsed_paa.command == "mine-paa"
    assert parsed_paa.query == "fastapi tutorial"
    assert parsed_paa.depth == 3
    assert parsed_paa.output == "paa.json"

    # 3. check-overlap
    parsed_overlap = parser.parse_args([
        "check-overlap", "query 1", "query 2",
        "--threshold", "0.55",
        "--urls-a", "https://a.com/1", "https://a.com/2",
        "--urls-b", "https://a.com/1", "https://b.com/2"
    ])
    assert parsed_overlap.command == "check-overlap"
    assert parsed_overlap.query_a == "query 1"
    assert parsed_overlap.query_b == "query 2"
    assert parsed_overlap.threshold == 0.55
    assert len(parsed_overlap.urls_a) == 2
    assert len(parsed_overlap.urls_b) == 2

    # 4. mine-suggest
    parsed_sug = parser.parse_args([
        "mine-suggest", "python web scraping",
        "--alphabet", "--lang", "es", "--country", "es"
    ])
    assert parsed_sug.command == "mine-suggest"
    assert parsed_sug.query == "python web scraping"
    assert parsed_sug.alphabet is True
    assert parsed_sug.lang == "es"
    assert parsed_sug.country == "es"

    # 5. audit-drift
    parsed_drift = parser.parse_args(["audit-drift", "https://spa.example.com"])
    assert parsed_drift.command == "audit-drift"
    assert parsed_drift.url == "https://spa.example.com"


def test_cli_extract_meta_execution(capsys):
    """Verify execution and stdout JSON output of extract-meta."""
    mock_meta = {
        "url": "https://example.com",
        "next_data": {"props": {"pageProps": {"id": 1}}},
        "nuxt_data": None,
        "json_ld": [{"@type": "Organization"}],
        "open_graph": {"og:title": "Example"},
    }

    with patch("behavioral_playwright.cli.main.run_extract_meta", new=AsyncMock(return_value=0)) as mock_run:
        ret = main(["extract-meta", "https://example.com"])
        assert ret == 0
        mock_run.assert_called_once()


def test_cli_mine_suggest_execution(capsys):
    """Verify execution of mine-suggest subcommand."""
    mock_result = SuggestResult(
        query="fastapi vs",
        suggestions=["fastapi vs flask", "fastapi vs django"],
        total_unique=2,
    )

    with patch("behavioral_playwright.mining.suggest_miner.GoogleSuggestMiner.mine", new=AsyncMock(return_value=mock_result)):
        ret = main(["mine-suggest", "fastapi vs"])
        assert ret == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["query"] == "fastapi vs"
        assert len(data["suggestions"]) == 2
        assert data["total_unique"] == 2


def test_cli_check_overlap_execution(capsys):
    """Verify execution of check-overlap with explicit URLs."""
    ret = main([
        "check-overlap", "query alpha", "query beta",
        "--urls-a", "https://target.com/page", "https://other.com/a",
        "--urls-b", "https://target.com/page", "https://diff.com/b",
        "--threshold", "0.30"
    ])
    assert ret == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["query_a"] == "query alpha"
    assert report["query_b"] == "query beta"
    assert "https://target.com/page" in report["common_urls"]
    assert report["recommendation"] == "MERGE_INTO_SINGLE_CANONICAL"


def test_cli_audit_drift_execution(capsys):
    """Verify execution of audit-drift command."""
    mock_drift = CSRDriftReport(
        url="https://example.com",
        raw_html_bytes=100,
        rendered_html_bytes=200,
        raw_dom_nodes=5,
        rendered_dom_nodes=10,
        raw_text_length=50,
        rendered_text_length=150,
        drift_ratio=0.35,
        missing_in_raw=["H1 headings rendered exclusively via CSR"],
        hydration_drift_detected=True,
        seo_indexation_risk="MEDIUM",
    )

    with patch("behavioral_playwright.verification.rendering_auditor.CSRRenderingDriftAuditor.audit_url_drift", new=AsyncMock(return_value=mock_drift)):
        ret = main(["audit-drift", "https://example.com"])
        assert ret == 0
        captured = capsys.readouterr()
        out = json.loads(captured.out)
        assert out["drift_ratio"] == 0.35
        assert out["seo_indexation_risk"] == "MEDIUM"
