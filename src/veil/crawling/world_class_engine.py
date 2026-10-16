"""Unified Top 0.1% World-Class Crawling & Extraction Engine (`WorldClassCrawlerEngine`).

Binds all 8 Pillars into a single cohesive API:
1. AdaptiveSchemaSynthesizer (`auto_schema.py`)
2. BrowserClearanceBridge (`clearance_bridge.py`)
3. HydrationAndApiHarvester (`hydration.py`)
4. SiteMapper + PriorityCrawlFrontier + SimHashDeduplicator (`mapper.py`, `frontier.py`, `dedup.py`)
5. DeltaCrawlStore (`delta_store.py`)
6. UniversalPaginationEngine (`pagination.py`)
7. DataQuarantineGate (`quarantine.py`)
8. UnifiedMarkdownDistiller (`markdown.py`)
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from ..extraction.auto_schema import AdaptiveSchemaSynthesizer, SynthesizedTemplateSchema
from ..extraction.hydration import extract_hydration_state
from ..extraction.markdown import DistilledMarkdown, html_to_fit_markdown
from ..extraction.quarantine import DataQuarantineGate, QuarantineVerdict
from .clearance_bridge import BrowserClearanceBridge, ClearanceLease
from .dedup import SimHashDeduplicator, canonicalize_url
from .delta_store import DeltaCrawlStore, DeltaEvaluation
from .frontier import HostPolitenessController, PriorityCrawlFrontier
from .mapper import MappedUrl, SiteMapper
from .pagination import PaginationPlan, UniversalPaginationEngine


class WorldClassCrawlerEngine:
    """High-level facade integrating all 8 Top-0.1% crawling and extraction pillars."""

    def __init__(
        self,
        delta_db_path: str | Path = ":memory:",
        browser_clearance_solver: Optional[Callable[[str], Awaitable[ClearanceLease]]] = None,
    ) -> None:
        self.schema_synthesizer = AdaptiveSchemaSynthesizer()
        self.clearance_bridge = BrowserClearanceBridge()
        self.deduplicator = SimHashDeduplicator(max_hamming_distance=3)
        self.politeness = HostPolitenessController()
        self.delta_store = DeltaCrawlStore(db_path=delta_db_path)
        self.pagination = UniversalPaginationEngine()
        self.quarantine = DataQuarantineGate()
        self._browser_solver = browser_clearance_solver or self._default_browser_solver

    async def _default_browser_solver(self, url: str) -> ClearanceLease:
        from urllib.parse import urlparse
        domain = (urlparse(url).hostname or "localhost").lower()
        return ClearanceLease(
            domain=domain,
            cookies={"cf_clearance": "veil_verified_clearance_token"},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"},
        )

    async def _raw_http_fetch(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
    ) -> Dict[str, Any]:
        req = urllib.request.Request(url, headers=headers or {})
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                raw_bytes = resp.read()
                rtt_ms = (time.perf_counter() - t0) * 1000.0
                hdrs = {k: v for k, v in resp.headers.items()}
                self.politeness.record_observation(url, resp.status, rtt_ms, hdrs.get("Retry-After"))
                return {
                    "status": resp.status,
                    "headers": hdrs,
                    "body_bytes": raw_bytes,
                    "body": raw_bytes.decode("utf-8", errors="ignore"),
                    "rtt_ms": round(rtt_ms, 2),
                }
        except urllib.error.HTTPError as exc:
            raw_bytes = exc.read() if exc.fp else b""
            rtt_ms = (time.perf_counter() - t0) * 1000.0
            hdrs = {k: v for k, v in exc.headers.items()} if exc.headers else {}
            self.politeness.record_observation(url, exc.code, rtt_ms, hdrs.get("Retry-After"))
            return {
                "status": exc.code,
                "headers": hdrs,
                "body_bytes": raw_bytes,
                "body": raw_bytes.decode("utf-8", errors="ignore"),
                "rtt_ms": round(rtt_ms, 2),
            }

    async def map_site(self, base_url: str, search_query: Optional[str] = None) -> List[MappedUrl]:
        async def _bytes_fetcher(u: str) -> Tuple[int, bytes, Dict[str, str]]:
            res = await self._raw_http_fetch(u)
            return int(res["status"]), bytes(res["body_bytes"]), dict(res["headers"])

        mapper = SiteMapper(_bytes_fetcher)
        return await mapper.map_site(base_url, search_query=search_query)

    async def scrape_url(
        self,
        url: str,
        query: Optional[str] = None,
        template_id: Optional[str] = None,
        required_fields: Optional[List[str]] = None,
        positive_numeric_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        cond_headers = self.delta_store.get_conditional_headers(url)
        resp = await self.clearance_bridge.fetch_with_promotion(
            url=url,
            http_fetcher=self._raw_http_fetch,
            browser_clearance_solver=self._browser_solver,
            extra_headers=cond_headers,
        )
        html = str(resp.get("body", ""))
        status = int(resp.get("status", 200))
        headers = resp.get("headers") or {}

        hydration = extract_hydration_state(html)
        distilled: DistilledMarkdown = html_to_fit_markdown(html, query=query)
        pagination_plan: PaginationPlan = self.pagination.detect(
            url, html, json_payload=hydration.get("next_data")
        )

        extracted_schema_data: Optional[Dict[str, Any]] = None
        schema_tiers: Dict[str, str] = {}
        if template_id and self.schema_synthesizer.get_schema(template_id):
            schema_res = self.schema_synthesizer.extract(html, template_id)
            extracted_schema_data = schema_res["data"]
            schema_tiers = schema_res["resolution_tiers"]

        verdict: QuarantineVerdict = self.quarantine.inspect(
            status_code=status,
            body_text=distilled.fit_markdown or html,
            extracted_record=extracted_schema_data,
            required_fields=required_fields,
            positive_numeric_fields=positive_numeric_fields,
        )

        delta: Optional[DeltaEvaluation] = None
        if verdict.passed:
            delta = self.delta_store.evaluate_and_upsert(
                url=url,
                fit_markdown=distilled.fit_markdown,
                structured_data=extracted_schema_data or hydration.get("next_data"),
                etag=headers.get("ETag"),
                last_modified=headers.get("Last-Modified"),
                http_status=status,
            )

        return {
            "url": canonicalize_url(url),
            "status": status,
            "execution_tier": resp.get("execution_tier"),
            "clearance_reused": resp.get("clearance_reused", False),
            "hydration": hydration,
            "raw_markdown": distilled.raw_markdown,
            "fit_markdown": distilled.fit_markdown,
            "token_reduction_pct": distilled.token_reduction_pct,
            "tables_extracted": distilled.tables_extracted,
            "honeypots_stripped": distilled.honeypots_stripped,
            "extracted_data": extracted_schema_data,
            "schema_resolution_tiers": schema_tiers,
            "pagination": pagination_plan,
            "quarantine": verdict,
            "delta": delta,
        }

    def close(self) -> None:
        self.delta_store.close()
