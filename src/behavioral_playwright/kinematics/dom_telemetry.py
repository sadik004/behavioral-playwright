"""Backward-compatible alias forwarding to `veil.kinematics.dom_telemetry`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.kinematics.dom_telemetry")
