"""Backward-compatibility forwarding module for providers.network.

Exposes CurlCffiProvider forwarded from veil.providers.network to guarantee
strict module and class identity parity across root and facade packages.
"""
from __future__ import annotations

from veil.providers.network import (
    CurlCffiProvider,
    ProviderInfo,
    ProviderUnavailableError,
    detect_provider,
)

__all__ = [
    "CurlCffiProvider",
    "ProviderInfo",
    "ProviderUnavailableError",
    "detect_provider",
]

