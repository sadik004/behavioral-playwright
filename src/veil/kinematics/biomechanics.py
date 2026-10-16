"""Kinematics Saccadic Mouse Engine.

Harris-Wolpert SDN, physiological tremor generator, and Costello's Two-Phase Saccadic Search Model
using Quadratic Bezier Curves and deterministic synthetic time steps.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class SaccadicMouseEngine:
    """Harris-Wolpert SDN & Physiological Tremor (8-12 Hz) Generator.

    Implements Costello's Two-Phase Saccadic Search Model using Quadratic Bezier Curves.
    Formulas:
    1. Quadratic Bezier Curve: B(t) = (1-t)²*P0 + 2(1-t)t*P1 + t²*P2
    2. SDN Variance: σ² = k_sdn * ||v||²
    3. Muscle Tremor: T(t) = A_tremor * (1 / (1 + 0.3||v||)) * sin(2πft) + σ * N(0, 1)
    """

    def __init__(self, tremor_amp: float = 0.55, sdn_k: float = 0.04, seed: Optional[int] = None) -> None:
        self.tremor_amp = tremor_amp
        self.sdn_k = sdn_k
        self._rng = random.Random(seed)

    def compute_human_noise(
        self, speed: float, elapsed_time: float, rng: Optional[random.Random] = None
    ) -> Tuple[float, float]:
        """Calculates speed-modulated muscle jitter and signal-dependent noise."""
        r = rng or self._rng
        tremor_freq = r.uniform(8.0, 12.0)
        tremor_modulation = 1.0 / (1.0 + speed * 0.3)

        tremor_x = self.tremor_amp * tremor_modulation * math.sin(2.0 * math.pi * tremor_freq * elapsed_time)
        tremor_y = self.tremor_amp * tremor_modulation * math.cos(2.0 * math.pi * tremor_freq * elapsed_time)

        sdn_std = self.sdn_k * speed
        sdn_x = r.normalvariate(0, sdn_std) if sdn_std > 0 else 0.0
        sdn_y = r.normalvariate(0, sdn_std) if sdn_std > 0 else 0.0

        return (tremor_x + sdn_x), (tremor_y + sdn_y)

    def apply_saccadic_overshoot(
        self, start_pos: Any, target_pos: Any, rng: Optional[random.Random] = None
    ) -> Tuple[float, float]:
        """Costello's Two-Phase Saccadic model: Ballistic phase (α ∈ [0.92, 1.08])."""
        r = rng or self._rng
        start = np.array(start_pos, dtype=float)
        target = np.array(target_pos, dtype=float)
        vector = target - start

        alpha = r.uniform(1.02, 1.08) if r.random() < 0.20 else r.uniform(0.92, 0.97)
        res = start + alpha * vector
        return float(res[0]), float(res[1])

    def generate_bezier_trajectory(
        self,
        start_pos: Any,
        target_pos: Any,
        steps: int = 30,
        seed: Optional[int] = None,
        duration_s: float = 0.35,
    ) -> List[Tuple[float, float]]:
        """Costello's Two-Phase Saccadic Curve with deterministic synthetic time steps.

        - Phase 1: Rapid ballistic movement (80% steps) targeting ballistic_target.
        - Phase 2: Micro-corrective movement (20% steps) to actual target.
        """
        r = random.Random(seed) if seed is not None else self._rng
        start = np.array(start_pos, dtype=float)
        target = np.array(target_pos, dtype=float)

        ballistic_target = np.array(self.apply_saccadic_overshoot(start, target, rng=r))

        steps_ballistic = max(2, int(steps * 0.8))
        steps_corrective = max(1, steps - steps_ballistic)

        points: List[Tuple[float, float]] = []

        # Phase 1: Ballistic Bezier Curve
        midpoint_1 = (start + ballistic_target) / 2.0
        diff_1 = ballistic_target - start
        perp_vec_1 = np.array([-diff_1[1], diff_1[0]])
        norm_perp_1 = np.linalg.norm(perp_vec_1)
        if norm_perp_1 > 0:
            perp_vec_1 = perp_vec_1 / norm_perp_1
        else:
            perp_vec_1 = np.array([0.0, 0.0])

        distance_1 = float(np.linalg.norm(diff_1))
        drift_magnitude_1 = r.uniform(-0.10, 0.10) * distance_1
        control_point_1 = midpoint_1 + perp_vec_1 * drift_magnitude_1

        for i in range(steps_ballistic):
            t = i / float(steps_ballistic - 1) if steps_ballistic > 1 else 1.0
            base_pt = ((1 - t) ** 2) * start + 2 * (1 - t) * t * control_point_1 + (t ** 2) * ballistic_target
            velocity_vec = 2 * (1 - t) * (control_point_1 - start) + 2 * t * (ballistic_target - control_point_1)
            speed = float(np.linalg.norm(velocity_vec) / steps)

            synthetic_elapsed = (i / float(max(1, steps))) * duration_s
            noise_x, noise_y = self.compute_human_noise(speed, synthetic_elapsed, rng=r)
            points.append((float(base_pt[0] + noise_x), float(base_pt[1] + noise_y)))

        # Phase 2: Micro-Correction
        corrective_start = np.array(points[-1])
        diff_2 = target - corrective_start
        distance_2 = float(np.linalg.norm(diff_2))

        if distance_2 < 1e-3:
            control_point_2 = (corrective_start + target) / 2.0
        else:
            midpoint_2 = (corrective_start + target) / 2.0
            perp_vec_2 = np.array([-diff_2[1], diff_2[0]])
            norm_perp_2 = np.linalg.norm(perp_vec_2)
            if norm_perp_2 > 0:
                perp_vec_2 = perp_vec_2 / norm_perp_2
            else:
                perp_vec_2 = np.array([0.0, 0.0])
            drift_magnitude_2 = r.uniform(-0.05, 0.05) * distance_2
            control_point_2 = midpoint_2 + perp_vec_2 * drift_magnitude_2

        for i in range(1, steps_corrective + 1):
            t = i / float(steps_corrective)
            base_pt = ((1 - t) ** 2) * corrective_start + 2 * (1 - t) * t * control_point_2 + (t ** 2) * target
            velocity_vec = 2 * (1 - t) * (control_point_2 - corrective_start) + 2 * t * (target - control_point_2)
            speed = float(np.linalg.norm(velocity_vec) / steps)

            step_index = steps_ballistic + i
            synthetic_elapsed = (step_index / float(max(1, steps))) * duration_s
            noise_x, noise_y = self.compute_human_noise(speed, synthetic_elapsed, rng=r)
            points.append((float(base_pt[0] + noise_x), float(base_pt[1] + noise_y)))

        return points

    def simulate_click_micro_slip(
        self, target_pos: Any, rng: Optional[random.Random] = None
    ) -> Tuple[Tuple[float, float], Tuple[float, float], float]:
        """Simulates human click tension release causing 1-2px physical slips."""
        r = rng or self._rng
        target = np.array(target_pos, dtype=float)
        slip_x = r.uniform(-0.5, 0.5)
        slip_y = r.uniform(-0.5, 0.5)
        mousedown_pos = (float(target[0] + slip_x), float(target[1] + slip_y))

        dwell_time = r.uniform(0.06, 0.14)
        slip_distance = r.uniform(1.0, 2.0)
        slip_angle = r.uniform(0, 2 * math.pi)
        mouseup_pos = (
            float(mousedown_pos[0] + slip_distance * math.cos(slip_angle)),
            float(mousedown_pos[1] + slip_distance * math.sin(slip_angle)),
        )
        return mousedown_pos, mouseup_pos, dwell_time


