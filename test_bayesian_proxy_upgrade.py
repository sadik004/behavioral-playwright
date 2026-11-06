"""Verification Test Suite: Architectural Upgrade 3 — Bayesian Thompson Sampling Proxy Optimizer.

Asserts:
1. Convergence Test: Simulating 100 rounds across 3 heterogeneous proxies:
   - Proxy A: 95% success rate, 150ms latency.
   - Proxy B: 50% success rate, 800ms latency.
   - Proxy C: 10% success rate, 2500ms latency.
   Asserts that Thompson Sampling dynamically converges and allocates > 70% of selections to Proxy A.
2. Challenge Penalty Test:
   Asserts that flagging a proxy with is_challenge=True applies an aggressive penalty to Beta (beta += 3.0).
3. Backward Compatibility:
   Asserts that policy='ucb1' and policy='round_robin' function properly without regression.
"""

import random
import unittest
from behavioral_playwright.crawling.bandit_proxy_rotator import (
    BanditProxyRotator,
    ProxyArmState,
)


class TestBayesianProxyUpgrade(unittest.TestCase):
    """Rigorous verification suite for Bayesian Thompson Sampling Proxy Optimizer."""

    def test_1_thompson_sampling_convergence(self) -> None:
        """Simulates 100 rounds across 3 proxies and asserts Proxy A receives >70% traffic."""
        proxies = [
            "http://proxy-fast-reliable:8080",    # Proxy A: 95% success, 150ms
            "http://proxy-medium:8080",           # Proxy B: 50% success, 800ms
            "http://proxy-slow-failing:8080",     # Proxy C: 10% success, 2500ms
        ]
        rotator = BanditProxyRotator(proxies=proxies, seed=12345)

        # Environment characteristics
        profiles = {
            proxies[0]: {"p_success": 0.95, "latency": 150.0},
            proxies[1]: {"p_success": 0.50, "latency": 800.0},
            proxies[2]: {"p_success": 0.10, "latency": 2500.0},
        }

        selection_counts = {p: 0 for p in proxies}
        sim_rng = random.Random(999)

        # Run 100 allocation and feedback cycles
        for _ in range(100):
            # Pick using Thompson sampling (with time fixed to 0 so no cooldown blocking affects exploration)
            arm = rotator.select_proxy(policy="thompson", now=1000000.0)
            chosen = arm.proxy_url
            selection_counts[chosen] += 1

            profile = profiles[chosen]
            is_success = sim_rng.random() < profile["p_success"]
            # Feedback
            rotator.record_feedback(
                proxy_url=chosen,
                success=is_success,
                latency_ms=profile["latency"],
                is_challenge=(not is_success),
                now=1000000.0,
            )

        proxy_a_ratio = selection_counts[proxies[0]] / 100.0
        print(f"\nSelection Distribution after 100 rounds: {selection_counts} (Proxy A: {proxy_a_ratio:.1%})")

        self.assertGreater(
            proxy_a_ratio,
            0.70,
            f"Expected Proxy A to receive >70% of traffic, but got {proxy_a_ratio:.1%}",
        )
        self.assertLess(selection_counts[proxies[2]], 10)

    def test_2_challenge_penalty_beta_increase(self) -> None:
        """Asserts that is_challenge=True adds a 3.0 penalty to the Beta distribution prior."""
        rotator = BanditProxyRotator(proxies=["http://cf-blocked-proxy:8080"])
        arm = rotator._arms["http://cf-blocked-proxy:8080"]

        initial_beta = arm.beta
        self.assertEqual(initial_beta, 1.0)

        # Record a WAF challenge drop
        rotator.record_feedback(
            proxy_url="http://cf-blocked-proxy:8080",
            success=False,
            latency_ms=1200.0,
            is_challenge=True,
        )

        self.assertEqual(arm.beta, initial_beta + 3.0)
        self.assertGreater(arm.cooldown_until, 0.0)

    def test_3_backward_compatibility_ucb1_and_round_robin(self) -> None:
        """Asserts that policy='ucb1' and policy='round_robin' operate with complete backward compatibility."""
        proxies = ["http://p1:8080", "http://p2:8080", "http://p3:8080"]
        rotator = BanditProxyRotator(proxies=proxies)

        # 1. Round-robin cycle
        picked_rr = [rotator.select_proxy(policy="round_robin").proxy_url for _ in range(3)]
        self.assertEqual(picked_rr, proxies)

        # 2. UCB1 selection
        picked_ucb = rotator.select_proxy(policy="ucb1")
        self.assertIn(picked_ucb.proxy_url, proxies)
        score = rotator.compute_ucb1_score(picked_ucb)
        self.assertIsInstance(score, float)

        # 3. get_proxy method delegation
        picked_default = rotator.get_proxy()
        self.assertIn(picked_default.proxy_url, proxies)

    def test_4_concurrent_thread_safety_under_contention(self) -> None:
        """Verifies that 16 threads executing 500 select_proxy + record_feedback operations suffer zero lost updates."""
        from concurrent.futures import ThreadPoolExecutor

        proxies = [f"http://proxy-{i}:8080" for i in range(5)]
        rotator = BanditProxyRotator(proxies=proxies, seed=77)

        def worker(idx: int) -> str:
            arm = rotator.select_proxy(policy="thompson")
            rotator.record_feedback(
                arm.proxy_url,
                success=(idx % 4 != 0),
                latency_ms=100.0 + (idx % 300),
                is_challenge=(idx % 10 == 0),
            )
            return arm.proxy_url

        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(worker, range(500)))

        self.assertEqual(len(results), 500)
        self.assertEqual(rotator._total_pulls, 500)
        self.assertEqual(sum(a.pulls for a in rotator._arms.values()), 500)


if __name__ == "__main__":
    unittest.main(verbosity=2)

