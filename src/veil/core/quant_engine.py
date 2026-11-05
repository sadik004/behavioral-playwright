"""Backward-compatible alias forwarding to `behavioral_playwright.core.quant_engine`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("behavioral_playwright.core.quant_engine")
