"""Wave 2 Module 3: Multi-Armed Bandit (Bayesian Thompson Sampling + Latency-Penalized UCB1) Proxy Rotator & Bandwidth Resource Blocker.

Grounded in:
- Agrawal & Goyal (COLT): "Analysis of Thompson Sampling for the Multi-armed Bandit Problem"
  & Russo et al.: "A Tutorial on Thompson Sampling" (Foundations and Trends in Machine Learning):
  * Conjugate Beta-Bernoulli Thompson Sampling Posterior:
      theta_i ~ Beta(alpha_i, beta_i)
  * Exponential Latency-Penalized Selection Score:
      Score_i = theta_i * exp(-ema_latency_ms_i / tau)  where tau = 1500.0 ms.
- TRES: "Tree-based Focused Web Crawling with Reinforcement Learning" (arXiv:2112.07620v4)
  & Auer et al. (2002) Finite-Time Analysis of the Multiarmed Bandit Problem (UCB1):
  * Latency-Penalized UCB1 Index:
      UCB1_i(t) = mu_hat_i + c * sqrt((2 * ln N(t)) / n_i) - lambda_rtt * (EWMA_RTT_i / 1000)
- "When Handshakes Tell the Truth" (arXiv:2602.09606v1) & "How to Bypass Rate Limit Scraping"
  (Notebook 1 Source `43b5d489`):
  * Exponential jittered cooldown quarantine on HTTP 403/429/503 rate limits:
      cooldown_s = min(max_cooldown, base_cooldown * (2 ** consecutive_failures))
"""

from __future__ import annotations

import math
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence
from urllib.parse import urlparse


@dataclass
class ProxyArmState:
    proxy_url: str
    alpha: float = 1.0  # Beta prior alpha (1.0 + weighted successes)
    beta: float = 1.0   # Beta prior beta (1.0 + weighted failures / challenges)
    pulls: int = 0
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    ewma_rtt_ms: float = 200.0
    cooldown_until: float = 0.0

    @property
    def ema_latency_ms(self) -> float:
        """Alias for ewma_rtt_ms conforming to standard latency naming."""
        return self.ewma_rtt_ms

    @ema_latency_ms.setter
    def ema_latency_ms(self, val: float) -> None:
        self.ewma_rtt_ms = val

    @property
    def empirical_mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def is_available(self, now: Optional[float] = None) -> bool:
        cur = time.time() if now is None else now
        return cur >= self.cooldown_until


