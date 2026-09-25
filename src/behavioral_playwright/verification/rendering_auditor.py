"""
Client-Side Rendering (CSR) Drift Auditor.
Compares initial static SSR/HTML payloads against post-hydration CSR DOM states,
detecting indexing hazards, hydration discrepancies, and missing search signals.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, List, Optional, Set
from urllib.parse import urlparse

from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.seo_dtos import CSRDriftReport

logger = get_logger("verification.rendering_auditor")

try:
    from bs4 import BeautifulSoup  # type: ignore
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

try:
    from curl_cffi.requests import AsyncSession  # type: ignore
    _HAS_CURL_CFFI = True
except ImportError:
    _HAS_CURL_CFFI = False


class CSRRenderingDriftAuditor:
    """
    Evaluates rendering divergence between raw server-delivered HTML and the client-side hydrated DOM.
    Quantifies token-level drift and detects critical SEO signals injected exclusively via CSR.
    """

    def __init__(self, drift_threshold: float = 0.25) -> None:
        self.drift_threshold = max(0.0, min(1.0, drift_threshold))

    @staticmethod
    def _extract_tokens(text: str) -> Set[str]:
        """Extracts normalized alphanumeric token set for O(1) Jaccard calculation."""
        if not text:
            return set()
        return set(re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower()))

    def audit_html_drift(
        self,
        raw_html: str,
        rendered_html: str,
        url: Optional[str] = None,
    ) -> CSRDriftReport:
        """
        Compares static HTML against hydrated DOM HTML to calculate rendering drift.
        """
        raw_html_bytes = len(raw_html.encode("utf-8")) if raw_html else 0
        rendered_html_bytes = len(rendered_html.encode("utf-8")) if rendered_html else 0

        missing_in_raw: List[str] = []

        if _HAS_BS4:
            soup_raw = BeautifulSoup(raw_html or "", "html.parser")
            soup_rendered = BeautifulSoup(rendered_html or "", "html.parser")

            # 1. DOM node counts
            raw_nodes = len(soup_raw.find_all())
            rendered_nodes = len(soup_rendered.find_all())

            # 2. Text extraction
            raw_text = soup_raw.get_text(separator=" ", strip=True)
            rendered_text = soup_rendered.get_text(separator=" ", strip=True)

            # 3. H1 Headings check
            raw_h1s = [h.get_text(strip=True) for h in soup_raw.find_all("h1") if h.get_text(strip=True)]
            rendered_h1s = [h.get_text(strip=True) for h in soup_rendered.find_all("h1") if h.get_text(strip=True)]
            if rendered_h1s and not raw_h1s:
                missing_in_raw.append("H1 headings rendered exclusively via CSR")

            # 4. Links comparison (anchors with href)
            raw_links = {a.get("href", "").strip() for a in soup_raw.find_all("a", href=True) if a.get("href", "").strip()}
            rendered_links = {a.get("href", "").strip() for a in soup_rendered.find_all("a", href=True) if a.get("href", "").strip()}
            client_only_links = rendered_links - raw_links
            if len(client_only_links) >= 3 and len(client_only_links) > (len(raw_links) * 0.4):
                missing_in_raw.append(f"{len(client_only_links)} links injected exclusively via CSR")

            # 5. Page Title check
            raw_title = soup_raw.title.string.strip() if soup_raw.title and soup_raw.title.string else ""
            rendered_title = soup_rendered.title.string.strip() if soup_rendered.title and soup_rendered.title.string else ""
            if rendered_title and not raw_title:
                missing_in_raw.append("Page <title> tag injected via CSR")

            # 6. JSON-LD structured schemas
            raw_jsonld = len(soup_raw.find_all("script", type="application/ld+json"))
            rendered_jsonld = len(soup_rendered.find_all("script", type="application/ld+json"))
            if rendered_jsonld > raw_jsonld:
                missing_in_raw.append(f"{rendered_jsonld - raw_jsonld} JSON-LD schema(s) injected via CSR")

            # 7. Empty SPA Root detection
            spa_indicators = soup_raw.select("div#root:empty, div#__next:empty, div#app:empty, app-root:empty")
            if spa_indicators and len(rendered_text) > 200:
                missing_in_raw.append("Empty SPA container detected in static HTML")

        else:
            # Fallback regex parsing
            raw_nodes = len(re.findall(r"<[a-zA-Z][^>]*>", raw_html or ""))
            rendered_nodes = len(re.findall(r"<[a-zA-Z][^>]*>", rendered_html or ""))
            raw_text = re.sub(r"<[^>]+>", " ", raw_html or "").strip()
            rendered_text = re.sub(r"<[^>]+>", " ", rendered_html or "").strip()

            if "<h1" in (rendered_html or "") and "<h1" not in (raw_html or ""):
                missing_in_raw.append("H1 headings rendered exclusively via CSR")
            if "<title>" in (rendered_html or "") and "<title>" not in (raw_html or ""):
                missing_in_raw.append("Page <title> tag injected via CSR")

        raw_text_length = len(raw_text)
        rendered_text_length = len(rendered_text)

        # Token-based Jaccard similarity
        tokens_raw = self._extract_tokens(raw_text)
        tokens_rendered = self._extract_tokens(rendered_text)

        if not tokens_rendered and not tokens_raw:
            drift_ratio = 0.0
        elif not tokens_rendered and tokens_raw:
            drift_ratio = 1.0
        else:
            intersection = tokens_raw.intersection(tokens_rendered)
            union = tokens_raw.union(tokens_rendered)
            jaccard = len(intersection) / len(union) if union else 1.0
            drift_ratio = round(max(0.0, min(1.0, 1.0 - jaccard)), 4)

        # Detect hydration drift
        hydration_drift_detected = (
            drift_ratio >= self.drift_threshold
            or len(missing_in_raw) > 0
            or (rendered_nodes > 0 and raw_nodes == 0)
        )

        # Risk level determination
        if drift_ratio >= 0.70 or ("H1 headings rendered exclusively via CSR" in missing_in_raw and "Empty SPA container detected in static HTML" in missing_in_raw):
            seo_risk = "CRITICAL"
        elif drift_ratio >= 0.45 or len(missing_in_raw) >= 2:
            seo_risk = "HIGH"
        elif drift_ratio >= 0.20 or len(missing_in_raw) >= 1:
            seo_risk = "MEDIUM"
        else:
            seo_risk = "LOW"

        return CSRDriftReport(
            url=url,
            raw_html_bytes=raw_html_bytes,
            rendered_html_bytes=rendered_html_bytes,
            raw_dom_nodes=raw_nodes,
            rendered_dom_nodes=rendered_nodes,
            raw_text_length=raw_text_length,
            rendered_text_length=rendered_text_length,
            drift_ratio=drift_ratio,
            missing_in_raw=missing_in_raw,
            hydration_drift_detected=hydration_drift_detected,
            seo_indexation_risk=seo_risk,
        )

    async def fetch_static_html(self, url: str, timeout: float = 10.0) -> str:
        """Fetches raw initial HTML payload over HTTP without executing JavaScript."""
        if _HAS_CURL_CFFI:
            try:
                async with AsyncSession(impersonate="chrome120") as session:
                    resp = await session.get(url, timeout=timeout)
                    return resp.text
            except Exception as exc:
                logger.debug(f"[CSRDriftAuditor] curl_cffi fetch failed for {url}: {exc}")

        # Fallback urllib
        try:
            import urllib.request

            def _fetch() -> str:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return response.read().decode("utf-8", errors="ignore")

            return await asyncio.to_thread(_fetch)
        except Exception as exc:
            logger.warning(f"[CSRDriftAuditor] urllib fetch failed for {url}: {exc}")
            return ""

    async def audit_url_drift(
        self,
        url: str,
        page: Optional[Any] = None,
        timeout: float = 15.0,
    ) -> CSRDriftReport:
        """
        Audits live URL by fetching raw static HTML and comparing against the browser DOM.
        """
        raw_html = await self.fetch_static_html(url, timeout=timeout)

        rendered_html = ""
        if page is not None:
            if hasattr(page, "goto") and hasattr(page, "content"):
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
                    rendered_html = await page.content()
                except Exception as exc:
                    logger.warning(f"[CSRDriftAuditor] Page navigation error: {exc}")
                    if hasattr(page, "content"):
                        rendered_html = await page.content()
            elif hasattr(page, "content"):
                rendered_html = await page.content()
        else:
            from behavioral_playwright.facade import BP
            async with BP() as bp:
                await bp.goto(url)
                if bp.page:
                    raw_p = getattr(bp.page, "raw_page", bp.page)
                    rendered_html = await raw_p.content()

        return self.audit_html_drift(raw_html=raw_html, rendered_html=rendered_html, url=url)


RenderingDriftAuditor = CSRRenderingDriftAuditor

__all__ = ["CSRRenderingDriftAuditor", "RenderingDriftAuditor"]
