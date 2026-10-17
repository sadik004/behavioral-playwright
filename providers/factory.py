"""Backward-compatibility forwarding module for providers.factory."""
from __future__ import annotations

from veil.providers.factory import (
    AGENT_PROVIDERS,
    BROWSER_PROVIDERS,
    NETWORK_PROVIDERS,
    create_agent_provider,
    create_browser_provider,
    create_network_provider,
    provider_matrix,
)

__all__ = [
    "AGENT_PROVIDERS",
    "BROWSER_PROVIDERS",
    "NETWORK_PROVIDERS",
    "create_browser_provider",
    "create_network_provider",
    "create_agent_provider",
    "provider_matrix",
]

