"""Unit tests for Reddit MCP server integration, DTOs, and facade wiring."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from behavioral_playwright.mcp.tools import MCP_TOOL_DEFINITIONS, McpToolDispatcher
from behavioral_playwright.models.reddit_dtos import (
    RedditAuthStatusDTO,
    RedditLeadAuditDTO,
    RedditLeadDTO,
)
from behavioral_playwright.integrations.reddit import RedditAutomationClient


def test_reddit_tools_in_definitions():
    """Verify Reddit tools are exposed in MCP_TOOL_DEFINITIONS."""
    tool_names = [t["name"] for t in MCP_TOOL_DEFINITIONS]
    assert "reddit_mine_jobs" in tool_names
    assert "reddit_analyze_lead" in tool_names
    assert "reddit_check_auth" in tool_names


def test_reddit_dtos_validation():
    """Verify Reddit Pydantic DTO models validate properly."""
    lead = RedditLeadDTO(
        id="t3_12345",
        title="[Hiring] Need Python Developer to Scrape E-Commerce Site ($500)",
        subreddit="forhire",
        author="biz_owner",
        url="https://reddit.com/r/forhire/comments/12345",
        budget_hint="$500",
        matched_keywords=["[hiring]", "python", "scrape"],
        selftext_snippet="Looking for someone to extract 10k product prices and bypass Cloudflare.",
    )
    assert lead.id == "t3_12345"
    assert lead.budget_hint == "$500"
    assert "python" in lead.matched_keywords

    auth_dto = RedditAuthStatusDTO(
        authenticated=True,
        username="dev_pro",
        message="Logged in",
    )
    assert auth_dto.authenticated is True


def test_pitch_generator_produces_custom_strategy():
    """Verify pitch generator creates targeted, winning pitch with repo proof."""
    client = RedditAutomationClient()
    lead = RedditLeadDTO(
        id="t3_abcde",
        title="[Hiring] Need help scraping site with Cloudflare Turnstile ($300)",
        subreddit="forhire",
        author="client_alex",
        url="https://reddit.com/r/forhire/comments/abcde",
        budget_hint="$300",
        matched_keywords=["cloudflare", "scraping"],
        selftext_snippet="My script gets blocked by Cloudflare Turnstile challenge.",
    )
    audit = client.analyze_lead_and_generate_pitch(lead)

    assert isinstance(audit, RedditLeadAuditDTO)
    assert audit.intent_level == "HIGH"
    assert "Cloudflare" in audit.technical_assessment
    assert "behavioral-playwright" in audit.pitch_draft
    assert "client_alex" in audit.pitch_draft


@pytest.mark.asyncio
async def test_mcp_dispatcher_reddit_analyze_lead():
    """Verify reddit_analyze_lead tool call via McpToolDispatcher."""
    dispatcher = McpToolDispatcher()
    res = await dispatcher.execute_tool(
        "reddit_analyze_lead",
        {
            "title": "[Hiring] Need a Playwright scraper for real estate data",
            "selftext": "Budget is $400. Need clean JSON export.",
            "author": "john_doe",
            "budget_hint": "$400",
        },
    )
    assert res["status"] == "success"
    assert "analysis" in res
    assert res["analysis"]["lead"]["title"] == "[Hiring] Need a Playwright scraper for real estate data"
    assert "pitch_draft" in res["analysis"]


@pytest.mark.asyncio
async def test_mcp_dispatcher_reddit_mine_jobs_mocked():
    """Verify reddit_mine_jobs execution using injected mock client."""
    mock_client = MagicMock()
    mock_client.mine_hiring_leads = AsyncMock(
        return_value=[
            RedditLeadDTO(
                id="t3_999",
                title="[Hiring] Python scraper for Amazon ($600)",
                subreddit="forhire",
                author="seller_pro",
                url="https://reddit.com/r/forhire/comments/999",
                budget_hint="$600",
                matched_keywords=["python", "scraper"],
            )
        ]
    )

    dispatcher = McpToolDispatcher(reddit_client=mock_client)
    res = await dispatcher.execute_tool(
        "reddit_mine_jobs",
        {"subreddits": ["forhire"], "limit_per_sub": 10},
    )
    assert res["status"] == "success"
    assert res["count"] == 1
    assert res["leads"][0]["title"] == "[Hiring] Python scraper for Amazon ($600)"
    mock_client.mine_hiring_leads.assert_awaited_once_with(
        subreddits=["forhire"],
        keywords=None,
        limit_per_sub=10,
    )


def test_bp_facade_reddit_integration():
    """Verify bp.reddit and bp.integrations.reddit wiring."""
    from behavioral_playwright import BP, RedditAutomationClient

    bp = BP()
    assert hasattr(bp, "reddit")
    assert isinstance(bp.reddit, RedditAutomationClient)
    assert hasattr(bp.integrations, "reddit")
    assert isinstance(bp.integrations.reddit, RedditAutomationClient)
