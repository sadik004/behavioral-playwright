"""CurlCffiProvider: TLS/JA3-impersonating HTTP client (provider-gated).

Backward-compatibility forwarding module ensuring strict class identity with
veil.providers.network.CurlCffiProvider.
"""

from __future__ import annotations

from veil.providers.network import CurlCffiProvider

__all__ = [
    "CurlCffiProvider",
]
