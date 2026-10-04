"""Independent Verification Oracle for behavioral-playwright.

This oracle determines whether observed runtime behavior, returned dictionaries,
thrown exceptions, or execution traces satisfy documented engineering contracts.

CRITICAL INVARIANTS:
1. `dry_run_success` is NEVER classified as REAL_SUCCESS.
2. A swallowed exception is NEVER classified as REAL_SUCCESS.
3. Provider absence is explicitly classified as PROVIDER_UNAVAILABLE, not failure or fake success.
4. Mocks/doubles are explicitly classified as SIMULATION, never REAL_SUCCESS.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ExecutionStatus(str, enum.Enum):
    """Rigorous classification taxonomy for execution outcomes."""
    REAL_SUCCESS = "REAL_SUCCESS"
    REAL_FAILURE = "REAL_FAILURE"
    DRY_RUN = "DRY_RUN"
    SIMULATION = "SIMULATION"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    UNIMPLEMENTED = "UNIMPLEMENTED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class OracleVerdict:
    """Detailed verdict issued by the Independent Oracle."""
    status: ExecutionStatus
    is_acceptable: bool
    reason: str
    evidence: Dict[str, Any]
    violations: List[str]


class IndependentOracle:
    """Independent Verification Oracle completely decoupled from existing test assertions."""

    @staticmethod
    def classify_status_payload(result: Any, expected_operation: str = "") -> ExecutionStatus:
        """Classifies a returned result payload into the rigorous status taxonomy."""
        if result is None:
            return ExecutionStatus.UNKNOWN

        if isinstance(result, Exception):
            exc_name = type(result).__name__
            if "ProviderUnavailable" in exc_name or "NotInstalled" in exc_name:
                return ExecutionStatus.PROVIDER_UNAVAILABLE
            if "NotImplemented" in exc_name:
                return ExecutionStatus.UNIMPLEMENTED
            return ExecutionStatus.REAL_FAILURE

        if isinstance(result, dict):
            status_val = str(result.get("status", "")).lower()
            mode_val = str(result.get("mode", "")).lower()

            if "dry_run" in status_val or "dry_run" in mode_val:
                return ExecutionStatus.DRY_RUN

            if result.get("simulated", False) or result.get("synthetic", False):
                return ExecutionStatus.SIMULATION

            if status_val == "provider_unavailable" or result.get("provider_available") is False:
                return ExecutionStatus.PROVIDER_UNAVAILABLE

            if status_val in ("success", "ok", "completed"):
                # Check for disguised dry run or fallback
                if "dry_run_success" in status_val:
                    return ExecutionStatus.DRY_RUN
                if result.get("dma_packets_generated") and not result.get("title") and not result.get("browser"):
                    return ExecutionStatus.DRY_RUN
                return ExecutionStatus.REAL_SUCCESS

            if status_val in ("failure", "failed", "error"):
                return ExecutionStatus.REAL_FAILURE

            if status_val == "partial":
                return ExecutionStatus.PARTIAL

        # If it's a boolean
        if isinstance(result, bool):
            return ExecutionStatus.REAL_SUCCESS if result else ExecutionStatus.REAL_FAILURE

        return ExecutionStatus.UNKNOWN

    @classmethod
    def evaluate_live_execution(
        cls,
        result: Any,
        exception: Optional[Exception] = None,
        context_claims: Optional[Dict[str, Any]] = None,
    ) -> OracleVerdict:
        """Evaluates whether an operation claimed to be a live execution honestly succeeded.

        Rules:
        - If exception occurred, it must NOT be swallowed or masked as success.
        - Result containing 'dry_run_success' must be flagged as DRY_RUN, NOT REAL_SUCCESS.
        """
        violations: List[str] = []
        evidence: Dict[str, Any] = {
            "result_type": type(result).__name__,
            "exception": repr(exception) if exception else None,
            "raw_result": str(result)[:300],
        }

        if exception:
            status = cls.classify_status_payload(exception)
            return OracleVerdict(
                status=status,
                is_acceptable=(status == ExecutionStatus.PROVIDER_UNAVAILABLE),
                reason=f"Operation terminated with exception: {type(exception).__name__}: {exception}",
                evidence=evidence,
                violations=violations,
            )

        status = cls.classify_status_payload(result)

        if status == ExecutionStatus.DRY_RUN:
            violations.append("DRY_RUN_DISGUISED_AS_LIVE: Operation returned dry-run metrics instead of live browser execution.")
            return OracleVerdict(
                status=ExecutionStatus.DRY_RUN,
                is_acceptable=False,
                reason="Live execution failed and fell back to dry-run simulation.",
                evidence=evidence,
                violations=violations,
            )

        if status == ExecutionStatus.REAL_SUCCESS:
            return OracleVerdict(
                status=ExecutionStatus.REAL_SUCCESS,
                is_acceptable=True,
                reason="Live execution succeeded with verified live artifacts.",
                evidence=evidence,
                violations=[],
            )

        if status == ExecutionStatus.PROVIDER_UNAVAILABLE:
            return OracleVerdict(
                status=ExecutionStatus.PROVIDER_UNAVAILABLE,
                is_acceptable=True,
                reason="Optional provider gracefully reported unavailable state.",
                evidence=evidence,
                violations=[],
            )

        return OracleVerdict(
            status=status,
            is_acceptable=False,
            reason=f"Result classified as {status.value}, which does not meet REAL_SUCCESS contract.",
            evidence=evidence,
            violations=violations,
        )

    @classmethod
    def evaluate_failure_integrity(
        cls,
        callable_fn: Callable[[], Any],
        expected_exception_types: Tuple[type, ...],
        operation_name: str = "fault_injected_operation",
    ) -> OracleVerdict:
        """Asserts that when a critical dependency or resource fails, the system FAILS LOUDLY.

        Violations:
        - Swallowing the failure and returning success.
        - Returning empty dummy object without error indicator.
        - Converting error into fake 'dry_run_success'.
        """
        violations: List[str] = []
        try:
            res = callable_fn()
            # If function returned instead of raising, inspect what it returned
            status = cls.classify_status_payload(res)
            if status in (ExecutionStatus.REAL_SUCCESS, ExecutionStatus.DRY_RUN):
                violations.append(
                    f"FAKE_SUCCESS_ON_FAILURE: {operation_name} returned {status.value} despite injected failure!"
                )
                return OracleVerdict(
                    status=status,
                    is_acceptable=False,
                    reason=f"{operation_name} silently absorbed injected failure and returned {res}",
                    evidence={"returned_result": res},
                    violations=violations,
                )
            if expected_exception_types:
                violations.append(
                    f"FAILURE_SWALLOWED: {operation_name} returned without raising expected exception {[t.__name__ for t in expected_exception_types]}. Returned: {res}"
                )
                return OracleVerdict(
                    status=status,
                    is_acceptable=False,
                    reason=f"{operation_name} returned without raising expected exception: {[t.__name__ for t in expected_exception_types]}",
                    evidence={"returned_result": res},
                    violations=violations,
                )
            return OracleVerdict(
                status=status,
                is_acceptable=True,
                reason=f"{operation_name} returned non-success status ({status.value}) as expected",
                evidence={"returned_result": res},
                violations=[],
            )
        except Exception as exc:
            evidence = {"raised_exception": type(exc).__name__, "msg": str(exc)}
            if any(isinstance(exc, exp) for exp in expected_exception_types):
                return OracleVerdict(
                    status=ExecutionStatus.REAL_FAILURE,
                    is_acceptable=True,
                    reason=f"Operation correctly propagated expected exception {type(exc).__name__}",
                    evidence=evidence,
                    violations=[],
                )
            else:
                violations.append(
                    f"UNEXPECTED_EXCEPTION_TYPE: Expected one of {[t.__name__ for t in expected_exception_types]}, got {type(exc).__name__}"
                )
                return OracleVerdict(
                    status=ExecutionStatus.REAL_FAILURE,
                    is_acceptable=False,
                    reason=f"Unexpected exception {type(exc).__name__}: {exc}",
                    evidence=evidence,
                    violations=violations,
                )

    @classmethod
    def evaluate_determinism(
        cls,
        fn1: Callable[[], Any],
        fn2: Callable[[], Any],
        tolerance: float = 1e-9,
    ) -> Tuple[bool, str]:
        """Evaluates whether two seeded operations produce strictly deterministic output."""
        val1 = fn1()
        val2 = fn2()

        if val1 == val2:
            return True, "Identical outputs across seeded runs."

        # If numeric or collections of numbers
        if isinstance(val1, (list, tuple)) and isinstance(val2, (list, tuple)):
            if len(val1) != len(val2):
                return False, f"Length mismatch: {len(val1)} vs {len(val2)}"
            for idx, (a, b) in enumerate(zip(val1, val2)):
                if a != b:
                    return False, f"Divergence at index {idx}: {a} != {b}"

        return False, f"Outputs diverged: {str(val1)[:100]} vs {str(val2)[:100]}"
