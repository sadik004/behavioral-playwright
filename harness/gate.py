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
import re
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.external_verifier import IndependentExternalVerifier
from harness.mutation import MutationRunner
from harness.oracle import IndependentOracle, OracleVerdict, RuntimeEvidenceContract
from harness.static_integrity import audit_repository

logger = logging.getLogger("harness.gate")


def verify_runtime_verdict(
    verdict: Any,
    contract: Optional[RuntimeEvidenceContract] = None,
) -> Tuple[bool, str]:
    """Master Gate independent verification of an execution verdict.

    Invariants enforced by the Master Gate & External Verifier (Phase D.5):
    1. Must be a genuine OracleVerdict instance.
    2. Must be authentic VERIFIED_REAL_SUCCESS and acceptable.
    3. Must possess a valid cryptographic Oracle seal.
    4. Must have execution_id and evidence_id bound.
    5. If contract provided, execution_id must match.
    6. Must contain zero violations.
    7. Must pass independent audit by IndependentExternalVerifier.
    """
    if not isinstance(verdict, OracleVerdict):
        return False, "GATE_REJECT: Verdict is not a genuine OracleVerdict instance."
    if not IndependentOracle.is_trusted_success(verdict):
        return False, "GATE_REJECT: Verdict does not possess a valid cryptographic Oracle seal or is not verified success."
    if not verdict.execution_id or not verdict.evidence_id:
        return False, "GATE_REJECT: Verdict lacks execution or evidence binding."
    if contract is not None and verdict.execution_id != contract.execution_id:
        return False, f"GATE_REJECT: Execution ID mismatch ('{verdict.execution_id}' != '{contract.execution_id}')."
    if len(verdict.violations) > 0:
        return False, f"GATE_REJECT: Verdict contains violations: {verdict.violations}"

    contract_dict = None
    if contract is not None:
        contract_dict = {
            "execution_id": contract.execution_id,
            "session_id": contract.session_id,
        }
    ext_audit = IndependentExternalVerifier.verify_oracle_verdict(
        verdict=verdict,
        oracle_secret=IndependentOracle._ORACLE_SECRET,
        contract=contract_dict,
    )
    if not ext_audit.is_valid:
        return False, f"GATE_REJECT: External verifier rejected verdict: {ext_audit.violations}"

    return True, "VERDICT_ACCEPTED_BY_GATE"


def parse_pytest_summary(output: str, returncode: int) -> Dict[str, Any]:
    """Authoritative pytest execution parser.

    Enforces process exit code as the primary invariant signal.
    Extracts metrics from standard pytest summary lines without trusting arbitrary log strings.
    """
    passed = 0
    failed = 0
    skipped = 0

    # Search from the end for candidate summary lines
    summary_line = None
    for line in reversed(output.splitlines()):
        line_clean = line.strip()
        if not line_clean:
            continue
        # Standard pytest summary: e.g. "422 passed, 1 failed, 2 skipped in 18.23s"
        # or "= 1 failed in 0.32s ="
        if ("passed" in line_clean or "failed" in line_clean or "skipped" in line_clean or "error" in line_clean):
            if re.search(r"\bin\s+[\d\.]+s\b", line_clean) or line_clean.startswith("="):
                summary_line = line_clean
                break

    if summary_line:
        m_p = re.search(r"\b(\d+)\s+passed\b", summary_line)
        if m_p:
            passed = int(m_p.group(1))
        m_f = re.search(r"\b(\d+)\s+failed\b", summary_line)
        if m_f:
            failed = int(m_f.group(1))
        m_s = re.search(r"\b(\d+)\s+skipped\b", summary_line)
        if m_s:
            skipped = int(m_s.group(1))
        m_e = re.search(r"\b(\d+)\s+error\b", summary_line)
        if m_e:
            failed += int(m_e.group(1))

    # Authoritative process exit-code invariant:
    # Any non-zero exit code means test suite execution failed
    if returncode != 0:
        failed = max(failed, 1)

    is_success = (returncode == 0 and failed == 0)
    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "exit_code": returncode,
        "success": is_success,
    }


