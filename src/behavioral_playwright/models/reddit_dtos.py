"""Pydantic DTO models for Reddit lead mining, job discovery, and outreach strategy."""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RedditLeadDTO(BaseModel):
    """Structured representation of a high-intent client lead from Reddit."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str = Field(default="", description="Post unique identifier")
    title: str = Field(..., description="Post title")
    subreddit: str = Field(..., description="Source subreddit (e.g. forhire, webscraping)")
    author: str = Field(default="", description="Author Reddit username")
    url: str = Field(..., description="Full URL to the Reddit post")
    created_utc: float = Field(default=0.0, description="Post creation epoch timestamp")
    budget_hint: Optional[str] = Field(default=None, description="Extracted budget if mentioned (e.g. $500, $50/hr)")
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords triggered by intent filter")
    selftext_snippet: str = Field(default="", description="Summary of the post body")


class RedditLeadAuditDTO(BaseModel):
    """Analysis of a specific Reddit client post with technical strategy and pitch draft."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    lead: RedditLeadDTO = Field(..., description="Original client lead DTO")
    intent_level: str = Field(default="HIGH", description="Urgency / intent score (HIGH, MEDIUM, LOW)")
    technical_assessment: str = Field(..., description="Root cause diagnosis of client problem")
    recommended_solution: str = Field(..., description="Proposed architectural solution stack")
    pitch_draft: str = Field(..., description="Custom personalized, winning DM/comment outreach message")


class RedditAuthStatusDTO(BaseModel):
    """Reddit session authentication and identity state."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    authenticated: bool = Field(..., description="Whether the Reddit session is active")
    username: Optional[str] = Field(default=None, description="Authenticated Reddit username")
    karma: Optional[int] = Field(default=None, description="Account total karma if accessible")
    message: str = Field(default="", description="Status explanation")
