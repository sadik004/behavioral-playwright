"""Backward-compatible alias forwarding to `veil.mining.suggest_miner`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.mining.suggest_miner")
