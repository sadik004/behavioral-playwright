"""Unit tests for Google Suggest Wildcard & Alphabet Miner."""

from unittest.mock import AsyncMock, patch
import pytest
from pydantic import ValidationError

from behavioral_playwright.mining.suggest_miner import GoogleSuggestMiner, SuggestMiner
from behavioral_playwright.models.seo_dtos import SuggestResult


def test_suggest_result_dto_validation():
    """Verify SuggestResult DTO validation, fields, and auto-computed total_unique."""
    res = SuggestResult(
        query="fastapi vs",
        suggestions=["fastapi vs flask", "fastapi vs django"],
        alphabet_tree={"f": ["fastapi vs flask"], "d": ["fastapi vs django"]},
    )
    assert res.query == "fastapi vs"
    assert len(res.suggestions) == 2
    assert res.total_unique == 2
    assert "f" in res.alphabet_tree

    # Query normalization
    res2 = SuggestResult(query="  python scraping  ", suggestions=[])
    assert res2.query == "python scraping"
    assert res2.total_unique == 0

    # Validation failure on empty query
    with pytest.raises(ValidationError):
        SuggestResult(query="", suggestions=[])


def test_clean_suggestion():
    """Verify HTML stripping and whitespace normalization in suggest output."""
    miner = GoogleSuggestMiner()
    assert miner._clean_suggestion("<b>fastapi</b> vs flask") == "fastapi vs flask"
    assert miner._clean_suggestion("fastapi\xa0vs\xa0django") == "fastapi vs django"
    assert miner._clean_suggestion("   fastapi vs express   ") == "fastapi vs express"
    assert miner._clean_suggestion("") == ""


def test_parse_response_json():
    """Verify parsing Chrome and Firefox JSON suggestion responses."""
    miner = GoogleSuggestMiner()

    # Chrome format: [query, [sug1, sug2, ...], ...]
    chrome_payload = [
        "fastapi vs",
        ["fastapi vs flask", "<b>fastapi</b> vs django", "fastapi vs express"],
        ["", "", ""],
    ]
    parsed = miner.parse_response_json(chrome_payload)
    assert len(parsed) == 3
    assert parsed[0] == "fastapi vs flask"
    assert parsed[1] == "fastapi vs django"
    assert parsed[2] == "fastapi vs express"

    # From string JSON
    import json
    parsed_str = miner.parse_response_json(json.dumps(chrome_payload))
    assert len(parsed_str) == 3

    # Malformed JSON
    assert miner.parse_response_json("not valid json") == []
    assert miner.parse_response_json([]) == []
    assert miner.parse_response_json(["only query"]) == []


@pytest.mark.asyncio
async def test_mine_base_query():
    """Verify base query suggestion mining without alphabet drilldown."""
    miner = GoogleSuggestMiner()

    mock_suggestions = ["fastapi vs flask", "fastapi vs django"]
    with patch.object(miner, "fetch_suggestions", new=AsyncMock(return_value=mock_suggestions)):
        res = await miner.mine("fastapi vs", alphabet=False)
        assert res.query == "fastapi vs"
        assert res.suggestions == mock_suggestions
        assert res.total_unique == 2
        assert res.alphabet_tree == {}


@pytest.mark.asyncio
async def test_mine_alphabet_drilldown():
    """Verify A-Z alphabet drilldown expansion and deduplication."""
    miner = GoogleSuggestMiner()

    async def mock_fetch(q: str, **kwargs):
        if q == "fastapi vs":
            return ["fastapi vs flask"]
        elif q == "fastapi vs a":
            return ["fastapi vs axum", "fastapi vs aiohttp"]
        elif q == "fastapi vs b":
            return ["fastapi vs bottle"]
        return []

    with patch.object(miner, "fetch_suggestions", side_effect=mock_fetch):
        res = await miner.mine("fastapi vs", alphabet=True)
        assert res.query == "fastapi vs"
        assert "fastapi vs flask" in res.suggestions
        assert "fastapi vs axum" in res.suggestions
        assert "fastapi vs bottle" in res.suggestions
        assert res.alphabet_tree["a"] == ["fastapi vs axum", "fastapi vs aiohttp"]
        assert res.alphabet_tree["b"] == ["fastapi vs bottle"]
        assert res.total_unique >= 4


@pytest.mark.asyncio
async def test_mine_wildcard_replacement():
    """Verify wildcard '*' and '_' pattern replacement during drilldown."""
    miner = GoogleSuggestMiner()

    queried_patterns = []

    async def mock_fetch(q: str, **kwargs):
        queried_patterns.append(q)
        return [f"{q} result"]

    with patch.object(miner, "fetch_suggestions", side_effect=mock_fetch):
        res = await miner.mine("fastapi vs *", alphabet=True)
        # Should have tested "fastapi vs a", "fastapi vs b", etc.
        assert "fastapi vs a" in queried_patterns
        assert "fastapi vs z" in queried_patterns
        assert res.total_unique > 0


def test_alias_export():
    """Verify SuggestMiner is an alias of GoogleSuggestMiner."""
    assert SuggestMiner is GoogleSuggestMiner
