"""Backward-compatible module alias forwarding to `veil.providers.base`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.providers.base")
