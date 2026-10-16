"""Backward-compatible module alias forwarding to `veil.cli.main`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.cli.main")
