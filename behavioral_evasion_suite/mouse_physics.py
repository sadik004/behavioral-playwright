"""
Patch 3: Biomechanical Mouse Physics with Neuromuscular Inertia Filter
Models high-fidelity human cursor movements based on Cubic Bézier curves,
physiological neuromuscular micro-tremors (Colored Pink Noise), and Logarithmic Deceleration.
Enhanced with Windows 1ms High-Resolution Multimedia Timer (winmm.timeBeginPeriod).
"""
import sys
import math
import random
import asyncio
from typing import Any, List, Tuple, Optional, NamedTuple


class WindowsHighResolutionTimer:
    """
    Overrides the default Windows OS 15.6ms timer interrupt tick rate using winmm.timeBeginPeriod(1).
    Ensures 1ms sub-millisecond precision for continuous USB HID polling emulation (125Hz-1000Hz).
    """
    def __init__(self):
        self.is_active = False
        if sys.platform == "win32":
            try:
                import ctypes
                self._winmm = ctypes.windll.winmm
                self._winmm.timeBeginPeriod(1)
                self.is_active = True
            except Exception:
                pass

    def close(self):
        if self.is_active:
            try:
                self._winmm.timeEndPeriod(1)
                self.is_active = False
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MousePoint(NamedTuple):
    x: float
    y: float
    timestamp_delta: float = 0.015


class BiomechanicalMousePhysics:
    """
    Models high-fidelity human cursor movements based on Cubic Bézier curves,
    physiological neuromuscular micro-tremors (Colored Pink Noise), and Logarithmic Deceleration.
    """
    def __init__(self, page: Any = None) -> None:
        self.page = page
        self.timer = WindowsHighResolutionTimer()

    async def human_move_to(
        self, x: float, y: float, steps: int = 30, start: Tuple[float, float] = (100.0, 100.0)
    ) -> None:
        """
        Smoothly moves the mouse to (x, y) on the configured page following
        biomechanical trajectory with sub-millisecond micro-delays.
        """
        if not self.page:
            raise ValueError("Page instance is required for human_move_to")
        trajectory = self.generate_trajectory(start=start, end=(x, y), steps=steps)
        with WindowsHighResolutionTimer():
            for pt in trajectory:
                await self.page.mouse.move(pt.x, pt.y)
                await asyncio.sleep(0.005)

    def generate_trajectory(
        self,
        start: Optional[Tuple[float, float]] = None,
        end: Optional[Tuple[float, float]] = None,
        steps: int = 30,
        start_pos: Optional[Tuple[float, float]] = None,
        target_pos: Optional[Tuple[float, float]] = None,
        duration: Optional[float] = None,
        target_size: Optional[float] = None,
    ) -> List[MousePoint]:
        """
        Creates authentic trajectory coordinate steps with Neuromuscular Inertia and Logarithmic Correction.
        """
        s = start if start is not None else (start_pos if start_pos is not None else (0.0, 0.0))
        e = end if end is not None else (target_pos if target_pos is not None else (100.0, 100.0))
        points: List[MousePoint] = []
        x1, y1 = s
        x2, y2 = e

        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if distance == 0:
            return [MousePoint(x1, y1)]

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

            points.append(MousePoint(curr_x, curr_y))

        # Part 2: Logarithmic Correction (Humans adjusting to target center smoothly)
        correction_steps = 8
        last_x, last_y = points[-1].x, points[-1].y
        for i in range(correction_steps):
            t = (i + 1) / float(correction_steps)
            # Logarithmic deceleration curve
            log_t = 1.0 - math.pow(1.0 - t, 3)

            curr_x = last_x + (x2 - last_x) * log_t
            curr_y = last_y + (y2 - last_y) * log_t
            points.append(MousePoint(curr_x, curr_y))

        return points
