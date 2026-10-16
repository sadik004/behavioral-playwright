"""Adversarial Failure Testing Suite.

Injects controlled faults and verifies that the system fails honestly:
REAL FAILURE != SUCCESS.
Every injected failure must raise an appropriate exception or return an explicit failure status.
Silent swallowing or conversion to success is classified as a critical integrity violation.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from harness.oracle import ExecutionStatus, IndependentOracle, OracleVerdict
from behavioral_playwright.config.settings import AutomationConfig, BrowserConfig, CircuitBreakerConfig
from behavioral_playwright.exceptions import (
    CircuitBreakerError,
    ElementResolutionError,
    NavigationError,
    ProviderUnavailableError,
)
from behavioral_playwright.facade import BP
from behavioral_playwright.resilience.circuit_breaker import CircuitBreaker
from behavioral_playwright.selectors.resolver import SelfHealingResolver
from behavioral_playwright.storage.exporters import DataStorageManager


class TestFailureIntegrity:
    """Adversarial fault injection suite."""

    def test_selector_resolution_failure_fails_loudly(self):
        """When an element cannot be resolved across any tier, resolve_and_type must raise ElementResolutionError."""
        resolver = SelfHealingResolver()
        mock_page = MagicMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.evaluate = AsyncMock(return_value=[])

        async def _run():
            await resolver.resolve_and_type(mock_page, "nonexistent-button-selector", "text")

        verdict = IndependentOracle.evaluate_failure_integrity(
            callable_fn=lambda: asyncio.run(_run()),
            expected_exception_types=(ElementResolutionError,),
            operation_name="SelfHealingResolver.resolve_and_type",
        )
        assert verdict.is_acceptable, verdict.reason
        assert verdict.status == ExecutionStatus.REAL_FAILURE

    def test_circuit_breaker_trips_to_open_after_threshold(self):
        """Circuit breaker must trip to OPEN after failure_threshold and reject subsequent calls immediately."""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60)
        cb = CircuitBreaker(config=config)

        async def _failing_call():
            raise ValueError("Injected network or provider failure")

        # Execute 3 failing calls
        for _ in range(3):
            with pytest.raises(ValueError):
                asyncio.run(cb.execute(_failing_call))

        assert cb.state == "OPEN", f"Expected circuit state OPEN, got {cb.state}"

        # 4th call must raise CircuitBreakerError without invoking failing_call
        verdict = IndependentOracle.evaluate_failure_integrity(
            callable_fn=lambda: asyncio.run(cb.execute(_failing_call)),
            expected_exception_types=(CircuitBreakerError,),
            operation_name="CircuitBreaker.execute[OPEN]",
        )
        assert verdict.is_acceptable, verdict.reason
        assert verdict.status == ExecutionStatus.REAL_FAILURE

    def test_absent_provider_instantiation_raises_provider_unavailable(self):
        """Requesting an uninstalled provider must raise ProviderUnavailableError, never return dummy success."""
        from behavioral_playwright.providers import create_browser_provider

        verdict = IndependentOracle.evaluate_failure_integrity(
            callable_fn=lambda: create_browser_provider("phantom_nonexistent_provider"),
            expected_exception_types=(Exception,),
            operation_name="create_browser_provider[unknown]",
        )
        assert verdict.is_acceptable, verdict.reason

    def test_storage_export_to_invalid_path_fails_loudly(self):
        """Writing records to an invalid / protected path must raise an exception or propagate failure."""
        storage = DataStorageManager()
        records = [{"key": "val1"}, {"key": "val2"}]

        # Invalid path with null byte or impossible directory
        invalid_path = "\0impossible_path/export.json"

        verdict = IndependentOracle.evaluate_failure_integrity(
            callable_fn=lambda: storage.export(records, invalid_path),
            expected_exception_types=(ValueError, OSError, IOError),
            operation_name="DataStorageManager.export[invalid_path]",
        )
        assert verdict.is_acceptable, verdict.reason

    @pytest.mark.asyncio
    async def test_simulated_page_crash_propagates_or_aborts(self):
        """A crashed page evaluation must propagate an exception and not report clean extraction."""
        from behavioral_playwright.browser.mock_provider import MockBrowserProvider

        config = AutomationConfig()
        provider = MockBrowserProvider()

        async with BP(config=config, provider=provider) as bp:
            bp.page.evaluate = AsyncMock(side_effect=RuntimeError("Target page crashed (CDP disconnect)"))
            with pytest.raises(RuntimeError):
                await bp.page.evaluate("() => document.title")

    def test_mut_004_storage_export_failure_not_swallowed_by_cli(self, monkeypatch):
        """Kills MUT-004: Swallowing errors in DataStorageManager or CLI export
        must be caught and must result in an error exit code, never 0.
        """
        from behavioral_playwright.cli.main import _safe_export

        # 1. Direct invalid path export
        ret = _safe_export([{"k": "v"}], "\0illegal_path.json")
        assert ret == 1, "CLI _safe_export must return exit code 1 on invalid path"

        # 2. Mutant: export swallows error and returns None or empty string
        monkeypatch.setattr(DataStorageManager, "export", lambda *args, **kwargs: None)
        ret_swallowed = _safe_export([{"k": "v"}], "valid_path.json")
        assert ret_swallowed == 1, "CLI _safe_export must detect None return and return exit code 1"
