"""In-Memory Adversarial Mutation Engine.

Introduces controlled, isolated mutations against critical implementation logic
to evaluate test-suite kill rate without permanently modifying production files.

Architecture (DEFECT-004 Remediation):
- Every mutation must be verified against an independent external test module.
- Mutation classification taxonomy:
    * EXTERNAL_KILLED: External pytest module failed (exit_code != 0) when mutant was active.
    * ORACLE_KILLED: IndependentOracle rejected mutated payload during contract verification.
    * SELF_KILLED: Inline self-assertion by runner (STRICTLY EXCLUDED from mutation score!).
    * SURVIVED: Test module passed despite active mutation (defect in test suite).
    * ERROR: Unexpected execution exception during mutation setup/teardown.
- Anti-Circularity Rule: Runner never validates mutants with inline assertions.
"""
from __future__ import annotations

import asyncio
import io
import logging
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("harness.mutation")


@dataclass
class MutationResult:
    mutation_id: str
    description: str
    target: str
    killed: bool
    classification: str  # EXTERNAL_KILLED, ORACLE_KILLED, SELF_KILLED, SURVIVED, ERROR
    killed_by: str
    details: str = ""


class MutationRunner:
    """Executes controlled monkeypatched mutations against test suites."""

    def __init__(self) -> None:
        self.results: List[MutationResult] = []

    def run_all(self) -> Dict[str, Any]:
        """Runs the complete mutation suite and computes the legitimate mutation score."""
        self.results.clear()

        self._mutate_circuit_breaker()
        self._mutate_provider_gating()
        self._mutate_powerhand_status()
        self._mutate_storage_export()
        self._mutate_mcp_unknown_tool()
        self._mutate_saccade_empty()
        self._mutate_entropy_guard()
        self._mutate_oracle_falsify()

        total = len(self.results)
        external_killed = sum(1 for r in self.results if r.classification == "EXTERNAL_KILLED")
        oracle_killed = sum(1 for r in self.results if r.classification == "ORACLE_KILLED")
        self_killed = sum(1 for r in self.results if r.classification == "SELF_KILLED")
        survived = sum(1 for r in self.results if r.classification == "SURVIVED")
        errors = sum(1 for r in self.results if r.classification == "ERROR")

        # DEFECT-004 INVARIANT: Self-killed mutants NEVER count towards legitimate kills!
        legitimate_kills = external_killed + oracle_killed
        score = (legitimate_kills / total * 100.0) if total > 0 else 0.0

        return {
            "total_mutations": total,
            "killed": legitimate_kills,
            "external_killed": external_killed,
            "oracle_killed": oracle_killed,
            "self_killed": self_killed,
            "survived": survived,
            "errors": errors,
            "mutation_score_pct": round(score, 2),
            "legitimate_score_pct": round(score, 2),
            "results": [
                {
                    "mutation_id": r.mutation_id,
                    "description": r.description,
                    "target": r.target,
                    "killed": r.killed,
                    "classification": r.classification,
                    "killed_by": r.killed_by,
                    "details": r.details,
                }
                for r in self.results
            ],
        }

    def _run_test_verifier(self, test_path: str, test_filter: str = "") -> Tuple[bool, int, str]:
        """Runs pytest in-process against active in-memory monkeypatch.

        Returns (is_killed, exit_code, detail_summary).
        """
        args = [test_path]
        if test_filter:
            args.extend(["-k", test_filter])
        args.append("-q")

        buffer = io.StringIO()
        with redirect_stdout(buffer), redirect_stderr(buffer):
            exit_code = pytest.main(args)

        output = buffer.getvalue().strip()
        last_line = output.splitlines()[-1] if output.splitlines() else f"exit_code={exit_code}"

        # In mutation testing:
        # If exit_code != 0, the test failed as expected, which means the mutant was KILLED!
        is_killed = (int(exit_code) != 0)
        return is_killed, int(exit_code), last_line

    # =========================================================================
    # Mutation 1: Circuit Breaker Bypass
    # =========================================================================
    def _mutate_circuit_breaker(self) -> None:
        from behavioral_playwright.resilience.circuit_breaker import CircuitBreaker

        original_execute = CircuitBreaker.execute

        # Mutant: bypasses state == OPEN guard
        async def mutated_execute(self_cb: Any, coro_fn: Any, operation_name: str = "operation") -> Any:
            return await coro_fn()

        CircuitBreaker.execute = mutated_execute  # type: ignore
        try:
            killed, code, details = self._run_test_verifier(
                "tests/unit/test_resilience.py", "test_circuit_breaker_transitions"
            )
            classification = "EXTERNAL_KILLED" if killed else "SURVIVED"
            killer = f"tests/unit/test_resilience.py (exit code {code})" if killed else "SURVIVED"
        except Exception as e:
            killed = False
            classification = "ERROR"
            killer = f"ERROR: {e}"
            details = str(e)
        finally:
            CircuitBreaker.execute = original_execute

        self.results.append(
            MutationResult(
                mutation_id="MUT-001",
                description="Bypass CircuitBreaker OPEN state guard",
                target="behavioral_playwright.resilience.circuit_breaker.CircuitBreaker.execute",
                killed=killed,
                classification=classification,
                killed_by=killer,
                details=details,
            )
        )

    # =========================================================================
    # Mutation 2: Provider Gating Bypass
    # =========================================================================
    def _mutate_provider_gating(self) -> None:
        from behavioral_playwright.providers.browser import PatchrightProvider

        original_is_available = PatchrightProvider.is_available
        original_require_available = PatchrightProvider.require_available

        # Mutant: uninstalled provider lies that it is available and skips require check
        PatchrightProvider.is_available = lambda self: True  # type: ignore
        PatchrightProvider.require_available = lambda self: None  # type: ignore

        try:
            killed, code, details = self._run_test_verifier(
                "tests/integrity/mutations/test_mut_002_provider_gating.py"
            )
            classification = "EXTERNAL_KILLED" if killed else "SURVIVED"
            killer = f"test_mut_002_provider_gating.py (exit code {code})" if killed else "SURVIVED"
        except Exception as e:
            killed = False
            classification = "ERROR"
            killer = f"ERROR: {e}"
            details = str(e)
        finally:
            PatchrightProvider.is_available = original_is_available
            PatchrightProvider.require_available = original_require_available

        self.results.append(
            MutationResult(
                mutation_id="MUT-002",
                description="Force uninstalled provider to report available and skip gating check",
                target="behavioral_playwright.providers.browser.PatchrightProvider.require_available",
                killed=killed,
                classification=classification,
                killed_by=killer,
                details=details,
            )
        )

    # =========================================================================
    # Mutation 3: PowerHand Status Mutation (Fake Success)
    # =========================================================================
    def _mutate_powerhand_status(self) -> None:
        from behavioral_evasion_suite.powerhand_master import PowerHandPlaywrightRunner

        original_execute = PowerHandPlaywrightRunner.execute_stealth_session

        # Mutant: changes dry_run_success fallback to literal "success"
        async def mutated_execute(self_r: Any, *args: Any, **kwargs: Any) -> Dict[str, Any]:
            res = await original_execute(self_r, *args, **kwargs)
            res["status"] = "success"  # MUTANT: fake success injection
            return res

        PowerHandPlaywrightRunner.execute_stealth_session = mutated_execute  # type: ignore
        try:
            killed, code, details = self._run_test_verifier(
                "tests/integrity/mutations/test_mut_003_powerhand_status.py"
            )
            classification = "EXTERNAL_KILLED" if killed else "SURVIVED"
            killer = f"test_mut_003_powerhand_status.py (exit code {code})" if killed else "SURVIVED"
        except Exception as e:
            killed = False
            classification = "ERROR"
            killer = f"ERROR: {e}"
            details = str(e)
        finally:
            PowerHandPlaywrightRunner.execute_stealth_session = original_execute

        self.results.append(
            MutationResult(
                mutation_id="MUT-003",
                description="Force PowerHandPlaywrightRunner to return 'success' on dry_run",
                target="behavioral_evasion_suite.powerhand_master.PowerHandPlaywrightRunner.execute_stealth_session",
                killed=killed,
                classification=classification,
                killed_by=killer,
                details=details,
            )
        )

    # =========================================================================
    # Mutation 4: Storage Export Silent Failure
    # =========================================================================
    def _mutate_storage_export(self) -> None:
        from behavioral_playwright.storage.exporters import DataStorageManager

        original_export = DataStorageManager.export

        # Mutant: swallows all errors and returns None
        def mutated_export(self_s: Any, records: Any, destination: str, format_type: str = "json") -> Any:
            return None  # MUTANT: swallowed failure

        DataStorageManager.export = mutated_export  # type: ignore
        try:
            killed, code, details = self._run_test_verifier(
                "tests/integrity/mutations/test_mut_004_storage_export.py"
            )
            classification = "EXTERNAL_KILLED" if killed else "SURVIVED"
            killer = f"test_mut_004_storage_export.py (exit code {code})" if killed else "SURVIVED"
        except Exception as e:
            killed = False
            classification = "ERROR"
            killer = f"ERROR: {e}"
            details = str(e)
        finally:
            DataStorageManager.export = original_export

        self.results.append(
            MutationResult(
                mutation_id="MUT-004",
                description="Swallow export errors silently in DataStorageManager.export",
                target="behavioral_playwright.storage.exporters.DataStorageManager.export",
                killed=killed,
                classification=classification,
                killed_by=killer,
                details=details,
            )
        )

    # =========================================================================
    # Mutation 5: MCP Unknown Tool Fake Success
    # =========================================================================
    def _mutate_mcp_unknown_tool(self) -> None:
        from behavioral_playwright.mcp.tools import MCP_TOOL_DEFINITIONS, McpToolDispatcher

        known_tools = {t["name"] for t in MCP_TOOL_DEFINITIONS}
        original_execute_tool = McpToolDispatcher.execute_tool

        # Mutant: returns success for nonexistent tool
        async def mutated_execute_tool(self_d: Any, tool_name: str, arguments: Optional[Dict[str, Any]]) -> Dict[str, Any]:
            if tool_name not in known_tools:
                return {"status": "success", "result": "fake_success"}  # MUTANT
            return await original_execute_tool(self_d, tool_name, arguments)

        McpToolDispatcher.execute_tool = mutated_execute_tool  # type: ignore
        try:
            killed, code, details = self._run_test_verifier(
                "tests/integrity/mutations/test_mut_005_mcp_unknown_tool.py"
            )
            classification = "EXTERNAL_KILLED" if killed else "SURVIVED"
            killer = f"test_mut_005_mcp_unknown_tool.py (exit code {code})" if killed else "SURVIVED"
        except Exception as e:
            killed = False
            classification = "ERROR"
            killer = f"ERROR: {e}"
            details = str(e)
        finally:
            McpToolDispatcher.execute_tool = original_execute_tool

        self.results.append(
            MutationResult(
                mutation_id="MUT-005",
                description="MCP returns success for unknown tool",
                target="behavioral_playwright.mcp.tools.McpToolDispatcher.execute_tool",
                killed=killed,
                classification=classification,
                killed_by=killer,
                details=details,
            )
        )

    # =========================================================================
    # Mutation 6: Empty Saccade Path
    # =========================================================================
    def _mutate_saccade_empty(self) -> None:
        from behavioral_evasion_suite.powerhand_master import PowerHandMaster

        original_saccade = PowerHandMaster.get_saccade_path

        # Mutant: returns empty list
        PowerHandMaster.get_saccade_path = lambda *args, **kwargs: []  # type: ignore
        try:
            killed, code, details = self._run_test_verifier(
                "tests/integrity/mutations/test_mut_006_saccade_empty.py"
            )
            classification = "EXTERNAL_KILLED" if killed else "SURVIVED"
            killer = f"test_mut_006_saccade_empty.py (exit code {code})" if killed else "SURVIVED"
        except Exception as e:
            killed = False
            classification = "ERROR"
            killer = f"ERROR: {e}"
            details = str(e)
        finally:
            PowerHandMaster.get_saccade_path = original_saccade

        self.results.append(
            MutationResult(
                mutation_id="MUT-006",
                description="PowerHandMaster returns empty saccade trajectory",
                target="behavioral_evasion_suite.powerhand_master.PowerHandMaster.get_saccade_path",
                killed=killed,
                classification=classification,
                killed_by=killer,
                details=details,
            )
        )

    # =========================================================================
    # Mutation 7: Entropy Anomaly Guard Bypass
    # =========================================================================
    def _mutate_entropy_guard(self) -> None:
        from behavioral_playwright.powerplay.schema_guard import ResolvedSchemaIntegrityGuard

        original_compute = ResolvedSchemaIntegrityGuard.compute_shannon_entropy

        # Mutant: always returns fixed 3.5 even on blank string
        ResolvedSchemaIntegrityGuard.compute_shannon_entropy = lambda data: 3.5  # MUTANT
        try:
            killed, code, details = self._run_test_verifier(
                "tests/integrity/mutations/test_mut_007_entropy_guard.py"
            )
            classification = "EXTERNAL_KILLED" if killed else "SURVIVED"
            killer = f"test_mut_007_entropy_guard.py (exit code {code})" if killed else "SURVIVED"
        except Exception as e:
            killed = False
            classification = "ERROR"
            killer = f"ERROR: {e}"
            details = str(e)
        finally:
            ResolvedSchemaIntegrityGuard.compute_shannon_entropy = staticmethod(original_compute)

        self.results.append(
            MutationResult(
                mutation_id="MUT-007",
                description="ResolvedSchemaIntegrityGuard returns fabricated entropy for empty input",
                target="behavioral_playwright.powerplay.schema_guard.ResolvedSchemaIntegrityGuard.compute_shannon_entropy",
                killed=killed,
                classification=classification,
                killed_by=killer,
                details=details,
            )
        )

    # =========================================================================
    # Mutation 8: Oracle Dry Run Falsification
    # =========================================================================
    def _mutate_oracle_falsify(self) -> None:
        from harness.oracle import ExecutionStatus, IndependentOracle

        original_classify = IndependentOracle.classify_status_payload

        # Mutant: oracle classifies dry_run_success as REAL_SUCCESS
        def mutated_classify(payload: Any, expected_operation: str = "") -> ExecutionStatus:
            if isinstance(payload, dict) and payload.get("status") == "dry_run_success":
                return ExecutionStatus.REAL_SUCCESS  # MUTANT
            return original_classify(payload, expected_operation)

        IndependentOracle.classify_status_payload = staticmethod(mutated_classify)  # type: ignore
        try:
            killed, code, details = self._run_test_verifier(
                "tests/integrity/mutations/test_mut_008_oracle_falsify.py"
            )
            classification = "EXTERNAL_KILLED" if killed else "SURVIVED"
            killer = f"test_mut_008_oracle_falsify.py (exit code {code})" if killed else "SURVIVED"
        except Exception as e:
            killed = False
            classification = "ERROR"
            killer = f"ERROR: {e}"
            details = str(e)
        finally:
            IndependentOracle.classify_status_payload = original_classify

        self.results.append(
            MutationResult(
                mutation_id="MUT-008",
                description="Oracle classifies dry_run_success as REAL_SUCCESS (Rule 10 violation)",
                target="harness.oracle.IndependentOracle.classify_status_payload",
                killed=killed,
                classification=classification,
                killed_by=killer,
                details=details,
            )
        )


if __name__ == "__main__":
    runner = MutationRunner()
    res = runner.run_all()
    print("=" * 60)
    print("MUTATION TESTING REPORT")
    print("=" * 60)
    print(f"Total Mutations:       {res['total_mutations']}")
    print(f"External Killed:       {res['external_killed']}")
    print(f"Oracle Killed:         {res['oracle_killed']}")
    print(f"Self Killed:           {res['self_killed']}")
    print(f"Survived:              {res['survived']}")
    print(f"Legitimate Kills:      {res['killed']}")
    print(f"Legitimate Score:      {res['legitimate_score_pct']}%")
    print("-" * 60)
    for r in res["results"]:
        status = "KILLED" if r["killed"] else "SURVIVED"
        print(f"[{status}] [{r['classification']}] {r['mutation_id']}: {r['description']} -> {r['killed_by']}")
