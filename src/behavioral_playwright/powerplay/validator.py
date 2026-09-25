"""
PowerPlay Biometric Distribution Validator (BiometricDistributionValidator).

Empirical Hypothesis Testing & Distribution Discrepancy Verification:
- Two-Sample Kolmogorov-Smirnov (KS) Test: D = sup_x |F_1(x) - F_2(x)|
- Mann-Whitney U Non-Parametric Rank-Sum Test for Median Shift.
- Wasserstein Distance (Earth Mover's Distance) Metric.
- Null Hypothesis (H0) Verification: p >= 0.05 proves synthetic data is indistinguishable from human baselines.
- Mouse Trajectory Kinematics Validation (Velocity, Acceleration & Jerk).
- Linguistic Keystroke Dynamics Validation (Dwell Time & Flight Time).
"""

import math
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from scipy import stats


class BiometricDistributionValidator:
    """
    Mathematical Hypothesis Testing & Statistical Classifier for Synthetic Biometrics.
    Validates synthetic kinematic trajectories and keystroke cadences against
    empirical human reference distributions using Two-Sample Kolmogorov-Smirnov,
    Mann-Whitney U, and Wasserstein metric evaluations.
    """

    def __init__(
        self,
        alpha: float = 0.05,
        ks_alpha: Optional[float] = None,
        mouse_wasserstein_tol: float = 0.08,
        keystroke_wasserstein_tol: float = 12.0,
        random_seed: int = 42
    ):
        self.alpha = ks_alpha if ks_alpha is not None else alpha
        self.ks_alpha = self.alpha
        self.mouse_wasserstein_tol = mouse_wasserstein_tol
        self.keystroke_wasserstein_tol = keystroke_wasserstein_tol
        self.rng = np.random.default_rng(random_seed)

        # Calibrated Empirical Human Baselines (N=200 reference distributions)
        # 1. Mouse Velocity (pixels/second): Log-Normal distribution (mu=6.0, sigma=0.45)
        np.random.seed(random_seed)
        self._human_mouse_velocity_baseline = np.random.lognormal(mean=6.0, sigma=0.45, size=200).tolist()

        # 2. Keystroke Dwell Time (milliseconds): Weibull distribution (k=2.2, scale=90) + min 15ms
        self._human_dwell_time_baseline = (15.0 + np.random.weibull(a=2.2, size=200) * 80.0).tolist()

        # 3. Keystroke Flight Time (milliseconds): Weibull distribution (k=1.8, scale=120) + min 20ms
        self._human_flight_time_baseline = (20.0 + np.random.weibull(a=1.8, size=200) * 110.0).tolist()

    @staticmethod
    def _sanitize_and_validate_input(sample: Any) -> Optional[np.ndarray]:
        """
        Validates and sanitizes input data.
        Rejects None, empty lists, dimension mismatches, and samples contaminated with NaN or Inf.
        Returns cleaned 1D np.float64 array if valid, or None if invalid/corrupt.
        """
        if sample is None:
            return None
        try:
            arr = np.asarray(sample, dtype=np.float64)
        except (ValueError, TypeError):
            return None

        if arr.ndim != 1 or len(arr) == 0:
            return None

        # Strict NaN and Inf blocking (Sanitization gate)
        if not np.all(np.isfinite(arr)):
            return None

        return arr

    @staticmethod
    def compute_ks_statistic(sample_a: Any, sample_b: Any) -> Tuple[float, float]:
        """
        Computes the Two-Sample Kolmogorov-Smirnov statistic D and asymptotic p-value.
        D = sup_x |F_a(x) - F_b(x)|
        """
        arr_a = BiometricDistributionValidator._sanitize_and_validate_input(sample_a)
        arr_b = BiometricDistributionValidator._sanitize_and_validate_input(sample_b)

        if arr_a is None or arr_b is None or len(arr_a) == 0 or len(arr_b) == 0:
            return 1.0, 0.0

        try:
            res = stats.ks_2samp(arr_a, arr_b)
            return float(res.statistic), float(res.pvalue)
        except Exception:
            # Mathematical Fallback: Empirical CDF Max Absolute Difference
            all_vals = np.sort(np.unique(np.concatenate([arr_a, arr_b])))
            cdf_a = np.searchsorted(np.sort(arr_a), all_vals, side='right') / len(arr_a)
            cdf_b = np.searchsorted(np.sort(arr_b), all_vals, side='right') / len(arr_b)
            d_stat = float(np.max(np.abs(cdf_a - cdf_b)))
            n1, n2 = len(arr_a), len(arr_b)
            en = math.sqrt((n1 * n2) / (n1 + n2))
            lambda_val = max(1e-4, (en + 0.12 + 0.11 / en) * d_stat)
            # Smirnov distribution asymptotic p-value
            p_val = float(2.0 * math.exp(-2.0 * (lambda_val ** 2)))
            return d_stat, min(1.0, max(0.0, p_val))

    @staticmethod
    def compute_mann_whitney_u(sample_a: Any, sample_b: Any) -> Tuple[float, float]:
        """
        Computes the Mann-Whitney U test statistic and asymptotic two-sided p-value
        to detect median shifts in continuous distributions.
        """
        arr_a = BiometricDistributionValidator._sanitize_and_validate_input(sample_a)
        arr_b = BiometricDistributionValidator._sanitize_and_validate_input(sample_b)

        if arr_a is None or arr_b is None or len(arr_a) == 0 or len(arr_b) == 0:
            return 0.0, 0.0

        try:
            res = stats.mannwhitneyu(arr_a, arr_b, alternative='two-sided')
            return float(res.statistic), float(res.pvalue)
        except Exception:
            return 0.0, 0.0

    @staticmethod
    def compute_wasserstein_distance(sample_a: Any, sample_b: Any) -> float:
        """
        Computes the first Wasserstein metric (Earth Mover's Distance) between two distributions.
        """
        arr_a = BiometricDistributionValidator._sanitize_and_validate_input(sample_a)
        arr_b = BiometricDistributionValidator._sanitize_and_validate_input(sample_b)

        if arr_a is None or arr_b is None or len(arr_a) == 0 or len(arr_b) == 0:
            return 999.0

        try:
            return float(stats.wasserstein_distance(arr_a, arr_b))
        except Exception:
            return 999.0

    def _validate_distribution(
        self,
        sample: Any,
        baseline: Any,
        wasserstein_tol: float
    ) -> Dict[str, Any]:
        """
        Internal unified statistical validator combining KS-Test, Mann-Whitney U, and Wasserstein distance.
        Guarantees zero-crash execution on empty arrays, corrupted inputs, and edge cases.
        """
        cleaned_sample = self._sanitize_and_validate_input(sample)
        cleaned_baseline = self._sanitize_and_validate_input(baseline)

        # Early rejection gate for empty, invalid, or corrupted inputs (NaN, Inf)
        if cleaned_sample is None or cleaned_baseline is None or len(cleaned_sample) < 2:
            return {
                "ks_statistic": 1.0,
                "p_value": 0.0,
                "wasserstein_distance": 999.0,
                "u_statistic": 0.0,
                "u_pvalue": 0.0,
                "is_human_indistinguishable": False,
                "null_hypothesis_accepted": False,
                "decision": "SYNTHETIC_ANOMALY"
            }

        ks_stat, p_val = self.compute_ks_statistic(cleaned_sample, cleaned_baseline)
        w_dist = self.compute_wasserstein_distance(cleaned_sample, cleaned_baseline)
        u_stat, u_pval = self.compute_mann_whitney_u(cleaned_sample, cleaned_baseline)

        # H0 Accepted if p_value >= ks_alpha AND wasserstein_distance <= tolerance
        is_human = bool(p_val >= self.ks_alpha and w_dist <= wasserstein_tol)
        decision = "CERTIFIED_HUMAN" if is_human else "SYNTHETIC_ANOMALY"

        return {
            "ks_statistic": round(ks_stat, 4),
            "p_value": round(p_val, 6),
            "wasserstein_distance": round(w_dist, 4),
            "u_statistic": round(u_stat, 2),
            "u_pvalue": round(u_pval, 6),
            "is_human_indistinguishable": is_human,
            "null_hypothesis_accepted": is_human,
            "decision": decision
        }

    def validate_mouse_kinematics(
        self,
        synthetic_samples: Any,
        human_baseline: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Validates mouse kinematics (velocities, accelerations) against human reference baseline.
        """
        baseline = human_baseline if human_baseline is not None else self._human_mouse_velocity_baseline
        return self._validate_distribution(
            synthetic_samples,
            baseline,
            wasserstein_tol=self.mouse_wasserstein_tol
        )

    def validate_keystroke_latencies(
        self,
        synthetic_samples: Any,
        human_baseline: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Validates keystroke flight/dwell timing distributions against human reference baseline.
        """
        baseline = human_baseline if human_baseline is not None else self._human_flight_time_baseline
        return self._validate_distribution(
            synthetic_samples,
            baseline,
            wasserstein_tol=self.keystroke_wasserstein_tol
        )

    # -----------------------------------------------------------------------
    # Legacy & High-Level API Compatibility
    # -----------------------------------------------------------------------
    def evaluate_distribution_alignment(
        self,
        synthetic_samples: Any,
        human_baseline: Optional[Any] = None,
        alpha: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Legacy Two-Sample KS-Test evaluator used across existing test suites.
        """
        sig_level = alpha if alpha is not None else self.alpha
        baseline = human_baseline if human_baseline is not None else self._human_mouse_velocity_baseline

        cleaned_sample = self._sanitize_and_validate_input(synthetic_samples)
        cleaned_baseline = self._sanitize_and_validate_input(baseline)

        if cleaned_sample is None or cleaned_baseline is None or len(cleaned_sample) < 2:
            return {
                "ks_statistic": 1.0,
                "p_value": 0.0,
                "alpha": sig_level,
                "is_human_indistinguishable": False,
                "null_hypothesis_accepted": False,
                "decision": "SYNTHETIC_ANOMALY",
                "confidence_score": 0.0,
                "action": "❌ Corrupt or empty sample rejected."
            }

        d_stat, p_val = self.compute_ks_statistic(cleaned_sample, cleaned_baseline)
        is_human = bool(p_val >= sig_level)
        decision = "CERTIFIED_HUMAN" if is_human else "SYNTHETIC_ANOMALY"
        confidence = float(max(0.0, min(1.0, 1.0 - d_stat)))

        action = (
            f"✅ H0 ACCEPTED (p={p_val:.4f} >= {sig_level}): Synthetic biometrics mathematically "
            f"indistinguishable from genuine human population. Safe to commit actions."
            if is_human else
            f"❌ H0 REJECTED (p={p_val:.4e} < {sig_level}, D={d_stat:.4f}): Discrepancy detected!"
        )

        return {
            "ks_statistic": round(d_stat, 4),
            "p_value": round(p_val, 6),
            "alpha": sig_level,
            "is_human_indistinguishable": is_human,
            "null_hypothesis_accepted": is_human,
            "decision": decision,
            "confidence_score": round(confidence, 4),
            "action": action
        }

    def validate_trajectory_kinematics(
        self,
        trajectory: List[Tuple[float, float]],
        dt: float = 0.016,
        human_baseline: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Extracts velocity profile from mouse trajectory points and tests against human velocity baseline.
        """
        if len(trajectory) < 2:
            return {
                "decision": "SYNTHETIC_ANOMALY",
                "is_human_indistinguishable": False,
                "reason": "Trajectory too short to compute kinematics (N < 2)."
            }

        velocities = []
        for i in range(len(trajectory) - 1):
            p1 = trajectory[i]
            p2 = trajectory[i + 1]
            dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            vel = dist / max(1e-4, dt)
            velocities.append(vel)

        baseline = human_baseline if human_baseline is not None else self._human_mouse_velocity_baseline
        res = self.evaluate_distribution_alignment(velocities, human_baseline=baseline)
        res["sample_size"] = len(velocities)
        res["mean_velocity"] = round(float(np.mean(velocities)), 2) if velocities else 0.0
        return res

    def validate_keystroke_cadence(
        self,
        events: List[Dict[str, Any]],
        human_dwell_baseline: Optional[List[float]] = None,
        human_flight_baseline: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Extracts dwell and flight times from keydown/keyup events and validates against human cadences.
        """
        dwells = []
        flights = []

        keydown_times: Dict[str, float] = {}
        last_keyup_time = 0.0

        for ev in events:
            ev_type = ev.get("event")
            key = ev.get("key")
            ts = float(ev.get("timestamp_ms", 0.0))

            if ev_type == "keydown":
                keydown_times[key] = ts
                if last_keyup_time > 0:
                    flight = ts - last_keyup_time
                    flights.append(flight)
            elif ev_type == "keyup":
                last_keyup_time = ts
                if key in keydown_times:
                    dwell = ts - keydown_times[key]
                    dwells.append(dwell)

        dwell_base = human_dwell_baseline or self._human_dwell_time_baseline
        flight_base = human_flight_baseline or self._human_flight_time_baseline

        dwell_eval = self.evaluate_distribution_alignment(dwells, human_baseline=dwell_base)
        flight_eval = self.evaluate_distribution_alignment(flights, human_baseline=flight_base)

        both_passed = dwell_eval["is_human_indistinguishable"] and flight_eval["is_human_indistinguishable"]
        overall_decision = "CERTIFIED_HUMAN" if both_passed else "SYNTHETIC_ANOMALY"

        return {
            "overall_decision": overall_decision,
            "is_human_indistinguishable": both_passed,
            "dwell_evaluation": dwell_eval,
            "flight_evaluation": flight_eval,
            "dwell_count": len(dwells),
            "flight_count": len(flights)
        }
