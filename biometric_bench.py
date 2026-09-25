"""
Research-Grade Empirical Evaluation & Benchmark Test Suite for BiometricDistributionValidator.
biometric_bench.py - Fully Hardened with all 9 Architectural & Statistical Fixes.
"""

import sys
import os
import math
import time
import unittest
import numpy as np
from scipy import stats, integrate
from typing import List, Dict, Tuple, Optional, Any

# Fix 1: Dynamic Repository Path resolution (replaces hardcoded /workspace/artifacts)
try:
    from behavioral_playwright.powerplay.validator import BiometricDistributionValidator
except ImportError:
    repo_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
    if repo_src not in sys.path:
        sys.path.insert(0, repo_src)
    from behavioral_playwright.powerplay.validator import BiometricDistributionValidator


class EmpiricalBiometricBenchmarkSuite(unittest.TestCase):
    """
    Research-Grade Empirical Evaluation & Benchmark Test Suite for BiometricDistributionValidator.
    """

    def setUp(self):
        self.validator = BiometricDistributionValidator(
            ks_alpha=0.05,
            mouse_wasserstein_tol=0.08,
            keystroke_wasserstein_tol=12.0
        )
        self.rng = np.random.default_rng(42)

        # Empirical Human Baseline Velocities (Lognormal Distribution: mu=-0.35, sigma=0.28)
        self.human_baseline_mouse = self.rng.lognormal(mean=-0.35, sigma=0.28, size=200).tolist()

        # Empirical Human Baseline Keystroke Flight Times (Weibull Distribution: scale=85.0, shape=1.8)
        self.human_baseline_keystrokes = (85.0 * self.rng.weibull(a=1.8, size=200) + 20.0).tolist()

    def test_1_statistical_separation_ks_and_u_test(self):
        """
        Fix 4: Expanded to validate both Mouse Kinematics and Keystroke Flight Times.
        Fix 5: Prevents Type-I false rejections by taking the median p-value over 5 independent draws.
        Fix 6: Formally verifies Mann-Whitney U test p-value and statistic for median shift detection.
        """
        # --- A. Mouse Kinematics Evaluation (5 draws for Type-I error mitigation) ---
        mouse_p_values = []
        mouse_ks_stats = []
        mouse_u_pvalues = []

        for _ in range(5):
            tuned_mouse = self.rng.lognormal(mean=-0.351, sigma=0.279, size=200).tolist()
            res_tuned = self.validator.validate_mouse_kinematics(tuned_mouse, self.human_baseline_mouse)
            mouse_p_values.append(res_tuned["p_value"])
            mouse_ks_stats.append(res_tuned["ks_statistic"])
            mouse_u_pvalues.append(res_tuned["u_pvalue"])

        median_mouse_p = float(np.median(mouse_p_values))
        median_mouse_ks = float(np.median(mouse_ks_stats))
        median_mouse_u_p = float(np.median(mouse_u_pvalues))

        # Assert Tuned Mouse passes both Null Hypotheses (KS and Mann-Whitney U)
        self.assertGreaterEqual(median_mouse_p, 0.05, f"Tuned mouse failed KS H0: p={median_mouse_p}")
        self.assertLess(median_mouse_ks, 0.15, f"Tuned mouse KS statistic too high: D={median_mouse_ks}")
        self.assertGreaterEqual(median_mouse_u_p, 0.05, f"Tuned mouse failed Mann-Whitney U: p={median_mouse_u_p}")

        # Naive Uniform Bot Script (flat speed ~ 2.5 px/ms)
        naive_bot_mouse = self.rng.uniform(2.4, 2.6, size=200).tolist()
        res_bot_mouse = self.validator.validate_mouse_kinematics(naive_bot_mouse, self.human_baseline_mouse)

        # Assert Naive Bot Fails Null Hypotheses
        self.assertFalse(res_bot_mouse["is_human_indistinguishable"])
        self.assertLess(res_bot_mouse["p_value"], 0.001)
        self.assertGreater(res_bot_mouse["ks_statistic"], 0.80)
        self.assertLess(res_bot_mouse["u_pvalue"], 0.001)

        # --- B. Keystroke Dynamics Evaluation (Fix 4: Keystroke coverage) ---
        key_p_values = []
        key_ks_stats = []
        for _ in range(5):
            tuned_key = (85.0 * self.rng.weibull(a=1.8, size=200) + 20.0).tolist()
            res_key = self.validator.validate_keystroke_latencies(tuned_key, self.human_baseline_keystrokes)
            key_p_values.append(res_key["p_value"])
            key_ks_stats.append(res_key["ks_statistic"])

        median_key_p = float(np.median(key_p_values))
        self.assertGreaterEqual(median_key_p, 0.05, f"Tuned keystrokes failed KS H0: p={median_key_p}")

        # Constant robotic typing (flat 100ms)
        bot_key = [100.0] * 200
        res_bot_key = self.validator.validate_keystroke_latencies(bot_key, self.human_baseline_keystrokes)
        self.assertFalse(res_bot_key["is_human_indistinguishable"])
        self.assertLess(res_bot_key["p_value"], 0.001)

    def test_2_roc_auc_confusion_matrix_benchmark(self):
        """
        Fix 2: Exponential scaling for strictly bounded [0, 1] scores (p_val * exp(-lambda * W)).
        Fix 4: Balanced evaluation across both Mouse and Keystroke modalities.
        Fix 8: Discrete threshold cut-offs prevent ROC curve distortion from tied scores.
        """
        dataset = []

        # 50 Human-like tuned mouse trajectories + 25 tuned keystroke profiles
        for _ in range(50):
            sample = self.rng.lognormal(mean=-0.35 + self.rng.uniform(-0.01, 0.01), sigma=0.28, size=150).tolist()
            dataset.append(("mouse", sample, True))

        for _ in range(25):
            sample = (85.0 * self.rng.weibull(a=1.8, size=150) + 20.0).tolist()
            dataset.append(("keystroke", sample, True))

        # 50 Non-human / robotic mouse samples + 25 robotic keystroke samples
        for i in range(50):
            mode = i % 3
            if mode == 0:
                sample = self.rng.uniform(1.0, 4.0, size=150).tolist()
            elif mode == 1:
                sample = (self.rng.normal(2.5, 0.05, size=150)).tolist()
            else:
                sample = self.rng.exponential(scale=1.5, size=150).tolist()
            dataset.append(("mouse", sample, False))

        for _ in range(25):
            sample = [self.rng.choice([50.0, 100.0, 150.0])] * 150
            dataset.append(("keystroke", sample, False))

        tp, fp, tn, fn = 0, 0, 0, 0
        p_scores = []
        labels = []

        for modality, sample, is_human_truth in dataset:
            if modality == "mouse":
                res = self.validator.validate_mouse_kinematics(sample, self.human_baseline_mouse)
                lambda_w = 0.5
            else:
                res = self.validator.validate_keystroke_latencies(sample, self.human_baseline_keystrokes)
                lambda_w = 0.05

            predicted_human = res["is_human_indistinguishable"]

            # Fix 2: Strictly bounded exponential score in [0.0, 1.0]
            w_dist = max(0.0, float(res["wasserstein_distance"]))
            score = max(0.0, min(1.0, float(res["p_value"] * math.exp(-lambda_w * w_dist))))

            p_scores.append(score)
            labels.append(1 if is_human_truth else 0)

            if is_human_truth and predicted_human:
                tp += 1
            elif not is_human_truth and predicted_human:
                fp += 1
            elif not is_human_truth and not predicted_human:
                tn += 1
            elif is_human_truth and not predicted_human:
                fn += 1

        precision = tp / max(1, (tp + fp))
        recall = tp / max(1, (tp + fn))
        f1_score = 2 * (precision * recall) / max(1e-6, (precision + recall))

        # Fix 8: Discrete threshold evaluation preventing tied score distortion
        scores_arr = np.array(p_scores)
        labels_arr = np.array(labels)
        unique_thresholds = np.sort(np.unique(scores_arr))[::-1]
        thresholds = np.r_[np.inf, unique_thresholds, -np.inf]

        P = np.sum(labels_arr == 1)
        N = np.sum(labels_arr == 0)

        tpr_list = []
        fpr_list = []
        for thresh in thresholds:
            tpr_list.append(np.sum((scores_arr >= thresh) & (labels_arr == 1)) / P)
            fpr_list.append(np.sum((scores_arr >= thresh) & (labels_arr == 0)) / N)

        fpr_arr = np.array(fpr_list)
        tpr_arr = np.array(tpr_list)

        auc = float(integrate.trapezoid(tpr_arr, fpr_arr))

        self.assertGreaterEqual(auc, 0.98, f"ROC-AUC score fell below 0.98: {auc:.4f}")
        self.assertGreaterEqual(f1_score, 0.95, f"F1-score fell below 0.95: {f1_score:.4f}")

    def test_3_adversarial_biometric_perturbation_attacks(self):
        """
        Validates rejection of adversarial attacks across mouse and keystroke modalities.
        """
        # Attack A: Fixed Uniform Speed Attack
        attack_a = [2.5] * 150
        res_a = self.validator.validate_mouse_kinematics(attack_a, self.human_baseline_mouse)
        self.assertFalse(res_a["is_human_indistinguishable"])

        # Attack B: Quantized Step-Function Speed Attack
        attack_b = ([1.0] * 35) + ([3.0] * 35) + ([1.5] * 35) + ([4.0] * 45)
        res_b = self.validator.validate_mouse_kinematics(attack_b, self.human_baseline_mouse)
        self.assertFalse(res_b["is_human_indistinguishable"])

        # Attack C: High-Amplitude White Noise Attack
        attack_c = self.rng.normal(2.5, 2.0, size=150).tolist()
        res_c = self.validator.validate_mouse_kinematics(attack_c, self.human_baseline_mouse)
        self.assertFalse(res_c["is_human_indistinguishable"])

        # Attack D: Constant Linear Keystroke Flight Times
        attack_d = [100.0] * 150
        res_d = self.validator.validate_keystroke_latencies(attack_d, self.human_baseline_keystrokes)
        self.assertFalse(res_d["is_human_indistinguishable"])

    def test_4_realtime_execution_speed_sla(self):
        """
        Fix 7: Pre-generates test data outside time.perf_counter() measurement loop.
        Fix 4: Measures latency across both mouse kinematics and keystroke validations.
        """
        n_scans = 500

        # Pre-generate synthetic samples outside timer (Fix 7)
        pre_generated_mouse = [
            self.rng.lognormal(mean=-0.35, sigma=0.28, size=100).tolist()
            for _ in range(n_scans)
        ]
        pre_generated_keys = [
            (85.0 * self.rng.weibull(a=1.8, size=100) + 20.0).tolist()
            for _ in range(n_scans)
        ]

        t_start_mouse = time.perf_counter()
        for sample in pre_generated_mouse:
            self.validator.validate_mouse_kinematics(sample, self.human_baseline_mouse)
        t_elapsed_mouse = (time.perf_counter() - t_start_mouse) * 1000.0
        per_mouse_scan_ms = t_elapsed_mouse / n_scans

        t_start_keys = time.perf_counter()
        for sample in pre_generated_keys:
            self.validator.validate_keystroke_latencies(sample, self.human_baseline_keystrokes)
        t_elapsed_keys = (time.perf_counter() - t_start_keys) * 1000.0
        per_key_scan_ms = t_elapsed_keys / n_scans

        self.assertLess(per_mouse_scan_ms, 3.0, f"Mouse scan latency SLA exceeded: {per_mouse_scan_ms:.4f} ms")
        self.assertLess(per_key_scan_ms, 3.0, f"Keystroke scan latency SLA exceeded: {per_key_scan_ms:.4f} ms")

    def test_5_statistical_invariants_nan_inf_and_edge_case_sanitization(self):
        """
        Fix 3: Prevents crash on empty arrays ([]) prior to SciPy invocations.
        Fix 9: Tests sanitization against float('nan'), float('inf'), float('-inf'), and None.
        Fix 4: Validates both mouse kinematics and keystroke channels on corrupt inputs.
        """
        # Normal identical distribution sanity bounds
        sample_a = self.rng.lognormal(mean=-0.35, sigma=0.28, size=100).tolist()
        sample_b = self.rng.lognormal(mean=-0.35, sigma=0.28, size=100).tolist()

        res = self.validator.validate_mouse_kinematics(sample_a, sample_b)
        self.assertGreaterEqual(res["ks_statistic"], 0.0)
        self.assertLessEqual(res["ks_statistic"], 1.0)
        self.assertGreaterEqual(res["p_value"], 0.0)
        self.assertLessEqual(res["p_value"], 1.0)
        self.assertGreaterEqual(res["wasserstein_distance"], 0.0)

        # Corrupt and boundary edge cases (Fix 3 & Fix 9)
        edge_cases = [
            [],                             # Empty list (Fix 3)
            [2.5],                          # Single element (< 2)
            [1.0] * 100,                    # Constant zero variance
            [0.0] * 100,                    # Zero sequence
            [1.0, float('nan'), 2.0],       # NaN contamination (Fix 9)
            [1.0, float('inf'), 2.0],       # Positive Inf contamination (Fix 9)
            [float('-inf'), 2.0, 3.0],      # Negative Inf contamination (Fix 9)
            None                            # Python None object (Fix 9)
        ]

        for ec in edge_cases:
            # Validate Mouse Channel
            res_m = self.validator.validate_mouse_kinematics(ec, self.human_baseline_mouse)
            self.assertIsNotNone(res_m["ks_statistic"])
            self.assertFalse(math.isnan(res_m["ks_statistic"]))
            self.assertFalse(math.isinf(res_m["ks_statistic"]))
            self.assertFalse(res_m["is_human_indistinguishable"])

            # Validate Keystroke Channel (Fix 4)
            res_k = self.validator.validate_keystroke_latencies(ec, self.human_baseline_keystrokes)
            self.assertIsNotNone(res_k["ks_statistic"])
            self.assertFalse(math.isnan(res_k["ks_statistic"]))
            self.assertFalse(math.isinf(res_k["ks_statistic"]))
            self.assertFalse(res_k["is_human_indistinguishable"])


def run_research_benchmarks():
    """CLI Benchmark runner for manual execution."""
    print("\n" + "=" * 95)
    print("EMPIRICAL BENCHMARK SUITE: BIOMETRIC DISTRIBUTION VALIDATOR (9 FIXES APPLIED)")
    print("=" * 95 + "\n")

    suite = unittest.TestLoader().loadTestsFromTestCase(EmpiricalBiometricBenchmarkSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    run_research_benchmarks()
