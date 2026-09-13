"""
Patch 3: Biomechanical Mouse Physics with Neuromuscular Inertia Filter
Models high-fidelity human cursor movements based on Cubic Bézier curves,
physiological neuromuscular micro-tremors (Colored Pink Noise), and Logarithmic Deceleration.
"""
import math
import random
from typing import List, Tuple


class BiomechanicalMousePhysics:
    """
    Models high-fidelity human cursor movements based on Cubic Bézier curves,
    physiological neuromuscular micro-tremors (Colored Pink Noise), and Logarithmic Deceleration.
    """
    def __init__(self) -> None:
        pass

    def generate_trajectory(
        self, start: Tuple[float, float], end: Tuple[float, float], steps: int = 30
    ) -> List[Tuple[float, float]]:
        """
        Creates authentic trajectory coordinate steps with Neuromuscular Inertia and Logarithmic Correction.
        """
        points = []
        x1, y1 = start
        x2, y2 = end

        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if distance == 0:
            return [start]

        # Fitts's Law Target Overshoot math
        overshoot_factor = 0.08 if distance > 150 else 0.02
        overshoot_x = x2 + (x2 - x1) * overshoot_factor
        overshoot_y = y2 + (y2 - y1) * overshoot_factor

        # Part 1: Accelerating toward overshoot point with Neuromuscular Inertia
        tremor_prev_x, tremor_prev_y = 0.0, 0.0
        inertia_coefficient = 0.82  # Aligns micro-jitters to model muscle mass damping

        for i in range(steps):
            t = i / float(steps)
            ease_t = 3 * t * t - 2 * t * t * t  # Cubic Bézier acceleration

            curr_x = x1 + (overshoot_x - x1) * ease_t
            curr_y = y1 + (overshoot_y - y1) * ease_t

            # Neuromuscular Colored Noise (Low-pass filtered white noise)
            raw_jitter_x = random.gauss(0, 1.2)
            raw_jitter_y = random.gauss(0, 1.2)

            filtered_jitter_x = (tremor_prev_x * inertia_coefficient) + (raw_jitter_x * (1 - inertia_coefficient))
            filtered_jitter_y = (tremor_prev_y * inertia_coefficient) + (raw_jitter_y * (1 - inertia_coefficient))

            tremor_prev_x, tremor_prev_y = filtered_jitter_x, filtered_jitter_y

            # Add dampening factor near end of deceleration
            scale = max(0.1, (1.0 - t) * 1.5)
            curr_x += filtered_jitter_x * scale
            curr_y += filtered_jitter_y * scale

            points.append((curr_x, curr_y))

        # Part 2: Logarithmic Correction (Humans adjusting to target center smoothly)
        correction_steps = 8
        last_x, last_y = points[-1]
        for i in range(correction_steps):
            t = (i + 1) / float(correction_steps)
            # Logarithmic deceleration curve
            log_t = 1.0 - math.pow(1.0 - t, 3)

            curr_x = last_x + (x2 - last_x) * log_t
            curr_y = last_y + (y2 - last_y) * log_t
            points.append((curr_x, curr_y))

        return points
