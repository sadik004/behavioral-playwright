"""Optional external provider adapters for the SQ framework.

Exposed adapters (all provider-gated; see providers.base.HONESTY_NOTE):
  browser: playwright / patchright / undetected_chromedriver
  network: curl_cffi
  agents:  browser_use / stagehand
"""

from .agents import BrowserUseProvider, StagehandProvider
from .base import (
    HONESTY_NOTE,
    ProviderInfo,
    ProviderUnavailableError,
    UnknownProviderError,
    detect_provider,
)
from .browser import (
    BrowserSession,
    PatchrightProvider,
    PlaywrightProvider,
    UndetectedChromedriverProvider,
)
from .factory import (
    AGENT_PROVIDERS,
    BROWSER_PROVIDERS,
    NETWORK_PROVIDERS,
    create_agent_provider,
    create_browser_provider,
    create_network_provider,
    provider_matrix,
)
from .network import CurlCffiProvider

__all__ = [
    "HONESTY_NOTE",
    "ProviderInfo",
    "ProviderUnavailableError",
    "UnknownProviderError",
    "detect_provider",
    "BrowserSession",
    "PlaywrightProvider",
    "PatchrightProvider",
    "UndetectedChromedriverProvider",
    "CurlCffiProvider",
    "BrowserUseProvider",
    "StagehandProvider",
    "BROWSER_PROVIDERS",
    "NETWORK_PROVIDERS",
    "AGENT_PROVIDERS",
    "create_browser_provider",
    "create_network_provider",
    "create_agent_provider",
    "provider_matrix",
]
