"""Backward-compatible module alias forwarding to `veil.kinematics.kernel_input_bridge`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.kinematics.kernel_input_bridge")
