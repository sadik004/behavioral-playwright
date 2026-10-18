"""Backward-compatible alias forwarding to `veil.blueprints.quant`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.blueprints.quant")
