"""Backward-compatible alias forwarding to `behavioral_playwright.crawling.clearance_bridge`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("behavioral_playwright.crawling.clearance_bridge")
