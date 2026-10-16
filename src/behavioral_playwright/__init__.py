"""Backward-compatible package alias forwarding to `veil`."""
from __future__ import annotations

import importlib as _importlib

_mod = _importlib.import_module("veil")
for _k, _v in _mod.__dict__.items():
    if _k not in ("__name__", "__loader__", "__package__", "__spec__", "__path__", "__file__", "__cached__"):
        globals()[_k] = _v

__all__ = getattr(_mod, "__all__", [k for k in globals() if not k.startswith("_")])


def __getattr__(name: str):
    return getattr(_mod, name)
