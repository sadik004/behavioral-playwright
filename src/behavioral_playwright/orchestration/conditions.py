"""Backward-compatible module alias forwarding to `veil.orchestration.conditions`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.orchestration.conditions")
