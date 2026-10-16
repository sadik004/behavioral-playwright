"""Pillar 7: Soft-Block & Data-Poisoning Quarantine Gate.

Protects downstream databases and RAG pipelines from "Silent Soft-Blocks" (where a
server returns HTTP 200 OK, but the page is actually a CAPTCHA wall, an empty shell,
or poisoned $0.00 placeholder data).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QuarantineVerdict:
    passed: bool
    action: str  # "ACCEPT" | "RETRY_HIGHER_TIER" | "ROTATE_PROXY_AND_RETRY" | "QUARANTINE_DROP"
    reason: str
    shannon_entropy: float
    null_rate: float = 0.0
    anomalies: List[str] = field(default_factory=list)


class DataQuarantineGate:
    """Evaluates HTTP responses and extracted records for soft-blocks and data poisoning."""

    _SOFT_BLOCK_PHRASES = (
        "please enable javascript",
        "enable cookies to continue",
        "pardon our interruption",
        "unusual traffic from your computer",
        "verify you are a human",
        "cf-turnstile",
        "g-recaptcha",
        "h-captcha",
        "access to this page has been denied",
        "bot detection",
    )

    def __init__(
        self,
        min_entropy_bits: float = 3.2,
        min_body_chars: int = 64,
        max_null_rate: float = 0.5,
    ) -> None:
        self.min_entropy_bits = min_entropy_bits
        self.min_body_chars = min_body_chars
        self.max_null_rate = max_null_rate

    @staticmethod
    def compute_shannon_entropy(text: str) -> float:
        if not text:
            return 0.0
        counts = Counter(text)
        n = len(text)
        return round(-sum((c / n) * math.log2(c / n) for c in counts.values()), 4)

    def inspect(
        self,
        status_code: int,
        body_text: str,
        extracted_record: Optional[Dict[str, Any]] = None,
        required_fields: Optional[List[str]] = None,
        positive_numeric_fields: Optional[List[str]] = None,
    ) -> QuarantineVerdict:
        anomalies: List[str] = []
        entropy = self.compute_shannon_entropy(body_text)

        # 1. Explicit HTTP block codes
        if status_code in (403, 429, 503):
            return QuarantineVerdict(
                passed=False,
                action="ROTATE_PROXY_AND_RETRY",
                reason=f"HTTP_{status_code}_BLOCK",
                shannon_entropy=entropy,
                anomalies=[f"status_code={status_code}"],
            )

        # 2. Soft-block phrase detection on 200 OK pages
        body_lower = (body_text or "").lower()
        for phrase in self._SOFT_BLOCK_PHRASES:
            if phrase in body_lower and len(body_text) < 12000:
                anomalies.append(f"soft_block_phrase:{phrase}")
                return QuarantineVerdict(
                    passed=False,
                    action="RETRY_HIGHER_TIER",
                    reason="SILENT_SOFT_BLOCK_DETECTED",
                    shannon_entropy=entropy,
                    anomalies=anomalies,
                )

        # 3. Empty shell / low Shannon entropy check
        if len((body_text or "").strip()) < self.min_body_chars or entropy < self.min_entropy_bits:
            anomalies.append(f"low_entropy_or_length(len={len(body_text)},entropy={entropy})")
            return QuarantineVerdict(
                passed=False,
                action="RETRY_HIGHER_TIER",
                reason="EMPTY_OR_LOW_ENTROPY_SHELL",
                shannon_entropy=entropy,
                anomalies=anomalies,
            )

        # 4. Extracted record data contract validation
        null_rate = 0.0
        if extracted_record is not None:
            total_fields = max(1, len(extracted_record))
            null_count = sum(
                1 for v in extracted_record.values() if v is None or str(v).strip() == ""
            )
            null_rate = round(null_count / total_fields, 3)
            if null_rate > self.max_null_rate:
                anomalies.append(f"high_null_rate={null_rate}")

            for req in required_fields or ():
                if not extracted_record.get(req):
                    anomalies.append(f"missing_required_field:{req}")

            for num_field in positive_numeric_fields or ():
                raw_val = extracted_record.get(num_field)
                if raw_val is not None:
                    cleaned = "".join(ch for ch in str(raw_val) if ch.isdigit() or ch in ".-")
                    try:
                        val_f = float(cleaned)
                        if val_f <= 0.0:
                            anomalies.append(f"non_positive_value:{num_field}={val_f}")
                    except ValueError:
                        anomalies.append(f"invalid_numeric:{num_field}={raw_val}")

            if anomalies:
                return QuarantineVerdict(
                    passed=False,
                    action="QUARANTINE_DROP",
                    reason="DATA_CONTRACT_VIOLATION",
                    shannon_entropy=entropy,
                    null_rate=null_rate,
                    anomalies=anomalies,
                )

        return QuarantineVerdict(
            passed=True,
            action="ACCEPT",
            reason="CLEAN_VERIFIED_RECORD",
            shannon_entropy=entropy,
            null_rate=null_rate,
        )
