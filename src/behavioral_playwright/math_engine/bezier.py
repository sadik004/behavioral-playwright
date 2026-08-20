"""
Cubic Bézier trajectory generator integrated with C1 Smoothstep and Sine Jitter Envelopes.
"""

import math
from typing import List, Tuple

from ..config.domain import MouseConfig
from ..utils.protocols import RandomSource


class BezierTrajectoryGenerator:
    """
    Generates physiological mouse paths utilizing Cubic Bezier mathematics
    integrated with continuous smoothstep velocity profiling and AR(1) tremor process.
    """

    @staticmethod
    def smoothstep(t: float) -> float:
        """Standard smoothstep: f(t) = t^2 * (3 - 2t). C1-continuous bounds."""
        t = max(0.0, min(1.0, t))
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def _calculate_bezier_point(
        p0: Tuple[float, float],
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        t: float,
    ) -> Tuple[float, float]:
        """Calculates exact points along a cubic curve."""
        u = 1.0 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t

        x = uuu * p0[0] + 3.0 * uu * t * p1[0] + 3.0 * u * tt * p2[0] + ttt * p3[0]
        y = uuu * p0[1] + 3.0 * uu * t * p1[1] + 3.0 * u * tt * p2[1] + ttt * p3[1]
        return x, y

    @classmethod
    def generate_path(
        cls,
        start: Tuple[float, float],
        end: Tuple[float, float],
        steps: int,
        config: MouseConfig,
        rng: RandomSource,
    ) -> List[Tuple[float, float]]:
        """Generates continuous coordinates with a Sine envelope dampening start/end tremors to 0.0."""
        if start == end:
            return [start]

        offset_x1 = (end[0] - start[0]) * rng.uniform(config.p1_offset_min, config.p1_offset_max)
        offset_y1 = (end[1] - start[1]) * rng.uniform(config.p1_offset_min, config.p1_offset_max)
        offset_x2 = (end[0] - start[0]) * rng.uniform(config.p2_offset_min, config.p2_offset_max)
        offset_y2 = (end[1] - start[1]) * rng.uniform(config.p2_offset_min, config.p2_offset_max)

        p0 = start
        p1 = (start[0] + offset_x1, start[1] + offset_y1)
        p2 = (start[0] + offset_x2, start[1] + offset_y2)
        p3 = end

        path: List[Tuple[float, float]] = []

        # Physics Tremor Engine: Autoregressive AR(1) process representing neuromuscular micro-tremors
        tremor_x = 0.0
        tremor_y = 0.0
        phi = config.fbm_phi  # AR(1) persistence coefficient

        for i in range(steps):
            t = i / (steps - 1)
            eased_t = cls.smoothstep(t)

            x, y = cls._calculate_bezier_point(p0, p1, p2, p3, eased_t)

            # Sine-shaped tremor envelope: tremor peaks in the middle and dampens to 0 at endpoints
            jitter_envelope = math.sin(t * math.pi)

            # Update AR(1) process with Gaussian white noise
            white_noise_x = rng.gauss(0.0, config.jitter_std)
            white_noise_y = rng.gauss(0.0, config.jitter_std)

            tremor_x = (phi * tremor_x) + white_noise_x
            tremor_y = (phi * tremor_y) + white_noise_y

            jitter_x = tremor_x * jitter_envelope
            jitter_y = tremor_y * jitter_envelope

            path.append((x + jitter_x, y + jitter_y))

        return path
