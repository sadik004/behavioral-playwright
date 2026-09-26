"""Integrations module for external platforms and services."""

from behavioral_playwright.integrations.extensions import IntegrationExtensions
from behavioral_playwright.integrations.linkedin import LinkedInAutomationClient
from behavioral_playwright.integrations.reddit import RedditAutomationClient

__all__ = [
    "IntegrationExtensions",
    "LinkedInAutomationClient",
    "RedditAutomationClient",
]


