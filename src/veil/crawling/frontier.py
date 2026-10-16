"""Pillar 4C: Craw4LLM Best-First Priority Frontier & Host-Aware AIMD Politeness.

Implements:
- `PriorityCrawlFrontier` (arXiv:2502.13347 & arXiv:2506.16146): Scores discovered URLs
  by query BM25/keyword relevance, high-value URL path segments, anchor text, and parent
  page influence while penalizing depth and filtering crawler traps.
- `HostPolitenessController` (arXiv:2610.13321): Per-host EWMA RTT tracking with
  Additive-Increase / Multiplicative-Decrease (AIMD) delay tuning and `Retry-After` support.
"""

from __future__ import annotations

import heapq
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from .dedup import canonicalize_url

_TRAP_PATTERNS = (
    "/login",
    "/logout",
    "/signin",
    "/signup",
    "/register",
    "/cart",
    "/checkout",
    "/wp-admin",
    "/wp-login",
    "/calendar/",
    "replytocom=",
    "share=",
)

_HIGH_VALUE_SEGMENTS = (
    "/product",
    "/item",
    "/dp/",
    "/pricing",
    "/docs",
    "/api",
    "/article",
    "/research",
    "/catalog",
    "/store",
)


@dataclass(order=True)
class FrontierItem:
    sort_key: float
    seq: int
    url: str = field(compare=False)
    depth: int = field(compare=False, default=0)
    priority_score: float = field(compare=False, default=1.0)
    anchor_text: str = field(compare=False, default="")
    parent_url: Optional[str] = field(compare=False, default=None)


class PriorityCrawlFrontier:
    """Max-priority crawl queue powered by `heapq` (negated sort_key)."""

    def __init__(self, target_query: Optional[str] = None, max_depth: int = 4) -> None:
        self.target_query = target_query or ""
        self.query_tokens = re.findall(r"[a-z0-9]+", self.target_query.lower())
        self.max_depth = max_depth
        self._heap: List[FrontierItem] = []
        self._seen: Set[str] = set()
        self._seq = 0

    def score_url(
        self,
        url: str,
        anchor_text: str = "",
        depth: int = 0,
        parent_score: float = 1.0,
    ) -> float:
        url_l = url.lower()
        anchor_l = (anchor_text or "").lower()

        score = 1.0 + (0.25 * parent_score) - (0.2 * depth)

        # High-value path boost
        for seg in _HIGH_VALUE_SEGMENTS:
            if seg in url_l:
                score += 1.2

        # Query token relevance (URL slug + Anchor text)
        for tok in self.query_tokens:
            if tok in url_l:
                score += 2.0
            if tok in anchor_l:
                score += 1.5

        return round(max(0.05, score), 4)

    def push(
        self,
        url: str,
        base_url: Optional[str] = None,
        anchor_text: str = "",
        depth: int = 0,
        parent_score: float = 1.0,
        parent_url: Optional[str] = None,
    ) -> bool:
        if depth > self.max_depth:
            return False
        canon = canonicalize_url(url, base_url=base_url)
        if canon in self._seen:
            return False
        canon_l = canon.lower()
        if any(trap in canon_l for trap in _TRAP_PATTERNS):
            return False

        self._seen.add(canon)
        self._seq += 1
        prio = self.score_url(canon, anchor_text=anchor_text, depth=depth, parent_score=parent_score)
        item = FrontierItem(
            sort_key=-prio,
            seq=self._seq,
            url=canon,
            depth=depth,
            priority_score=prio,
            anchor_text=anchor_text,
            parent_url=parent_url,
        )
        heapq.heappush(self._heap, item)
        return True

    def pop(self) -> Optional[FrontierItem]:
        if not self._heap:
            return None
        return heapq.heappop(self._heap)

    def __len__(self) -> int:
        return len(self._heap)


@dataclass
class HostPolitenessState:
    host: str
    ewma_rtt_ms: float = 150.0
    current_delay_ms: float = 100.0
    concurrency_limit: int = 4
    consecutive_ok: int = 0


class HostPolitenessController:
    """Host-Aware AIMD Politeness Controller (arXiv:2610.13321)."""

    def __init__(self, min_delay_ms: float = 50.0, max_delay_ms: float = 10000.0) -> None:
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms
        self._hosts: Dict[str, HostPolitenessState] = {}

    def _state(self, url_or_host: str) -> HostPolitenessState:
        host = (urlparse(url_or_host).hostname or url_or_host).lower()
        if host not in self._hosts:
            self._hosts[host] = HostPolitenessState(host=host)
        return self._hosts[host]

    def record_observation(
        self,
        url_or_host: str,
        status_code: int,
        rtt_ms: float,
        retry_after_header: Optional[str] = None,
    ) -> HostPolitenessState:
        st = self._state(url_or_host)
        st.ewma_rtt_ms = round((0.7 * st.ewma_rtt_ms) + (0.3 * max(1.0, rtt_ms)), 2)

        if status_code in (429, 503):
            st.consecutive_ok = 0
            st.concurrency_limit = max(1, st.concurrency_limit // 2)
            if retry_after_header and retry_after_header.strip().isdigit():
                st.current_delay_ms = min(self.max_delay_ms, float(retry_after_header.strip()) * 1000.0)
            else:
                # Multiplicative Increase of delay
                st.current_delay_ms = min(self.max_delay_ms, max(st.current_delay_ms * 2.0, st.ewma_rtt_ms * 2.5))
        elif 200 <= status_code < 400:
            st.consecutive_ok += 1
            # Additive Decrease of delay toward min_delay_ms
            st.current_delay_ms = max(self.min_delay_ms, st.current_delay_ms * 0.9 - 5.0)
            if st.consecutive_ok >= 5 and st.concurrency_limit < 16:
                st.concurrency_limit += 1
                st.consecutive_ok = 0

        return st
