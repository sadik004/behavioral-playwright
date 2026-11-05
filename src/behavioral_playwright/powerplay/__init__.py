"""Backward-compatible package alias forwarding to `behavioral_playwright.kinematics`."""
import importlib as _importlib

_mod = _importlib.import_module("behavioral_playwright.kinematics")
for _k, _v in _mod.__dict__.items():
    if _k not in ("__name__", "__loader__", "__package__", "__spec__", "__path__", "__file__", "__cached__"):
        globals()[_k] = _v
