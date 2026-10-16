#!/usr/bin/env python3
"""Auto-Discovering Cryptographic Test Lock & Bootstrap Harness (`lock_and_guard_harness.py`)."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List

PROTECTED_PATTERNS: List[str] = [
    "harness/*.py",
    "integrity/baseline.json",
    "integrity/claims.json",
    "scripts/ast_anti_gaming.py",
    "scripts/validate_findings.py",
    "tests/integrity/**/*.py",
    "tests/test_honesty_hardening.py",
]

BOOTSTRAP_AST_SCANNER = '''#!/usr/bin/env python3
"""AST Static Anti-Gaming & Fraud Inspector (`scripts/ast_anti_gaming.py`)."""
from __future__ import annotations
import argparse, ast, glob, sys
from pathlib import Path
from typing import List, Tuple

class AntiGamingVisitor(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: List[str] = []

    def visit_Assert(self, node: ast.Assert) -> None:
        if isinstance(node.test, ast.Constant) and bool(node.test.value) is True:
            self.violations.append(f"{self.filename}:{node.lineno}: Tautological assert {node.test.value!r}")
        elif isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Constant) and len(node.test.comparators) == 1:
            right = node.test.comparators[0]
            if isinstance(right, ast.Constant) and node.test.left.value == right.value:
                self.violations.append(f"{self.filename}:{node.lineno}: Dummy constant comparison")
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.violations.append(f"{self.filename}:{node.lineno}: Silent exception handler (except: pass)")
        self.generic_visit(node)

def audit_files(patterns: List[str]) -> Tuple[int, List[str]]:
    violations: List[str] = []
    count = 0
    for pattern in patterns:
        for p in glob.glob(pattern, recursive=True):
            fpath = Path(p)
            if not fpath.is_file() or not fpath.name.endswith(".py") or "archive" in fpath.parts:
                continue
            count += 1
            try:
                tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
                v = AntiGamingVisitor(fpath.as_posix())
                v.visit(tree)
                violations.extend(v.violations)
            except Exception as e:
                violations.append(f"{fpath.as_posix()}: Parse Error: {e}")
    return count, violations

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests", default="tests/**/*.py")
    parser.add_argument("--src", default="src/**/*.py")
    args = parser.parse_args()
    t_cnt, t_v = audit_files([args.tests])
    s_cnt, s_v = audit_files([args.src])
    all_v = t_v + s_v
    if all_v:
        print(f"[FAIL] Found {len(all_v)} anti-gaming violations:", file=sys.stderr)
        for v in all_v:
            print(f"  - {v}", file=sys.stderr)
        sys.exit(1)
    print(f"[PASS] AST Anti-Gaming Audit Passed! Checked {t_cnt} test files and {s_cnt} src files (0 violations).")

if __name__ == "__main__":
    main()
'''

BOOTSTRAP_ORACLE_TEST = '''"""First-Principles Independent Oracle Test Suite (`tests/integrity/test_independent_oracles.py`)."""
from __future__ import annotations
import math, struct
from collections import Counter

def test_shannon_entropy_oracle() -> None:
    text = "ABCD" * 25
    n = len(text)
    counts = Counter(text)
    h = -sum((c / n) * math.log2(c / n) for c in counts.values())
    assert abs(h - 2.0) < 1e-9

def test_itch50_add_order_wire_oracle() -> None:
    pkt = struct.pack(">cHH6sQcI8sI", b"A", 1, 2, (1000).to_bytes(6, "big"), 999, b"B", 100, b"AAPL    ", 1502500)
    assert len(pkt) == 36
    msg_type, locate, tracking, ts_bytes, order_ref, side, shares, stock, price4 = struct.unpack(">cHH6sQcI8sI", pkt)
    assert msg_type == b"A"
    assert stock.decode("ascii").rstrip() == "AAPL"
    assert price4 / 10000.0 == 150.25
'''

GUARD_HOOK_CODE = """#!/usr/bin/env python3
import json, sys

PROTECTED_PREFIXES = (
    "harness/",
    "integrity/baseline.json",
    "integrity/claims.json",
    "scripts/ast_anti_gaming.py",
    "scripts/validate_findings.py",
    "tests/integrity/",
    "tests/test_honesty_hardening.py",
    "LOCK.json",
    ".gemini/",
)

