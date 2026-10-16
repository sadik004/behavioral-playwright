"""Backward-compatible alias forwarding to `veil.extraction.markdown`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.extraction.markdown")
