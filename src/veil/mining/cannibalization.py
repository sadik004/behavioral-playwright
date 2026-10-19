from __future__ import annotations

from typing import List, Optional, Sequence
from veil.models.seo_dtos import CannibalizationReport


class SERPCannibalizationEngine:
    def __init__(self, merge_threshold: float = 0.40) -> None:
        self.merge_threshold = float(merge_threshold)

    def compute_overlap(
        self,
        query_a: str,
        query_b: str,
        urls_a: Optional[Sequence[str]] = None,
        urls_b: Optional[Sequence[str]] = None,
        threshold: Optional[float] = None,
    ) -> CannibalizationReport:
        thresh = float(threshold) if threshold is not None else self.merge_threshold
        set_a = {u.strip().rstrip("/") for u in (urls_a or []) if u and u.strip()}
        set_b = {u.strip().rstrip("/") for u in (urls_b or []) if u and u.strip()}
        shared: List[str] = sorted(set_a.intersection(set_b))
        union_len = len(set_a.union(set_b))
        jaccard = round(len(shared) / union_len, 4) if union_len > 0 else 0.0
        is_cannibalized = jaccard >= thresh
        rec = "Consolidate competing pages or differentiate search intent." if is_cannibalized else "Distinct SERP intent."
        return CannibalizationReport(
            query_a=query_a,
            query_b=query_b,
            jaccard_similarity=jaccard,
            shared_urls=shared,
            is_cannibalized=is_cannibalized,
            recommendation=rec,
        )

    def evaluate_cannibalization(
        self,
        query_a: str,
        query_b: str,
        urls_a: Optional[Sequence[str]] = None,
        urls_b: Optional[Sequence[str]] = None,
        threshold: Optional[float] = None,
    ) -> CannibalizationReport:
        return self.compute_overlap(query_a=query_a, query_b=query_b, urls_a=urls_a, urls_b=urls_b, threshold=threshold)
