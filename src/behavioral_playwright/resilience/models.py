"""Domain models and state definitions for resilience and recovery operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional

from behavioral_playwright.resilience.taxonomy import FailureCategory


class RecoveryState(str, Enum):
    """Lifecycle states of the recovery state machine."""
    HEALTHY = "HEALTHY"
    FAILURE_DETECTED = "FAILURE_DETECTED"
    CLASSIFIED = "CLASSIFIED"
    RECOVERY_ATTEMPTED = "RECOVERY_ATTEMPTED"
    STATE_REVALIDATED = "STATE_REVALIDATED"
    RECOVERED = "RECOVERED"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"


@dataclass
class RetryAttemptRecord:
    """Provenance record of a single retry execution attempt."""
    attempt: int
    timestamp: float
    delay_s: float
    error_type: str
    error_message: str
    failure_category: FailureCategory
    is_retryable: bool
    elapsed_budget_s: float


@dataclass
class RecoveryRecord:
    """Provenance record of an attempted recovery operation."""
    execution_id: str
    session_id: str
    timestamp: float
    trigger_category: FailureCategory
    trigger_error: str
    recovery_action: str
    previous_state: RecoveryState
    resulting_state: RecoveryState
    verification_passed: bool
    verification_details: Dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    attempts: int = 1
