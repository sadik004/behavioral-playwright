from __future__ import annotations

from typing import Any, List, Optional, Sequence
from .aio_auditor import AIOAuditor
from .cannibalization import SERPCannibalizationEngine
from .paa_miner import PAAMiner
from .rendering_drift import CSRRenderingDriftAuditor
from .suggest_miner import GoogleSuggestMiner


class SEOMiningEngine:
    def __init__(self) -> None:
        self.paa = PAAMiner()
        self.suggest = GoogleSuggestMiner()
        self.cannibalization = SERPCannibalizationEngine()
        self.aio = AIOAuditor()
        self.drift = CSRRenderingDriftAuditor()

    async def mine_paa(self, page: Any = None, query: Optional[str] = None, max_depth: int = 2) -> List[Any]:
        q = query or "web scraping"
        return await self.paa.mine(q, max_depth=max_depth, page=page)

    async def check_cannibalization(
        self,
        query_a: str,
        query_b: str,
        urls_a: Optional[Sequence[str]] = None,
        urls_b: Optional[Sequence[str]] = None,
        threshold: float = 0.35,
    ) -> Any:
        ua = list(urls_a) if urls_a else [f"https://example.com/{query_a.replace(' ', '-')}"]
        ub = list(urls_b) if urls_b else [f"https://example.com/{query_b.replace(' ', '-')}"]
        return self.cannibalization.compute_overlap(query_a, query_b, ua, ub, threshold=threshold)
