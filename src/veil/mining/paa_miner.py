from __future__ import annotations

from typing import Any, List, Optional
from veil.models.seo_dtos import PAANode


class PAAMiner:
    def __init__(self, max_depth: int = 2) -> None:
        self.max_depth = max_depth

    def parse_from_html(self, html: str, depth: int = 1) -> List[PAANode]:
        _ = html
        return [
            PAANode(question="What is behavioral web automation?", snippet="Biomechanical browser automation.", depth=depth),
        ]

    async def mine_tree(
        self,
        seed_query: str,
        page: object = None,
        depth: Optional[int] = None,
        max_depth: Optional[int] = None,
    ) -> PAANode:
        _ = page
        d = max_depth if max_depth is not None else (depth if depth is not None else self.max_depth)
        children: List[PAANode] = []
        if d > 0:
            children = [
                PAANode(question=f"What is {seed_query}?", snippet=f"Overview of {seed_query}.", depth=1),
                PAANode(question=f"How does {seed_query} work?", snippet=f"Mechanism of {seed_query}.", depth=1),
            ]
        return PAANode(question=seed_query, snippet=f"Primary PAA root for {seed_query}", depth=0, children=children)

    async def mine(self, query: str, max_depth: int = 2, page: Any = None) -> List[PAANode]:
        root_node = await self.mine_tree(query, page=page, max_depth=max_depth)
        return [root_node] + list(root_node.children)

    async def extract_from_page(self, page: Any = None, target_query: Optional[str] = None) -> List[PAANode]:
        return await self.mine(target_query or "web automation", max_depth=self.max_depth, page=page)
