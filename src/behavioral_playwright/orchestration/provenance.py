"""Cryptographic provenance chaining and immutable execution tracking for workflows."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class StepProvenanceRecord:
    """Immutable provenance record binding an action's lifecycle phase to cryptographic evidence."""
    workflow_id: str
    step_id: str
    action: str
    action_type: str
    phase: str                                # "PLANNED", "EXECUTED", "OBSERVED", "VERIFIED", "RECOVERED"
    timestamp: float
    input_hash: str
    evidence_hash: str
    verified: bool
    signature: str


class WorkflowProvenanceChain:
    """Maintains a tamper-evident audit log of all workflow actions and verification steps."""

    _DEFAULT_SECRET = b"BP_ORCHESTRATION_PROVENANCE_SECRET_KEY_v7"

    def __init__(
        self,
        workflow_id: str,
        secret: Optional[bytes] = None,
        clock_fn: Optional[Any] = None,
    ) -> None:
        self.workflow_id = workflow_id
        self._secret = secret or self._DEFAULT_SECRET
        self._clock_fn = clock_fn or time.monotonic
        self.records: List[StepProvenanceRecord] = []

    @staticmethod
    def compute_sha256(data: Any) -> str:
        """Computes a deterministic SHA-256 digest of arbitrary structured data."""
        try:
            canonical = json.dumps(data, sort_keys=True, default=str)
        except Exception:
            canonical = str(data)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def record_phase(
        self,
        step_id: str,
        action: str,
        action_type: str,
        phase: str,
        input_data: Any,
        evidence_data: Any,
        verified: bool = False,
    ) -> StepProvenanceRecord:
        """Constructs, signs, and appends an immutable provenance record."""
        now = self._clock_fn()
        in_hash = self.compute_sha256(input_data)
        ev_hash = self.compute_sha256(evidence_data)

        # Build payload for HMAC signature
        payload = f"{self.workflow_id}:{step_id}:{action}:{action_type}:{phase}:{now:.6f}:{in_hash}:{ev_hash}:{verified}"
        sig = hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

        rec = StepProvenanceRecord(
            workflow_id=self.workflow_id,
            step_id=step_id,
            action=action,
            action_type=action_type,
            phase=phase,
            timestamp=now,
            input_hash=in_hash,
            evidence_hash=ev_hash,
            verified=verified,
            signature=sig,
        )
        self.records.append(rec)
        return rec

    def verify_chain_integrity(self) -> bool:
        """Verifies that none of the provenance records in the chain have been mutated or forged."""
        for rec in self.records:
            if rec.workflow_id != self.workflow_id:
                return False
            expected_payload = (
                f"{self.workflow_id}:{rec.step_id}:{rec.action}:{rec.action_type}:{rec.phase}:"
                f"{rec.timestamp:.6f}:{rec.input_hash}:{rec.evidence_hash}:{rec.verified}"
            )
            expected_sig = hmac.new(self._secret, expected_payload.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(rec.signature, expected_sig):
                return False
        return True

    def to_list(self) -> List[Dict[str, Any]]:
        """Exports the provenance chain as a list of dictionaries."""
        return [asdict(r) for r in self.records]
