"""Pillar 2: Browser-to-HTTP Clearance & Session Promotion Bridge.

Solves the biggest speed vs. stealth bottleneck in web crawling:
- When a fast Tier 1/2 HTTP request hits a 403/503 WAF challenge (Cloudflare Turnstile,
  DataDome, Akamai), the bridge invokes the Stealth Browser solver ONCE for that domain,
  harvests the cleared cookies (`cf_clearance`, `datadome`, session cookies), exact
  `User-Agent` / `sec-ch-ua` headers, and sticky proxy binding, and promotes subsequent
  requests back to 100x faster Tier 1/2 HTTP requests!
"""

from __future__ import annotations

import json
import threading
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

    def __init__(
        self,
        default_ttl_seconds: float = 1800.0,
        proxy_rotator: Optional[Any] = None,
        shared_store: Optional[Any] = None,
    ) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self.proxy_rotator = proxy_rotator
        self.shared_store = shared_store
        self._leases: Dict[str, ClearanceLease] = {}
        self._lock = threading.Lock()
        self.stats = {
            "fast_http_hits": 0,
            "challenge_escalations": 0,
            "promoted_http_reuses": 0,
        }

    @staticmethod
    def _extract_domain(domain_or_url: str) -> str:
        raw = (domain_or_url or "").strip()
        if not raw:
            return "localhost"
        if "://" not in raw:
            raw = f"http://{raw}"
        return (urlparse(raw).hostname or "localhost").lower()

    def get_valid_lease(self, domain_or_url: str) -> Optional[ClearanceLease]:
        domain = self._extract_domain(domain_or_url)
        with self._lock:
            lease = self._leases.get(domain)
            if lease is not None and not lease.is_expired:
                return lease
            if lease is not None and lease.is_expired:
                self._leases.pop(domain, None)

            # Check shared_store read-through for distributed workers
            if self.shared_store is not None:
                key = f"bp:lease:{domain}"
                raw = None
                try:
                    if hasattr(self.shared_store, "get"):
                        raw = self.shared_store.get(key)
                    elif isinstance(self.shared_store, dict):
                        raw = self.shared_store.get(key)
                except Exception:
                    raw = None

                if raw:
                    data = None
                    if isinstance(raw, str):
                        try:
                            data = json.loads(raw)
                        except Exception:
                            data = None
                    elif isinstance(raw, dict):
                        data = raw

                    if data and isinstance(data, dict):
                        try:
                            l = ClearanceLease(
                                domain=data.get("domain", domain),
                                cookies=dict(data.get("cookies", {})),
                                headers=dict(data.get("headers", {})),
                                proxy_url=data.get("proxy_url"),
                                tls_impersonate=data.get("tls_impersonate", "chrome124"),
                                acquired_at=float(data.get("acquired_at", time.time())),
                                ttl_seconds=float(data.get("ttl_seconds", self.default_ttl_seconds)),
                                reuse_count=int(data.get("reuse_count", 0)),
                            )
                            if not l.is_expired:
                                self._leases[domain] = l
                                return l
                            else:
                                if hasattr(self.shared_store, "delete"):
                                    self.shared_store.delete(key)
                                elif isinstance(self.shared_store, dict):
                                    self.shared_store.pop(key, None)
                        except Exception:
                            pass
            return None

    def store_lease(self, lease: ClearanceLease) -> None:
        domain = lease.domain.lower()
        with self._lock:
            self._leases[domain] = lease
            if self.shared_store is not None:
                key = f"bp:lease:{domain}"
                payload = {
                    "domain": domain,
                    "cookies": dict(lease.cookies),
                    "headers": dict(lease.headers),
                    "proxy_url": lease.proxy_url,
                    "tls_impersonate": lease.tls_impersonate,
                    "acquired_at": float(lease.acquired_at),
                    "ttl_seconds": float(lease.ttl_seconds),
                    "reuse_count": int(lease.reuse_count),
                }
                json_str = json.dumps(payload)
                try:
                    if hasattr(self.shared_store, "set"):
                        self.shared_store.set(key, json_str)
                    elif isinstance(self.shared_store, dict):
                        self.shared_store[key] = json_str
                except Exception:
                    pass

    def invalidate_lease(self, url: str) -> None:
        domain = self._extract_domain(url)
        with self._lock:
            self._leases.pop(domain, None)
            if self.shared_store is not None:
                key = f"bp:lease:{domain}"
                try:
                    if hasattr(self.shared_store, "delete"):
                        self.shared_store.delete(key)
                    elif isinstance(self.shared_store, dict):
                        self.shared_store.pop(key, None)
                except Exception:
                    pass

    def export_leases(self) -> Dict[str, Dict[str, Any]]:
        """Thread-safely exports active non-expired leases for worker sync."""
        with self._lock:
            out: Dict[str, Dict[str, Any]] = {}
            for domain, lease in list(self._leases.items()):
                if not lease.is_expired:
                    out[domain] = {
                        "domain": lease.domain,
                        "cookies": dict(lease.cookies),
                        "headers": dict(lease.headers),
                        "proxy_url": lease.proxy_url,
                        "tls_impersonate": lease.tls_impersonate,
                        "acquired_at": float(lease.acquired_at),
                        "ttl_seconds": float(lease.ttl_seconds),
                        "reuse_count": int(lease.reuse_count),
                    }
                else:
                    self._leases.pop(domain, None)
            return out

    def import_leases(self, payload: Dict[str, Dict[str, Any]]) -> int:
        """Thread-safely imports leases keeping newest acquired_at lease per domain."""
        imported = 0
        with self._lock:
            for domain, raw in payload.items():
                try:
                    lease = ClearanceLease(
                        domain=raw.get("domain", domain),
                        cookies=dict(raw.get("cookies", {})),
                        headers=dict(raw.get("headers", {})),
                        proxy_url=raw.get("proxy_url"),
                        tls_impersonate=raw.get("tls_impersonate", "chrome124"),
                        acquired_at=float(raw.get("acquired_at", time.time())),
                        ttl_seconds=float(raw.get("ttl_seconds", self.default_ttl_seconds)),
                        reuse_count=int(raw.get("reuse_count", 0)),
                    )
                    if not lease.is_expired:
                        dom_k = lease.domain.lower()
                        existing = self._leases.get(dom_k)
                        if existing is None or lease.acquired_at >= existing.acquired_at:
                            self._leases[dom_k] = lease
                            imported += 1
                except Exception:
                    pass
        return imported

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
        tls_impersonate = lease.tls_impersonate if lease else "chrome124"

        try:
            resp = await http_fetcher(url, req_headers, proxy, tls_impersonate)
        except TypeError:
            try:
                resp = await http_fetcher(url, req_headers, proxy)
            except TypeError:
                resp = await http_fetcher(url, req_headers)
        status = int(resp.get("status", 200))
        resp_headers = resp.get("headers") or {}
        body = str(resp.get("body", ""))
        rtt_ms = float(resp.get("rtt_ms", 200.0))

        if not self.is_challenge_response(status, resp_headers, body):
            if self.proxy_rotator is not None and proxy is not None:
                self.proxy_rotator.report_success(proxy, latency_ms=rtt_ms)
            if lease is not None:
                lease.reuse_count += 1
                self.stats["promoted_http_reuses"] += 1
            else:
                self.stats["fast_http_hits"] += 1
            return {
                **resp,
                "execution_tier": "HTTP_WITH_PROMOTED_CLEARANCE" if lease else "HTTP_FAST",
                "clearance_reused": lease is not None,
                "tls_impersonate": tls_impersonate,
            }

        # Challenge detected -> Penalize proxy in Bayesian rotator, invalidate stale lease & invoke Stealth Browser once
        if self.proxy_rotator is not None and proxy is not None:
            self.proxy_rotator.report_failure(proxy, is_challenge=True, latency_ms=rtt_ms)
        self.invalidate_lease(url)
        self.stats["challenge_escalations"] += 1
        new_lease = await browser_clearance_solver(url)
        self.store_lease(new_lease)

        # Replay via fast HTTP with the newly acquired clearance lease
        promoted_headers = new_lease.build_request_headers(extra_headers)
        promoted_tls = new_lease.tls_impersonate or "chrome124"
        try:
            retry_resp = await http_fetcher(url, promoted_headers, new_lease.proxy_url, promoted_tls)
        except TypeError:
            try:
                retry_resp = await http_fetcher(url, promoted_headers, new_lease.proxy_url)
            except TypeError:
                retry_resp = await http_fetcher(url, promoted_headers)
        new_lease.reuse_count += 1
        self.stats["promoted_http_reuses"] += 1
        return {
            **retry_resp,
            "execution_tier": "HTTP_PROMOTED_AFTER_BROWSER_SOLVE",
            "clearance_reused": True,
            "clearance_cookies": dict(new_lease.cookies),
            "tls_impersonate": promoted_tls,
        }
