"""Backward-compatible module alias forwarding to `veil.fingerprint.persona_profile`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.fingerprint.persona_profile")
