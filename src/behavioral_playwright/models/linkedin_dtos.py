"""Pydantic DTO models for LinkedIn profile automation and MCP tool outputs."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LinkedInProfileDTO(BaseModel):
    """Structured representation of a scraped or verified LinkedIn profile."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = Field(default="", description="Full user display name")
    headline: str = Field(default="", description="Professional headline or title")
    about: Optional[str] = Field(default=None, description="Summary or About text section")
    location: Optional[str] = Field(default=None, description="Geographic location string")
    profile_url: Optional[str] = Field(default=None, description="URL of the profile")


class LinkedInAuthStatusDTO(BaseModel):
    """Authentication verification state."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    authenticated: bool = Field(..., description="Whether the session is active and logged in")
    checkpoint_triggered: bool = Field(default=False, description="Whether 2FA/CAPTCHA checkpoint was detected")
    username: Optional[str] = Field(default=None, description="Authenticated username if detected")
    message: str = Field(default="", description="Descriptive status message")


class LinkedInUpdateResultDTO(BaseModel):
    """Result of profile mutation operation (headline/about)."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    success: bool = Field(..., description="Whether the mutation was committed")
    field_updated: str = Field(..., description="The profile field modified")
    old_value: Optional[str] = Field(default=None, description="Previous field value before modification")
    new_value: str = Field(..., description="New field value applied")
    message: str = Field(default="", description="Execution summary or diagnostic notes")
