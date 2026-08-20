"""Unit tests for configuration models."""

import pytest
from behavioral_playwright.config.settings import (
    AutomationConfig,
    BrowserConfig,
    CircuitBreakerConfig,
    ResolverConfig,
    RetryConfig,
)


def test_browser_config_defaults():
    config = BrowserConfig()
    assert config.headless is True
    assert config.width == 1920
    assert config.height == 1080
    assert config.timeout_ms == 30000


def test_resolver_config_defaults():
    config = ResolverConfig()
    assert config.enabled is True
    assert "L1_EXACT" in config.strategies
    assert "L2_SEMANTIC" in config.strategies
    assert "L3_FUZZY" in config.strategies
    assert config.confidence_threshold == 0.60
    assert config.fuzzy_similarity_threshold == 0.65


def test_retry_config_custom():
    config = RetryConfig(max_attempts=5, base_delay=0.5, exponential_backoff=False)
    assert config.max_attempts == 5
    assert config.base_delay == 0.5
    assert config.exponential_backoff is False


def test_circuit_breaker_config_defaults():
    config = CircuitBreakerConfig()
    assert config.failure_threshold == 5
    assert config.recovery_timeout == 30.0


def test_automation_config_aggregation():
    auto = AutomationConfig(
        browser=BrowserConfig(headless=False),
        resolver=ResolverConfig(confidence_threshold=0.85)
    )
    assert auto.browser.headless is False
    assert auto.resolver.confidence_threshold == 0.85
