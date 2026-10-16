"""Backward-compatible module alias forwarding to `veil.core.engine_v15`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.core.engine_v15")