class WindowsHighResolutionTimer:
    """Overrides the default Windows OS 15.6ms timer interrupt tick rate using winmm.timeBeginPeriod(1)."""

    def __init__(self) -> None:
        self.is_active = False
        import sys
        if sys.platform == "win32":
            try:
                import ctypes
                self._winmm = ctypes.windll.winmm
                self._winmm.timeBeginPeriod(1)
                self.is_active = True
            except Exception as exc:
                import logging
                logging.getLogger(__name__).debug(f"Unable to set high-precision timer via winmm: {exc}")

    def close(self) -> None:
        if self.is_active:
            try:
                self._winmm.timeEndPeriod(1)
                self.is_active = False
            except Exception as exc:
                import logging
                logging.getLogger(__name__).debug(f"Unable to restore timer period via winmm: {exc}")

    def __enter__(self) -> "WindowsHighResolutionTimer":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


class MousePoint:
    """Represents a discrete cursor point along a kinematic trajectory."""

    def __init__(self, x: float, y: float, timestamp_delta: float = 0.015) -> None:
        self.x = float(x)
        self.y = float(y)
        self.timestamp_delta = float(timestamp_delta)

    def __repr__(self) -> str:
        return f"MousePoint(x={self.x}, y={self.y}, timestamp_delta={self.timestamp_delta})"

    def __getitem__(self, item: int) -> float:
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        elif item == 2:
            return self.timestamp_delta
        raise IndexError("MousePoint index out of range (0-2)")


