"""
SERP Cannibalization & Generative Engine Optimization (GEO) Overlap Analysis Engine.
Computes Jaccard distance over organic search results and recommends canonical/split strategies.
"""

from __future__ import annotations

from typing import List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.seo_dtos import CannibalizationReport

logger = get_logger("mining.cannibalization")

# Tracking and ephemeral query parameters to strip during normalization
STRIP_QUERY_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "msclkid", "ref", "source", "srsltid"
}


class SERPCannibalizationEngine:
    """
    Quantifies semantic query overlap and keyword cannibalization across organic SERPs.
    Calculates Jaccard similarity coefficient: J(A, B) = |A ∩ B| / |A ∪ B|.
    """

    def __init__(self, merge_threshold: float = 0.40) -> None:
        self.merge_threshold = max(0.0, min(1.0, merge_threshold))

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalizes destination URLs by stripping tracking parameters, fragments,
        trailing slashes, and standardizing protocol/host casings.
        """
        if not url or not isinstance(url, str):
            return ""

        try:
            parsed = urlparse(url.strip())
            if not parsed.netloc:
                return url.strip().rstrip("/")

            # Normalize query parameters by stripping UTM and tracking tags
            query_dict = parse_qs(parsed.query, keep_blank_values=False)
            filtered_query = {
                k: v for k, v in query_dict.items()
                if k.lower() not in STRIP_QUERY_PARAMS
            }

            cleaned_query = urlencode(filtered_query, doseq=True)
            cleaned_path = parsed.path.rstrip("/")

            normalized = urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                cleaned_path,
                "",  # params
                cleaned_query,
                ""   # fragment
            ))
            return normalized
        except Exception:
            return url.strip().rstrip("/")

    def calculate_jaccard(
        self,
        urls_a: List[str],
        urls_b: List[str]
    ) -> Tuple[float, List[str]]:
        """
        Calculates Jaccard similarity between two lists of SERP URLs.
        Returns: (jaccard_score, common_urls)
        """
        set_a: Set[str] = {self.normalize_url(u) for u in urls_a if self.normalize_url(u)}
        set_b: Set[str] = {self.normalize_url(u) for u in urls_b if self.normalize_url(u)}

        intersection = set_a.intersection(set_b)
        union = set_a.union(set_b)

        if not union:
            return 0.0, []

        jaccard = round(len(intersection) / len(union), 4)
        sorted_common = sorted(list(intersection))
        return jaccard, sorted_common

    def evaluate_cannibalization(
        self,
        query_a: str,
        query_b: str,
        urls_a: List[str],
        urls_b: List[str],
        threshold: Optional[float] = None
    ) -> CannibalizationReport:
        """
        Generates a CannibalizationReport with definitive engineering recommendations.
        """
        active_threshold = self.merge_threshold if threshold is None else threshold
        jaccard, common = self.calculate_jaccard(urls_a, urls_b)

        if jaccard >= active_threshold:
            recommendation = "MERGE_INTO_SINGLE_CANONICAL"
        else:
            recommendation = "SPLIT_INTO_SEPARATE_PAGES"

        return CannibalizationReport(
            query_a=query_a,
            query_b=query_b,
            jaccard_score=jaccard,
            common_urls=common,
            recommendation=recommendation
        )


__all__ = ["SERPCannibalizationEngine"]
