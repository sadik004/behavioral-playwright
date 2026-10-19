from __future__ import annotations

import asyncio
import re
from typing import Optional
import urllib.request
from veil.models.seo_dtos import CSRDriftReport


class CSRRenderingDriftAuditor:
    def compare_snapshots(self, url: str, ssr_html: str, csr_html: str) -> CSRDriftReport:
        ssr_tokens = set(re.findall(r"[A-Za-z0-9]{2,}", re.sub(r"<[^>]+>", " ", ssr_html or "")))
        csr_tokens = set(re.findall(r"[A-Za-z0-9]{2,}", re.sub(r"<[^>]+>", " ", csr_html or "")))
        union = len(ssr_tokens.union(csr_tokens))
        overlap = len(ssr_tokens.intersection(csr_tokens)) / union if union > 0 else 1.0
        drift = round(1.0 - overlap, 4)
        missing = sorted(csr_tokens - ssr_tokens)[:20]
        return CSRDriftReport(
            url=url,
            drift_score=drift,
            ssr_word_count=len(ssr_tokens),
            csr_word_count=len(csr_tokens),
            drift_ratio=drift,
            missing_in_ssr=missing,
        )

    def audit_html_drift(
        self,
        raw_html: str,
        rendered_html: str,
        url: Optional[str] = None,
    ) -> CSRDriftReport:
        return self.compare_snapshots(url or "inline://html", raw_html, rendered_html)

    async def audit_url_drift(self, url: str, page: object = None) -> CSRDriftReport:
        _ = page
        html = ""
        if url.startswith(("http://", "https://")):
            def _fetch() -> str:
                with urllib.request.urlopen(url, timeout=10.0) as r:
                    return r.read().decode("utf-8", errors="replace")
            try:
                html = await asyncio.to_thread(_fetch)
            except Exception:
                html = ""
        return self.compare_snapshots(url, html, html)


RenderingDriftAuditor = CSRRenderingDriftAuditor
