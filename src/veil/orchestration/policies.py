"""Backward-compatible alias forwarding to `behavioral_playwright.orchestration.policies`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("behavioral_playwright.orchestration.policies")
