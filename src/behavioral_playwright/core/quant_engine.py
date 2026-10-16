"""Backward-compatible module alias forwarding to `veil.core.quant_engine`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.core.quant_engine")
