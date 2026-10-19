from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request
from typing import Any, Dict

from veil.kinematics.biomechanics import compute_teleport_click_ratio, generate_pre_click_stream
from veil.kinematics.keystrokes import LinguisticKeystrokeDynamicsEngine


class CognitiveFormAgentBlueprint:
    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.keystrokes = LinguisticKeystrokeDynamicsEngine(seed=seed)

    async def submit_form(self, action_url: str, form_data: Dict[str, str]) -> Dict[str, Any]:
        typing_events = sum(len(self.keystrokes.generate_typing_sequence(v, seed=self.seed)) for v in form_data.values())
        click_stream = generate_pre_click_stream((20.0, 20.0), (150.0, 150.0), steps=20, seed=self.seed)
        t_ratio = compute_teleport_click_ratio(click_stream)
        encoded = urllib.parse.urlencode(form_data).encode("utf-8")

        def _post() -> tuple[int, str, str]:
            req = urllib.request.Request(action_url, data=encoded, method="POST")
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace"), resp.headers.get("Set-Cookie", "")

        status, body, cookie = await asyncio.to_thread(_post)
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return {
            "action_url": action_url,
            "status_code": status,
            "response": parsed,
            "cookie": cookie,
            "keystroke_events_generated": typing_events,
            "click_telemetry": {"teleport_click_ratio": t_ratio, "events": len(click_stream)},
        }
