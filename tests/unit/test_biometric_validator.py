"""
Unit test suite for BiometricDistributionValidator (Problem 7: Distribution Discrepancy & Hypothesis Testing).
Verifies Two-Sample KS-Test, Null Hypothesis verification (p >= 0.05), synthetic anomaly detection,
mouse trajectory kinematics, and keystroke cadence validation.
"""

import numpy as np
from behavioral_playwright import BP, Bpp, BiometricDistributionValidator


def test_validator_initialization_and_reference_baselines():
    validator = BiometricDistributionValidator(alpha=0.05)
    assert len(validator._human_mouse_velocity_baseline) == 200
    assert len(validator._human_dwell_time_baseline) == 200
    assert len(validator._human_flight_time_baseline) == 200


def test_two_sample_ks_test_null_hypothesis_accepted_on_human_like_data():
    np.random.seed(42)
    validator = BiometricDistributionValidator(alpha=0.05)

    # Generate synthetic velocity samples drawn from approximately human lognormal distribution
    synthetic_human_like = np.random.lognormal(mean=6.0, sigma=0.45, size=150).tolist()

    res = validator.evaluate_distribution_alignment(synthetic_human_like)
    assert res["is_human_indistinguishable"] is True
    assert res["null_hypothesis_accepted"] is True
    assert res["decision"] == "CERTIFIED_HUMAN"
    assert res["p_value"] >= 0.05
    assert res["ks_statistic"] < 0.20


def test_two_sample_ks_test_rejects_rigid_robotic_anomalies():
    validator = BiometricDistributionValidator(alpha=0.05)

    # Constant robotic velocity (e.g. 500 px/s with 0 variance)
    rigid_robotic = [500.0] * 100

    res = validator.evaluate_distribution_alignment(rigid_robotic)
    assert res["is_human_indistinguishable"] is False
    assert res["null_hypothesis_accepted"] is False
    assert res["decision"] == "SYNTHETIC_ANOMALY"
    assert res["p_value"] < 0.001
    assert res["ks_statistic"] > 0.50


def test_validate_trajectory_kinematics_via_bp_powerplay():
    bp = BP()

    # Generate a realistic Costello Bezier trajectory with Plamondon & tremor dynamics
    trajectory = bp.powerplay.generate_mouse_trajectory(start_pos=(100, 100), target_pos=(600, 450), steps=60)

    # Validate kinematics
    res = bp.powerplay.validate_trajectory_kinematics(trajectory, dt=0.016)
    assert "ks_statistic" in res
    assert "p_value" in res
    assert res["sample_size"] == 59
    assert res["mean_velocity"] > 0.0


def test_validate_keystroke_cadence_via_bp_powerplay():
    bp = BP()

    # Generate typing sequence with Weibull latency and QWERTY Euclidean distances
    sequence = bp.powerplay.generate_keystroke_sequence("AntigravityBehavioralAutomationTesting2026")

    # Validate cadence
    res = bp.powerplay.validate_keystroke_cadence(sequence)
    assert "overall_decision" in res
    assert res["dwell_count"] > 0
    assert res["flight_count"] > 0
    assert "dwell_evaluation" in res
    assert "flight_evaluation" in res


def test_bpp_orchestrator_and_bp_facade_attachment():
    bp = BP()
    bot = Bpp()

    assert isinstance(bp.powerplay.validator, BiometricDistributionValidator)
    assert isinstance(bp.validator, BiometricDistributionValidator)
    assert isinstance(bot.validator, BiometricDistributionValidator)
    assert bp.powerplay.BiometricDistributionValidator is BiometricDistributionValidator
