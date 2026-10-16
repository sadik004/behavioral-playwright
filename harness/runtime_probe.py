"""Trusted Runtime Probe & Cryptographic Provenance Anchor for behavioral-playwright.

Provides tamper-evident observation of real Playwright browser executions:
1. Validates genuine Playwright Page identity and active browser connection.
2. Captures real-time DOM states, URLs, and page titles directly from the engine.
3. Computes immediate SHA-256 cryptographic digests of generated artifacts.
4. Generates execution-bound, session-bound, and evidence-bound UUIDs.
5. Seals observation bundles with an ephemeral in-memory HMAC signature.
"""
from __future__ import annotations

import hashlib
import hmac
import inspect
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ProvenanceError(Exception):
    """Raised when runtime evidence or page object fails provenance validation."""


@dataclass(frozen=True)
class RuntimeEvidence:
    """Immutable, cryptographically sealed runtime observation bundle."""
    execution_id: str
    session_id: str
    evidence_id: str
    created_at: float
    observed_url: str
    observed_title: str
    dom_observed_state: Dict[str, str]
    artifact_digests: Dict[str, str]
    browser_pid: Optional[int]
    probe_signature: str


class TrustedRuntimeProbe:
    """Authoritative runtime observation probe directly attached to live browser engines."""

    # Ephemeral 256-bit secret generated per harness run in memory (never written to disk)
    _PROBE_SECRET: bytes = os.urandom(32)

    @classmethod
    def _compute_evidence_mac(
        cls,
        execution_id: str,
        session_id: str,
        evidence_id: str,
        created_at: float,
        observed_url: str,
        observed_title: str,
        dom_observed_state: Dict[str, str],
        artifact_digests: Dict[str, str],
    ) -> str:
        """Computes HMAC-SHA256 signature over all canonical evidence fields."""
        canonical_str = (
            f"exec:{execution_id}|sess:{session_id}|ev:{evidence_id}|"
            f"time:{created_at:.6f}|url:{observed_url}|title:{observed_title}|"
            f"dom:{sorted(dom_observed_state.items())}|"
            f"art:{sorted(artifact_digests.items())}"
        )
        return hmac.new(cls._PROBE_SECRET, canonical_str.encode("utf-8"), hashlib.sha256).hexdigest()

    @classmethod
    def verify_evidence_signature(cls, evidence: RuntimeEvidence) -> bool:
        """Cryptographically verifies that evidence was produced by this trusted probe without tampering."""
        if not isinstance(evidence, RuntimeEvidence):
            return False
        expected_mac = cls._compute_evidence_mac(
            execution_id=evidence.execution_id,
            session_id=evidence.session_id,
            evidence_id=evidence.evidence_id,
            created_at=evidence.created_at,
            observed_url=evidence.observed_url,
            observed_title=evidence.observed_title,
            dom_observed_state=evidence.dom_observed_state,
            artifact_digests=evidence.artifact_digests,
        )
        return hmac.compare_digest(evidence.probe_signature, expected_mac)

    @classmethod
    def is_genuine_playwright_page(cls, page: Any) -> bool:
        """Determines if target object is an authentic Playwright Page class."""
        if page is None:
            return False
        cls_name = getattr(page.__class__, "__name__", "")
        cls_module = getattr(page.__class__, "__module__", "")
        if cls_name == "Page" and "playwright." in cls_module:
            return True
        try:
            from playwright.sync_api import Page as SyncPage
            from playwright.async_api import Page as AsyncPage
            if isinstance(page, (SyncPage, AsyncPage)):
                return True
        except ImportError:
            pass
        return False

    @classmethod
    def extract_real_playwright_page(cls, target: Any) -> Optional[Any]:
        """Unwraps adapter or helper objects to extract the underlying genuine Playwright Page."""
        if target is None:
            return None
        if cls.is_genuine_playwright_page(target):
            return target
        # Check standard attributes
        for attr in ("_page", "page", "_real_page", "playwright_page"):
            if hasattr(target, attr):
                val = getattr(target, attr)
                if cls.is_genuine_playwright_page(val):
                    return val
        # Check closure cells of methods (e.g. LivePageAdapter in live tests)
        for method_name in ("is_closed", "query_selector", "title", "url"):
            fn = getattr(target, method_name, None)
            if fn and hasattr(fn, "__closure__") and fn.__closure__:
                for cell in fn.__closure__:
                    try:
                        contents = cell.cell_contents
                        if cls.is_genuine_playwright_page(contents):
                            return contents
                    except (ValueError, ReferenceError):
                        pass
        return None

    @classmethod
    def validate_playwright_page(cls, page: Any) -> Tuple[bool, str]:
        """Strictly validates that page is (or directly wraps) a genuine, active Playwright Page object."""
        if page is None:
            return False, "TARGET_PAGE_IS_NONE: No live page object supplied."

        # 1. Type identity validation: Must be genuine Playwright Page class or unwrap to one
        real_page = cls.extract_real_playwright_page(page)
        if real_page is None and not cls.is_genuine_playwright_page(page):
            type_module = getattr(type(page), "__module__", "")
            type_name = getattr(type(page), "__name__", "")
            return False, (
                f"FORGED_PAGE_OBJECT: Target live_page is not a genuine Playwright Page instance! "
                f"Detected mock/duck type: {type_module}.{type_name}"
            )

        target_page = real_page or page

        # 2. Browser context & connection validation
        context = getattr(target_page, "context", None)
        if context is None:
            return False, "FORGED_CONTEXT: page.context is None. Page is detached or fabricated."

        browser = getattr(context, "browser", None)
        if browser is None:
            return False, "FORGED_BROWSER: page.context.browser is None. Context lacks active browser."

        try:
            is_connected = browser.is_connected()
            if not is_connected:
                return False, "DISCONNECTED_BROWSER: Underlying Playwright browser is disconnected."
        except Exception as e:
            return False, f"BROWSER_CHECK_FAILED: Failed to check browser.is_connected(): {e}"

        # 3. Page active state
        try:
            is_closed_fn = getattr(page, "is_closed", None) or getattr(target_page, "is_closed", None)
            if callable(is_closed_fn) and is_closed_fn():
                return False, "BROWSER_CLOSED_BEFORE_VERIFICATION: Live page is already closed."
        except Exception as e:
            return False, f"PAGE_CLOSED_CHECK_FAILED: {e}"

        return True, "Genuine active Playwright Page instance verified."

    @classmethod
    def capture_observation(
        cls,
        page: Any,
        expected_url: Optional[str] = None,
        expected_title: Optional[str] = None,
        expected_dom_selector: Optional[str] = None,
        expected_dom_text: Optional[str] = None,
        artifact_paths: Optional[List[str]] = None,
        execution_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> RuntimeEvidence:
        """Captures fresh, synchronous runtime observation directly from a genuine Playwright Page."""
        is_valid, reason = cls.validate_playwright_page(page)
        if not is_valid:
            raise ProvenanceError(reason)

        observed_url = getattr(page, "url", "")
        if callable(observed_url):
            observed_url = observed_url()

        title_val = page.title() if callable(getattr(page, "title", None)) else ""

        # Query live DOM state
        dom_observed: Dict[str, str] = {}
        if expected_dom_selector:
            el = page.query_selector(expected_dom_selector)
            if el is None:
                raise ProvenanceError(
                    f"DOM_EVIDENCE_FORGERY: Selector '{expected_dom_selector}' not found in live page DOM."
                )
            text_content = el.inner_text() if callable(getattr(el, "inner_text", None)) else ""
            dom_observed[expected_dom_selector] = text_content
            if expected_dom_text and expected_dom_text not in text_content:
                raise ProvenanceError(
                    f"DOM_TEXT_MISMATCH: Live text '{text_content}' does not match expected '{expected_dom_text}'."
                )

        # Immediate SHA-256 digesting of all artifacts at capture time
        digests: Dict[str, str] = {}
        if artifact_paths:
            for art in artifact_paths:
                p = Path(art).resolve()
                if not p.exists():
                    raise ProvenanceError(f"FAKE_ARTIFACT_NONEXISTENT: Artifact '{art}' does not exist on disk.")
                if p.stat().st_size == 0:
                    raise ProvenanceError(f"EMPTY_ARTIFACT: Artifact '{art}' has 0 bytes.")
                content_bytes = p.read_bytes()
                digests[str(p)] = hashlib.sha256(content_bytes).hexdigest()

        # Capture browser PID if available
        target_page = cls.extract_real_playwright_page(page) or page
        browser_pid = None
        try:
            ctx = getattr(page, "context", None) or getattr(target_page, "context", None)
            if ctx:
                br = getattr(ctx, "browser", None)
                if br:
                    proc = getattr(br, "_process", None)
                    if proc and hasattr(proc, "pid"):
                        browser_pid = proc.pid
        except Exception:
            pass

        exec_id = execution_id or f"exec-{uuid.uuid4().hex[:12]}"
        sess_id = session_id or f"sess-{uuid.uuid4().hex[:12]}"
        ev_id = f"ev-{uuid.uuid4().hex[:12]}"
        created_at = time.time()

        signature = cls._compute_evidence_mac(
            execution_id=exec_id,
            session_id=sess_id,
            evidence_id=ev_id,
            created_at=created_at,
            observed_url=observed_url,
            observed_title=title_val,
            dom_observed_state=dom_observed,
            artifact_digests=digests,
        )

        return RuntimeEvidence(
            execution_id=exec_id,
            session_id=sess_id,
            evidence_id=ev_id,
            created_at=created_at,
            observed_url=observed_url,
            observed_title=title_val,
            dom_observed_state=dom_observed,
            artifact_digests=digests,
            browser_pid=browser_pid,
            probe_signature=signature,
        )

    @classmethod
    async def capture_observation_async(
        cls,
        page: Any,
        expected_url: Optional[str] = None,
        expected_title: Optional[str] = None,
        expected_dom_selector: Optional[str] = None,
        expected_dom_text: Optional[str] = None,
        artifact_paths: Optional[List[str]] = None,
        execution_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> RuntimeEvidence:
        """Captures fresh, asynchronous runtime observation directly from an async Playwright Page."""
        is_valid, reason = cls.validate_playwright_page(page)
        if not is_valid:
            raise ProvenanceError(reason)

        observed_url = page.url
        title_val = await page.title()

        dom_observed: Dict[str, str] = {}
        if expected_dom_selector:
            el = await page.query_selector(expected_dom_selector)
            if el is None:
                raise ProvenanceError(
                    f"DOM_EVIDENCE_FORGERY: Selector '{expected_dom_selector}' not found in live page DOM."
                )
            text_content = await el.inner_text()
            dom_observed[expected_dom_selector] = text_content
            if expected_dom_text and expected_dom_text not in text_content:
                raise ProvenanceError(
                    f"DOM_TEXT_MISMATCH: Live text '{text_content}' does not match expected '{expected_dom_text}'."
                )

        digests: Dict[str, str] = {}
        if artifact_paths:
            for art in artifact_paths:
                p = Path(art).resolve()
                if not p.exists():
                    raise ProvenanceError(f"FAKE_ARTIFACT_NONEXISTENT: Artifact '{art}' does not exist on disk.")
                if p.stat().st_size == 0:
                    raise ProvenanceError(f"EMPTY_ARTIFACT: Artifact '{art}' has 0 bytes.")
                content_bytes = p.read_bytes()
                digests[str(p)] = hashlib.sha256(content_bytes).hexdigest()

        browser_pid = None
        try:
            proc = getattr(page.context.browser, "_process", None)
            if proc and hasattr(proc, "pid"):
                browser_pid = proc.pid
        except Exception:
            pass

        exec_id = execution_id or f"exec-{uuid.uuid4().hex[:12]}"
        sess_id = session_id or f"sess-{uuid.uuid4().hex[:12]}"
        ev_id = f"ev-{uuid.uuid4().hex[:12]}"
        created_at = time.time()

        signature = cls._compute_evidence_mac(
            execution_id=exec_id,
            session_id=sess_id,
            evidence_id=ev_id,
            created_at=created_at,
            observed_url=observed_url,
            observed_title=title_val,
            dom_observed_state=dom_observed,
            artifact_digests=digests,
        )

        return RuntimeEvidence(
            execution_id=exec_id,
            session_id=sess_id,
            evidence_id=ev_id,
            created_at=created_at,
            observed_url=observed_url,
            observed_title=title_val,
            dom_observed_state=dom_observed,
            artifact_digests=digests,
            browser_pid=browser_pid,
            probe_signature=signature,
        )
