"""Wave 2 Module 1: Host-Aware Crawl Budget & Sample-Then-Deepen Allocator.

Grounded in:
- Malte Ostendorff (Common Crawl Foundation, Oct 2026), "Host-Aware Web Crawling for LLM
  Pretraining Data", arXiv:2610.13321v1 (Accepted at WaC-13 @ EMNLP 2026).
  * Equation (1): Per-host quality density:
      QualityDensity(h) = (# high-quality pages fetched on h) / (# total pages fetched on h)
  * Equation (2): Shrout-Fleiss one-way Intraclass Correlation (ICC1):
      ICC1 = sigma^2_between / (sigma^2_between + sigma^2_within)
    computed via one-way ANOVA mean squares:
      MSB = sum_h n_h (y_bar_h - y_bar)^2 / (K - 1)
      MSW = sum_h sum_i (y_{hi} - y_bar_h)^2 / (N - K)
      n_0 = (N - sum_h n_h^2 / N) / (K - 1)
      sigma^2_between = max(0, (MSB - MSW) / n_0),  sigma^2_within = MSW
  * Equation (3): Spearman-Brown host reliability bound for mean sample size m_bar:
      R(m_bar) = (m_bar * ICC1) / (1 + (m_bar - 1) * ICC1)
  * Section 4.3: Sample-Then-Deepen Policy:
    Probes k = 3 pages per host first, estimates Bayesian-smoothed quality density,
    identifies "hidden-gem" hosts (below-median coverage + top-decile quality density),
    and scales per-host depth budget proportionally (up to 7.8x yield over uniform breadth).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence
from urllib.parse import urlparse


def compute_host_quality_density(
    scores: Sequence[float],
    quality_threshold: float = 0.5,
) -> float:
    """Implements Equation (1) of arXiv:2610.13321v1:
    fraction of a host's fetched pages whose quality score >= `quality_threshold`.
    """
    if not scores:
        return 0.0
    hq_count = sum(1 for s in scores if s >= quality_threshold)
    return round(hq_count / len(scores), 6)


def compute_shrout_fleiss_icc1(host_scores: Dict[str, Sequence[float]]) -> float:
    """Implements Equation (2) of arXiv:2610.13321v1:
    Shrout-Fleiss one-way random-effects Intraclass Correlation (ICC1)
    measuring the share of per-document quality variance that lies between hosts.
    """
    valid_groups = [list(vals) for vals in host_scores.values() if len(vals) >= 1]
    k_hosts = len(valid_groups)
    n_total = sum(len(g) for g in valid_groups)
    if k_hosts < 2 or n_total <= k_hosts:
        return 0.0

    grand_mean = sum(sum(g) for g in valid_groups) / n_total

    ss_between = sum(len(g) * ((sum(g) / len(g)) - grand_mean) ** 2 for g in valid_groups)
    ss_within = 0.0
    for g in valid_groups:
        g_mean = sum(g) / len(g)
        ss_within += sum((x - g_mean) ** 2 for x in g)

    msb = ss_between / (k_hosts - 1)
    msw = ss_within / (n_total - k_hosts)

    sum_n_sq = sum(len(g) ** 2 for g in valid_groups)
    n_0 = (n_total - (sum_n_sq / n_total)) / (k_hosts - 1)
    if n_0 <= 0.0:
        return 0.0

    sigma_sq_between = max(0.0, (msb - msw) / n_0)
    sigma_sq_within = max(0.0, msw)
    denom = sigma_sq_between + sigma_sq_within
    if denom <= 1e-12:
        return 0.0
    return round(sigma_sq_between / denom, 6)


def spearman_brown_reliability(m_bar: float, icc1: float) -> float:
    """Implements Equation (3) of arXiv:2610.13321v1:
    Spearman-Brown reliability R(m_bar) = (m_bar * ICC1) / (1 + (m_bar - 1) * ICC1).
    """
    if m_bar <= 0.0 or icc1 <= 0.0:
        return 0.0
    icc_clamped = min(1.0, max(0.0, icc1))
    denom = 1.0 + (m_bar - 1.0) * icc_clamped
    if denom <= 1e-12:
        return 0.0
    return round((m_bar * icc_clamped) / denom, 6)


@dataclass
class HostBudgetState:
    host: str
    known_urls: int = 0
    fetched_pages: int = 0
    page_scores: List[float] = field(default_factory=list)
    quality_density: float = 0.0
    smoothed_quality: float = 0.5
    allocated_max_depth_pages: int = 3
    phase: str = "PROBING"  # "PROBING" | "DEEPENING" | "CAPPED"


class SampleThenDeepenAllocator:
    """Implements the Sample-Then-Deepen host crawl policy (arXiv:2610.13321v1 §4.3 & §4.4).

    1. Probes `probe_sample_size` (default k=3) pages per host.
    2. Computes Eq. (1) `quality_density` and Laplace-smoothed quality score.
    3. Expands `allocated_max_depth_pages` up to `max_host_pages` for high-yield hosts
       while capping low-quality hosts right after the k=3 probe phase.
    4. Detects under-crawled "hidden-gem" hosts (below-median coverage + top-decile quality).
    """

    def __init__(
        self,
        probe_sample_size: int = 3,
        min_host_pages: int = 3,
        max_host_pages: int = 100,
        quality_threshold: float = 0.5,
        prior_weight: float = 1.0,
        prior_mean: float = 0.4,
    ) -> None:
        self.probe_sample_size = max(1, probe_sample_size)
        self.min_host_pages = max(1, min_host_pages)
        self.max_host_pages = max(self.min_host_pages, max_host_pages)
        self.quality_threshold = quality_threshold
        self.prior_weight = prior_weight
        self.prior_mean = prior_mean
        self._hosts: Dict[str, HostBudgetState] = {}

    @staticmethod
    def _normalize_host(url_or_host: str) -> str:
        if "://" in url_or_host:
            return (urlparse(url_or_host).hostname or url_or_host).lower()
        return url_or_host.lower().strip()

    def register_known_urls(self, url_or_host: str, count: int = 1) -> HostBudgetState:
        host = self._normalize_host(url_or_host)
        st = self._hosts.setdefault(
            host,
            HostBudgetState(host=host, allocated_max_depth_pages=self.probe_sample_size),
        )
        st.known_urls += max(0, count)
        return st

    def record_page_quality(self, url_or_host: str, quality_score: float) -> HostBudgetState:
        host = self._normalize_host(url_or_host)
        st = self._hosts.setdefault(
            host,
            HostBudgetState(host=host, allocated_max_depth_pages=self.probe_sample_size),
        )
        clamped = min(1.0, max(0.0, float(quality_score)))
        st.fetched_pages += 1
        st.page_scores.append(clamped)
        st.quality_density = compute_host_quality_density(st.page_scores, self.quality_threshold)

        hq_hits = sum(1 for s in st.page_scores if s >= self.quality_threshold)
        st.smoothed_quality = round(
            (hq_hits + self.prior_weight * self.prior_mean) / (len(st.page_scores) + self.prior_weight),
            6,
        )

        if st.fetched_pages >= self.probe_sample_size:
            if st.quality_density >= self.quality_threshold:
                st.phase = "DEEPENING"
                span = self.max_host_pages - self.min_host_pages
                st.allocated_max_depth_pages = self.min_host_pages + int(round(span * (st.smoothed_quality ** 1.25)))
            else:
                st.phase = "CAPPED"
                st.allocated_max_depth_pages = self.min_host_pages

        return st

    def can_fetch_more(self, url_or_host: str) -> bool:
        host = self._normalize_host(url_or_host)
        st = self._hosts.get(host)
        if st is None:
            return True
        return st.fetched_pages < st.allocated_max_depth_pages

    def compute_corpus_icc1_and_reliability(self) -> Dict[str, float]:
        score_map = {h: st.page_scores for h, st in self._hosts.items() if st.page_scores}
        icc1 = compute_shrout_fleiss_icc1(score_map)
        m_bar = (
            sum(len(v) for v in score_map.values()) / len(score_map)
            if score_map
            else 0.0
        )
        rel = spearman_brown_reliability(m_bar, icc1)
        return {
            "icc1": icc1,
            "mean_pages_per_host": round(m_bar, 3),
            "spearman_brown_reliability": rel,
        }

    def find_hidden_gem_hosts(self, quality_quantile: float = 0.75) -> List[HostBudgetState]:
        """Implements §4.4 of arXiv:2610.13321v1:
        Identifies 'hidden-gem' hosts whose crawl coverage (fetched / known) is below
        the corpus median while their quality density is in the top quantile.
        """
        candidates = [st for st in self._hosts.values() if st.fetched_pages > 0]
        if not candidates:
            return []

        coverages = sorted(
            st.fetched_pages / max(1, st.known_urls or st.fetched_pages)
            for st in candidates
        )
        median_cov = coverages[len(coverages) // 2]

        densities = sorted(st.quality_density for st in candidates)
        q_idx = min(len(densities) - 1, max(0, int(math.floor(len(densities) * quality_quantile))))
        top_q_density = densities[q_idx]

        gems = [
            st
            for st in candidates
            if (st.fetched_pages / max(1, st.known_urls or st.fetched_pages)) <= median_cov
            and st.quality_density >= top_q_density
            and st.quality_density > 0.0
        ]
        gems.sort(key=lambda s: (-s.quality_density, s.fetched_pages))
        return gems
