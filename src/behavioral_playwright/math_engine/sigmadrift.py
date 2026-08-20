"""
Sigma-lognormal velocity profiling, Fitts's Law, Ornstein-Uhlenbeck drift, and Signal-Dependent Noise.
"""

import math
from typing import List, Tuple

from ..config.domain import MouseConfig
from ..utils.protocols import RandomSource


class SigmaDriftTrajectoryGenerator:
    """
    Constructs trajectories from six motor control foundations:
    1. Sigma-lognormal velocity primitives.
    2. Two-phase surge architecture.
    3. Ornstein-Uhlenbeck (OU) lateral drift.
    4. Signal-Dependent Noise (SDN).
    5. Speed-modulated physiological hand tremor.
    6. Gamma-distributed timing.
    """

    @staticmethod
    def lognormal_cdf(t: float, t0: float, mu: float, sigma: float) -> float:
        if t <= t0:
            return 0.0
        try:
            val = (math.log(t - t0) - mu) / (sigma * math.sqrt(2.0))
            return 0.5 * (1.0 + math.erf(val))
        except (ValueError, ZeroDivisionError):
            return 0.0

    @classmethod
    def generate_biomechanical_path(
        cls,
        start: Tuple[float, float],
        end: Tuple[float, float],
        config: MouseConfig,
        rng: RandomSource,
    ) -> List[Tuple[float, float, float]]:  # Returns (x, y, timestamp_ms)
        x0, y0 = start
        x1, y1 = end
        distance = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
        if distance == 0:
            return [(x0, y0, 0.0)]

        # Fitts' Law movement duration (MT) in ms
        fitts_pred = config.fitts_a + config.fitts_b * math.log2(distance / config.target_width + 1.0)
        mt = fitts_pred * math.exp(rng.gauss(0.0, 0.08))  # trial-to-trial lognormal CV of 8%

        # Undertarget / Overtarget reach fractions
        overshoot = rng.random() < 0.15
        reach = rng.uniform(1.02, 1.08) if overshoot else rng.uniform(0.92, 0.97)
        primary_d = distance * reach

        # Lognormal mode peaking at 35% of MT
        mode = mt * 0.35
        primary_sigma = 0.25
        primary_mu = math.log(mode) + (primary_sigma**2)

        path: List[Tuple[float, float, float]] = []
        tx = (x1 - x0) / distance
        ty = (y1 - y0) / distance

        # Lateral drift process and tremor parameters
        ou_x = 0.0
        ou_y = 0.0
        phase_x = rng.uniform(0, 2 * math.pi)

        t = 0.0
        while t < mt:
            s = cls.lognormal_cdf(t, 0.0, primary_mu, primary_sigma)
            bx = x0 + tx * primary_d * s
            by = y0 + ty * primary_d * s

            # Inject corrective sub-movement
            if not overshoot and s > 0.95:
                corr_s = cls.lognormal_cdf(t, mt * 0.8, math.log(mt * 0.1), 0.15)
                bx += tx * (distance - primary_d) * corr_s
                by += ty * (distance - primary_d) * corr_s

            # Direction dependent curvature
            perp_x = -ty
            perp_y = tx
            angle = math.atan2(ty, tx)
            sa = abs(math.sin(angle))
            ca = abs(math.cos(angle))
            direction_factor = 0.5 + 0.8 * sa - 0.15 * ca
            curvature_amplitude = distance * 0.025 * direction_factor * rng.gauss(0, 1)

            curve_profile = 0.0
            if 0.0 < s < 1.0:
                v = s * s * (1.0 - s) * (1.0 - s) * (1.0 - s)
                norm = 0.4 * 0.4 * 0.6 * 0.6 * 0.6
                curve_profile = v / norm

            bx += perp_x * curvature_amplitude * curve_profile
            by += perp_y * curvature_amplitude * curve_profile

            # Gamma distributed interval (standard hardware rate of ~125Hz polling)
            dt = rng.gamma(config.gamma_shape, config.gamma_scale)
            dt_s = dt / 1000.0

            # Ornstein-Uhlenbeck (OU) lateral drift
            ou_x += -config.ou_theta * ou_x * dt_s + config.ou_sigma * math.sqrt(dt_s) * rng.gauss(0.0, 1.0)
            ou_y += -config.ou_theta * ou_y * dt_s + config.ou_sigma * math.sqrt(dt_s) * rng.gauss(0.0, 1.0)

            # Velocity calculations for physiological gain suppression
            if t > 0:
                prev_s = cls.lognormal_cdf(t - dt, 0.0, primary_mu, primary_sigma)
                speed = abs(s - prev_s) * primary_d / (dt_s * 1000.0)
            else:
                speed = 0.0

            # Speed-modulated Tremor
            trem_mod = 1.0 / (1.0 + speed * 0.3)
            tremor_amp = config.tremor_amp_max * trem_mod
            tr_x = tremor_amp * math.sin(2.0 * math.pi * config.tremor_freq * (t / 1000.0) + phase_x)
            tr_y = tremor_amp * math.sin(2.0 * math.pi * config.tremor_freq * (t / 1000.0) + phase_x + 1.5)

            # Signal Dependent Noise (SDN)
            sdn_x = config.sdn_k * speed * rng.gauss(0.0, 1.0)
            sdn_y = config.sdn_k * speed * rng.gauss(0.0, 1.0)

            path.append((bx + ou_x + tr_x + sdn_x, by + ou_y + tr_y + sdn_y, t))
            t += dt

        path.append((x1, y1, mt))
        return path
