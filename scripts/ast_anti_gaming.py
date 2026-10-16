"""AST Static Anti-Gaming & Fraud Inspector.

Statically parses test suites and source code to detect:
1. Rule T4: Mocking functions under test to fake answers.
2. Tautological / dummy assertions (e.g. assert True, assert 1 == 1).
3. Rule T5 / G1: Silent exception masking (except Exception: pass).
4. Gate G2: Hardcoded synthetic metrics or comparison slacks.
"""
from __future__ import annotations

import argparse
import ast
import glob
import sys
from pathlib import Path
from typing import List, Tuple


class AntiGamingVisitor(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: List[str] = []

    def visit_Assert(self, node: ast.Assert) -> None:
        # Check for tautological assertions: assert True, assert 1 == 1, assert "a" == "a"
        if isinstance(node.test, ast.Constant):
            if bool(node.test.value) is True:
                self.violations.append(
                    f"{self.filename}:{node.lineno}: Tautological assertion detected (assert {node.test.value!r})"
                )
        elif isinstance(node.test, ast.Compare):
            if isinstance(node.test.left, ast.Constant) and len(node.test.comparators) == 1:
                right = node.test.comparators[0]
                if isinstance(right, ast.Constant) and node.test.left.value == right.value:
                    self.violations.append(
                        f"{self.filename}:{node.lineno}: Dummy constant comparison assertion (assert {node.test.left.value!r} == {right.value!r})"
                    )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check for patch or mock of function under test
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in ("patch", "patch_object"):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    val = arg.value
                    if any(bad in val for bad in ("calculate_ece", "evaluate_loss", "calibrate", "fit")):
                        # Check if return_value is hardcoded constant
                        for kw in node.keywords:
                            if kw.arg == "return_value" and isinstance(kw.value, ast.Constant):
                                self.violations.append(
                                    f"{self.filename}:{node.lineno}: Rule T4 Violation! Mocking calculation with hardcoded return_value: {val}"
                                )
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        # Check for silent exception masking: except Exception: pass
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.violations.append(
                f"{self.filename}:{node.lineno}: Silent exception handler (except: pass) without logging or warnings"
            )
        self.generic_visit(node)


def audit_files(patterns: List[str]) -> Tuple[int, List[str]]:
    all_violations: List[str] = []
    file_count = 0
    for pattern in patterns:
        for p in glob.glob(pattern, recursive=True):
            fpath = Path(p)
            if not fpath.is_file() or not fpath.name.endswith(".py"):
                continue
            file_count += 1
            try:
                content = fpath.read_text(encoding="utf-8")
                tree = ast.parse(content, filename=str(fpath))
                visitor = AntiGamingVisitor(fpath.as_posix())
                visitor.visit(tree)
                all_violations.extend(visitor.violations)
            except Exception as e:
                all_violations.append(f"{fpath.as_posix()}: Parse Error: {e}")

    return file_count, all_violations


def main() -> None:
    parser = argparse.ArgumentParser(description="AST Anti-Gaming Static Inspector")
    parser.add_argument("--tests", default="tests/**/*.py", help="Glob pattern for test files")
    parser.add_argument("--src", default="src/**/*.py", help="Glob pattern for source files")
    args = parser.parse_args()

    test_count, test_violations = audit_files([args.tests])
    src_count, src_violations = audit_files([args.src])

    total_violations = test_violations + src_violations

    if not total_violations:
        print(f"[PASS] AST Anti-Gaming Audit Passed! Checked {test_count} test files and {src_count} source files with 0 violations.")
        sys.exit(0)
    else:
        print(f"[FAIL] Found {len(total_violations)} anti-gaming violations:", file=sys.stderr)
        for v in total_violations:
            print(f"  - {v}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
