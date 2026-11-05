"""Pillar 2: Browser-to-HTTP Clearance & Session Promotion Bridge.

Solves the biggest speed vs. stealth bottleneck in web crawling:
- When a fast Tier 1/2 HTTP request hits a 403/503 WAF challenge (Cloudflare Turnstile,
  DataDome, Akamai), the bridge invokes the Stealth Browser solver ONCE for that domain,
  harvests the cleared cookies (`cf_clearance`, `datadome`, session cookies), exact
  `User-Agent` / `sec-ch-ua` headers, and sticky proxy binding, and promotes subsequent
  requests back to 100x faster Tier 1/2 HTTP requests!
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional
from urllib.parse import urlparse


@dataclass
class ClearanceLease:
    domain: str
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    proxy_url: Optional[str] = None
    tls_impersonate: str = "chrome124"
    acquired_at: float = field(default_factory=time.time)
    ttl_seconds: float = 1800.0
    reuse_count: int = 0

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.acquired_at) >= self.ttl_seconds

    def to_cookie_header(self) -> str:
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())

    def build_request_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        merged = dict(self.headers)
        cookie_str = self.to_cookie_header()
        if cookie_str:
            merged["Cookie"] = cookie_str
        if extra_headers:
            merged.update(extra_headers)
        return merged


class BrowserClearanceBridge:
    """Manages domain clearance leases and coordinates 1-Browser -> N-HTTP promotion."""

    _CHALLENGE_MARKERS = (
        "cf-mitigated",
        "cf-turnstile",
        "just a moment...",
        "attention required! | cloudflare",
        "datadome",
        "dd_cid",
        "pardon our interruption",
        "_abck",
        "x-kpsdk-ct",
    )

    def __init__(self, default_ttl_seconds: float = 1800.0) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._leases: Dict[str, ClearanceLease] = {}
        self.stats = {
            "fast_http_hits": 0,
            "challenge_escalations": 0,
            "promoted_http_reuses": 0,
        }

    @staticmethod
    def _extract_domain(url: str) -> str:
        return (urlparse(url).hostname or "localhost").lower()

    def get_valid_lease(self, url: str) -> Optional[ClearanceLease]:
        domain = self._extract_domain(url)
        lease = self._leases.get(domain)
        if lease is not None and not lease.is_expired:
            return lease
        if lease is not None and lease.is_expired:
            del self._leases[domain]
        return None

    def store_lease(self, lease: ClearanceLease) -> None:
        self._leases[lease.domain.lower()] = lease

    def invalidate_lease(self, url: str) -> None:
        domain = self._extract_domain(url)
        self._leases.pop(domain, None)

    def is_challenge_response(
        self,
        status_code: int,
        headers: Optional[Dict[str, str]] = None,
        body: str = "",
    ) -> bool:
        hdrs_lower = {k.lower(): str(v).lower() for k, v in (headers or {}).items()}
        if "cf-mitigated" in hdrs_lower or "x-datadome" in hdrs_lower:
            return True
        if status_code in (403, 429, 503):
            body_l = (body or "")[:8192].lower()
            if any(m in body_l for m in self._CHALLENGE_MARKERS):
                return True
            if status_code == 403:
                return True
        return False

    async def fetch_with_promotion(
        self,
        url: str,
        http_fetcher: Callable[[str, Dict[str, str], Optional[str]], Awaitable[Dict[str, Any]]],
        browser_clearance_solver: Callable[[str], Awaitable[ClearanceLease]],
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Executes fast HTTP fetch using any cached clearance lease; if challenged,
        solves once via `browser_clearance_solver`, caches the lease, and replays via HTTP.
        """
        lease = self.get_valid_lease(url)
        req_headers = lease.build_request_headers(extra_headers) if lease else dict(extra_headers or {})
        proxy = lease.proxy_url if lease else None

        resp = await http_fetcher(url, req_headers, proxy)
        status = int(resp.get("status", 200))
        resp_headers = resp.get("headers") or {}
        body = str(resp.get("body", ""))

        if not self.is_challenge_response(status, resp_headers, body):
            if lease is not None:
                lease.reuse_count += 1
                self.stats["promoted_http_reuses"] += 1
            else:
                self.stats["fast_http_hits"] += 1
            return {
                **resp,
                "execution_tier": "HTTP_WITH_PROMOTED_CLEARANCE" if lease else "HTTP_FAST",
                "clearance_reused": lease is not None,
            }

        # Challenge detected -> Invalidate stale lease & invoke Stealth Browser once
        self.invalidate_lease(url)
        self.stats["challenge_escalations"] += 1
        new_lease = await browser_clearance_solver(url)
        self.store_lease(new_lease)

        # Replay via fast HTTP with the newly acquired clearance lease
        promoted_headers = new_lease.build_request_headers(extra_headers)
        retry_resp = await http_fetcher(url, promoted_headers, new_lease.proxy_url)
        new_lease.reuse_count += 1
        self.stats["promoted_http_reuses"] += 1
        return {
            **retry_resp,
            "execution_tier": "HTTP_PROMOTED_AFTER_BROWSER_SOLVE",
            "clearance_reused": True,
            "clearance_cookies": dict(new_lease.cookies),
        }
