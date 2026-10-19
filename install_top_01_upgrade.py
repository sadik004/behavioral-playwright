#!/usr/bin/env python3
"""One-Command Installer for the 8-Pillar Top 0.1% Crawling & Extraction Upgrade.

Copies all verified modules into `src/veil/extraction/`, `src/veil/crawling/`,
and `tests/integration/test_top_01_pillars_real.py`, creates forwarding aliases in
`src/behavioral_playwright/`, and runs the live integration test suite.

Usage:
    python install_top_01_upgrade.py --repo-root .
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SHIM_TEMPLATE = '''"""Backward-compatible alias forwarding to `{mod_target}`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("{mod_target}")
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Top 0.1% Crawling & Extraction Upgrade into Veil")
    parser.add_argument("--repo-root", type=str, default=".", help="Path to behavioral-playwright-main root")
    args = parser.parse_args()

    pkg_root = Path(__file__).resolve().parent
    repo_root = Path(args.repo_root).resolve()

    files_to_copy = [
        ("src/veil/extraction/auto_schema.py", "src/veil/extraction/auto_schema.py"),
        ("src/veil/extraction/hydration.py", "src/veil/extraction/hydration.py"),
        ("src/veil/extraction/quarantine.py", "src/veil/extraction/quarantine.py"),
        ("src/veil/extraction/markdown.py", "src/veil/extraction/markdown.py"),
        ("src/veil/crawling/clearance_bridge.py", "src/veil/crawling/clearance_bridge.py"),
        ("src/veil/crawling/dedup.py", "src/veil/crawling/dedup.py"),
        ("src/veil/crawling/mapper.py", "src/veil/crawling/mapper.py"),
        ("src/veil/crawling/frontier.py", "src/veil/crawling/frontier.py"),
        ("src/veil/crawling/delta_store.py", "src/veil/crawling/delta_store.py"),
        ("src/veil/crawling/pagination.py", "src/veil/crawling/pagination.py"),
        ("src/veil/crawling/world_class_engine.py", "src/veil/crawling/world_class_engine.py"),
        ("tests/integration/test_top_01_pillars_real.py", "tests/integration/test_top_01_pillars_real.py"),
    ]

    for src_rel, dst_rel in files_to_copy:
        src_path = pkg_root / src_rel
        dst_path = repo_root / dst_rel
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        print(f"[INSTALLED] {dst_rel}")

        if dst_rel.startswith("src/veil/"):
            sub_rel = dst_rel[len("src/veil/") :]
            bp_dst = repo_root / "src" / "behavioral_playwright" / sub_rel
            bp_dst.parent.mkdir(parents=True, exist_ok=True)
            mod_target = "veil." + sub_rel[:-3].replace("/", ".")
            bp_dst.write_text(SHIM_TEMPLATE.format(mod_target=mod_target), encoding="utf-8")

    print("\n[VERIFYING] Running live integration test suite (test_top_01_pillars_real.py)...")
    res = subprocess.run(
        [sys.executable, str(repo_root / "tests/integration/test_top_01_pillars_real.py")],
        cwd=str(repo_root),
    )
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
