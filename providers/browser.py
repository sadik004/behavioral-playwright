"""Browser provider adapters: Playwright, Patchright, Undetected-Chromedriver.

Each adapter is provider-gated: the backing library is imported lazily and its
absence raises ``ProviderUnavailableError``. A documented ``session_factory``
test seam allows deterministic test doubles; when supplied, it receives the
launch keyword arguments and must return a ready ``BrowserSession``.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from .base import ProviderInfo, ProviderUnavailableError, detect_provider


class BrowserSession:
    """Uniform lifecycle wrapper around a real native driver object.

    The adapter adds nothing to the driver's capabilities: ``native`` exposes
    the genuine driver (Playwright Browser / selenium WebDriver). ``close()``
    performs the provider-appropriate teardown exactly once.
    """

    def __init__(self, provider: str, native: Any, closer: Callable[[], None]) -> None:
        self.provider = provider
        self.native = native
        self._closer = closer
        self._closed = False

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._closer()


class BaseBrowserProvider:
    display_name: str = "browser"
    module: str = ""

    def __init__(self, session_factory: Optional[Callable[..., Any]] = None) -> None:
        # Documented test seam: when supplied, it replaces the real client
        # constructor entirely (deterministic doubles); availability gating
        # is intentionally bypassed because no real library is involved.
        self._session_factory = session_factory
        self._info: Optional[ProviderInfo] = None

    def info(self) -> ProviderInfo:
        if self._info is None:
            self._info = detect_provider(self.display_name, self.module)
        return self._info

    def is_available(self) -> bool:
        return self.info().installed

    def require_available(self) -> None:
        info = self.info()
        if not info.installed:
            raise ProviderUnavailableError(
                self.display_name,
                self.module,
                self.install_hint,
            )

    install_hint: str = f"pip install <{module}>"  # overwritten per subclass


class PlaywrightProvider(BaseBrowserProvider):
    display_name = "playwright"
    module = "playwright"
    install_hint = "pip install playwright && playwright install chromium"

    def launch(self, headless: bool = True, **kwargs: Any) -> BrowserSession:
        if self._session_factory is not None:
            return self._session_factory(headless=headless, **kwargs)
        self.require_available()
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        try:
            browser = pw.chromium.launch(headless=headless, **kwargs)
        except Exception:
            pw.stop()
            raise

        def _close() -> None:
            browser.close()
            pw.stop()

        return BrowserSession(self.display_name, browser, _close)


class PatchrightProvider(BaseBrowserProvider):
    """Patchright is a drop-in Playwright replacement (verified: same API)."""

    display_name = "patchright"
    module = "patchright"
    install_hint = "pip install patchright && patchright install chromium"

    def launch(self, headless: bool = True, **kwargs: Any) -> BrowserSession:
        if self._session_factory is not None:
            return self._session_factory(headless=headless, **kwargs)
        self.require_available()
        from patchright.sync_api import sync_playwright

        pw = sync_playwright().start()
        try:
            browser = pw.chromium.launch(headless=headless, **kwargs)
        except Exception:
            pw.stop()
            raise

        def _close() -> None:
            browser.close()
            pw.stop()

        return BrowserSession(self.display_name, browser, _close)


class UndetectedChromedriverProvider(BaseBrowserProvider):
    """undetected_chromedriver: patched chromedriver; API verified from PyPI
    (``uc.Chrome(headless=..., use_subprocess=...)`` -> selenium WebDriver)."""

    display_name = "undetected_chromedriver"
    module = "undetected_chromedriver"
    install_hint = "pip install undetected-chromedriver"

    def launch(self, headless: bool = True, **kwargs: Any) -> BrowserSession:
        if self._session_factory is not None:
            return self._session_factory(headless=headless, **kwargs)
        self.require_available()
        import undetected_chromedriver as uc

        driver = uc.Chrome(headless=headless, use_subprocess=True, **kwargs)
        return BrowserSession(self.display_name, driver, driver.quit)
