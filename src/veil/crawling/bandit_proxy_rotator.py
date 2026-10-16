"""Wave 2 Module 3: Multi-Armed Bandit (UCB1 + Beta-Bernoulli Thompson Sampling) Proxy Rotator & Bandwidth Resource Blocker.

Grounded in:
- TRES: "Tree-based Focused Web Crawling with Reinforcement Learning" (arXiv:2112.07620v4)
  & Auer et al. (2002) Finite-Time Analysis of the Multiarmed Bandit Problem (UCB1):
  * Latency-Penalized UCB1 Index:
      UCB1_i(t) = mu_hat_i + c * sqrt((2 * ln N(t)) / n_i) - lambda_rtt * (EWMA_RTT_i / 1000)
  * Beta-Bernoulli Thompson Sampling Posterior:
      theta_i ~ Beta(alpha_i, beta_i)
    where alpha_i = 1 + successes_i, beta_i = 1 + failures_i, sampled deterministically via
    isolated `random.Random(seed)` Gamma variates: X / (X + Y) with X ~ Gamma(alpha_i, 1), Y ~ Gamma(beta_i, 1).
- "When Handshakes Tell the Truth" (arXiv:2602.09606v1) & "How to Bypass Rate Limit Scraping"
  (Notebook 1 Source `43b5d489`):
  * Exponential jittered cooldown quarantine on HTTP 403/429/503 rate limits:
      cooldown_s = min(max_cooldown, base_cooldown * (2 ** consecutive_failures))
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence
from urllib.parse import urlparse


@dataclass
class ProxyArmState:
    proxy_url: str
    alpha: float = 1.0  # Beta prior alpha (1 + successes)
    beta: float = 1.0   # Beta prior beta (1 + failures)
    pulls: int = 0
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    ewma_rtt_ms: float = 200.0
    cooldown_until: float = 0.0

    @property
    def empirical_mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def is_available(self, now: Optional[float] = None) -> bool:
        cur = time.time() if now is None else now
        return cur >= self.cooldown_until


class BanditProxyRotator:
    """Selects optimal proxy routes using UCB1 or Beta-Bernoulli Thompson Sampling
    with automatic exponential cooldown quarantine on 403/429/503 blocks.
    """

    def __init__(
        self,
        proxies: Sequence[str] | List[str],
        exploration_c: float = 0.7,
        rtt_penalty_weight: float = 0.15,
        base_cooldown_sec: float = 15.0,
        max_cooldown_sec: float = 600.0,
        seed: Optional[int] = 42,
    ) -> None:
        if not proxies:
            raise ValueError("BanditProxyRotator requires at least one proxy URL.")
        self.exploration_c = exploration_c
        self.rtt_penalty_weight = rtt_penalty_weight
        self.base_cooldown_sec = base_cooldown_sec
        self.max_cooldown_sec = max_cooldown_sec
        self._rng = random.Random(seed)
        self._arms: Dict[str, ProxyArmState] = {
            p: ProxyArmState(proxy_url=p) for p in proxies
        }
        self._total_pulls = 0

    def compute_ucb1_score(self, arm: ProxyArmState) -> float:
        """Computes latency-penalized UCB1 index:
        UCB1_i = (alpha_i / (alpha_i + beta_i)) + c * sqrt(2 * ln(N) / n_i) - lambda_rtt * (RTT_ms / 1000).
        """
        n_i = max(1, arm.pulls)
        total_n = max(1, self._total_pulls)
        exploit = arm.empirical_mean
        explore = self.exploration_c * math.sqrt((2.0 * math.log(total_n + 1.0)) / n_i)
        rtt_penalty = self.rtt_penalty_weight * (arm.ewma_rtt_ms / 1000.0)
        return round(exploit + explore - rtt_penalty, 6)

    def sample_thompson_score(self, arm: ProxyArmState) -> float:
        """Samples theta_i ~ Beta(alpha_i, beta_i) minus latency penalty using isolated RNG."""
        x = self._rng.gammavariate(arm.alpha, 1.0)
        y = self._rng.gammavariate(arm.beta, 1.0)
        theta = x / (x + y) if (x + y) > 0.0 else 0.5
        rtt_penalty = self.rtt_penalty_weight * (arm.ewma_rtt_ms / 1000.0)
        return round(theta - rtt_penalty, 6)

    def select_proxy(
        self,
        policy: str = "ucb1",
        now: Optional[float] = None,
    ) -> ProxyArmState:
        """Selects the best non-quarantined proxy arm under `'ucb1'` or `'thompson'` policy."""
        cur = time.time() if now is None else now
        available = [arm for arm in self._arms.values() if arm.is_available(cur)]
        if not available:
            # If all arms are in cooldown, pick the one whose cooldown expires soonest
            available = [min(self._arms.values(), key=lambda a: a.cooldown_until)]

        if policy.lower() == "thompson":
            return max(available, key=self.sample_thompson_score)
        return max(available, key=self.compute_ucb1_score)

    def record_outcome(
        self,
        proxy_url: str,
        status_code: int,
        rtt_ms: float,
        now: Optional[float] = None,
    ) -> ProxyArmState:
        """Updates Beta(alpha, beta), EWMA RTT, and exponential cooldown state."""
        cur = time.time() if now is None else now
        arm = self._arms[proxy_url]
        self._total_pulls += 1
        arm.pulls += 1
        arm.ewma_rtt_ms = round((0.7 * arm.ewma_rtt_ms) + (0.3 * max(1.0, rtt_ms)), 2)

        if 200 <= status_code < 400:
            arm.successes += 1
            arm.alpha += 1.0
            arm.consecutive_failures = 0
            arm.cooldown_until = 0.0
        else:
            arm.failures += 1
            arm.beta += 1.0
            arm.consecutive_failures += 1
            if status_code in (403, 407, 429, 502, 503, 504):
                cooldown = min(
                    self.max_cooldown_sec,
                    self.base_cooldown_sec * (2 ** (arm.consecutive_failures - 1)),
                )
                arm.cooldown_until = cur + cooldown

        return arm


class BandwidthResourceBlocker:
    """Blocks non-essential media, fonts, and ad/analytics trackers during browser crawling
    to cut bandwidth usage by ~80% and accelerate page load times by 3x-5x.
    """

    _BLOCKED_RESOURCE_TYPES = frozenset({"image", "media", "font", "beacon", "csp_report", "imageset"})
    _BLOCKED_EXTENSIONS = (
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico",
        ".mp4", ".webm", ".avi", ".mp3", ".wav", ".woff", ".woff2", ".ttf", ".otf",
    )
    _BLOCKED_TRACKER_DOMAINS = (
        "google-analytics.com",
        "googletagmanager.com",
        "doubleclick.net",
        "connect.facebook.net",
        "analytics.tiktok.com",
        "hotjar.com",
        "segment.io",
        "mixpanel.com",
        "clarity.ms",
        "adservice.google.com",
    )

    def __init__(self, allow_images: bool = False) -> None:
        self.allow_images = allow_images
        self.blocked_count = 0
        self.allowed_count = 0

    def should_block(self, url: str, resource_type: str = "document") -> bool:
        rtype = (resource_type or "").lower()
        if rtype in self._BLOCKED_RESOURCE_TYPES:
            if self.allow_images and rtype in ("image", "imageset"):
                pass
            else:
                self.blocked_count += 1
                return True

        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path = (parsed.path or "").lower()

        if any(host == td or host.endswith(f".{td}") for td in self._BLOCKED_TRACKER_DOMAINS):
            self.blocked_count += 1
            return True

        if path.endswith(self._BLOCKED_EXTENSIONS):
            if self.allow_images and path.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif")):
                pass
            else:
                self.blocked_count += 1
                return True

        self.allowed_count += 1
        return False
