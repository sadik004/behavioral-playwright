"""Independent verifier for MUT-002: Provider Gating Bypass."""
import pytest
from behavioral_playwright.providers.browser import PatchrightProvider
from behavioral_playwright.providers.base import ProviderUnavailableError


def test_uninstalled_provider_strictly_fails_gating():
    """Uninstalled provider must not report available and require_available must raise."""
    p = PatchrightProvider()
    # In an environment where patchright is not installed:
    # 1. is_available() must be False
    # 2. require_available() must raise ProviderUnavailableError
    assert p.is_available() is False, "Uninstalled provider must report is_available() == False"
    with pytest.raises(ProviderUnavailableError):
        p.require_available()
