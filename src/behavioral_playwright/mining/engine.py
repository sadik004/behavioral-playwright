"""
Unified SEO, AEO, and GEO Mining Engine.
Integrates PAA query expansion, AI Overview audit, and SERP cannibalization analysis.
"""

from __future__ import annotations

from typing import Any, List, Optional

from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.seo_dtos import (
    AIOAuditResult,
    CannibalizationReport,
    PAANode,
)
from behavioral_playwright.mining.aio_auditor import AIOAuditor
from behavioral_playwright.mining.cannibalization import SERPCannibalizationEngine
from behavioral_playwright.mining.paa_miner import PAAMiner

logger = get_logger("mining.engine")


class SEOMiningEngine:
    """
    Unified search intelligence and Generative Engine Optimization (GEO) mining facade.
    Provides automated audit tools for modern SERPs, AI Overviews, and keyword cannibalization.
    """

    def __init__(
        self,
        brand: Optional[str] = None,
        competitors: Optional[List[str]] = None,
        cannibalization_threshold: float = 0.40,
    ) -> None:
        self.paa = PAAMiner()
        self.aio = AIOAuditor(brand_domain_or_name=brand, competitor_domains=competitors)
        self.cannibalization = SERPCannibalizationEngine(merge_threshold=cannibalization_threshold)

    async def mine_paa(
        self,
        page_or_html: Any,
        target_query: Optional[str] = None,
    ) -> List[PAANode]:
        """Mines People Also Ask nodes from a live Playwright page or static HTML."""
        if isinstance(page_or_html, str):
            return self.paa.parse_from_html(page_or_html)
        return await self.paa.extract_from_page(page_or_html, target_query=target_query)

    async def audit_aio(
        self,
        page_or_html: Any,
        query: str,
        brand: Optional[str] = None,
        competitors: Optional[List[str]] = None,
    ) -> AIOAuditResult:
        """Audits AI Overview presence, summary content, citations, and brand visibility."""
        if isinstance(page_or_html, str):
            return self.aio.audit_html(
                html_content=page_or_html,
                query=query,
                brand=brand,
                competitors=competitors,
            )
        return await self.aio.audit_page(
            page=page_or_html,
            query=query,
            brand=brand,
            competitors=competitors,
        )

    def audit_cannibalization(
        self,
        query_a: str,
        query_b: str,
        urls_a: List[str],
        urls_b: List[str],
        threshold: Optional[float] = None,
    ) -> CannibalizationReport:
        """Computes Jaccard similarity between two query SERPs and returns canonical recommendation."""
        return self.cannibalization.evaluate_cannibalization(
            query_a=query_a,
            query_b=query_b,
            urls_a=urls_a,
            urls_b=urls_b,
            threshold=threshold,
        )


__all__ = ["SEOMiningEngine", "PAAMiner", "AIOAuditor", "SERPCannibalizationEngine"]
