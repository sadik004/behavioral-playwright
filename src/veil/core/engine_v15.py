"""Backward-compatible alias forwarding to `behavioral_playwright.core.engine_v15`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("behavioral_playwright.core.engine_v15")
