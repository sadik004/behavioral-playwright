"""Backward-compatible alias forwarding to `veil.blueprints.cognitive_form`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.blueprints.cognitive_form")
