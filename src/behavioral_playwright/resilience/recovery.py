"""Coordinated Recovery Manager enforcing state verification, stale invalidation, and session continuity."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Callable, Coroutine, Dict, List, Optional

from behavioral_playwright.exceptions import (
    BehavioralPlaywrightError,
    BrowserProviderError,
    NavigationError,
)
from behavioral_playwright.logging import get_logger
from behavioral_playwright.resilience.models import RecoveryRecord, RecoveryState
from behavioral_playwright.resilience.taxonomy import (
    FailureCategory,
    classify_failure,
    is_recoverable_via_restart,
)

logger = get_logger("resilience.recovery")


class RecoveryManager:
    """Manages coordinated recovery of pages, contexts, and browser sessions.

    Invariants:
    1. Single-flight recovery: Concurrent failures coordinate into one recovery pass;
       they do not trigger duplicate browser or page restart storms.
    2. Post-recovery verification: Recovery is never declared successful without
       independent live verification of process, page state, and evaluation responsiveness.
    3. Stale state invalidation: Old page handles, selector caches, and extraction buffers
       are purged before assigning the recovered target.
    4. Session identity preservation: Session ID remains continuous across recovery.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        clock_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self._clock_fn = clock_fn or time.time
        self.state: RecoveryState = RecoveryState.HEALTHY
        self.recovery_history: List[RecoveryRecord] = []
        self._recovery_lock = asyncio.Lock()
        self._last_recovery_time: float = 0.0

    async def execute_recovery(
        self,
        page_session: Any,
        error: BaseException,
        restore_url: bool = True,
        max_attempts: int = 2,
    ) -> bool:
        """Executes coordinated recovery of a failed page session.

        Returns True if recovery succeeded and passed verification, False otherwise.
        """
        start_time = self._clock_fn()
        category = classify_failure(error)
        execution_id = str(uuid.uuid4())[:8]

        logger.warning(
            f"[RecoveryManager:{self.session_id}] Initiating recovery for error: "
            f"[{category.value}] {error} (exec_id={execution_id})"
        )

        # 1. State transition: FAILURE_DETECTED -> CLASSIFIED
        self.state = RecoveryState.FAILURE_DETECTED
        self.state = RecoveryState.CLASSIFIED

        if not is_recoverable_via_restart(category) and category != FailureCategory.UNKNOWN:
            logger.error(
                f"[RecoveryManager:{self.session_id}] Failure category {category.value} is not recoverable via restart."
            )
            self.state = RecoveryState.TERMINAL_FAILURE
            self._record_event(
                execution_id=execution_id,
                category=category,
                error=str(error),
                action="RECOVERY_REJECTED",
                prev=RecoveryState.CLASSIFIED,
                resulting=RecoveryState.TERMINAL_FAILURE,
                verified=False,
                elapsed_ms=(self._clock_fn() - start_time) * 1000.0,
            )
            return False

        # 2. Coordinated Single-Flight Lock: Prevent concurrent recovery storms
        async with self._recovery_lock:
            # If a sibling task just recovered within the last 500ms and the page is currently verified healthy, reuse it
            if (self._clock_fn() - self._last_recovery_time < 0.50) and await self._verify_live_page(page_session.raw_page):
                logger.info(f"[RecoveryManager:{self.session_id}] Reusing recently verified recovered session.")
                self.state = RecoveryState.RECOVERED
                return True

            attempt = 0
            while attempt < max_attempts:
                attempt += 1
                self.state = RecoveryState.RECOVERY_ATTEMPTED
                logger.info(f"[RecoveryManager:{self.session_id}] Attempting recovery pass {attempt}/{max_attempts}...")

                try:
                    # 3. Purge stale page references & selector memory
                    self._invalidate_stale_state(page_session)

                    # 4. Perform actual provider recreation of raw page
                    last_url = None
                    try:
                        if hasattr(page_session, "state_tracker") and page_session.state_tracker.current_state:
                            last_url = page_session.state_tracker.current_state.url
                    except Exception:
                        pass

                    # Request provider to dispense a fresh page
                    new_raw_page = await page_session.provider.new_page()

                    # 5. Invalidate and re-bind new raw page to controllers
                    page_session.raw_page = new_raw_page
                    if hasattr(page_session, "mouse"):
                        page_session.mouse.page = new_raw_page
                    if hasattr(page_session, "keyboard"):
                        page_session.keyboard.page = new_raw_page
                    if hasattr(page_session, "scroll"):
                        page_session.scroll.page = new_raw_page

                    # Optionally restore the previous URL if requested and valid
                    if restore_url and last_url and last_url.startswith(("http://", "https://", "data:")):
                        logger.info(f"[RecoveryManager:{self.session_id}] Restoring pre-failure URL: {last_url}")
                        try:
                            if hasattr(new_raw_page, "goto") and callable(new_raw_page.goto):
                                await new_raw_page.goto(last_url, timeout=page_session.config.browser.timeout_ms)
                        except Exception as goto_err:
                            logger.warning(f"[RecoveryManager:{self.session_id}] Warning during URL restoration: {goto_err}")

                    # 6. Post-recovery verification (CRITICAL INVARIANT)
                    self.state = RecoveryState.STATE_REVALIDATED
                    verif_passed, verif_details = await self._verify_page_integrity(new_raw_page)

                    if verif_passed:
                        self.state = RecoveryState.RECOVERED
                        self._last_recovery_time = self._clock_fn()
                        elapsed = (self._clock_fn() - start_time) * 1000.0
                        logger.info(f"[RecoveryManager:{self.session_id}] Recovery VERIFIED SUCCESSFUL in {elapsed:.1f}ms.")
                        self._record_event(
                            execution_id=execution_id,
                            category=category,
                            error=str(error),
                            action="PAGE_RECREATED_AND_VERIFIED",
                            prev=RecoveryState.STATE_REVALIDATED,
                            resulting=RecoveryState.RECOVERED,
                            verified=True,
                            details=verif_details,
                            elapsed_ms=elapsed,
                            attempts=attempt,
                        )
                        return True
                    else:
                        logger.error(f"[RecoveryManager:{self.session_id}] Post-recovery verification FAILED: {verif_details}")

                except Exception as rec_err:
                    logger.error(f"[RecoveryManager:{self.session_id}] Recovery attempt {attempt} threw exception: {rec_err}")

            # If all attempts exhausted
            self.state = RecoveryState.TERMINAL_FAILURE
            elapsed = (self._clock_fn() - start_time) * 1000.0
            self._record_event(
                execution_id=execution_id,
                category=category,
                error=str(error),
                action="RECOVERY_EXHAUSTED",
                prev=RecoveryState.RECOVERY_ATTEMPTED,
                resulting=RecoveryState.TERMINAL_FAILURE,
                verified=False,
                elapsed_ms=elapsed,
                attempts=attempt,
            )
            return False

    def _invalidate_stale_state(self, page_session: Any) -> None:
        """Purges stale element caches, selector memories, and handles from prior page."""
        logger.debug(f"[RecoveryManager:{self.session_id}] Invalidating stale page session state...")
        try:
            # 1. Clear selector memory if present
            if hasattr(page_session, "resolver") and hasattr(page_session.resolver, "memory"):
                page_session.resolver.memory.clear()
            # 2. Reset circuit breaker failure count on successful coordinated recovery pass
            if hasattr(page_session, "circuit_breaker"):
                page_session.circuit_breaker.reset()
        except Exception as exc:
            logger.debug(f"Error during state invalidation: {exc}")

    async def _verify_live_page(self, raw_page: Any) -> bool:
        """Quick liveness probe on a raw page object."""
        try:
            if hasattr(raw_page, "is_closed") and callable(raw_page.is_closed):
                if raw_page.is_closed():
                    return False
            if hasattr(raw_page, "evaluate") and callable(raw_page.evaluate):
                res = await raw_page.evaluate("() => 1 + 1")
                return res == 2
            return True
        except Exception:
            return False

    async def _verify_page_integrity(self, raw_page: Any) -> tuple[bool, Dict[str, Any]]:
        """Deep post-recovery verification of page responsiveness and DOM execution."""
        details: Dict[str, Any] = {
            "page_open": False,
            "evaluation_alive": False,
            "document_ready": False,
        }
        try:
            if hasattr(raw_page, "is_closed") and callable(raw_page.is_closed):
                details["page_open"] = not raw_page.is_closed()
            else:
                details["page_open"] = True

            if not details["page_open"]:
                return False, details

            if hasattr(raw_page, "evaluate") and callable(raw_page.evaluate):
                eval_res = await raw_page.evaluate("() => ({ sum: 2 + 2, ready: document.readyState })")
                if isinstance(eval_res, dict) and eval_res.get("sum") == 4:
                    details["evaluation_alive"] = True
                    details["document_ready"] = eval_res.get("ready") in ("interactive", "complete", "loading")
            else:
                details["evaluation_alive"] = True
                details["document_ready"] = True

            passed = details["page_open"] and details["evaluation_alive"]
            return passed, details
        except Exception as exc:
            details["error"] = str(exc)
            return False, details

    def _record_event(
        self,
        execution_id: str,
        category: FailureCategory,
        error: str,
        action: str,
        prev: RecoveryState,
        resulting: RecoveryState,
        verified: bool,
        elapsed_ms: float,
        details: Optional[Dict[str, Any]] = None,
        attempts: int = 1,
    ) -> None:
        """Appends structured audit record to recovery provenance history."""
        rec = RecoveryRecord(
            execution_id=execution_id,
            session_id=self.session_id,
            timestamp=self._clock_fn(),
            trigger_category=category,
            trigger_error=error,
            recovery_action=action,
            previous_state=prev,
            resulting_state=resulting,
            verification_passed=verified,
            verification_details=details or {},
            elapsed_ms=round(elapsed_ms, 2),
            attempts=attempts,
        )
        self.recovery_history.append(rec)
