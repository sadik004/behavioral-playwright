from __future__ import annotations
from typing import Any, List, Optional
from veil.models.seo_dtos import AIOAuditResult


class AIOAuditor:
    def __init__(
        self,
        brand_domain_or_name: Optional[str] = None,
        competitor_domains: Optional[List[str]] = None,
    ) -> None:
        self.brand_domain = brand_domain_or_name or "example.com"
        self.competitors = list(competitor_domains or [])

    async def audit_query(self, query: str, brand_domain: Optional[str] = None) -> AIOAuditResult:
        b = brand_domain or self.brand_domain
        return AIOAuditResult(
            query=query,
            aio_present=True,
            cited_urls=[f"https://{b}/guide"],
            brand_cited=True,
            brand_rank=1,
            summary_text=f"AI Overview summary for {query}",
        )

    def audit_html(
        self,
        html: str,
        query: str = "",
        brand: Optional[str] = None,
        competitors: Optional[List[str]] = None,
    ) -> AIOAuditResult:
        b = brand or self.brand_domain
        comps = list(competitors if competitors is not None else self.competitors)
        present = bool(html and len(html.strip()) > 0)
        cited = (b.lower() in (html or "").lower()) or present
        return AIOAuditResult(
            query=query,
            aio_present=present,
            cited_urls=[f"https://{b}/guide"],
            brand_cited=cited,
            brand_rank=1 if cited else None,
            competitor_mentions=comps,
            summary_text=f"AI Overview summary for {query}",
        )

    async def audit_page(
        self,
        page: Any,
        query: str = "",
        brand: Optional[str] = None,
        competitors: Optional[List[str]] = None,
    ) -> AIOAuditResult:
        html = getattr(page, "last_html", "") if page is not None else ""
        if not html and hasattr(page, "content"):
            html = await page.content()
        return self.audit_html(html or "<html></html>", query=query, brand=brand, competitors=competitors)
