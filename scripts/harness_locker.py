"""Cryptographic Test Suite Locker & Integrity Verifier (SHA-256).

Generates or verifies LOCK.json against critical test files to prevent test weakening,
assertion deletion, or test bypassing.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, Tuple


def compute_file_sha256(filepath: Path) -> str:
    """Compute exact SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def lock_tests(patterns: list[str], lock_file: Path) -> None:
    """Lock test files matching patterns into lock_file."""
    manifest: Dict[str, Dict[str, str]] = {}
    matched_files = []
    for pattern in patterns:
        for p in glob.glob(pattern, recursive=True):
            matched_files.append(Path(p))

    if not matched_files:
        print(f"[ERROR] No test files matched patterns: {patterns}", file=sys.stderr)
        sys.exit(1)

    for fpath in sorted(matched_files):
        rel_path = fpath.as_posix()
        manifest[rel_path] = {
            "sha256": compute_file_sha256(fpath),
            "size_bytes": str(fpath.stat().st_size),
        }

    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(f"[OK] Successfully locked {len(manifest)} test files into {lock_file}")


def verify_lock_integrity(lock_file: Path = Path("tests/verification/LOCK.json")) -> Tuple[bool, str]:
    """Verify that all files in lock_file match their recorded SHA-256 hashes."""
    if not lock_file.exists():
        # Fallback to tests/LOCK.json
        alt = Path("tests/LOCK.json")
        if alt.exists():
            lock_file = alt
        else:
            return False, f"Lock manifest not found at {lock_file}"

    with open(lock_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for rel_path, data in manifest.items():
        fpath = Path(rel_path)
        if not fpath.exists():
            return False, f"Locked test file deleted or missing: {rel_path}"

        current_hash = compute_file_sha256(fpath)
        expected_hash = data.get("sha256")
        if current_hash != expected_hash:
            return False, (
                f"INTEGRITY VIOLATION: Locked test file has been modified! "
                f"File: {rel_path} | Expected: {expected_hash[:12]}... | Got: {current_hash[:12]}..."
            )

    return True, f"Verified {len(manifest)} locked test files matching SHA-256"


def main() -> None:
    parser = argparse.ArgumentParser(description="Cryptographic Test Suite Locker")
    parser.add_argument("--lock", nargs="+", help="Glob patterns for test files to lock")
    parser.add_argument("--verify", action="store_true", help="Verify locked test integrity")
    parser.add_argument("--manifest", default="tests/verification/LOCK.json", help="Path to LOCK.json")
    args = parser.parse_args()

    lock_path = Path(args.manifest)

    if args.lock:
        lock_tests(args.lock, lock_path)
    elif args.verify or not sys.argv[1:]:
        passed, msg = verify_lock_integrity(lock_path)
        if passed:
            print(f"[PASS] {msg}")
            sys.exit(0)
        else:
            print(f"[FAIL] {msg}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