def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        return 0
    try:
        payload = json.loads(raw)
    except Exception:
        return 0
    tool_name = str(payload.get("tool_name", "")).lower()
    tool_input = json.dumps(payload.get("tool_input", {})).replace("\\\\\\\\", "/")
    if any(k in tool_name for k in ("write", "edit", "replace", "delete", "patch", "rm", "mv")):
        for prefix in PROTECTED_PREFIXES:
            if prefix in tool_input:
                sys.stderr.write(
                    f"[HARNESS BLOCK] Forbidden modification to protected path '{prefix}'. "
                    "Fix the implementation under src/ instead!\\n"
                )
                return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""


def resolve_repo_root(explicit_root: str | None = None) -> Path:
    if explicit_root:
        return Path(explicit_root).resolve()

    cwd = Path(".").resolve()
    # 1. Check current directory and immediate children/grandchildren
    candidates: List[Path] = [cwd]
    for p in cwd.glob("*"):
        if p.is_dir():
            candidates.append(p)
            for sub in p.glob("*"):
                if sub.is_dir():
                    candidates.append(sub)

    # 2. Also check common E:\ project directories if on Windows
    for extra in ("E:/Behavioural", "E:/Bug", "E:/behavioral-playwright-main", "E:/behavioral-playwright"):
        ep = Path(extra)
        if ep.exists():
            candidates.append(ep.resolve())

    for cand in candidates:
        if (cand / "harness").exists() or (cand / "src" / "behavioral_playwright").exists() or (cand / "pyproject.toml").exists():
            return cand.resolve()

    return cwd


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_bootstrap_oracles(root: Path) -> None:
    ast_file = root / "scripts" / "ast_anti_gaming.py"
    if not ast_file.exists():
        ast_file.parent.mkdir(parents=True, exist_ok=True)
        ast_file.write_text(BOOTSTRAP_AST_SCANNER, encoding="utf-8")

    oracle_test = root / "tests" / "integrity" / "test_independent_oracles.py"
    if not oracle_test.exists():
        oracle_test.parent.mkdir(parents=True, exist_ok=True)
        oracle_test.write_text(BOOTSTRAP_ORACLE_TEST, encoding="utf-8")


def collect_protected_hashes(root: Path) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for pattern in PROTECTED_PATTERNS:
        for match in sorted(glob.glob(str(root / pattern), recursive=True)):
            p = Path(match)
            if p.is_file():
                rel = p.resolve().relative_to(root.resolve()).as_posix()
                hashes[rel] = sha256_file(p)
    return hashes


def install_antigravity_hooks(root: Path) -> None:
    gemini_dir = root / ".gemini"
    hooks_dir = gemini_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (hooks_dir / "guard_protected_files.py").write_text(GUARD_HOOK_CODE, encoding="utf-8")
    settings = {
        "hooks": {
            "BeforeTool": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "name": "immutable-harness-lock",
                            "type": "command",
                            "command": "python .gemini/hooks/guard_protected_files.py",
                            "timeout": 5000,
                        }
                    ],
                }
            ]
        }
    }
    (gemini_dir / "settings.json").write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=str, default=None, help="Explicit path to repo root")
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    root = resolve_repo_root(args.repo_root)
    lock_file = root / "LOCK.json"

    if args.init:
        ensure_bootstrap_oracles(root)
        hashes = collect_protected_hashes(root)
        lock_file.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        install_antigravity_hooks(root)
        print(f"[LOCKED] Detected Repo Root: {root}")
        print(f"[LOCKED] Sealed {len(hashes)} harness/oracle files in {lock_file}:")
        for k in list(hashes.keys())[:10]:
            print(f"   - {k}")
        if len(hashes) > 10:
            print(f"   ... and {len(hashes) - 10} more files.")
        return 0

    if args.verify:
        if not lock_file.exists():
            print(f"[FAIL] {lock_file} is missing!", file=sys.stderr)
            return 1
        expected = json.loads(lock_file.read_text(encoding="utf-8"))
        actual = collect_protected_hashes(root)
        violations = [
            f"TAMPERED/DELETED: {rel}"
            for rel, exp_h in expected.items()
            if actual.get(rel) != exp_h
        ]
        if violations:
            print("[FAIL] Cryptographic Harness Lock violated:", file=sys.stderr)
            for v in violations:
                print(f"  - {v}", file=sys.stderr)
            return 1
        print(f"[PASS] All {len(expected)} protected harness/oracle files in {root} verified intact.")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
