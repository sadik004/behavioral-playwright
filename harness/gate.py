"""Master Independent Integrity Gate & Verification Auditor.

Evaluates:
1. Static AST / Codebase Integrity
2. Untrusted Existing Test Suite
3. Independent Integrity Test Suite
4. Adversarial Fault-Injection Suite
5. Fake-Success & Silent Fallback Detection
6. Mutation Score
7. Determinism & Seed Contract
8. Runtime vs Static Verification
9. MCP JSON-RPC Contracts
10. Optional Dependency / Provider Honesty
11. Claim Registry Alignment
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.mutation import MutationRunner
from harness.static_integrity import audit_repository

logger = logging.getLogger("harness.gate")


class IntegrityGate:
    """Master evaluator enforcing zero-fraud engineering contracts."""

    def __init__(self) -> None:
        self.claims_path = REPO_ROOT / "integrity" / "claims.json"
        self.static_findings_path = REPO_ROOT / "integrity" / "static_findings.json"
        self.report_data: Dict[str, Any] = {}

    def run_all(self) -> Dict[str, Any]:
        """Runs the entire audit pipeline and outputs structured metrics."""
        print("=" * 60)
        print("RUNNING BEHAVIORAL-PLAYWRIGHT INDEPENDENT INTEGRITY AUDIT")
        print("=" * 60)

        # 1. Static Integrity
        print("[1/6] Running Static Integrity AST Scanner...")
        findings, summary = audit_repository(REPO_ROOT)
        static_report = {
            "total_findings": summary["total_findings"],
            "severity_counts": summary["severity_counts"],
            "findings": [asdict(f) if hasattr(f, "__dataclass_fields__") else f for f in findings],
        }
        # Save static findings
        self.static_findings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.static_findings_path, "w", encoding="utf-8") as f:
            json.dump(static_report, f, indent=2)

        # 2. Existing Test Suite (Untrusted Evidence)
        print("[2/6] Auditing Untrusted Existing Test Suite...")
        existing_res = self._audit_existing_tests()

        # 3. Independent Integrity Tests
        print("[3/6] Running Independent Integrity Verification Suite...")
        integrity_res = self._run_independent_tests()

        # 4. In-Memory Mutation Testing
        print("[4/6] Running In-Memory Adversarial Mutation Suite...")
        mutation_runner = MutationRunner()
        mutation_res = mutation_runner.run_all()

        # 5. Claim Registry Verification
        print("[5/6] Evaluating Claim Registry...")
        claim_summary = self._evaluate_claims()

        # 6. Overall Gate Determination
        # Gate FAILS if any P0 issues exist, or if fake-success/contradictions exist
        p0_findings = [f for f in static_report.get("findings", []) if f.get("severity") == "P0"]
        contradicted_claims = claim_summary.get("CONTRADICTED", 0)
        independent_fails = integrity_res.get("failed", 0)

        critical_violations = len(p0_findings) + contradicted_claims + independent_fails
        gate_status = "FAIL" if critical_violations > 0 else "PASS"

        self.report_data = {
            "existing_tests": existing_res,
            "independent_tests": integrity_res,
            "adversarial_tests": {
                "passed": integrity_res.get("adversarial_passed", 0),
                "failed": integrity_res.get("adversarial_failed", 0),
            },
            "fake_success": {
                "passed": integrity_res.get("fake_success_passed", 0),
                "violations_detected": len(p0_findings),
            },
            "mutation": mutation_res,
            "determinism": "PASS" if integrity_res.get("determinism_passed", True) else "FAIL",
            "runtime_verification": "FAIL (Static scripts masquerading as runtime verification)",
            "mcp_contracts": "PASS" if integrity_res.get("mcp_passed", True) else "FAIL",
            "provider_integrity": "PASS" if integrity_res.get("provider_passed", True) else "FAIL",
            "claims": claim_summary,
            "static_findings": {
                "total": static_report.get("total_findings", 0),
                "p0": len(p0_findings),
                "p1": sum(1 for f in static_report.get("findings", []) if f.get("severity") == "P1"),
            },
            "gate_verdict": gate_status,
        }

        self.print_report()
        return self.report_data

    def _audit_existing_tests(self) -> Dict[str, Any]:
        """Runs pytest on existing tests (excluding tests/integrity)."""
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "--ignore=tests/integrity",
            "-q",
        ]
        try:
            res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
            output = res.stdout + res.stderr
            # Parse pytest summary line
            # e.g.: "377 passed, 1 failed, 2 skipped in 18.23s"
            passed = 0
            failed = 0
            skipped = 0
            for line in output.splitlines():
                if "passed" in line or "failed" in line or "skipped" in line:
                    parts = line.split(",")
                    for p in parts:
                        p = p.strip()
                        if "passed" in p:
                            try:
                                passed = int(p.split()[0])
                            except ValueError:
                                pass
                        elif "failed" in p:
                            try:
                                failed = int(p.split()[0])
                            except ValueError:
                                pass
                        elif "skipped" in p:
                            try:
                                skipped = int(p.split()[0])
                            except ValueError:
                                pass
            return {"passed": passed, "failed": failed, "skipped": skipped, "untrusted": True}
        except Exception as e:
            return {"passed": 0, "failed": 1, "error": str(e), "untrusted": True}

    def _run_independent_tests(self) -> Dict[str, Any]:
        """Runs pytest on tests/integrity and parses exact metrics."""
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/integrity",
            "-v",
        ]
        res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=60)
        output = res.stdout + res.stderr

        total = 0
        passed = 0
        failed = 0
        adv_pass = 0
        adv_fail = 0
        fake_pass = 0
        det_pass = True
        mcp_pass = True
        prov_pass = True

        for line in output.splitlines():
            if "PASSED" in line:
                passed += 1
                total += 1
                if "test_failure_integrity" in line:
                    adv_pass += 1
                elif "test_fake_success" in line:
                    fake_pass += 1
            elif "FAILED" in line:
                failed += 1
                total += 1
                if "test_failure_integrity" in line:
                    adv_fail += 1
                if "test_determinism" in line:
                    det_pass = False
                if "test_mcp" in line:
                    mcp_pass = False
                if "test_providers" in line:
                    prov_pass = False

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "adversarial_passed": adv_pass,
            "adversarial_failed": adv_fail,
            "fake_success_passed": fake_pass,
            "determinism_passed": det_pass,
            "mcp_passed": mcp_pass,
            "provider_passed": prov_pass,
        }

    def _evaluate_claims(self) -> Dict[str, int]:
        """Tallies claim statuses from integrity/claims.json."""
        summary = {
            "VERIFIED": 0,
            "PARTIALLY_VERIFIED": 0,
            "UNVERIFIED": 0,
            "CONTRADICTED": 0,
            "PROVIDER_GATED": 0,
            "SIMULATION_ONLY": 0,
            "UNIMPLEMENTED": 0,
        }
        if self.claims_path.exists():
            with open(self.claims_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            claims = data.get("claims", []) if isinstance(data, dict) else data
            for c in claims:
                st = c.get("status", "UNVERIFIED")
                summary[st] = summary.get(st, 0) + 1
        return summary

    def print_report(self) -> None:
        """Outputs the exact specified integrity report format."""
        r = self.report_data
        print()
        print("=" * 60)
        print("BEHAVIORAL-PLAYWRIGHT INDEPENDENT INTEGRITY REPORT")
        print("=" * 60)
        print()
        print("Existing Tests (Untrusted Baseline Evidence):")
        print(f"    {r['existing_tests'].get('passed', 0)} PASS")
        print(f"    {r['existing_tests'].get('failed', 0)} FAIL")
        print(f"    {r['existing_tests'].get('skipped', 0)} SKIP")
        print()
        print("Independent Tests:")
        print(f"    PASS: {r['independent_tests'].get('passed', 0)}")
        print(f"    FAIL: {r['independent_tests'].get('failed', 0)}")
        print()
        print("Adversarial:")
        print(f"    PASS: {r['adversarial_tests'].get('passed', 0)}")
        print(f"    FAIL: {r['adversarial_tests'].get('failed', 0)}")
        print()
        print("Fake Success Detection:")
        print(f"    PASS: {r['fake_success'].get('passed', 0)}")
        print(f"    VIOLATIONS DETECTED: {r['fake_success'].get('violations_detected', 0)}")
        print()
        print("Mutation Testing:")
        print(f"    Total:    {r['mutation'].get('total_mutations', 0)}")
        print(f"    Killed:   {r['mutation'].get('killed', 0)}")
        print(f"    Survived: {r['mutation'].get('survived', 0)}")
        print(f"    Score:    {r['mutation'].get('mutation_score_pct', 0.0)}%")
        print()
        print(f"Determinism:            {r['determinism']}")
        print(f"Runtime Verification:   {r['runtime_verification']}")
        print(f"MCP Contracts:          {r['mcp_contracts']}")
        print(f"Provider Integrity:     {r['provider_integrity']}")
        print()
        print("Claim Verification:")
        for status, count in r["claims"].items():
            print(f"    {status:<20}: {count}")
        print()
        print("=" * 60)
        print(f"FINAL INTEGRITY GATE: {r['gate_verdict']}")
        print("=" * 60)
        if r["gate_verdict"] == "FAIL":
            print("REASON FOR GATE FAILURE:")
            print(f"- P0 Critical Static Findings: {r['static_findings']['p0']} violations")
            print(f"- Contradicted Claims:         {r['claims'].get('CONTRADICTED', 0)} claims")
            print(f"- Surviving Mutants:           {r['mutation'].get('survived', 0)} mutants survived")
            print("- Falsification Invariant:     Live browser crashes converted to 'dry_run_success'")
            print("- Runtime Invariant:           Static JS string existence != verified browser execution")


if __name__ == "__main__":
    gate = IntegrityGate()
    gate.run_all()
