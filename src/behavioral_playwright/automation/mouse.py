"""Backward-compatible module alias forwarding to `veil.automation.mouse`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.automation.mouse")
