"""CurlCffiProvider: TLS/JA4 & HTTP/2 impersonating HTTP client (provider-gated).

Integrates high-performance curl_cffi with BoringSSL transport impersonation
("chrome124"), automatic cookie/header forwarding, normalized response dicts,
and graceful lazy fallback to standard urllib when uninstalled.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import ssl
import time
from typing import Any, Callable, Dict, Optional

from .base import ProviderInfo, ProviderUnavailableError, detect_provider

logger = logging.getLogger(__name__)

try:
    import curl_cffi
    from curl_cffi.requests import AsyncSession
    CURL_CFFI_AVAILABLE = True
except (ImportError, Exception):
    CURL_CFFI_AVAILABLE = False


class AwaitableDict(dict):
    """A dictionary that is also awaitable, resolving to the coroutine's result."""

    def __init__(self, coro_fn: Callable[[], Any], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._coro_fn = coro_fn

    def __await__(self) -> Any:
        return self._coro_fn().__await__()


_ALLOWED_METHODS = frozenset({"get", "post", "put", "delete", "head", "options", "patch"})


class CurlCffiProvider:
    display_name = "curl_cffi"
    module = "curl_cffi"
    install_hint = "pip install curl-cffi"
    DEFAULT_IMPERSONATE = "chrome"

    def __init__(
        self,
        request_factory: Optional[Callable[..., Any]] = None,
        fallback: bool = True,
    ) -> None:
        self._request_factory = request_factory
        self.fallback = fallback
        self._info: Optional[ProviderInfo] = None

    def info(self) -> ProviderInfo:
        if self._info is None:
            self._info = detect_provider(self.display_name, self.module)
        return self._info

    def is_available(self) -> bool:
        if not CURL_CFFI_AVAILABLE:
            return False
        return self.info().installed

    def require_available(self) -> None:
        if not self.is_available():
            raise ProviderUnavailableError(self.display_name, self.module, self.install_hint)
        try:
            import importlib
            importlib.import_module(self.module)
        except Exception as exc:
            raise ProviderUnavailableError(self.display_name, self.module, str(exc))

    def _sync_urllib_fetch(
        self,
        url: str,
        method: str,
        headers: Optional[Dict[str, str]],
        cookies: Optional[Dict[str, str]],
        proxy: Optional[str],
        timeout: float,
    ) -> Dict[str, Any]:
        import urllib.request
        import urllib.error

        req_headers = dict(headers or {})
        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            req_headers["Cookie"] = cookie_str
        if "User-Agent" not in req_headers:
            req_headers["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )

        req = urllib.request.Request(url, headers=req_headers, method=method.upper())

        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        handlers: list[Any] = [urllib.request.HTTPSHandler(context=ctx)]
        if proxy:
            handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))

        opener = urllib.request.build_opener(*handlers)
        start_t = time.perf_counter()
        try:
            with opener.open(req, timeout=timeout) as resp:
                body_bytes = resp.read()
                body_text = body_bytes.decode("utf-8", errors="replace")
                status_code = int(resp.status)
                resp_headers = dict(resp.headers)
        except urllib.error.HTTPError as exc:
            body_bytes = exc.read()
            body_text = body_bytes.decode("utf-8", errors="replace")
            status_code = int(exc.code)
            resp_headers = dict(exc.headers)
        except (ssl.SSLError, urllib.error.URLError, ConnectionResetError, TimeoutError) as exc:
            # If SSL verification failed on fallback, attempt once with unverified context
            if isinstance(exc, ssl.SSLError) or (
                isinstance(exc, urllib.error.URLError) and isinstance(getattr(exc, "reason", None), ssl.SSLError)
            ):
                unverified_ctx = ssl.create_default_context()
                unverified_ctx.check_hostname = False
                unverified_ctx.verify_mode = ssl.CERT_NONE
                retry_handlers: list[Any] = [urllib.request.HTTPSHandler(context=unverified_ctx)]
                if proxy:
                    retry_handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
                retry_opener = urllib.request.build_opener(*retry_handlers)
                with retry_opener.open(req, timeout=timeout) as resp:
                    body_bytes = resp.read()
                    body_text = body_bytes.decode("utf-8", errors="replace")
                    status_code = int(resp.status)
                    resp_headers = dict(resp.headers)
            else:
                raise
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        return {
            "status": status_code,
            "headers": resp_headers,
            "body": body_text,
            "body_bytes": body_bytes,
            "rtt_ms": elapsed_ms,
            "impersonate": "urllib_fallback",
            "engine": "urllib_fallback",
        }

    async def _async_execute(
        self,
        url: str,
        method_key: str,
        headers: Optional[Dict[str, str]],
        cookies: Optional[Dict[str, str]],
        proxy: Optional[str],
        timeout: float,
        target_impersonate: str,
        fallback: bool,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not self.is_available():
            if not fallback:
                self.require_available()
            return await asyncio.to_thread(
                self._sync_urllib_fetch,
                url=url,
                method=method_key,
                headers=headers,
                cookies=cookies,
                proxy=proxy,
                timeout=timeout,
            )

        from curl_cffi.requests import AsyncSession

        session_kwargs: Dict[str, Any] = {"impersonate": target_impersonate}
        if cookies:
            session_kwargs["cookies"] = cookies
        if proxy:
            session_kwargs["proxies"] = {"http": proxy, "https": proxy}

        start_t = time.perf_counter()
        try:
            async with AsyncSession(**session_kwargs) as session:
                fn = getattr(session, method_key)
                resp = await fn(url, headers=headers, timeout=timeout, **kwargs)
                elapsed_ms = (time.perf_counter() - start_t) * 1000.0
                return {
                    "status": int(resp.status_code),
                    "headers": dict(resp.headers),
                    "body": resp.text,
                    "body_bytes": resp.content,
                    "rtt_ms": elapsed_ms,
                    "impersonate": target_impersonate,
                    "engine": "curl_cffi",
                }
        except Exception as exc:
            if fallback:
                logger.warning("curl_cffi execution failed (%s); falling back to urllib", exc)
                return await asyncio.to_thread(
                    self._sync_urllib_fetch,
                    url=url,
                    method=method_key,
                    headers=headers,
                    cookies=cookies,
                    proxy=proxy,
                    timeout=timeout,
                )
            raise

    def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        timeout: Optional[float] = None,
        timeout_s: float = 15.0,
        impersonate: Optional[str] = None,
        fallback: Optional[bool] = None,
        **kwargs: Any,
    ) -> Any:
        """Perform an HTTP request via curl_cffi (or fallback to urllib)."""
        method_key = method.lower()
        if method_key not in _ALLOWED_METHODS:
            raise ValueError(
                f"unsupported HTTP method {method!r}; allowed: {sorted(_ALLOWED_METHODS)}"
            )

        effective_timeout = timeout if timeout is not None else timeout_s
        target_impersonate = (
            impersonate
            or (self.DEFAULT_IMPERSONATE if self._request_factory is not None else "chrome124")
        )
        if fallback is None:
            if self._info is not None and not self._info.installed:
                effective_fallback = False
            else:
                effective_fallback = self.fallback
        else:
            effective_fallback = fallback

        if self._request_factory is not None:
            return self._request_factory(
                method=method_key,
                url=url,
                impersonate=target_impersonate,
                timeout=effective_timeout,
                headers=headers,
                cookies=cookies,
                proxy=proxy,
                **kwargs,
            )

        if not self.is_available() and not effective_fallback:
            self.require_available()

        coro_fn = lambda: self._async_execute(
            url=url,
            method_key=method_key,
            headers=headers,
            cookies=cookies,
            proxy=proxy,
            timeout=effective_timeout,
            target_impersonate=target_impersonate,
            fallback=effective_fallback,
            **kwargs,
        )
        return AwaitableDict(coro_fn)

    async def afetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        timeout: Optional[float] = None,
        timeout_s: float = 15.0,
        impersonate: Optional[str] = None,
        fallback: Optional[bool] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Asynchronously perform an HTTP request through curl_cffi AsyncSession."""
        res = self.fetch(
            url,
            method=method,
            headers=headers,
            cookies=cookies,
            proxy=proxy,
            timeout=timeout,
            timeout_s=timeout_s,
            impersonate=impersonate,
            fallback=fallback,
            **kwargs,
        )
        if hasattr(res, "__await__"):
            return await res
        return res
