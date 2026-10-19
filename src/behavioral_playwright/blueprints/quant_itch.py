"""Backward-compatible alias forwarding to `veil.blueprints.quant_itch`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.blueprints.quant_itch")
