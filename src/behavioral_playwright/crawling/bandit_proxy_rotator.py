"""Backward-compatible alias forwarding to `veil.crawling.bandit_proxy_rotator`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.crawling.bandit_proxy_rotator")
