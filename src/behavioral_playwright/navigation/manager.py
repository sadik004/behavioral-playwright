"""
NavigationManager handling safe navigation, exponential backoff, and circuit-breaker triage.
"""

import logging

from ..config.root import AutomationConfig
from ..diagnostics.bridges import EbpfTcpSpoofBridge
from ..diagnostics.poc_exporter import ExploitPoCExporter
from ..exceptions import ConfigurationError, NavigationError
from ..utils.protocols import PageProtocol
from .circuit_breaker import CircuitBreaker, CircuitState
from .markov import MarkovLoopDetector

logger = logging.getLogger("BehavioralAutomation.Navigation.Manager")


class NavigationManager:
    """
    Handles secure, robust navigations. Decodes distinct failure classes
    to route retries vs immediate circuit breaker triages.
    """

    def __init__(self, config: AutomationConfig, circuit_breaker: CircuitBreaker) -> None:
        self.cfg = config
        self.cb = circuit_breaker
        self.markov_detector = MarkovLoopDetector(
            history_limit=config.network.markov_history_limit,
            entropy_threshold=config.network.markov_entropy_limit,
        )

    def _validate_url_structure(self, url: str) -> None:
        """Rigorous URL validation to trigger immediate configuration failures."""
        if not (url.startswith("http://") or url.startswith("https://") or url == "about:blank"):
            raise ConfigurationError(f"Protocol check failed: malformed configuration URL '{url}'. Aborting lifecycle.")

    async def safe_goto(self, page: PageProtocol, url: str) -> bool:
        """Navigates to URL safely under retry policies unless blocked by the Circuit Breaker."""
        try:
            self._validate_url_structure(url)
        except ConfigurationError as ce:
            logger.error(f"Fatal Invalid Config: {ce}")
            self.cb.record_failure()
            return False

        ebpf = EbpfTcpSpoofBridge(target_os="Windows")
        ebpf.enable_tcp_option_spoofing()

        if not self.cb.allow_request():
            logger.error(f"Circuit breaker is OPEN. Safe_goto aborted immediately for URL: '{url}'")
            return False

        self.markov_detector.record_transition(url)
        if self.markov_detector.is_loop_detected():
            logger.error(
                f"[MARKOV] Stuck in navigation loop on state: '{url}'! Shannon transition entropy below threshold."
            )
            self.cb.record_failure()
            return False

        attempt = 1
        delay = self.cfg.network.initial_delay
        state_prefix = f" [State: {self.cb.state.value}]" if self.cb.state != CircuitState.CLOSED else ""

        while attempt <= self.cfg.network.max_attempts:
            try:
                logger.info(f"Navigating to '{url}' (Attempt {attempt}/{self.cfg.network.max_attempts}){state_prefix}")
                response = await page.goto(url, wait_until="load", timeout=self.cfg.network.navigation_timeout_ms)

                if response and response.ok:
                    logger.info(f"Successfully arrived at '{url}' (HTTP: {response.status})")
                    self.cb.record_success()
                    return True
                else:
                    status = response.status if response else "Unknown"
                    logger.warning(f"Arrived at site, but received failing status code: {status}")

                    if status in [403, 429, 503, "Unknown"]:
                        ExploitPoCExporter.export_poc(
                            url=url,
                            method="GET",
                            headers={
                                "User-Agent": self.cfg.locale.user_agent,
                                "Accept-Language": self.cfg.locale.locale,
                            },
                            cookies={"session_id": "simulated_session_cookie"},
                            payload=None,
                        )
                    raise NavigationError(f"HTTP response code failed with: {status}")

            except Exception as e:
                err_msg = str(e).lower()
                if "timeout" in err_msg:
                    logger.warning(f"Retryable Timeout exception triggered on attempt {attempt}: {e}")
                elif "connection" in err_msg or "reset" in err_msg or "failed" in err_msg:
                    logger.warning(f"Retryable Network exception triggered on attempt {attempt}: {e}")
                else:
                    logger.error(f"Non-retryable / Fatal browser exception encountered: {e}")
                    self.cb.record_failure()
                    raise NavigationError(f"Fatal navigation failure: {e}") from e

            if attempt == self.cfg.network.max_attempts:
                break

            logger.info(f"Backing off for {delay:.2f} seconds before retrying...")
            await self.cb.clock.sleep(delay)
            delay *= self.cfg.network.backoff_factor
            attempt += 1

        self.cb.record_failure()
        return False
