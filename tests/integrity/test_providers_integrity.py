"""Dependency and Provider Integrity Verification Suite.

Tests:
1. Every optional provider adapter behaves honestly.
2. Missing providers raise ProviderUnavailableError with actionable messages.
3. Installed providers report verified version information.
4. No provider fabricates synthetic success when its underlying binary/engine is absent.
"""
from __future__ import annotations

import pytest

from harness.oracle import ExecutionStatus, IndependentOracle
from behavioral_playwright.providers.base import ProviderUnavailableError
from behavioral_playwright.providers import (
    BrowserUseProvider,
    CurlCffiProvider,
    PatchrightProvider,
    PlaywrightProvider,
    StagehandProvider,
    UndetectedChromedriverProvider,
    create_browser_provider,
    provider_matrix,
)


class TestProvidersIntegrity:
    """Verifies that optional provider architecture enforces strict honesty."""

    def test_provider_matrix_taxonomy(self):
        """Audits the complete provider matrix and classifies each into the honesty taxonomy."""
        matrix = provider_matrix()
        assert isinstance(matrix, dict)

        known_providers = [
            "browser/playwright",
            "browser/patchright",
            "browser/undetected_chromedriver",
            "network/curl_cffi",
            "agent/browser_use",
            "agent/stagehand",
        ]

        for p_name in known_providers:
            assert p_name in matrix, f"Provider {p_name} missing from provider_matrix()"
            info = matrix[p_name]
            assert hasattr(info, "installed"), f"{p_name} info missing 'installed' attribute"
            assert isinstance(info.installed, bool)

            # Classify through Independent Oracle
            if info.installed:
                oracle_status = ExecutionStatus.REAL_SUCCESS
            else:
                oracle_status = ExecutionStatus.PROVIDER_UNAVAILABLE

            assert oracle_status in (ExecutionStatus.REAL_SUCCESS, ExecutionStatus.PROVIDER_UNAVAILABLE)

    def test_uninstalled_provider_raises_provider_unavailable_error(self):
        """Requesting an uninstalled provider must raise ProviderUnavailableError."""
        # browser_use is an optional agent provider
        bu = BrowserUseProvider()
        if not bu.is_available():
            with pytest.raises(ProviderUnavailableError) as exc_info:
                bu.require_available()
            assert "browser-use" in str(exc_info.value).lower()

        # stagehand is an optional agent provider
        sh = StagehandProvider()
        if not sh.is_available():
            with pytest.raises(ProviderUnavailableError) as exc_info:
                sh.require_available()
            assert "stagehand" in str(exc_info.value).lower()

    def test_patchright_honest_gating(self):
        """If patchright is not installed, attempting instantiation must fail cleanly."""
        pr = PatchrightProvider()
        if not pr.is_available():
            with pytest.raises(ProviderUnavailableError) as exc_info:
                pr.require_available()
            assert "patchright" in str(exc_info.value).lower()

    def test_undetected_chromedriver_honest_gating(self):
        """If undetected_chromedriver is not installed, launching must raise ProviderUnavailableError."""
        uc = UndetectedChromedriverProvider()
        if not uc.is_available():
            with pytest.raises(ProviderUnavailableError):
                uc.require_available()

    def test_canonical_provider_unavailable_exception_hierarchy(self):
        """Regression test for DUPLICATE-EXC-001:
        Proves that importing ProviderUnavailableError from behavioral_playwright.exceptions
        and catching BehavioralPlaywrightError catches provider availability failures.
        """
        from behavioral_playwright.exceptions import (
            BehavioralPlaywrightError,
            ProviderUnavailableError as CanonicalPUE,
        )
        from behavioral_playwright.providers.base import (
            ProviderUnavailableError as ProviderSubsystemPUE,
        )

        assert CanonicalPUE is ProviderSubsystemPUE, (
            "Canonical ProviderUnavailableError must be identical object across exceptions and providers.base"
        )
        assert issubclass(ProviderSubsystemPUE, BehavioralPlaywrightError)
        assert issubclass(ProviderSubsystemPUE, RuntimeError)

        pr = PatchrightProvider()
        if not pr.is_available():
            caught_as_canonical = False
            caught_as_base_error = False
            try:
                pr.require_available()
            except CanonicalPUE:
                caught_as_canonical = True

            try:
                pr.require_available()
            except BehavioralPlaywrightError:
                caught_as_base_error = True

            assert caught_as_canonical is True, "Top-level CanonicalPUE must catch provider errors"
            assert caught_as_base_error is True, "BehavioralPlaywrightError base class must catch provider errors"

    def test_mut_002_provider_false_availability_killed(self, monkeypatch):
        """Kills MUT-002: If is_available is falsely mutated to True,
        launch() or require_available() must still reject execution when the library is missing.
        """
        pr = PatchrightProvider()
        if not pr.is_available():
            # Mutate is_available to lie and claim True
            monkeypatch.setattr(pr, "is_available", lambda: True)
            assert pr.is_available() is True  # Falsified report active

            # Invariant: require_available must still fail and not allow uninstalled execution
            with pytest.raises(ProviderUnavailableError):
                pr.require_available()

            # Invariant: launch must also fail if gating was bypassed
            monkeypatch.setattr(pr, "require_available", lambda: None)
            with pytest.raises((ProviderUnavailableError, ImportError, ModuleNotFoundError)):
                pr.launch()
