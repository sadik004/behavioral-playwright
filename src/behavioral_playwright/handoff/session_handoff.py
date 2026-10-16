"""Backward-compatible module alias forwarding to `veil.handoff.session_handoff`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.handoff.session_handoff")
