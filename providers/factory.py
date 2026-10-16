"""Explicit provider selection.

Providers are chosen by name through these factories; the V15 core remains
authoritative and works with zero optional providers installed. Unknown names
raise ``UnknownProviderError`` listing the valid choices (machine-detectable).
"""

from __future__ import annotations

from typing import Any, Dict, Type

from .agents import BrowserUseProvider, StagehandProvider
from .base import (
    HONESTY_NOTE,
    ProviderInfo,
    ProviderUnavailableError,
    UnknownProviderError,
)
from .browser import (
    BrowserSession,
    PatchrightProvider,
    PlaywrightProvider,
    UndetectedChromedriverProvider,
)
from .network import CurlCffiProvider

BROWSER_PROVIDERS: Dict[str, Type[Any]] = {
    "playwright": PlaywrightProvider,
    "patchright": PatchrightProvider,
    "undetected_chromedriver": UndetectedChromedriverProvider,
}
NETWORK_PROVIDERS: Dict[str, Type[Any]] = {
    "curl_cffi": CurlCffiProvider,
}
AGENT_PROVIDERS: Dict[str, Type[Any]] = {
    "browser_use": BrowserUseProvider,
    "stagehand": StagehandProvider,
}


def _select(registry: Dict[str, Type[Any]], kind: str, name: str, **kwargs: Any):
    try:
        cls = registry[name.lower()]
    except KeyError:
        raise UnknownProviderError(
            f"unknown {kind} provider {name!r}; available: {sorted(registry)}"
        ) from None
    return cls(**kwargs)


def create_browser_provider(name: str, **kwargs: Any):
    return _select(BROWSER_PROVIDERS, "browser", name, **kwargs)


def create_network_provider(name: str, **kwargs: Any):
    return _select(NETWORK_PROVIDERS, "network/TLS", name, **kwargs)


def create_agent_provider(name: str, **kwargs: Any):
    return _select(AGENT_PROVIDERS, "AI browser/agent", name, **kwargs)


def provider_matrix() -> Dict[str, ProviderInfo]:
    """Honest capability detection across all five optional providers."""
    infos = {}
    for name, cls in BROWSER_PROVIDERS.items():
        infos[f"browser/{name}"] = cls().info()
    for name, cls in NETWORK_PROVIDERS.items():
        infos[f"network/{name}"] = cls().info()
    for name, cls in AGENT_PROVIDERS.items():
        infos[f"agent/{name}"] = cls().info()
    return infos