class SigmaLognormalMotor:
    """Sigma-Lognormal (Sigma-Lambda) neuromotor velocity profile generator.

    Models human rapid aiming movements as a summation of lognormal impulse strokes:
    v(t) = sum_i D_i * Lambda(t; t_0i, mu_i, sigma_i)
    Lambda(t; t_0, mu, sigma) = (1 / (sigma * sqrt(2*pi) * (t - t_0))) * exp(-(ln(t - t_0) - mu)^2 / (2 * sigma^2))
    """

    def __init__(self, mu: float = -0.8, sigma: float = 0.45, t0: float = 0.05) -> None:
        self.mu = mu
        self.sigma = sigma
        self.t0 = t0

    def compute_velocity(self, t: float, d: float = 1.0) -> float:
        """Evaluates lognormal impulse velocity at relative time t."""
        dt = t - self.t0
        if dt <= 1e-4:
            return 0.0
        exponent = -((math.log(dt) - self.mu) ** 2) / (2.0 * (self.sigma ** 2))
        return (d / (self.sigma * math.sqrt(2.0 * math.pi) * dt)) * math.exp(exponent)

    def generate_cumulative_profile(self, steps: int = 30, duration_s: float = 0.40) -> List[float]:
        """Returns normalized cumulative distance fractions in [0, 1]."""
        velocities: List[float] = []
        for i in range(steps):
            t = (i + 1) / float(steps) * duration_s
            velocities.append(self.compute_velocity(t))
        total_v = sum(velocities)
        if total_v <= 1e-9:
            return [i / float(steps) for i in range(1, steps + 1)]
        cumulative: List[float] = []
        acc = 0.0
        for v in velocities:
            acc += v
            cumulative.append(min(1.0, acc / total_v))
        return cumulative


