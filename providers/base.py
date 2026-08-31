"""Optional external provider adapters (Phase 4 integration).

IMPORTANT HONESTY NOTE
----------------------
These adapters integrate third-party automation libraries for AUTHORIZED
automation, testing, and research purposes. They are NOT guaranteed bypasses
of any website's security controls, and the framework never treats them as
such. Provider absence always produces an explicit, machine-detectable
unavailable state - never a fabricated fallback.
"""

from __future__ import annotations

import importlib
import importlib.metadata
from dataclasses import dataclass
from typing import Optional

HONESTY_NOTE = (
    "Optional provider adapters for authorized automation/testing/research. "
    "No provider guarantees bypass of any website's security controls."
)


class ProviderUnavailableError(RuntimeError):
    """Raised when a selected provider's backing library is not importable."""

    def __init__(self, provider: str, module: str, install_hint: str) -> None:
        super().__init__(
            f"{provider} provider is UNAVAILABLE: module {module!r} cannot be "
            f"imported. Optional install: {install_hint}. "
            "No fallback or fabricated behavior is provided."
        )
        self.provider = provider
        self.module = module


class UnknownProviderError(ValueError):
    """Raised when a provider name is not in the registry."""


@dataclass(frozen=True)
class ProviderInfo:
    """Honest capability-detection result for one provider."""

    provider: str
    module: str
    installed: bool
    version: Optional[str] = None
    error: Optional[str] = None


def detect_provider(provider: str, module: str) -> ProviderInfo:
    """Attempt a real import and report the truth about availability."""
    try:
        mod = importlib.import_module(module)
    except Exception as exc:  # ImportError or broken dependency chain
        return ProviderInfo(
            provider=provider,
            module=module,
            installed=False,
            error=f"{type(exc).__name__}: {exc}",
        )
    version = getattr(mod, "__version__", None)
    if version is None:
        try:
            version = importlib.metadata.version(module.replace("_", "-"))
        except Exception:
            version = None
    return ProviderInfo(provider=provider, module=module, installed=True, version=version)
