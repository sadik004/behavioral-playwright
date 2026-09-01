"""Proxy models and data structures."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProxyProtocol(str, Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class ProxyRotationStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_USED = "least_used"
    LATENCY_WEIGHTED = "latency_weighted"


@dataclass
class ProxyNode:
    """Represents a single proxy endpoint with health and performance metrics."""

    host: str
    port: int
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    active: bool = True
    total_requests: int = 0
    failed_requests: int = 0
    last_latency_ms: float = 0.0
    last_used_epoch: float = 0.0
    quarantine_until_epoch: float = 0.0
    tags: list[str] = field(default_factory=list)

    @property
    def url(self) -> str:
        """Formats the proxy as a standard connection URL."""
        auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
        return f"{self.protocol.value}://{auth}{self.host}:{self.port}"

    @property
    def is_available(self) -> bool:
        """Determines if the proxy is active and not currently quarantined."""
        return self.active and time.time() >= self.quarantine_until_epoch

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return max(0.0, 1.0 - (self.failed_requests / self.total_requests))

    def record_success(self, latency_ms: float = 0.0) -> None:
        self.total_requests += 1
        self.last_latency_ms = latency_ms
        self.last_used_epoch = time.time()

    def record_failure(self, quarantine_seconds: float = 60.0) -> None:
        self.total_requests += 1
        self.failed_requests += 1
        self.last_used_epoch = time.time()
        self.quarantine_until_epoch = time.time() + quarantine_seconds
