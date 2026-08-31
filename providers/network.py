"""CurlCffiProvider: TLS/JA3-impersonating HTTP client (provider-gated).

Verified API (PyPI ``curl-cffi``): ``from curl_cffi import requests`` with
``requests.get(url, impersonate="chrome...")`` / ``Session(impersonate=...)``.
The adapter performs no result fabrication: the genuine curl_cffi response
object is returned unchanged, and provider absence raises explicitly.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from .base import ProviderInfo, ProviderUnavailableError, detect_provider

_ALLOWED_METHODS = frozenset({"get", "post", "put", "delete", "head", "options", "patch"})


class CurlCffiProvider:
    display_name = "curl_cffi"
    module = "curl_cffi"
    install_hint = "pip install curl-cffi"
    DEFAULT_IMPERSONATE = "chrome"

    def __init__(self, request_factory: Optional[Callable[..., Any]] = None) -> None:
        # Documented test seam: replaces ``curl_cffi.requests.<method>`` with a
        # deterministic double; must accept (method, url, **kwargs).
        self._request_factory = request_factory
        self._info: Optional[ProviderInfo] = None

    def info(self) -> ProviderInfo:
        if self._info is None:
            self._info = detect_provider(self.display_name, self.module)
        return self._info

    def is_available(self) -> bool:
        return self.info().installed

    def require_available(self) -> None:
        if not self.info().installed:
            raise ProviderUnavailableError(self.display_name, self.module, self.install_hint)

    def fetch(self, url: str, *, method: str = "GET", impersonate: Optional[str] = None,
              timeout: float = 30.0, **kwargs: Any) -> Any:
        """Perform an HTTP request through curl_cffi (or the injected factory).

        Returns the genuine response object. Failures propagate as the real
        library's exceptions - nothing is swallowed or synthesized.
        """
        method_key = method.lower()
        if method_key not in _ALLOWED_METHODS:
            raise ValueError(
                f"unsupported HTTP method {method!r}; allowed: {sorted(_ALLOWED_METHODS)}"
            )
        target_impersonate = impersonate or self.DEFAULT_IMPERSONATE
        if self._request_factory is not None:
            return self._request_factory(
                method=method_key, url=url, impersonate=target_impersonate,
                timeout=timeout, **kwargs
            )
        self.require_available()
        from curl_cffi import requests as curl_requests

        fn = getattr(curl_requests, method_key)
        return fn(url, impersonate=target_impersonate, timeout=timeout, **kwargs)
