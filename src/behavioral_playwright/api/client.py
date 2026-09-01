"""High-performance API client with connection pooling, caching, and proxy integration."""

from __future__ import annotations

import asyncio
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union


@dataclass
class ApiResponse:
    status_code: int
    headers: Dict[str, str]
    body: bytes
    elapsed_ms: float
    cached: bool = False

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text)


class ApiRequestCache:
    """In-memory TTL request cache."""

    def __init__(self, default_ttl_seconds: float = 60.0) -> None:
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[str, tuple[ApiResponse, float]] = {}

    def get(self, key: str) -> Optional[ApiResponse]:
        if key in self._cache:
            resp, expires_at = self._cache[key]
            if time.time() < expires_at:
                return ApiResponse(
                    status_code=resp.status_code,
                    headers=resp.headers,
                    body=resp.body,
                    elapsed_ms=0.0,
                    cached=True,
                )
            del self._cache[key]
        return None

    def set(self, key: str, response: ApiResponse, ttl: Optional[float] = None) -> None:
        exp = time.time() + (ttl if ttl is not None else self.default_ttl)
        self._cache[key] = (response, exp)

    def clear(self) -> None:
        self._cache.clear()


from behavioral_playwright.config.settings import AuthConfig


class AsyncApiClient:
    """Optimized async API client with connection pooling, caching, proxy, and circuit breaker."""

    def __init__(
        self,
        default_timeout: float = 15.0,
        cache_ttl: float = 60.0,
        proxy_url: Optional[str] = None,
        proxy_pool: Optional[Any] = None,
        circuit_breaker: Optional[Any] = None,
        auth_config: Optional[AuthConfig] = None,
    ) -> None:
        self.default_timeout = default_timeout
        self.cache = ApiRequestCache(default_ttl_seconds=cache_ttl)
        self.proxy_url = proxy_url
        self.proxy_pool = proxy_pool
        self.circuit_breaker = circuit_breaker
        self.auth_config = auth_config or AuthConfig()

    def _make_sync_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[Dict[str, Any], bytes, str]] = None,
        timeout: Optional[float] = None,
        proxy: Optional[str] = None,
    ) -> ApiResponse:
        req_headers = {
            "User-Agent": "BehavioralPlaywright-ApiClient/10.0",
            "Accept": "application/json, text/plain, */*",
        }
        # Merge resolved auth headers without mutating caller dictionaries
        auth_hdrs = self.auth_config.get_headers()
        req_headers.update(auth_hdrs)
        if headers:
            req_headers.update(headers)

        body_bytes: Optional[bytes] = None
        if data is not None:
            if isinstance(data, dict):
                body_bytes = json.dumps(data).encode("utf-8")
                req_headers.setdefault("Content-Type", "application/json")
            elif isinstance(data, str):
                body_bytes = data.encode("utf-8")
            else:
                body_bytes = data

        req = urllib.request.Request(url, data=body_bytes, headers=req_headers, method=method.upper())
        effective_timeout = timeout or self.default_timeout

        # Resolve proxy (explicit > instance default > proxy_pool)
        eff_proxy = proxy or self.proxy_url
        selected_proxy_node = None
        if not eff_proxy and self.proxy_pool is not None:
            selected_proxy_node = self.proxy_pool.get_proxy()
            if selected_proxy_node:
                eff_proxy = selected_proxy_node.url

        handlers = []
        if eff_proxy:
            handlers.append(urllib.request.ProxyHandler({"http": eff_proxy, "https": eff_proxy}))
        opener = urllib.request.build_opener(*handlers) if handlers else urllib.request.build_opener()

        start = time.perf_counter()
        try:
            with opener.open(req, timeout=effective_timeout) as resp:
                raw_body = resp.read()
                elapsed = (time.perf_counter() - start) * 1000.0
                resp_headers = dict(resp.headers)
                if selected_proxy_node and self.proxy_pool is not None:
                    self.proxy_pool.report_success(selected_proxy_node, latency_ms=elapsed)

                return ApiResponse(
                    status_code=resp.status,
                    headers=resp_headers,
                    body=raw_body,
                    elapsed_ms=elapsed,
                    cached=False,
                )

        except urllib.error.HTTPError as exc:
            elapsed = (time.perf_counter() - start) * 1000.0
            if selected_proxy_node and self.proxy_pool is not None:
                if exc.code >= 500:
                    self.proxy_pool.report_failure(selected_proxy_node)
                else:
                    self.proxy_pool.report_success(selected_proxy_node, latency_ms=elapsed)

            return ApiResponse(
                status_code=exc.code,
                headers=dict(exc.headers),
                body=exc.read(),
                elapsed_ms=elapsed,
                cached=False,
            )
        except Exception as exc:
            if selected_proxy_node and self.proxy_pool is not None:
                self.proxy_pool.report_failure(selected_proxy_node)
            raise exc

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[Dict[str, Any], bytes, str]] = None,
        timeout: Optional[float] = None,
        cache_ttl: Optional[float] = None,
        use_cache: bool = True,
        proxy: Optional[str] = None,
    ) -> ApiResponse:
        method_upper = method.upper()

        auth_fp = ""
        if self.auth_config:
            auth_hdrs = self.auth_config.get_headers()
            if auth_hdrs:
                auth_fp = f":auth={hash(frozenset(auth_hdrs.items()))}"

        cache_key = f"{method_upper}:{url}{auth_fp}" if (use_cache and method_upper == "GET") else None

        if cache_key:
            cached_resp = self.cache.get(cache_key)
            if cached_resp:
                return cached_resp


        async def _execute_fetch() -> ApiResponse:
            loop = asyncio.get_running_loop()
            fetch_resp: ApiResponse = await loop.run_in_executor(
                None,
                lambda: self._make_sync_request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=data,
                    timeout=timeout,
                    proxy=proxy,
                ),
            )
            return fetch_resp

        if self.circuit_breaker is not None:
            resp = await self.circuit_breaker.execute(_execute_fetch, operation_name=f"api_{method_upper}")
        else:
            resp = await _execute_fetch()

        if cache_key and 200 <= resp.status_code < 400:
            self.cache.set(cache_key, resp, ttl=cache_ttl)

        return resp

    async def get(self, url: str, **kwargs: Any) -> ApiResponse:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, data: Optional[Any] = None, **kwargs: Any) -> ApiResponse:
        return await self.request("POST", url, data=data, **kwargs)

    async def put(self, url: str, data: Optional[Any] = None, **kwargs: Any) -> ApiResponse:
        return await self.request("PUT", url, data=data, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> ApiResponse:
        return await self.request("DELETE", url, **kwargs)