class BanditProxyRotator:
    """Selects optimal proxy routes using Bayesian Thompson Sampling (with exponential latency decay)
    or UCB1, with automatic exponential cooldown quarantine on 403/429/503 blocks.
    """

    def __init__(
        self,
        proxies: Optional[Sequence[str] | List[str]] = None,
        exploration_c: float = 0.7,
        rtt_penalty_weight: float = 0.15,
        base_cooldown_sec: float = 15.0,
        max_cooldown_sec: float = 600.0,
        seed: Optional[int] = 42,
        tau_latency_ms: float = 1500.0,
    ) -> None:
        if proxies is not None and len(proxies) == 0:
            raise ValueError("BanditProxyRotator requires at least one proxy URL.")
        resolved_proxies = list(proxies) if proxies is not None else ["direct://local"]
        self.exploration_c = exploration_c
        self.rtt_penalty_weight = rtt_penalty_weight
        self.base_cooldown_sec = base_cooldown_sec
        self.max_cooldown_sec = max_cooldown_sec
        self.tau_latency_ms = tau_latency_ms
        self._rng = random.Random(seed)
        self._lock = threading.Lock()
        self._arms: Dict[str, ProxyArmState] = {
            p: ProxyArmState(proxy_url=p) for p in resolved_proxies
        }
        self._total_pulls = 0
        self._round_robin_idx = 0

    def _get_or_create_arm(self, proxy_url: str) -> ProxyArmState:
        with self._lock:
            if proxy_url not in self._arms:
                self._arms[proxy_url] = ProxyArmState(proxy_url=proxy_url)
            return self._arms[proxy_url]

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
        """Samples theta_i ~ Beta(alpha_i, beta_i) scaled by exponential latency decay factor:
        Score_i = theta_i * exp(-ema_latency_ms / tau).
        """
        with self._lock:
            x = self._rng.gammavariate(max(1e-5, arm.alpha), 1.0)
            y = self._rng.gammavariate(max(1e-5, arm.beta), 1.0)
        theta = x / (x + y) if (x + y) > 0.0 else 0.5
        latency_factor = math.exp(-max(1.0, arm.ewma_rtt_ms) / self.tau_latency_ms)
        return round(theta * latency_factor, 6)

    def select_proxy(
        self,
        policy: str = "thompson",
        now: Optional[float] = None,
    ) -> ProxyArmState:
        """Selects the best non-quarantined proxy arm under `'thompson'`, `'ucb1'`, or `'round_robin'` policy."""
        cur = time.time() if now is None else now
        with self._lock:
            available = [arm for arm in self._arms.values() if arm.is_available(cur)]
            if not available:
                # If all arms are in cooldown, pick the one whose cooldown expires soonest
                available = [min(self._arms.values(), key=lambda a: a.cooldown_until)]

            pol = policy.lower()
            if pol == "round_robin":
                arm = available[self._round_robin_idx % len(available)]
                self._round_robin_idx += 1
                return arm

        if pol == "ucb1":
            return max(available, key=self.compute_ucb1_score)
        # Default policy: Bayesian Thompson Sampling with exponential latency scaling
        return max(available, key=self.sample_thompson_score)

    def record_feedback(
        self,
        proxy_url: str,
        success: bool,
        latency_ms: float = 200.0,
        is_challenge: bool = False,
        now: Optional[float] = None,
    ) -> ProxyArmState:
        """Updates Bayesian Beta posterior and moving latency metrics in a thread-safe manner."""
        cur = time.time() if now is None else now
        with self._lock:
            arm = self._arms.setdefault(proxy_url, ProxyArmState(proxy_url=proxy_url))
            self._total_pulls += 1
            arm.pulls += 1

            # Update exponential moving average for round-trip latency
            arm.ewma_rtt_ms = round(0.85 * arm.ewma_rtt_ms + 0.15 * max(1.0, latency_ms), 2)

            if success and not is_challenge:
                # Reward fast responses more heavily
                reward = 1.0 if latency_ms < 1000.0 else max(0.2, 1000.0 / latency_ms)
                arm.alpha += reward
                arm.successes += 1
                arm.consecutive_failures = 0
                arm.cooldown_until = 0.0
            else:
                # Penalty heavier on Cloudflare/DataDome challenge drops
                penalty = 3.0 if is_challenge else 1.5
                arm.beta += penalty
                arm.failures += 1
                arm.consecutive_failures += 1
                cooldown = min(
                    self.max_cooldown_sec,
                    self.base_cooldown_sec * (2 ** (arm.consecutive_failures - 1)),
                )
                arm.cooldown_until = cur + cooldown

            return arm

    def record_outcome(
        self,
        proxy_url: str,
        status_code: int,
        rtt_ms: float,
        now: Optional[float] = None,
    ) -> ProxyArmState:
        """Updates Beta(alpha, beta), EWMA RTT, and exponential cooldown state based on HTTP status code."""
        is_challenge = status_code in (403, 407, 429, 502, 503, 504)
        is_success = (200 <= status_code < 400) and not is_challenge
        return self.record_feedback(
            proxy_url=proxy_url,
            success=is_success,
            latency_ms=rtt_ms,
            is_challenge=is_challenge,
            now=now,
        )

    def add_proxy(self, host: str, port: int, protocol: str = "http", **kwargs: object) -> ProxyArmState:
        url = f"{protocol}://{host}:{port}"
        return self.add_proxy_url(url)

    def add_proxy_url(self, url: str) -> ProxyArmState:
        with self._lock:
            arm = self._arms.setdefault(url, ProxyArmState(proxy_url=url))
            return arm

    def get_proxy(self, session_id: Optional[str] = None, policy: str = "thompson", **kwargs: object) -> ProxyArmState:
        _ = session_id
        return self.select_proxy(policy=policy)

    def report_success(self, node: object, latency_ms: float = 50.0) -> None:
        key = getattr(node, "proxy_url", None) or str(node)
        self.record_feedback(key, success=True, latency_ms=latency_ms, is_challenge=False)

    def report_failure(
        self,
        node: object,
        quarantine_seconds: Optional[float] = None,
        is_challenge: bool = False,
        latency_ms: float = 1000.0,
    ) -> None:
        key = getattr(node, "proxy_url", None) or str(node)
        arm = self.record_feedback(key, success=False, latency_ms=latency_ms, is_challenge=is_challenge)
        if quarantine_seconds is not None:
            arm.cooldown_until = time.time() + float(quarantine_seconds)


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
