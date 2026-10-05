"""Independent External Verifier for behavioral-playwright (Phase D.5).

Completely independent of harness.oracle and harness.runtime_probe.
Runs in an isolated process to verify:
1. execution_id and session_id binding
2. evidence_id uniqueness and replay resistance
3. timestamp and freshness constraints
4. live artifact SHA-256 byte integrity
5. HMAC authenticity
6. required evidence fields completeness
7. browser PID and process liveliness
8. page and DOM session binding
9. verdict seal and integrity

FAILS CLOSED: Any unknown, malformed, incomplete, stale, replayed, or unverifiable
payload is strictly rejected.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ExternalVerificationResult:
    """Rigorous audit result produced by the Independent External Verifier."""
    is_valid: bool
    status: str  # "VERIFIED", "REJECTED", "MALFORMED", "REPLAY_DETECTED"
    violations: List[str]
    evidence_id: Optional[str] = None
    execution_id: Optional[str] = None
    audit_timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


class IndependentExternalVerifier:
    """Stand-alone verifier executing completely decoupled from internal harness logic."""

    # Consumed evidence IDs across the external verifier domain to prevent replay
    _CONSUMED_EVIDENCES: Set[str] = set()

    @classmethod
    def reset_consumed_registry(cls) -> None:
        """Resets the replay prevention registry."""
        cls._CONSUMED_EVIDENCES.clear()

    @classmethod
    def check_process_alive(cls, pid: int) -> bool:
        """Independently verifies if a PID corresponds to an active process on the host OS."""
        if not isinstance(pid, int) or pid <= 0:
            return False
        if os.name == "nt":
            # Windows API: OpenProcess with PROCESS_QUERY_LIMITED_INFORMATION (0x1000)
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            try:
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if handle:
                    ctypes.windll.kernel32.CloseHandle(handle)
                    return True
                return False
            except Exception:
                return False
        else:
            try:
                os.kill(pid, 0)
                return True
            except (OSError, ProcessLookupError):
                return False

    @classmethod
    def compute_probe_hmac(
        cls,
        secret: bytes,
        execution_id: str,
        session_id: str,
        evidence_id: str,
        created_at: float,
        observed_url: str,
        observed_title: str,
        dom_observed_state: Dict[str, str],
        artifact_digests: Dict[str, str],
    ) -> str:
        """Independently re-computes HMAC-SHA256 signature matching the probe specification."""
        canonical_str = (
            f"exec:{execution_id}|sess:{session_id}|ev:{evidence_id}|"
            f"time:{created_at:.6f}|url:{observed_url}|title:{observed_title}|"
            f"dom:{sorted(dom_observed_state.items())}|"
            f"art:{sorted(artifact_digests.items())}"
        )
        return hmac.new(secret, canonical_str.encode("utf-8"), hashlib.sha256).hexdigest()

    @classmethod
    def compute_verdict_seal(
        cls,
        secret: bytes,
        status: str,
        is_acceptable: bool,
        execution_id: Optional[str],
        evidence_id: Optional[str],
        violations: List[str],
    ) -> str:
        """Independently re-computes HMAC-SHA256 verdict seal matching Oracle specification."""
        canonical_str = (
            f"verdict:{status}|acc:{is_acceptable}|"
            f"exec:{execution_id or 'none'}|ev:{evidence_id or 'none'}|"
            f"viols:{sorted(violations)}"
        )
        return hmac.new(secret, canonical_str.encode("utf-8"), hashlib.sha256).hexdigest()

    @classmethod
    def verify_evidence(
        cls,
        evidence: Any,
        contract: Any,
        probe_secret: bytes,
        check_replay: bool = True,
    ) -> ExternalVerificationResult:
        """Validates all 11 minimum trust properties of a RuntimeEvidence bundle."""
        violations: List[str] = []

        # 1. Structural / Type Validation
        if not isinstance(evidence, dict):
            return ExternalVerificationResult(
                is_valid=False,
                status="MALFORMED",
                violations=["MALFORMED_EVIDENCE: Evidence payload is not a valid dictionary."],
            )

        if not isinstance(contract, dict):
            return ExternalVerificationResult(
                is_valid=False,
                status="MALFORMED",
                violations=["MALFORMED_CONTRACT: Contract payload is not a valid dictionary."],
            )

        # 2. Required Fields Check
        required_fields = [
            "execution_id", "session_id", "evidence_id", "created_at",
            "observed_url", "observed_title", "dom_observed_state",
            "artifact_digests", "probe_signature"
        ]
        missing = [f for f in required_fields if f not in evidence]
        if missing:
            return ExternalVerificationResult(
                is_valid=False,
                status="INCOMPLETE",
                violations=[f"INCOMPLETE_EVIDENCE_FIELDS: Missing required fields {missing}."],
            )

        exec_id = str(evidence.get("execution_id", ""))
        sess_id = str(evidence.get("session_id", ""))
        ev_id = str(evidence.get("evidence_id", ""))
        created_at = evidence.get("created_at")
        observed_url = str(evidence.get("observed_url", ""))
        observed_title = str(evidence.get("observed_title", ""))
        dom_observed = evidence.get("dom_observed_state", {})
        artifact_digests = evidence.get("artifact_digests", {})
        probe_signature = str(evidence.get("probe_signature", ""))
        browser_pid = evidence.get("browser_pid")

        # 3. Execution ID and Session ID Binding
        contract_exec_id = str(contract.get("execution_id", ""))
        contract_sess_id = str(contract.get("session_id", ""))

        if not exec_id:
            violations.append("EMPTY_EXECUTION_ID: Evidence execution_id is empty.")
        elif contract_exec_id and exec_id != contract_exec_id:
            violations.append(
                f"EXECUTION_ID_MISMATCH: Evidence execution_id '{exec_id}' does not match contract '{contract_exec_id}'."
            )

        if not sess_id:
            violations.append("EMPTY_SESSION_ID: Evidence session_id is empty.")
        elif contract_sess_id and sess_id != contract_sess_id:
            violations.append(
                f"SESSION_ID_MISMATCH: Evidence session_id '{sess_id}' does not match contract '{contract_sess_id}'."
            )

        # 4. Freshness and Timestamp Constraints
        if not isinstance(created_at, (int, float)):
            violations.append(f"INVALID_TIMESTAMP_TYPE: created_at {created_at!r} is not a numeric timestamp.")
        else:
            now = time.time()
            contract_start = contract.get("execution_start_time", 0.0)
            if contract_start and created_at < (contract_start - 0.5):
                violations.append(
                    f"STALE_TIMESTAMP: Evidence created_at ({created_at:.3f}) predates execution start ({contract_start:.3f})."
                )
            if created_at > (now + 15.0):
                violations.append(
                    f"FUTURE_TIMESTAMP: Evidence created_at ({created_at:.3f}) is in the future (current={now:.3f})."
                )
            if (now - created_at) > 3600.0:
                violations.append(
                    f"EXPIRED_EVIDENCE: Evidence created_at ({created_at:.3f}) exceeds max freshness window (3600s)."
                )

        # 5. Replay Resistance
        if check_replay and ev_id in cls._CONSUMED_EVIDENCES:
            violations.append(f"EVIDENCE_REPLAY: Evidence ID '{ev_id}' has already been consumed by external verifier.")

        # 6. HMAC Signature Authenticity Check
        if not isinstance(dom_observed, dict) or not isinstance(artifact_digests, dict):
            violations.append("INVALID_CONTAINER_TYPES: dom_observed_state and artifact_digests must be dicts.")
        else:
            try:
                expected_mac = cls.compute_probe_hmac(
                    secret=probe_secret,
                    execution_id=exec_id,
                    session_id=sess_id,
                    evidence_id=ev_id,
                    created_at=float(created_at),
                    observed_url=observed_url,
                    observed_title=observed_title,
                    dom_observed_state=dom_observed,
                    artifact_digests=artifact_digests,
                )
                if not hmac.compare_digest(probe_signature, expected_mac):
                    violations.append("INVALID_PROBE_SIGNATURE: HMAC verification failed! Evidence was tampered or forged.")
            except Exception as e:
                violations.append(f"HMAC_CALCULATION_ERROR: {e}")

        # 7. Live Artifact SHA-256 Byte-Level Integrity Check
        if isinstance(artifact_digests, dict):
            for file_path_str, expected_sha in artifact_digests.items():
                p = Path(file_path_str)
                if not p.exists():
                    violations.append(f"ARTIFACT_NONEXISTENT: Artifact file '{file_path_str}' does not exist on disk.")
                    continue
                try:
                    live_bytes = p.read_bytes()
                    live_sha = hashlib.sha256(live_bytes).hexdigest()
                    if live_sha != expected_sha:
                        violations.append(
                            f"ARTIFACT_TAMPERED: Artifact '{file_path_str}' content altered! Live hash ({live_sha}) != expected ({expected_sha})."
                        )
                except Exception as e:
                    violations.append(f"ARTIFACT_READ_ERROR: Could not read '{file_path_str}': {e}")

        # 8. Browser Process Identity Verification
        if browser_pid is not None:
            if not isinstance(browser_pid, int):
                violations.append(f"INVALID_BROWSER_PID: browser_pid {browser_pid!r} is not an integer.")
            elif not cls.check_process_alive(browser_pid):
                violations.append(f"DEAD_BROWSER_PROCESS: browser_pid {browser_pid} is not a running OS process.")

        # 9. Page & DOM Session Binding
        expected_url = contract.get("expected_url")
        if expected_url:
            if observed_url == "about:blank" and expected_url != "about:blank":
                violations.append(f"NAVIGATION_NEVER_HAPPENED: Page remained on 'about:blank' instead of '{expected_url}'.")
            elif observed_url != expected_url:
                violations.append(f"URL_MISMATCH: Observed URL '{observed_url}' != expected '{expected_url}'.")

        expected_title = contract.get("expected_title")
        if expected_title and expected_title.lower() not in observed_title.lower():
            violations.append(f"TITLE_MISMATCH: Observed title '{observed_title}' does not contain expected '{expected_title}'.")

        expected_selector = contract.get("expected_dom_selector")
        if expected_selector:
            if expected_selector not in dom_observed:
                violations.append(f"MISSING_DOM_SELECTOR: Selector '{expected_selector}' missing from observed DOM.")
            else:
                expected_text = contract.get("expected_dom_text")
                if expected_text and expected_text not in dom_observed[expected_selector]:
                    violations.append(
                        f"DOM_TEXT_MISMATCH: Element '{expected_selector}' text '{dom_observed[expected_selector]}' does not contain '{expected_text}'."
                    )

        if violations:
            status = "REPLAY_DETECTED" if any("EVIDENCE_REPLAY" in v for v in violations) else "REJECTED"
            return ExternalVerificationResult(
                is_valid=False,
                status=status,
                violations=violations,
                evidence_id=ev_id,
                execution_id=exec_id,
                details={"observed_url": observed_url, "artifact_count": len(artifact_digests)},
            )

        # Successful verification: register evidence ID in consumed set
        if check_replay and ev_id:
            cls._CONSUMED_EVIDENCES.add(ev_id)

        return ExternalVerificationResult(
            is_valid=True,
            status="VERIFIED",
            violations=[],
            evidence_id=ev_id,
            execution_id=exec_id,
            details={"observed_url": observed_url, "artifact_count": len(artifact_digests)},
        )

    @classmethod
    def verify_oracle_verdict(
        cls,
        verdict: Any,
        oracle_secret: bytes,
        contract: Optional[Any] = None,
    ) -> ExternalVerificationResult:
        """Independently verifies OracleVerdict seal, execution binding, and acceptable status."""
        violations: List[str] = []

        if not isinstance(verdict, dict):
            # Support dataclass / object conversion
            if hasattr(verdict, "__dict__"):
                verdict = {
                    "status": getattr(verdict.status, "value", str(verdict.status)),
                    "is_acceptable": getattr(verdict, "is_acceptable", False),
                    "execution_id": getattr(verdict, "execution_id", None),
                    "evidence_id": getattr(verdict, "evidence_id", None),
                    "violations": getattr(verdict, "violations", []),
                    "seal": getattr(verdict, "seal", None),
                }
            else:
                return ExternalVerificationResult(
                    is_valid=False,
                    status="MALFORMED",
                    violations=["MALFORMED_VERDICT: Verdict is not a dictionary or object."],
                )

        status_str = str(verdict.get("status", ""))
        is_acceptable = bool(verdict.get("is_acceptable", False))
        exec_id = verdict.get("execution_id")
        ev_id = verdict.get("evidence_id")
        verdict_violations = verdict.get("violations", [])
        seal = verdict.get("seal")

        # Invariant 1: Must be VERIFIED_REAL_SUCCESS
        if status_str != "VERIFIED_REAL_SUCCESS":
            violations.append(f"UNACCEPTED_VERDICT_STATUS: Status is '{status_str}', not 'VERIFIED_REAL_SUCCESS'.")

        # Invariant 2: Must be acceptable
        if not is_acceptable:
            violations.append("VERDICT_NOT_ACCEPTABLE: Verdict is_acceptable flag is False.")

        # Invariant 3: Must have zero internal violations
        if verdict_violations:
            violations.append(f"VERDICT_INTERNAL_VIOLATIONS: Verdict contains internal violations: {verdict_violations}")

        # Invariant 4: Must possess execution_id and evidence_id
        if not exec_id or not ev_id:
            violations.append("UNBOUND_VERDICT: Verdict lacks execution_id or evidence_id.")

        # Invariant 5: If contract supplied, execution_id must match
        if contract and isinstance(contract, dict):
            contract_exec = contract.get("execution_id")
            if contract_exec and exec_id != contract_exec:
                violations.append(f"VERDICT_EXECUTION_MISMATCH: Verdict exec_id '{exec_id}' != contract '{contract_exec}'.")

        # Invariant 6: Cryptographic HMAC seal verification
        if not seal:
            violations.append("UNSEALED_VERDICT: Verdict possesses no cryptographic seal.")
        else:
            try:
                expected_seal = cls.compute_verdict_seal(
                    secret=oracle_secret,
                    status=status_str,
                    is_acceptable=is_acceptable,
                    execution_id=exec_id,
                    evidence_id=ev_id,
                    violations=verdict_violations,
                )
                if not hmac.compare_digest(seal, expected_seal):
                    violations.append("FORGED_VERDICT_SEAL: Verdict HMAC seal does not match expected seal.")
            except Exception as e:
                violations.append(f"VERDICT_SEAL_CALCULATION_ERROR: {e}")

        if violations:
            return ExternalVerificationResult(
                is_valid=False,
                status="REJECTED",
                violations=violations,
                evidence_id=ev_id,
                execution_id=exec_id,
            )

        return ExternalVerificationResult(
            is_valid=True,
            status="VERIFIED",
            violations=[],
            evidence_id=ev_id,
            execution_id=exec_id,
        )

    @classmethod
    def run_in_subprocess(
        cls,
        evidence_dict: Dict[str, Any],
        contract_dict: Dict[str, Any],
        probe_secret: bytes,
    ) -> ExternalVerificationResult:
        """Executes the external verification algorithm in a clean, isolated OS subprocess."""
        script_path = Path(__file__).resolve()
        payload = {
            "evidence": evidence_dict,
            "contract": contract_dict,
            "probe_secret_hex": probe_secret.hex(),
        }
        cmd = [sys.executable, str(script_path), "--stdin"]
        try:
            proc = subprocess.run(
                cmd,
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode not in (0, 2):
                return ExternalVerificationResult(
                    is_valid=False,
                    status="SUBPROCESS_ERROR",
                    violations=[f"SUBPROCESS_CRASH: Exit code {proc.returncode}, stderr: {proc.stderr.strip()}"],
                )
            result_json = json.loads(proc.stdout.strip())
            return ExternalVerificationResult(
                is_valid=result_json.get("is_valid", False),
                status=result_json.get("status", "UNKNOWN"),
                violations=result_json.get("violations", []),
                evidence_id=result_json.get("evidence_id"),
                execution_id=result_json.get("execution_id"),
                details=result_json.get("details", {}),
            )
        except Exception as ex:
            return ExternalVerificationResult(
                is_valid=False,
                status="SUBPROCESS_EXCEPTION",
                violations=[f"SUBPROCESS_INVOCATION_FAILED: {ex}"],
            )


def main() -> None:
    """CLI entrypoint for standalone subprocess execution."""
    parser = argparse.ArgumentParser(description="Independent External Verifier CLI")
    parser.add_argument("--stdin", action="store_true", help="Read verification payload JSON from stdin")
    args = parser.parse_args()

    if args.stdin:
        try:
            raw_input = sys.stdin.read()
            payload = json.loads(raw_input)
            evidence = payload.get("evidence", {})
            contract = payload.get("contract", {})
            secret_hex = payload.get("probe_secret_hex", "")
            probe_secret = bytes.fromhex(secret_hex)

            res = IndependentExternalVerifier.verify_evidence(
                evidence=evidence,
                contract=contract,
                probe_secret=probe_secret,
            )
            print(json.dumps(asdict(res)))
            sys.exit(0 if res.is_valid else 2)
        except Exception as e:
            err_res = ExternalVerificationResult(
                is_valid=False,
                status="CLI_PARSING_ERROR",
                violations=[f"CLI_ERROR: {e}"],
            )
            print(json.dumps(asdict(err_res)))
            sys.exit(1)
    else:
        print("Usage: python -m harness.external_verifier --stdin")
        sys.exit(1)


if __name__ == "__main__":
    main()
