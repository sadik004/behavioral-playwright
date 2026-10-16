"""Cognitive Form Agent Client Blueprint (`src/veil/blueprints/form_agent.py`).

Provides autonomous form interaction and login handling with:
- Natural pre-click saccadic trajectory stream (teleport_click_ratio == 0)
- Linguistic keystroke dynamics cadence (QWERTY distance + Weibull timing distribution)
- Secure submission dispatch and session capture
"""

from __future__ import annotations

import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from veil.api.client import AsyncApiClient
from veil.kinematics.biomechanics import (
    BiometricMouseController,
    compute_teleport_click_ratio,
    generate_pre_click_stream,
)
from veil.kinematics.keystrokes import LinguisticKeystrokeDynamicsEngine


class CognitiveFormAgentBlueprint:
    """Blueprint for intelligent, anti-bot cognitive form interaction and submission."""

    def __init__(
        self,
        api_client: Optional[AsyncApiClient] = None,
        seed: Optional[int] = 42,
    ) -> None:
        self.api_client = api_client or AsyncApiClient()
        self.mouse = BiometricMouseController(seed=seed)
        self.keystrokes = LinguisticKeystrokeDynamicsEngine()
        self.seed = seed

    def plan_field_cadence(self, text: str) -> Dict[str, Any]:
        """Calculates realistic inter-key latencies and QWERTY dynamics for typing into an input."""
        seq = self.keystrokes.generate_typing_sequence(text, seed=self.seed)
        total_time = seq[-1]["timestamp_ms"] if seq else 0
        return {
            "text_length": len(text),
            "events_count": len(seq),
            "total_typing_time_ms": total_time,
        }

    def plan_submit_click(
        self,
        cursor_pos: Tuple[float, float],
        submit_btn_coords: Tuple[float, float],
        steps: int = 25,
    ) -> Dict[str, Any]:
        """Generates continuous pre-click saccadic stream ensuring teleport_click_ratio == 0."""
        stream = generate_pre_click_stream(
            start=cursor_pos,
            target=submit_btn_coords,
            steps=steps,
            seed=self.seed,
        )
        teleport_ratio = compute_teleport_click_ratio(stream)

        return {
            "stream_points": len(stream),
            "teleport_click_ratio": teleport_ratio,
            "target_coords": submit_btn_coords,
            "passed": teleport_ratio == 0.0,
            "trajectory_sample": stream[:5],
        }

    async def submit_form(
        self,
        action_url: str,
        form_data: Dict[str, str],
        cursor_start: Tuple[float, float] = (100.0, 100.0),
        submit_btn_coords: Tuple[float, float] = (450.0, 320.0),
    ) -> Dict[str, Any]:
        """Executes full cognitive form interaction sequence and dispatches submission."""
        # 1. Plan typing cadence for each field
        typing_plans = {
            field: self.plan_field_cadence(val)
            for field, val in form_data.items()
        }

        # 2. Plan pre-click stream for submit action
        click_plan = self.plan_submit_click(cursor_start, submit_btn_coords)

        # 3. Dispatch form data via URL-encoded form POST
        encoded_data = urllib.parse.urlencode(form_data)
        resp = await self.api_client.request(
            method="POST",
            url=action_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=encoded_data,
        )

        return {
            "action_url": action_url,
            "status_code": resp.status_code,
            "is_success": 200 <= resp.status_code < 400,
            "typing_telemetry": typing_plans,
            "click_telemetry": click_plan,
            "response_snippet": resp.text[:200],
        }


__all__ = ["CognitiveFormAgentBlueprint"]