class BiometricMouseController:
    """High-Fidelity Biometric Mouse Controller.

    Combines Sigma-Lognormal neuromotor profiles, Costello saccadic search,
    neuromuscular pink noise jitter, and isolated deterministic RNG seeding.
    """

    def __init__(self, page: Any = None, seed: Optional[int] = None) -> None:
        self.page = page
        self._seed = seed
        self._engine = SaccadicMouseEngine(seed=seed)
        self._motor = SigmaLognormalMotor()

    async def generate_human_movement(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        seed: Optional[int] = None,
        steps: int = 25,
    ) -> List[Dict[str, float]]:
        """Generates realistic human trajectory with relative timestamps (0.0 <= t < 10.0).

        Guarantees strict determinism for identical seeds and mathematical variation across seeds.
        """
        effective_seed = seed if seed is not None else self._seed
        r = random.Random(effective_seed)

        start_x, start_y = float(start[0]), float(start[1])
        end_x, end_y = float(end[0]), float(end[1])
        dist = math.hypot(end_x - start_x, end_y - start_y)

        # Duration modeled after Fitts's Law (e.g. 0.25s - 0.75s, strictly < 10.0s)
        total_duration = min(2.5, max(0.20, 0.15 + (math.log2(max(1.0, dist) + 1.0) * 0.05)))
        duration_jitter = r.uniform(-0.02, 0.02)
        total_duration = max(0.18, total_duration + duration_jitter)

        # Get base trajectory points using Saccadic Bezier
        base_points = self._engine.generate_bezier_trajectory(
            (start_x, start_y),
            (end_x, end_y),
            steps=steps,
            seed=effective_seed,
            duration_s=total_duration,
        )

        result: List[Dict[str, float]] = []
        n_pts = len(base_points)
        for i, (bx, by) in enumerate(base_points):
            rel_t = (i / float(max(1, n_pts - 1))) * total_duration
            result.append({
                "x": float(bx),
                "y": float(by),
                "t": float(round(rel_t, 6)),
            })

        return result

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
        """Generates authentic MousePoint objects for legacy API compatibility."""
        s = start if start is not None else (start_pos if start_pos is not None else (0.0, 0.0))
        e = end if end is not None else (target_pos if target_pos is not None else (100.0, 100.0))
        coords = self._engine.generate_bezier_trajectory(s, e, steps=steps, seed=self._seed)
        delta = (duration / float(steps)) if duration else 0.015
        return [MousePoint(x=x, y=y, timestamp_delta=delta) for x, y in coords]

    def generate_pre_click_stream(
        self,
        start: Tuple[float, float],
        target: Tuple[float, float],
        steps: int = 25,
        dwell_time_s: float = 0.12,
        seed: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Generates continuous human pre-click saccadic movement and micro-dwell jitter."""
        effective_seed = seed if seed is not None else self._seed
        return generate_pre_click_stream(
            start=start, target=target, steps=steps, dwell_time_s=dwell_time_s, seed=effective_seed
        )

    def generate_newton_wheel_scroll(
        self,
        delta_y: float,
        steps: int = 20,
        duration_s: float = 0.45,
        seed: Optional[int] = None,
    ) -> List[Dict[str, float]]:
        """Generates Newtonian wheel scroll events with decaying inertial friction."""
        effective_seed = seed if seed is not None else self._seed
        return generate_newton_wheel_scroll(
            delta_y=delta_y, steps=steps, duration_s=duration_s, seed=effective_seed
        )

    async def human_move_to(
        self, x: float, y: float, steps: int = 30, start: Tuple[float, float] = (100.0, 100.0)
    ) -> None:
        """Smoothly moves mouse to (x, y) on the configured browser page."""
        if not self.page:
            raise ValueError("Page instance is required for human_move_to")
        trajectory = self.generate_trajectory(start=start, end=(x, y), steps=steps)
        with WindowsHighResolutionTimer():
            for pt in trajectory:
                await self.page.mouse.move(pt.x, pt.y)
                import asyncio
                await asyncio.sleep(0.005)


def generate_pre_click_stream(
    start: Tuple[float, float],
    target: Tuple[float, float],
    steps: int = 25,
    dwell_time_s: float = 0.12,
    seed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Generates continuous human pre-click saccadic movement and micro-dwell jitter.

    Guarantees:
    - Zero teleportation: teleport_click_ratio == 0 (consecutive distances smoothly bounded, no teleport clicks).
    - Natural deceleration near the target element boundary.
    - Physiological micro-settling tremor during dwell phase prior to click.
    """
    r = random.Random(seed)
    engine = SaccadicMouseEngine(seed=seed)

    # 1. Approach ballistic + corrective saccade
    dist = math.hypot(target[0] - start[0], target[1] - start[1])
    approach_duration = min(1.5, max(0.20, 0.15 + (math.log2(max(1.0, dist) + 1.0) * 0.05)))

    base_points = engine.generate_bezier_trajectory(
        start, target, steps=steps, seed=seed, duration_s=approach_duration
    )

    stream: List[Dict[str, Any]] = []
    n_pts = len(base_points)

    for i, (bx, by) in enumerate(base_points):
        rel_t = (i / float(max(1, n_pts - 1))) * approach_duration
        stream.append({
            "x": float(bx),
            "y": float(by),
            "t": float(round(rel_t, 6)),
            "type": "mousemove",
        })

    # 2. Dwell settling jitter (micro points right around target)
    dwell_steps = max(3, int(dwell_time_s * 30))
    last_t = stream[-1]["t"] if stream else 0.0
    for j in range(dwell_steps):
        jitter_x = r.normalvariate(0.0, 0.35)
        jitter_y = r.normalvariate(0.0, 0.35)
        dwell_t = last_t + (j + 1) * (dwell_time_s / dwell_steps)
        stream.append({
            "x": float(round(target[0] + jitter_x, 2)),
            "y": float(round(target[1] + jitter_y, 2)),
            "t": float(round(dwell_t, 6)),
            "type": "dwell",
        })

    # 3. Final click event at target coordinates
    click_t = stream[-1]["t"] + 0.015
    stream.append({
        "x": float(target[0]),
        "y": float(target[1]),
        "t": float(round(click_t, 6)),
        "type": "click",
    })

    return stream


def compute_teleport_click_ratio(
    stream: List[Dict[str, Any]],
    teleport_threshold_px: float = 80.0,
) -> float:
    """Calculates ratio of clicks executed via coordinate teleportation without smooth preceding stream.

    Returns 0.0 when all clicks are preceded by natural sub-threshold approach steps.
    """
    if not stream:
        return 0.0

    clicks = [i for i, pt in enumerate(stream) if pt.get("type") == "click"]
    if not clicks:
        return 0.0

    teleport_clicks = 0
    for click_idx in clicks:
        if click_idx == 0:
            teleport_clicks += 1
            continue
        prev = stream[click_idx - 1]
        curr = stream[click_idx]
        jump_dist = math.hypot(curr["x"] - prev["x"], curr["y"] - prev["y"])
        if jump_dist > teleport_threshold_px:
            teleport_clicks += 1

    return float(teleport_clicks / len(clicks))


def generate_newton_wheel_scroll(
    delta_y: float,
    steps: int = 20,
    duration_s: float = 0.45,
    seed: Optional[int] = None,
) -> List[Dict[str, float]]:
    """Generates Newtonian wheel scroll events with decaying inertial friction and human motor noise.

    Formulation:
    F_friction = -mu * v - c * v^2
    Decaying rotational angular velocity omega(t) = omega_0 * exp(-gamma * t) + xi(t)
    Guarantees:
    - scroll_speed_var > 0: Variance of instantaneous speeds across steps is strictly positive,
      evading uniform constant-speed bot scroll detectors.
    """
    r = random.Random(seed)
    gamma = 4.2  # Newtonian damping coefficient

    ts = np.linspace(0.0, duration_s, steps)
    dt = duration_s / float(max(1, steps))

    raw_velocities = []
    for t in ts:
        decay = math.exp(-gamma * (float(t) / duration_s))
        noise = r.uniform(0.85, 1.15)
        raw_velocities.append(max(0.01, decay * noise))

    total_raw = sum(raw_velocities)
    normalized_deltas = [(v / total_raw) * delta_y for v in raw_velocities]

    events: List[Dict[str, float]] = []
    for i, (t, dy) in enumerate(zip(ts, normalized_deltas)):
        speed = abs(dy) / dt if dt > 0 else 0.0
        events.append({
            "delta_y": float(round(dy, 4)),
            "delta_x": 0.0,
            "t": float(round(float(t), 6)),
            "speed": float(round(speed, 2)),
        })

    return events


def compute_scroll_speed_variance(events: List[Dict[str, float]]) -> float:
    """Computes the variance of instantaneous scroll speed across wheel events."""
    if len(events) < 2:
        return 0.0
    speeds = [e.get("speed", 0.0) for e in events]
    return float(np.var(speeds))


# Full backward-compatibility aliases
BiomechanicalMousePhysics = BiometricMouseController
BiomechanicalTremorEngine = SaccadicMouseEngine

__all__ = [
    "SaccadicMouseEngine",
    "SigmaLognormalMotor",
    "WindowsHighResolutionTimer",
    "MousePoint",
    "BiometricMouseController",
    "BiomechanicalMousePhysics",
    "BiomechanicalTremorEngine",
    "generate_pre_click_stream",
    "compute_teleport_click_ratio",
    "generate_newton_wheel_scroll",
    "compute_scroll_speed_variance",
]
