"""Backward-compatible module alias forwarding to `veil.security.oob_listener`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.security.oob_listener")
