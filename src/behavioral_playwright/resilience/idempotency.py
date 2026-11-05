"""Operation classification and idempotency policies for safe retry decisions."""

from __future__ import annotations

from enum import Enum
from typing import Optional


class OperationType(str, Enum):
    """Classification of automation operations based on external side effects."""
    READ = "READ"                               # Pure observation: DOM extraction, title, url, screenshot
    IDEMPOTENT_WRITE = "IDEMPOTENT_WRITE"       # Replaceable state: goto, fill whole input, clear, set_viewport
    NON_IDEMPOTENT_WRITE = "NON_IDEMPOTENT_WRITE" # State-mutating: click button, submit form, payment, keyboard enter
    UNKNOWN = "UNKNOWN"                         # Untyped operation: must be treated as unsafe


class IdempotencyPolicy:
    """Evaluates whether an operation can be safely retried following an exception."""

    @staticmethod
    def is_safe_to_retry(
        op_type: OperationType,
        attempt: int,
        started_execution: bool = True,
        explicit_idempotent: Optional[bool] = None,
    ) -> bool:
        """Determines if repeating an operation violates idempotency.

        Invariants:
        1. If explicit_idempotent is True, caller explicitly certifies the action is repeatable.
        2. READ operations are unconditionally safe to retry.
        3. IDEMPOTENT_WRITE operations (e.g. goto, clear, replace input) are safe to retry.
        4. NON_IDEMPOTENT_WRITE operations (e.g. click, checkout, submit) are strictly forbidden
           from blind retries if execution was initiated, because the action may have already
           reached the remote web server.
        5. UNKNOWN operations default to fail-safe rejection.
        """
        if explicit_idempotent is True:
            return True
        if explicit_idempotent is False:
            return False

        if op_type == OperationType.READ:
            return True

        if op_type == OperationType.IDEMPOTENT_WRITE:
            return True

        if op_type == OperationType.NON_IDEMPOTENT_WRITE:
            # Safe only if we have guaranteed evidence that the operation failed BEFORE execution began
            # (e.g., target locator failed before emitting any mouse or keyboard dispatch).
            return not started_execution

        # Default: fail closed
        return False
