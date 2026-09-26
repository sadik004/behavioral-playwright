"""Unit tests for LinkedIn MCP server integration and DTOs."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from behavioral_playwright.mcp.tools import MCP_TOOL_DEFINITIONS, McpToolDispatcher
from behavioral_playwright.models.linkedin_dtos import (
    LinkedInAuthStatusDTO,
    LinkedInProfileDTO,
    LinkedInUpdateResultDTO,
)


def test_linkedin_tools_in_definitions():
    """Verify LinkedIn tools are exposed in MCP_TOOL_DEFINITIONS."""
    tool_names = [t["name"] for t in MCP_TOOL_DEFINITIONS]
    assert "linkedin_check_auth" in tool_names
    assert "linkedin_get_profile" in tool_names
    assert "linkedin_update_headline" in tool_names
    assert "linkedin_update_about" in tool_names


def test_linkedin_dtos_validation():
    """Verify LinkedIn Pydantic DTO models validate properly."""
    auth_dto = LinkedInAuthStatusDTO(
        authenticated=True,
        checkpoint_triggered=False,
        username="john-doe",
        message="Valid session",
    )
    assert auth_dto.authenticated is True
    assert auth_dto.username == "john-doe"

    profile_dto = LinkedInProfileDTO(
        name="Jane Smith",
        headline="Senior AI Engineer",
        about="Specialized in Clean Architecture & Automation",
        location="San Francisco, CA",
    )
    assert profile_dto.name == "Jane Smith"
    assert profile_dto.headline == "Senior AI Engineer"

    update_dto = LinkedInUpdateResultDTO(
        success=True,
        field_updated="headline",
        old_value="Junior Dev",
        new_value="Senior Dev",
        message="Updated",
    )
    assert update_dto.success is True
    assert update_dto.new_value == "Senior Dev"


@pytest.mark.asyncio
async def test_mcp_dispatcher_linkedin_check_auth_missing_file():
    """Verify tool dispatcher returns unauthenticated status gracefully when storage file is absent."""
    dispatcher = McpToolDispatcher()
    res = await dispatcher.execute_tool(
        "linkedin_check_auth",
        {"storage_state": "non_existent_file_xyz.json"},
    )
    assert res["status"] == "success"
    assert res["result"]["authenticated"] is False
    assert "not found" in res["result"]["message"].lower()


@pytest.mark.asyncio
async def test_mcp_dispatcher_linkedin_update_headline_missing_param():
    """Verify validation error when new_headline argument is omitted."""
    dispatcher = McpToolDispatcher()
    res = await dispatcher.execute_tool(
        "linkedin_update_headline",
        {"storage_state": "dummy.json"},
    )
    assert "error" in res
    assert "Missing required argument 'new_headline'" in res["error"]


@pytest.mark.asyncio
async def test_mcp_dispatcher_linkedin_update_about_missing_param():
    """Verify validation error when new_about argument is omitted."""
    dispatcher = McpToolDispatcher()
    res = await dispatcher.execute_tool(
        "linkedin_update_about",
        {"storage_state": "dummy.json"},
    )
    assert "error" in res
    assert "Missing required argument 'new_about'" in res["error"]


@pytest.mark.asyncio
async def test_mcp_dispatcher_linkedin_mocked_execution():
    """Verify mock injection into McpToolDispatcher for LinkedIn client."""
    mock_client = MagicMock()
    mock_client.update_headline = AsyncMock(
        return_value=LinkedInUpdateResultDTO(
            success=True,
            field_updated="headline",
            old_value="Old Title",
            new_value="Lead Architect",
            message="Committed",
        )
    )

    dispatcher = McpToolDispatcher(linkedin_client=mock_client)
    res = await dispatcher.execute_tool(
        "linkedin_update_headline",
        {"new_headline": "Lead Architect", "storage_state": "session.json"},
    )
    assert res["status"] == "success"
    assert res["result"]["success"] is True
    assert res["result"]["new_value"] == "Lead Architect"
    mock_client.update_headline.assert_awaited_once_with(
        new_headline="Lead Architect",
        storage_state_path="session.json",
    )


def test_bp_facade_linkedin_integration():
    """Verify bp.linkedin and bp.integrations.linkedin facade wiring."""
    from behavioral_playwright import BP, LinkedInAutomationClient

    bp = BP()
    assert hasattr(bp, "linkedin")
    assert isinstance(bp.linkedin, LinkedInAutomationClient)
    assert hasattr(bp.integrations, "linkedin")
    assert isinstance(bp.integrations.linkedin, LinkedInAutomationClient)

