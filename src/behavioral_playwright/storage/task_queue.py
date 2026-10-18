"""Backward-compatible alias forwarding to `veil.storage.task_queue`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.storage.task_queue")