def evaluate_gate_verdict(
    static_report: Dict[str, Any],
    existing_res: Dict[str, Any],
    integrity_res: Dict[str, Any],
    mutation_res: Dict[str, Any],
    claim_summary: Dict[str, int],
    runtime_status: str,
) -> Tuple[str, List[str]]:
    """Strict fail-closed gate evaluation.

    If any mandatory engineering contract fails, overall gate MUST be FAIL.
    """
    violations: List[str] = []

    # 1. P0 Static Critical Findings
    p0_count = sum(1 for f in static_report.get("findings", []) if f.get("severity") == "P0")
    if p0_count > 0:
        violations.append(f"P0 Critical Static Findings: {p0_count} violations")

    # 2. Contradicted Claims
    contradicted = claim_summary.get("CONTRADICTED", 0)
    if contradicted > 0:
        violations.append(f"Contradicted Claims: {contradicted} claims")

    # 3. Independent Integrity Tests
    if integrity_res.get("failed", 0) > 0 or integrity_res.get("exit_code", 0) != 0:
        violations.append(
            f"Independent Integrity Tests Failed: {integrity_res.get('failed', 0)} failed (exit code {integrity_res.get('exit_code', 0)})"
        )

    # 4. Existing Test Process (authoritative exit code)
    if existing_res.get("failed", 0) > 0 or existing_res.get("exit_code", 0) != 0:
        violations.append(
            f"Existing Test Suite Failed: {existing_res.get('failed', 0)} failed (exit code {existing_res.get('exit_code', 0)})"
        )

    # 5. Runtime Verification
    if "FAIL" in str(runtime_status).upper() or not runtime_status or "MASQUERADING" in str(runtime_status).upper():
        violations.append(f"Runtime Verification Invariant Violated: {runtime_status}")

    # 6. Determinism Invariant
    if integrity_res.get("determinism_passed") is False or integrity_res.get("determinism") == "FAIL":
        violations.append("Determinism Invariant Violated: Seed reproducibility failed")

    # 7. MCP Contracts
    if integrity_res.get("mcp_passed") is False or integrity_res.get("mcp_contracts") == "FAIL":
        violations.append("MCP Contract Integrity Violated")

    # 8. Provider Integrity
    if integrity_res.get("provider_passed") is False or integrity_res.get("provider_integrity") == "FAIL":
        violations.append("Provider Integrity Violated: Missing provider dishonest reporting")

    # 9. Mutation Score & Surviving / Self-Killed Mutants
    survived_count = mutation_res.get("survived", 0)
    self_killed_count = mutation_res.get("self_killed", 0)
    legit_score = mutation_res.get("legitimate_score_pct", mutation_res.get("mutation_score_pct", 0.0))
    if survived_count > 0:
        violations.append(f"Surviving Mutants Detected: {survived_count} mutants survived")
    if self_killed_count > 0:
        violations.append(f"Unverified Self-Killed Mutants Detected: {self_killed_count} mutants not verified by test suite")
    # 10. External Verifier Invariant (Phase D.5)
    if integrity_res.get("external_verifier_passed") is False:
        violations.append("External Verifier Invariant Violated: External verification attacks or audit failed")

    gate_verdict = "FAIL" if violations else "PASS"
    return gate_verdict, violations


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

        # 6. Overall Fail-Closed Gate Determination
        runtime_verification_status = (
            "PASS (Independent live browser execution & 7-pillar contract verified)"
            if integrity_res.get("browser_reality_passed") and integrity_res.get("exit_code") == 0
            else "FAIL (No verified live browser runtime execution)"
        )
        gate_status, gate_violations = evaluate_gate_verdict(
            static_report=static_report,
            existing_res=existing_res,
            integrity_res=integrity_res,
            mutation_res=mutation_res,
            claim_summary=claim_summary,
            runtime_status=runtime_verification_status,
        )

        p0_findings = [f for f in static_report.get("findings", []) if f.get("severity") == "P0"]

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
            "runtime_verification": runtime_verification_status,
            "mcp_contracts": "PASS" if integrity_res.get("mcp_passed", True) else "FAIL",
            "provider_integrity": "PASS" if integrity_res.get("provider_passed", True) else "FAIL",
            "claims": claim_summary,
            "static_findings": {
                "total": static_report.get("total_findings", 0),
                "p0": len(p0_findings),
                "p1": sum(1 for f in static_report.get("findings", []) if f.get("severity") == "P1"),
            },
            "gate_verdict": gate_status,
            "gate_violations": gate_violations,
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
            res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=240)
            output = res.stdout + res.stderr
            parsed = parse_pytest_summary(output, res.returncode)
            parsed["untrusted"] = True
            return parsed
        except Exception as e:
            return {"passed": 0, "failed": 1, "skipped": 0, "exit_code": 1, "error": str(e), "untrusted": True, "success": False}

    def _run_independent_tests(self) -> Dict[str, Any]:
        """Runs pytest on tests/integrity and parses exact metrics."""
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/integrity",
            "-v",
        ]
        try:
            res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=60)
            output = res.stdout + res.stderr
            parsed = parse_pytest_summary(output, res.returncode)

            total = 0
            passed = 0
            failed = 0
            adv_pass = 0
            adv_fail = 0
            fake_pass = 0
            det_pass = True
            mcp_pass = True
            prov_pass = True
            browser_pass = True
            browser_count = 0
            ext_verifier_pass = True
            ext_verifier_count = 0

            for line in output.splitlines():
                if "PASSED" in line:
                    passed += 1
                    total += 1
                    if "test_failure_integrity" in line:
                        adv_pass += 1
                    elif "test_fake_success" in line:
                        fake_pass += 1
                    elif "test_browser_reality" in line:
                        browser_count += 1
                    elif "test_external_verifier" in line:
                        ext_verifier_count += 1
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
                    if "test_browser_reality" in line:
                        browser_pass = False
                    if "test_external_verifier" in line:
                        ext_verifier_pass = False

            if res.returncode != 0:
                failed = max(failed, 1)

            return {
                "total": total,
                "passed": passed,
                "failed": failed,
                "exit_code": res.returncode,
                "adversarial_passed": adv_pass,
                "adversarial_failed": adv_fail,
                "fake_success_passed": fake_pass,
                "browser_reality_passed": browser_pass and browser_count > 0,
                "external_verifier_passed": ext_verifier_pass and ext_verifier_count > 0,
                "external_verifier_count": ext_verifier_count,
                "determinism_passed": det_pass and (res.returncode == 0 or not "test_determinism" in output),
                "mcp_passed": mcp_pass and (res.returncode == 0 or not "test_mcp" in output),
                "provider_passed": prov_pass and (res.returncode == 0 or not "test_providers" in output),
            }
        except Exception as e:
            return {
                "total": 0,
                "passed": 0,
                "failed": 1,
                "exit_code": 1,
                "error": str(e),
                "adversarial_passed": 0,
                "adversarial_failed": 1,
                "fake_success_passed": 0,
                "determinism_passed": False,
                "mcp_passed": False,
                "provider_passed": False,
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
        print(f"    Total:           {r['mutation'].get('total_mutations', 0)}")
        print(f"    External Killed: {r['mutation'].get('external_killed', 0)}")
        print(f"    Oracle Killed:   {r['mutation'].get('oracle_killed', 0)}")
        print(f"    Self Killed:     {r['mutation'].get('self_killed', 0)}")
        print(f"    Survived:        {r['mutation'].get('survived', 0)}")
        print(f"    Score:           {r['mutation'].get('legitimate_score_pct', 0.0)}%")
        print()
        print(f"Determinism:            {r['determinism']}")
        print(f"Runtime Verification:   {r['runtime_verification']}")
        print(f"MCP Contracts:          {r['mcp_contracts']}")
        print(f"Provider Integrity:     {r['provider_integrity']}")
        print(f"External Verifier:      {'PASS' if r.get('independent_tests', {}).get('external_verifier_passed') else 'FAIL'}")
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
            for v in r.get("gate_violations", []):
                print(f"- {v}")


if __name__ == "__main__":
    gate = IntegrityGate()
    gate.run_all()
