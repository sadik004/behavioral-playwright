"""Backward-compatible module alias forwarding to `veil.core.itch_binary`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.core.itch_binary")
