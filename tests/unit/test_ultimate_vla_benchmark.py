"""
Empirical Evaluation & Benchmark Test Suite for UltimateVisionLanguageActionGuard.
Grounded in UI Computer Vision and Academic Self-Healing Automation Standards.
"""

import time
import numpy as np
from scipy import stats, integrate

from behavioral_playwright.powerplay.vision_guard import UltimateVisionLanguageActionGuard


class TestEmpiricalVLABenchmarkSuite:
    """
    Research-Grade Empirical Evaluation & Test Suite for UltimateVisionLanguageActionGuard.
    """

    guard = UltimateVisionLanguageActionGuard(lambda_spatial=0.005)
    box_intended = [100.0, 200.0, 250.0, 240.0]
    vec_intended = np.array([0.85, 0.15, 0.40, 0.10, 0.30], dtype=np.float64)

    def test_1_statistical_separation_ks_test(self):
        np.random.seed(42)
        n_samples = 50

        scores_valid = []
        scores_distractors = []

        for i in range(n_samples):
            # Valid Shifted Elements (slight drift in box and vector)
            dx = np.random.uniform(-15.0, 25.0)
            dy = np.random.uniform(-10.0, 15.0)
            dw = np.random.uniform(-10.0, 20.0)
            box_valid = [
                self.box_intended[0] + dx,
                self.box_intended[1] + dy,
                self.box_intended[2] + dx + dw,
                self.box_intended[3] + dy
            ]
            vec_noise = np.random.normal(0.0, 0.015, size=5)
            vec_valid = self.vec_intended + vec_noise

            res_v = self.guard.evaluate_and_heal_click(self.vec_intended, vec_valid, self.box_intended, box_valid)
            scores_valid.append(res_v["composite_score"])

            # Deceptive UI Distractors (far spatial offset, conflicting/orthogonal semantic vectors)
            dx_d = np.random.uniform(300.0, 800.0)
            dy_d = np.random.uniform(200.0, 600.0)
            box_distractor = [
                self.box_intended[0] + dx_d,
                self.box_intended[1] + dy_d,
                self.box_intended[2] + dx_d,
                self.box_intended[3] + dy_d
            ]
            vec_distractor = np.random.uniform(-1.0, 1.0, size=5)

            res_d = self.guard.evaluate_and_heal_click(self.vec_intended, vec_distractor, self.box_intended, box_distractor)
            scores_distractors.append(res_d["composite_score"])

        ks_stat, p_value = stats.ks_2samp(scores_valid, scores_distractors)

        assert p_value < 0.001
        assert ks_stat > 0.85

    def test_2_roc_auc_confusion_matrix_benchmark(self):
        np.random.seed(42)

        dataset = []
        # 50 True drifted targets
        for i in range(50):
            dx = np.random.uniform(-20.0, 30.0)
            dy = np.random.uniform(-15.0, 20.0)
            box = [
                self.box_intended[0] + dx,
                self.box_intended[1] + dy,
                self.box_intended[2] + dx + np.random.uniform(-5.0, 15.0),
                self.box_intended[3] + dy
            ]
            vec = self.vec_intended + np.random.normal(0.0, 0.01, size=5)
            dataset.append((vec, box, True))

        # 50 False traps / distractors
        for i in range(50):
            dx = np.random.uniform(250.0, 700.0)
            dy = np.random.uniform(150.0, 500.0)
            box = [
                self.box_intended[0] + dx,
                self.box_intended[1] + dy,
                self.box_intended[2] + dx,
                self.box_intended[3] + dy
            ]
            vec = np.random.uniform(-1.0, 1.0, size=5)
            dataset.append((vec, box, False))

        tp, fp, tn, fn = 0, 0, 0, 0
        scores = []
        labels = []

        for vec, box, is_true_target in dataset:
            res = self.guard.evaluate_and_heal_click(self.vec_intended, vec, self.box_intended, box, threshold=0.75)
            score = res["composite_score"]
            predicted_healed = res["is_healed"]

            scores.append(score)
            labels.append(1 if is_true_target else 0)

            if is_true_target and predicted_healed:
                tp += 1
            elif not is_true_target and predicted_healed:
                fp += 1
            elif not is_true_target and not predicted_healed:
                tn += 1
            elif is_true_target and not predicted_healed:
                fn += 1

        precision = tp / max(1, (tp + fp))
        recall = tp / max(1, (tp + fn))
        f1_score = 2 * (precision * recall) / max(1e-6, (precision + recall))

        sorted_indices = np.argsort(scores)[::-1]
        sorted_labels = np.array(labels)[sorted_indices]
        tpr_arr = np.cumsum(sorted_labels) / np.sum(sorted_labels)
        fpr_arr = np.cumsum(1 - sorted_labels) / np.sum(1 - sorted_labels)

        tpr_arr = np.insert(tpr_arr, 0, 0.0)
        fpr_arr = np.insert(fpr_arr, 0, 0.0)

        auc = float(integrate.trapezoid(tpr_arr, fpr_arr))

        assert auc >= 0.98
        assert f1_score >= 0.95

    def test_3_adversarial_ui_perturbation_attacks(self):
        # a) Spatial Chameleon Trap (Same box, conflicting semantic vector)
        vec_chameleon = -1.0 * self.vec_intended
        res_a = self.guard.evaluate_and_heal_click(self.vec_intended, vec_chameleon, self.box_intended, self.box_intended)
        assert res_a["is_healed"] is False
        assert res_a["status"] == "REJECTED"

        # b) Phantom Proximity Attack (5px away, deceptive vector)
        box_phantom = [105.0, 205.0, 255.0, 245.0]
        vec_phantom = np.array([0.0, 0.95, -0.20, 0.10, 0.0], dtype=np.float64)
        res_b = self.guard.evaluate_and_heal_click(self.vec_intended, vec_phantom, self.box_intended, box_phantom)
        assert res_b["is_healed"] is False
        assert res_b["status"] == "REJECTED"

        # c) Extreme Aspect-Ratio Deformation (Mobile layout stretched 2.5x)
        box_stretched = [100.0, 200.0, 475.0, 240.0]  # width=375 instead of 150
        res_c = self.guard.evaluate_and_heal_click(self.vec_intended, self.vec_intended, self.box_intended, box_stretched)
        assert res_c["is_healed"] is True
        assert res_c["status"] == "HEALED"

        # d) Sub-Pixel Coordinate Drift (High micro-jitter displacement)
        box_subpixel = [100.12, 200.34, 250.45, 240.56]
        res_d = self.guard.evaluate_and_heal_click(self.vec_intended, self.vec_intended, self.box_intended, box_subpixel)
        assert res_d["is_healed"] is True
        assert res_d["healed_click_x"] > box_subpixel[0]
        assert res_d["healed_click_x"] < box_subpixel[2]
        assert res_d["healed_click_y"] > box_subpixel[1]
        assert res_d["healed_click_y"] < box_subpixel[3]

    def test_4_realtime_latency_complexity_verification(self):
        candidate_counts = [5, 20, 50, 100, 500]
        runtimes_ms = []

        np.random.seed(42)

        for K in candidate_counts:
            candidates = []
            for k in range(K):
                cand_box = [
                    self.box_intended[0] + np.random.uniform(-50, 300),
                    self.box_intended[1] + np.random.uniform(-50, 300),
                    self.box_intended[2] + np.random.uniform(-50, 300),
                    self.box_intended[3] + np.random.uniform(-50, 300)
                ]
                cand_vec = np.random.uniform(-1.0, 1.0, size=5)
                candidates.append({"box": cand_box, "vector": cand_vec})

            t_start = time.perf_counter()
            self.guard.select_best_candidate(self.vec_intended, self.box_intended, candidates, threshold=0.75)
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            runtimes_ms.append(t_elapsed_ms)

        # Index 3 corresponds to K=100 candidates
        time_100_candidates_ms = runtimes_ms[3]

        log_k = np.log10(candidate_counts)
        log_times = np.log10(np.maximum(1e-5, runtimes_ms))
        slope, _ = np.polyfit(log_k, log_times, 1)

        assert time_100_candidates_ms < 5.0
        assert slope <= 1.25

    def test_5_geometric_invariants_and_stability(self):
        # GIoU Boundedness Verification
        giou_identical = self.guard.compute_normalized_giou(self.box_intended, self.box_intended)
        assert abs(giou_identical - 1.0) < 1e-4

        box_overlap = [120.0, 210.0, 270.0, 250.0]
        giou_overlap = self.guard.compute_normalized_giou(self.box_intended, box_overlap)
        assert 0.0 <= giou_overlap <= 1.0

        box_disjoint = [800.0, 900.0, 950.0, 940.0]
        giou_disjoint = self.guard.compute_normalized_giou(self.box_intended, box_disjoint)
        assert 0.0 <= giou_disjoint <= 1.0

        # Containment Invariant Verification across 50 random boxes
        np.random.seed(42)
        for _ in range(50):
            x1 = np.random.uniform(0.0, 1000.0)
            y1 = np.random.uniform(0.0, 1000.0)
            w = np.random.uniform(10.0, 200.0)
            h = np.random.uniform(10.0, 100.0)
            random_box = [x1, y1, x1 + w, y1 + h]

            click_x, click_y = self.guard.synthesize_healed_click(random_box)
            assert click_x > x1
            assert click_x < x1 + w
            assert click_y > y1
            assert click_y < y1 + h

        # Zero-Division & Edge-Case Resilience
        zero_vec = np.zeros(5)
        cos_zero = self.guard.compute_cosine_similarity(zero_vec, self.vec_intended)
        assert cos_zero == 0.0

        degenerate_box = [10.0, 10.0, 10.0, 10.0]  # Zero area
        giou_degen = self.guard.compute_normalized_giou(degenerate_box, self.box_intended)
        assert 0.0 <= giou_degen <= 1.0

        neg_box1 = [-100.0, -200.0, -50.0, -160.0]
        neg_box2 = [-90.0, -190.0, -40.0, -150.0]
        giou_neg = self.guard.compute_normalized_giou(neg_box1, neg_box2)
        assert 0.0 <= giou_neg <= 1.0
