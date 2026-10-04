"""Generic Multi-Gate Quality Scorecard Runner.

Executes quality gates G0..GN, formats an ASCII scorecard, and outputs machine-readable gate_report.json.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, List, Optional


@dataclass
class GateResult:
    gate_id: str
    name: str
    passed: bool
    evidence: str
    details: Optional[Any] = None


class QualityScorecard:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.results: List[GateResult] = []

    def run_command(self, cmd: List[str]) -> Tuple[int, str]:
        res = subprocess.run(cmd, cwd=str(self.root_dir), capture_output=True, text=True)
        out = (res.stdout.strip() + "\n" + res.stderr.strip()).strip()
        return res.returncode, out

    def add_result(self, result: GateResult) -> None:
        self.results.append(result)
        status_str = "PASS [OK]" if result.passed else "FAIL [X]"
        print(f"[{result.gate_id}] {result.name:<45}: {status_str}")

    def render_markdown_table(self) -> str:
        lines = [
            "=" * 80,
            f"| {'Gate':<4} | {'Name':<40} | {'Status':^8} | {'Evidence':<20} |",
            f"|:{'-'*4}|:{'-'*40}|:{'-'*8}:|:{'-'*20}|",
        ]
        for r in self.results:
            st = "PASS" if r.passed else "FAIL"
            ev = r.evidence.replace("\n", " ")[:40]
            lines.append(f"| {r.gate_id:<4} | {r.name:<40} | {st:^8} | {ev:<20} |")
        lines.append("=" * 80)
        return "\n".join(lines)

    def write_json_report(self, dest: Path) -> None:
        data = [asdict(r) for r in self.results]
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Adversarial Quality Scorecard Runner")
    parser.add_argument("--root", default=".", help="Root workspace directory")
    parser.add_argument("--json", default="gate_report.json", help="Path to save JSON report")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    runner = QualityScorecard(root)

    print("=" * 70)
    print("RUNNING ADVERSARIAL QUALITY SCORECARD")
    print(f"Workspace: {root}")
    print("=" * 70)

    # 1. Gate G0: Test Lock & Anti-Gaming
    lock_script = root / "scripts" / "harness_locker.py"
    if lock_script.exists():
        code, out = runner.run_command([sys.executable, str(lock_script), "--verify"])
        runner.add_result(GateResult("G0", "Test-Integrity Lock Gate", code == 0, out.splitlines()[-1] if out else ""))
    else:
        runner.add_result(GateResult("G0", "Test-Integrity Lock Gate", True, "Skipped (no LOCK.json)"))

    # 2. Gate G1: AST Static Anti-Gaming
    ast_script = root / "scripts" / "ast_anti_gaming.py"
    if ast_script.exists():
        code, out = runner.run_command([sys.executable, str(ast_script)])
        runner.add_result(GateResult("G1", "Zero Silent Handlers & Anti-Gaming", code == 0, out.splitlines()[-1] if out else ""))
    else:
        runner.add_result(GateResult("G1", "Zero Silent Handlers & Anti-Gaming", True, "Skipped (ast_anti_gaming not found)"))

    # 3. Gate G2: Test Suite Full Green
    code, out = runner.run_command([sys.executable, "-m", "pytest", "-q", "--disable-warnings"])
    last_line = out.splitlines()[-1] if out else ""
    runner.add_result(GateResult("G2", "Test Suite 100% Green", code == 0, last_line))

    # Render Summary
    print()
    print(runner.render_markdown_table())

    runner.write_json_report(Path(args.json))

    all_passed = all(r.passed for r in runner.results)
    exit_code = 0 if all_passed else 1
    print(f"\nFinal Verdict: {sum(r.passed for r in runner.results)}/{len(runner.results)} gates passed. Exit code: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
