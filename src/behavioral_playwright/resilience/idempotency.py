"""Backward-compatible module alias forwarding to `veil.resilience.idempotency`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.resilience.idempotency")
