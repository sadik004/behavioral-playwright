"""Backward-compatible module alias forwarding to `veil.mining.engine`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.mining.engine")
