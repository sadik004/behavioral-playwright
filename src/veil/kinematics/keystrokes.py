"""Kinematics Keystroke Cadence Engine.

Dhakal keyboard kinematics, Euclidean key distance scaling, Weibull latencies,
and cumulative timestamps with deterministic isolated RNG.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional


class KeystrokeCadenceEngine:
    """Calculates key layout Euclidean distances to scale Weibull flight latencies

    and maps them statefully using cumulative timestamps (timestamp_ms).
    """

    def __init__(self, w_shape: float = 1.5, w_scale: float = 110.0, seed: Optional[int] = None) -> None:
        self.w_shape = w_shape
        self.w_scale = w_scale
        self._seed = seed
        self._rng = random.Random(seed) if seed is not None else None
        self.layout: Dict[str, tuple[float, float]] = {
            "q": (0, 0), "w": (1, 0), "e": (2, 0), "r": (3, 0), "t": (4, 0),
            "y": (5, 0), "u": (6, 0), "i": (7, 0), "o": (8, 0), "p": (9, 0),
            "a": (0, 1), "s": (1, 1), "d": (2, 1), "f": (3, 1), "g": (4, 1),
            "h": (5, 1), "j": (6, 1), "k": (7, 1), "l": (8, 1),
            "z": (0, 2), "x": (1, 2), "c": (2, 2), "v": (3, 2), "b": (4, 2),
            "n": (5, 2), "m": (6, 2), " ": (4.5, 3),
        }

    def get_qwerty_distance(self, char1: str, char2: str) -> float:
        """Calculates physical key distance on standard layout."""
        c1, c2 = char1.lower(), char2.lower()
        if c1 in self.layout and c2 in self.layout:
            return math.hypot(self.layout[c1][0] - self.layout[c2][0], self.layout[c1][1] - self.layout[c2][1])
        return 1.8

    def generate_typing_sequence(
        self, text: str, seed: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Generates typing sequence where flight latencies scale logically with keyboard distances."""
        if seed is not None:
            r = random.Random(seed)
        elif self._rng is not None:
            r = self._rng
        else:
            r = random.Random()
            r.setstate(random.getstate())
        events: List[Dict[str, Any]] = []
        current_time_ms = 0
        for idx, char in enumerate(text):
            prev_char = text[idx - 1] if idx > 0 else " "
            dist = self.get_qwerty_distance(prev_char, char)

            scale_mod = self.w_scale * (0.6 + 0.12 * dist)
            dwell_time = max(15, int(r.weibullvariate(scale_mod, self.w_shape)))
            flight_time = max(20, int(r.weibullvariate(scale_mod * 0.85, self.w_shape)))

            current_time_ms += flight_time
            events.append({"key": char, "event": "keydown", "timestamp_ms": current_time_ms})
            current_time_ms += dwell_time
            events.append({"key": char, "event": "keyup", "timestamp_ms": current_time_ms})
        return events


# Backward-compatible alias
LinguisticKeystrokeDynamicsEngine = KeystrokeCadenceEngine
