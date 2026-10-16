"""Backward-compatible root re-export shim for locked test_honesty_hardening.py."""
from pathlib import Path

_legacy_path = Path(__file__).resolve().parent / "archive" / "deduplicated_legacy" / "behavioral_evasion_ten_patches_hardened_v15.py"
with open(_legacy_path, "r", encoding="utf-8") as _f:
    exec(_f.read(), globals())
