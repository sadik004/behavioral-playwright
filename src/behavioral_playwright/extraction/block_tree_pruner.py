"""Backward-compatible alias forwarding to `veil.extraction.block_tree_pruner`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("veil.extraction.block_tree_pruner")
