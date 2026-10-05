"""Runaway loop protection and autonomous boundary enforcement."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from behavioral_playwright.orchestration.exceptions import RunawayLoopError


@dataclass
class LoopProtectionConfig:
    """Configurable boundaries protecting against runaway agent loops."""
    max_steps: int = 50
    max_repeated_actions: int = 3
    max_recovery_attempts: int = 2
    max_planner_iterations: int = 5
    max_verification_cycles: int = 3
    detect_oscillation: bool = True
    detect_no_progress: bool = True
    no_progress_window: int = 4


class LoopProtector:
    """Detects repeated actions, cycling states, and runaway execution loops."""

    def __init__(self, config: Optional[LoopProtectionConfig] = None) -> None:
        self.config = config or LoopProtectionConfig()
        self.total_steps: int = 0
        self.recovery_count: int = 0
        self.planner_iterations: int = 0
        self.verification_cycles: int = 0
        
        # History for loop & oscillation detection
        self._action_history: List[str] = []
        self._state_hash_history: List[str] = []

    @staticmethod
    def _action_fingerprint(action: str, input_data: Dict[str, Any]) -> str:
        try:
            inp_str = json.dumps(input_data, sort_keys=True, default=str)
        except Exception:
            inp_str = str(input_data)
        return f"{action}::{inp_str}"

    def record_action(self, action: str, input_data: Dict[str, Any]) -> None:
        """Records an action invocation and enforces loop / step limits."""
        self.total_steps += 1
        if self.total_steps > self.config.max_steps:
            raise RunawayLoopError(
                f"Workflow exceeded maximum step budget ({self.config.max_steps} steps). Terminating execution safely."
            )

        fp = self._action_fingerprint(action, input_data)
        self._action_history.append(fp)

        # 1. Repeated identical actions check
        if len(self._action_history) >= self.config.max_repeated_actions:
            recent = self._action_history[-self.config.max_repeated_actions:]
            if all(item == fp for item in recent):
                raise RunawayLoopError(
                    f"Runaway loop detected: action '{action}' was repeatedly executed {self.config.max_repeated_actions} "
                    f"times with identical parameters. Bounded execution enforced."
                )

        # 2. Oscillation check: [A, B, A, B] pattern
        if self.config.detect_oscillation and len(self._action_history) >= 4:
            h = self._action_history
            if h[-4] == h[-2] and h[-3] == h[-1] and h[-4] != h[-3]:
                raise RunawayLoopError(
                    f"Oscillating loop detected: workflow is alternating repeatedly between actions "
                    f"({h[-4]} <-> {h[-3]}). Terminating execution safely."
                )

    def record_recovery(self) -> None:
        """Tracks recovery attempts and halts on runaway recovery cycles."""
        self.recovery_count += 1
        if self.recovery_count > self.config.max_recovery_attempts:
            raise RunawayLoopError(
                f"Recovery loop detected: workflow reached maximum recovery attempts ({self.config.max_recovery_attempts}). "
                "Halting to prevent endless recovery cycling."
            )

    def record_planner_iteration(self) -> None:
        """Tracks planner invocation cycles."""
        self.planner_iterations += 1
        if self.planner_iterations > self.config.max_planner_iterations:
            raise RunawayLoopError(
                f"Planner loop detected: planner exceeded maximum refinement iterations ({self.config.max_planner_iterations})."
            )

    def record_verification_cycle(self) -> None:
        """Tracks verification re-checks."""
        self.verification_cycles += 1
        if self.verification_cycles > self.config.max_verification_cycles:
            raise RunawayLoopError(
                f"Verification loop detected: step re-verified {self.config.max_verification_cycles} times without progression."
            )

    def record_progress_state(self, state_hash: str) -> None:
        """Tracks observable state progression to detect zero-progress loops."""
        if not self.config.detect_no_progress:
            return

        self._state_hash_history.append(state_hash)
        w = self.config.no_progress_window
        if len(self._state_hash_history) >= w:
            recent = self._state_hash_history[-w:]
            if all(s == recent[0] for s in recent):
                raise RunawayLoopError(
                    f"Zero-progress execution loop detected: {w} consecutive actions produced zero observable "
                    "DOM or state mutation. Halting execution."
                )
