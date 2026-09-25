"""
Google AI Overview (AIO) & Answer Engine Optimization (AEO) Audit Engine.
Detects generative AI summary cards, extracts citations, and computes brand/competitor presence.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional

from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.seo_dtos import AIOAuditResult

logger = get_logger("mining.aio")

try:
    from bs4 import BeautifulSoup  # type: ignore
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


class AIOAuditor:
    """
    Audits Google SERPs for Search Generative Experience (SGE) / AI Overview presence.
    Extracts summary markdown/text, source citations, brand citations, and competitor ranks.
    """

    def __init__(self, brand_domain_or_name: Optional[str] = None, competitor_domains: Optional[List[str]] = None) -> None:
        self.default_brand = brand_domain_or_name
        self.default_competitors = competitor_domains or []

    def audit_html(
        self,
        html_content: str,
        query: str,
        brand: Optional[str] = None,
        competitors: Optional[List[str]] = None,
    ) -> AIOAuditResult:
        """Audits static HTML content for AI Overview card presence and citations."""
        target_brand = (brand or self.default_brand or "").lower().strip()
        target_competitors = [c.lower().strip() for c in (competitors or self.default_competitors)]

        has_aio = False
        summary_text: Optional[str] = None
        citations: List[str] = []

        if not html_content:
            return AIOAuditResult(
                query=query,
                has_aio_card=False,
                summary_text=None,
                citations=[],
                brand_cited=False,
                brand_rank=None,
                competitors_cited=[]
            )

        if _HAS_BS4:
            soup = BeautifulSoup(html_content, "html.parser")

            # Check known AIO container markers
            aio_container = soup.select_one(
                "div.YzSd6, div[data-attrid*='description'], div[data-attrid*='wa:'], "
                "div[data-attrid*='ai_overview'], div[data-attrid*='overview'], div[data-attrid*='ai'], "
                "div[jsname='pa3P8e'], div.x54gtf, div.AUQ4Eb, div[data-sge], div.MjjYud:has(div[data-attrid*='ai'])"
            )

            # Secondary text check if container attribute isn't directly matched
            if not aio_container:
                for text_node in soup.find_all(string=re.compile(r"AI Overview|Generative AI is experimental|AI-generated|AI Summary", re.I)):
                    parent = text_node.find_parent("div")
                    if parent:
                        aio_container = parent
                        break

            if aio_container:
                has_aio = True
                # Extract summary text
                summary_elem = aio_container.select_one("div.xpdopen, div.wDYxhc, div.LGOjhe, div.kno-rdesc, div.BNeawe")
                if summary_elem:
                    summary_text = summary_elem.get_text(separator=" ", strip=True)
                else:
                    summary_text = aio_container.get_text(separator=" ", strip=True)[:1000]

                # Extract citations
                for a_tag in aio_container.select("a[href^='http']"):
                    href = a_tag.get("href", "")
                    if href and href not in citations and not href.startswith("https://support.google.com"):
                        citations.append(href)

        else:
            # Regex fallback
            if "AI Overview" in html_content or "Generative AI is experimental" in html_content or "data-attrid=\"ai_overview\"" in html_content or "YzSd6" in html_content or "data-attrid=\"wa:/description\"" in html_content:
                has_aio = True
                # Extract links in vicinity
                found_links = re.findall(r"href=[\"'](https?://(?!support\.google)[^\"']+)[\"']", html_content)
                for link in found_links[:10]:
                    if link not in citations:
                        citations.append(link)
                summary_text = "AI Overview detected on SERP (regex fallback mode)."

        # Determine brand citation and rank
        brand_cited = False
        brand_rank: Optional[int] = None
        if target_brand:
            for idx, cit in enumerate(citations, start=1):
                if target_brand in cit.lower():
                    brand_cited = True
                    brand_rank = idx
                    break
            if not brand_cited and summary_text and target_brand in summary_text.lower():
                brand_cited = True
                brand_rank = None

        # Determine competitor citations
        competitors_cited: List[str] = []
        for comp in target_competitors:
            if not comp:
                continue
            for cit in citations:
                if comp in cit.lower():
                    if cit not in competitors_cited:
                        competitors_cited.append(cit)
            if not any(comp in c.lower() for c in competitors_cited) and summary_text and comp in summary_text.lower():
                if comp not in competitors_cited:
                    competitors_cited.append(comp)

        return AIOAuditResult(
            query=query,
            has_aio_card=has_aio,
            summary_text=summary_text,
            citations=citations,
            brand_cited=brand_cited,
            brand_rank=brand_rank,
            competitors_cited=competitors_cited
        )

    async def audit_page(
        self,
        page: Any,
        query: str,
        brand: Optional[str] = None,
        competitors: Optional[List[str]] = None,
    ) -> AIOAuditResult:
        """Audits an active Playwright page (navigating to Google query if needed)."""
        if hasattr(page, "goto") and hasattr(page, "url") and "google.com" not in page.url:
            from urllib.parse import quote_plus
            url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en"
            await page.goto(url, wait_until="domcontentloaded")

        html_content = ""
        if hasattr(page, "content"):
            html_content = await page.content()
        elif hasattr(page, "inner_html"):
            html_content = await page.inner_html("body")

        return self.audit_html(
            html_content=html_content,
            query=query,
            brand=brand,
            competitors=competitors
        )


__all__ = ["AIOAuditor"]
