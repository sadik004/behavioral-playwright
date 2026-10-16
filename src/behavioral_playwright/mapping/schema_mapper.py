"""Backward-compatible module alias forwarding to `veil.mapping.schema_mapper`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.mapping.schema_mapper")
