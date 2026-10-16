"""
Research-Grade Empirical Evaluation & Benchmark Test Suite for ResolvedCAPTCHAInfiniteLoopDetector.
Grounded in Academic Standards for Resilient Automated Systems, Markov Graph Analysis, and Circuit Breakers.
"""

import math
import time
import unittest

from behavioral_playwright.powerplay.captcha import ResolvedCAPTCHAInfiniteLoopDetector


class TestEmpiricalCAPTCHABenchmarkSuite(unittest.TestCase):
    """
    Research-Grade Empirical Evaluation & Benchmark Test Suite for ResolvedCAPTCHAInfiniteLoopDetector.
    """

    def setUp(self):
        self.detector = ResolvedCAPTCHAInfiniteLoopDetector(
            window_sec=180.0,
            expected_lambda=0.5,
            decay_gamma=0.30,  # 0.30 ensures monotonic decay across 5 steps without premature trip (< 0.20 at step 6)
            trip_trust_threshold=0.20,
            half_open_timeout_sec=0.1,  # Fast timeout for testing
            history_limit=20
        )

    def test_1_poisson_arrival_process_and_tail_anomaly(self):
        # 1. Normal rare challenge arrival (k = 1 challenge)
        res_normal = self.detector.record_navigation("https://example.com/login", is_challenge=True)
        p_normal = res_normal["poisson_probability"]
        self.assertGreaterEqual(p_normal, 0.01, f"Normal arrival false positive: P={p_normal}")

        # Reset detector for storm simulation
        self.detector.reset()

        # 2. Aggressive challenge storm (k = 6 challenges in short order)
        p_storm = 1.0
        for i in range(6):
            res_storm = self.detector.record_navigation(f"https://example.com/challenge?step={i}", is_challenge=True)
            p_storm = res_storm["poisson_probability"]

        # Assert Poisson tail probability P(X >= 6) < 0.01 triggers anomaly detection
        self.assertLess(p_storm, 0.01, f"Poisson storm anomaly missed: P={p_storm}")
        self.assertEqual(res_storm["circuit_state"], ResolvedCAPTCHAInfiniteLoopDetector.STATE_OPEN)
        self.assertEqual(res_storm["recommended_action"], ResolvedCAPTCHAInfiniteLoopDetector.ACTION_ROTATE_PROXY_AND_ABORT)

    def test_2_bayesian_trust_decay_and_boundary_invariants(self):
        trust_scores = []

        # Test recurring challenge events and verify monotonic decay across 5 degradation steps
        for i in range(5):
            res = self.detector.record_navigation(f"https://example.com/step_{i}", is_challenge=True)
            t_val = res["trust_score"]
            trust_scores.append(t_val)

            # Assert strict boundedness
            self.assertGreaterEqual(t_val, 0.0)
            self.assertLessEqual(t_val, 1.0)

            # Prior to step 6, trust score stays above 0.20
            self.assertGreater(t_val, 0.20, f"Premature trust drop at step {i}: {t_val}")

            if i > 0:
                self.assertLess(t_val, trust_scores[i - 1], f"Non-monotonic decay: {t_val} >= {trust_scores[i-1]}")

        # Assert circuit trips to OPEN at step 6 (step_final) when trust_score drops below 0.20
        final_res = self.detector.record_navigation("https://example.com/step_final", is_challenge=True)
        self.assertLess(final_res["trust_score"], 0.20)
        self.assertEqual(final_res["circuit_state"], ResolvedCAPTCHAInfiniteLoopDetector.STATE_OPEN)

    def test_3_markov_redirection_graph_and_cyclic_traps(self):
        # Topology A: Immediate Self-Loop (URL A -> A -> A)
        self.detector.reset()
        self.detector.record_navigation("https://example.com/pageA")
        self.detector.record_navigation("https://example.com/pageA")
        res_a = self.detector.record_navigation("https://example.com/pageA")
        self.assertTrue(res_a["loop_detected"], "Self-loop A->A not detected")
        self.assertEqual(res_a["circuit_state"], ResolvedCAPTCHAInfiniteLoopDetector.STATE_OPEN)

        # Topology B: Oscillating 2-Cycle Trap (URL A -> B -> A -> B)
        self.detector.reset()
        self.detector.record_navigation("https://example.com/pageA")
        self.detector.record_navigation("https://example.com/pageB")
        # Step 3: Legitimate user back navigation (A -> B -> A): Must NOT trigger false-positive
        res_b1 = self.detector.record_navigation("https://example.com/pageA")
        self.assertFalse(res_b1["loop_detected"], "False positive: Single back navigation A->B->A incorrectly flagged as loop")

        # Step 4: Repeated oscillation back to B (A -> B -> A -> B): Trap confirmed
        res_b2 = self.detector.record_navigation("https://example.com/pageB")
        self.assertTrue(res_b2["loop_detected"], "2-Cycle A->B->A->B not detected")

        # Topology C: Complex 3-Node Cycle (URL A -> B -> C -> A -> B)
        self.detector.reset()
        self.detector.record_navigation("https://example.com/pageA")
        self.detector.record_navigation("https://example.com/pageB")
        self.detector.record_navigation("https://example.com/pageC")
        self.detector.record_navigation("https://example.com/pageA")
        res_c2 = self.detector.record_navigation("https://example.com/pageB")
        self.assertTrue(res_c2["loop_detected"], "3-Cycle A->B->C->A->B not detected")

        # Legitimate Linear Funnel (URL A -> B -> C -> D -> E)
        self.detector.reset()
        linear_urls = [
            "https://example.com/step1",
            "https://example.com/step2",
            "https://example.com/step3",
            "https://example.com/step4",
            "https://example.com/step5"
        ]
        false_positives = 0
        for url in linear_urls:
            res_lin = self.detector.record_navigation(url)
            if res_lin["loop_detected"]:
                false_positives += 1

        self.assertEqual(false_positives, 0, f"False positive loops in linear funnel: {false_positives}")

    def test_4_circuit_breaker_state_transition_matrix(self):
        self.detector.reset()

        # Initial State: CLOSED
        self.assertEqual(self.detector.circuit_state, ResolvedCAPTCHAInfiniteLoopDetector.STATE_CLOSED)

        # Trigger OPEN via recurring challenge (needs 6 steps at gamma=0.30)
        for _ in range(6):
            res_open = self.detector.record_navigation("https://example.com/challenge", is_challenge=True)

        self.assertEqual(res_open["circuit_state"], ResolvedCAPTCHAInfiniteLoopDetector.STATE_OPEN)
        self.assertEqual(res_open["recommended_action"], ResolvedCAPTCHAInfiniteLoopDetector.ACTION_ROTATE_PROXY_AND_ABORT)

        # Wait for HALF_OPEN timeout with safe buffer (0.1s timeout + 0.1s buffer = 0.20s sleep)
        time.sleep(0.20)

        # Next navigation probes HALF_OPEN -> Succeeded (is_challenge=False)
        res_half = self.detector.record_navigation("https://example.com/clean_probe", is_challenge=False)
        self.assertEqual(res_half["circuit_state"], ResolvedCAPTCHAInfiniteLoopDetector.STATE_CLOSED)
        self.assertEqual(res_half["recommended_action"], ResolvedCAPTCHAInfiniteLoopDetector.ACTION_PROCEED)

        # Trigger OPEN again and test HALF_OPEN Probe Failure
        for _ in range(6):
            self.detector.record_navigation("https://example.com/challenge", is_challenge=True)
        self.assertEqual(self.detector.circuit_state, ResolvedCAPTCHAInfiniteLoopDetector.STATE_OPEN)

        time.sleep(0.20)
        # Probe fails with challenge -> trips back to OPEN
        res_failed_probe = self.detector.record_navigation("https://example.com/challenge", is_challenge=True)
        self.assertEqual(res_failed_probe["circuit_state"], ResolvedCAPTCHAInfiniteLoopDetector.STATE_OPEN)
        self.assertEqual(res_failed_probe["recommended_action"], ResolvedCAPTCHAInfiniteLoopDetector.ACTION_ROTATE_PROXY_AND_ABORT)

    def test_5_sub_millisecond_latency_and_stability(self):
        self.detector.reset()

        # Benchmark 1,000 continuous navigation events
        n_events = 1000
        t_start = time.perf_counter()

        for i in range(n_events):
            url = f"https://example.com/page_{i % 50}"
            self.detector.record_navigation(url, is_challenge=(i % 100 == 0))

        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        per_event_ms = t_elapsed_ms / n_events

        self.assertLess(per_event_ms, 0.5, f"Per-event latency exceeded SLA: {per_event_ms:.4f} ms >= 0.5 ms")

        # Edge cases: empty URLs, malformed queries, None object, and string "None"
        self.detector.reset()
        edge_urls = ["", "   ", "https://example.com/??&&=", "http://localhost:8080/test#fragment", None, "None"]

        for e_url in edge_urls:
            res_edge = self.detector.record_navigation(e_url, is_challenge=False)
            self.assertIsNotNone(res_edge["trust_score"])
            self.assertFalse(math.isnan(res_edge["trust_score"]))
            self.assertFalse(math.isinf(res_edge["trust_score"]))
