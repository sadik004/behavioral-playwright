"""Intelligent Proxy Pool & Session Management."""

from __future__ import annotations

import random
import time
from typing import Dict, List, Optional

from behavioral_playwright.proxy.models import (
    ProxyNode,
    ProxyProtocol,
    ProxyRotationStrategy,
)


class ProxyPool:
    """Manages a pool of proxies with automatic health tracking, rotation, and sticky sessions."""

    def __init__(
        self,
        nodes: Optional[List[ProxyNode]] = None,
        strategy: ProxyRotationStrategy = ProxyRotationStrategy.ROUND_ROBIN,
        default_quarantine_seconds: float = 60.0,
    ) -> None:
        self._nodes: List[ProxyNode] = list(nodes) if nodes else []
        self.strategy = strategy
        self.default_quarantine_seconds = default_quarantine_seconds
        self._rr_index: int = 0
        self._sticky_sessions: Dict[str, tuple[ProxyNode, float]] = {}

    def add_proxy(
        self,
        host: str,
        port: int,
        protocol: ProxyProtocol = ProxyProtocol.HTTP,
        username: Optional[str] = None,
        password: Optional[str] = None,
        country: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> ProxyNode:
        node = ProxyNode(
            host=host,
            port=port,
            protocol=protocol,
            username=username,
            password=password,
            country=country,
            tags=tags or [],
        )
        self._nodes.append(node)
        return node

    def add_proxy_url(self, url: str) -> ProxyNode:
        """Parses a proxy URL string (e.g., http://user:pass@host:port) into a ProxyNode."""
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        protocol = ProxyProtocol(parsed.scheme.lower()) if parsed.scheme else ProxyProtocol.HTTP
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 8080
        username = parsed.username
        password = parsed.password
        return self.add_proxy(
            host=host,
            port=port,
            protocol=protocol,
            username=username,
            password=password,
        )

    @property
    def total_count(self) -> int:
        return len(self._nodes)

    @property
    def available_count(self) -> int:
        return sum(1 for node in self._nodes if node.is_available)

    def get_proxy(
        self,
        session_id: Optional[str] = None,
        sticky_ttl_seconds: float = 300.0,
        tag: Optional[str] = None,
    ) -> Optional[ProxyNode]:
        """Returns the next suitable proxy based on strategy or sticky session binding."""
        # 1. Check sticky session
        if session_id:
            now = time.time()
            if session_id in self._sticky_sessions:
                node, expires_at = self._sticky_sessions[session_id]
                if now < expires_at and node.is_available:
                    return node

        # 2. Filter candidates
        candidates = [n for n in self._nodes if n.is_available]
        if tag:
            candidates = [n for n in candidates if tag in n.tags]

        if not candidates:
            return None

        # 3. Apply rotation strategy
        selected: ProxyNode
        if self.strategy == ProxyRotationStrategy.ROUND_ROBIN:
            self._rr_index = (self._rr_index + 1) % len(candidates)
            selected = candidates[self._rr_index]
        elif self.strategy == ProxyRotationStrategy.RANDOM:
            selected = random.choice(candidates)
        elif self.strategy == ProxyRotationStrategy.LEAST_USED:
            selected = min(candidates, key=lambda n: n.total_requests)
        elif self.strategy == ProxyRotationStrategy.LATENCY_WEIGHTED:
            selected = min(
                candidates,
                key=lambda n: n.last_latency_ms if n.last_latency_ms > 0 else 9999.0,
            )
        else:
            selected = candidates[0]

        # 4. Bind to sticky session if requested
        if session_id:
            self._sticky_sessions[session_id] = (selected, time.time() + sticky_ttl_seconds)

        return selected

    def report_success(self, node: ProxyNode, latency_ms: float = 0.0) -> None:
        node.record_success(latency_ms)

    def report_failure(self, node: ProxyNode, quarantine_seconds: Optional[float] = None) -> None:
        sec = quarantine_seconds if quarantine_seconds is not None else self.default_quarantine_seconds
        node.record_failure(quarantine_seconds=sec)

    def clear(self) -> None:
        self._nodes.clear()
        self._sticky_sessions.clear()
        self._rr_index = 0
