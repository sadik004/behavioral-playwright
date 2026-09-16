"""
Cognitive Gaze Physics - Level 5 Quantum Edition
Newtonian Inertial Scroll & Cognitive Reading Pause Engine.
Counters Behavioral AI Kinematic Analysis and Bot Saccadic Anomaly Detectors.
"""

import math
import random
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger("BehavioralEvasion.CognitiveGazePhysics")


class ScrollTrajectoryPoint(BaseModel):
    """Single discrete displacement delta in inertial scroll stream."""
    delta_y: float
    delay_ms: float


class GazePhysicsConfig(BaseModel):
    """Configuration schema for Newtonian inertial scroll physics."""
    friction_coefficient: float = Field(default=0.92, ge=0.5, le=0.99)
    mass: float = Field(default=1.2, ge=0.5, le=5.0)
    min_step_delay_ms: float = Field(default=12.0, ge=4.0)
    max_step_delay_ms: float = Field(default=28.0, le=100.0)


class CognitiveGazePhysics:
    """
    Computes human-realistic physical trajectories incorporating Newtonian momentum,
    viscous drag, and foveal gaze fixation pauses.
    """

    def __init__(self, config: Optional[GazePhysicsConfig] = None):
        self.config = config or GazePhysicsConfig()

    def generate_inertial_scroll_steps(
        self,
        distance_y: float,
        target_duration_ms: Optional[float] = None
    ) -> List[ScrollTrajectoryPoint]:
        """
        Calculates Newtonian deceleration curve for mouse wheel / touch scroll events.
        v(t) = v0 * exp(-gamma * t) with micro-tremor perturbations.
        """
        if abs(distance_y) < 1.0:
            return []

        direction = 1.0 if distance_y > 0 else -1.0
        remaining = abs(distance_y)

        steps: List[ScrollTrajectoryPoint] = []
        # Estimate initial velocity based on distance
        v = math.sqrt(2.0 * remaining * (1.0 - self.config.friction_coefficient) * 100.0) + 15.0
        gamma = (1.0 - self.config.friction_coefficient) * 1.5

        elapsed_ms = 0.0
        while remaining > 2.0:
            step_dt = random.uniform(self.config.min_step_delay_ms, self.config.max_step_delay_ms)
            # Velocity decay with drag
            v *= math.exp(-gamma * (step_dt / 16.67))

            # Micro-tremor perturbation (hand tremor on wheel)
            jitter = random.gauss(1.0, 0.08)
            displacement = max(1.0, v * (step_dt / 16.67) * jitter)

            if displacement > remaining:
                displacement = remaining

            steps.append(ScrollTrajectoryPoint(
                delta_y=round(direction * displacement, 2),
                delay_ms=round(step_dt, 1)
            ))
            remaining -= displacement
            elapsed_ms += step_dt

            if len(steps) > 80:
                # Append final settle step
                if remaining > 0:
                    steps.append(ScrollTrajectoryPoint(
                        delta_y=round(direction * remaining, 2),
                        delay_ms=20.0
                    ))
                break

        return steps


async def cognitive_reading_pause(min_ms: float = 350.0, max_ms: float = 1400.0):
    """
    Simulates foveal visual processing fixation pause using log-normal latency distribution.
    """
    mu = math.log((min_ms + max_ms) / 2.0)
    sigma = 0.35
    duration_ms = random.lognormvariate(mu, sigma)
    clamped_ms = max(min_ms, min(max_ms * 1.5, duration_ms))
    logger.debug(f"Cognitive reading pause: {clamped_ms:.1f}ms")
    await asyncio.sleep(clamped_ms / 1000.0)


async def human_scroll(page, target_y: int, max_speed: float = 800.0, duration_ms: Optional[int] = None):
    """
    Dispatches physically authentic Newtonian inertial scroll events to a Playwright page.
    """
    try:
        current_y = 0
        if hasattr(page, "evaluate"):
            try:
                current_y = await page.evaluate("() => window.scrollY || window.pageYOffset || 0")
            except Exception:
                current_y = 0

        distance = target_y - current_y
        physics = CognitiveGazePhysics()
        steps = physics.generate_inertial_scroll_steps(float(distance), target_duration_ms=duration_ms)

        if hasattr(page, "mouse") and hasattr(page.mouse, "wheel"):
            for step in steps:
                try:
                    await page.mouse.wheel(0, step.delta_y)
                    await asyncio.sleep(step.delay_ms / 1000.0)
                except Exception:
                    pass
        elif hasattr(page, "evaluate"):
            for step in steps:
                try:
                    await page.evaluate(f"window.scrollBy(0, {step.delta_y})")
                    await asyncio.sleep(step.delay_ms / 1000.0)
                except Exception:
                    pass

        # Brief cognitive reading pause after scrolling into view
        await cognitive_reading_pause(200.0, 500.0)
        logger.info(f"Human inertial scroll dispatched: {current_y} -> {target_y} ({len(steps)} steps)")
    except Exception as e:
        logger.warning(f"human_scroll fallback triggered: {e}")
