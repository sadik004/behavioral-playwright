"""Backward-compatible module alias forwarding to `veil.verification.verifier`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.verification.verifier")
