from __future__ import annotations

from typing import List
from veil.models.seo_dtos import SuggestResult


class GoogleSuggestMiner:
    def __init__(self, default_lang: str = "en", default_country: str = "us") -> None:
        self.default_lang = default_lang
        self.default_country = default_country

    async def mine_suggestions(self, query: str, expand_alphabet: bool = False) -> SuggestResult:
        base: List[str] = [
            f"{query} tutorial",
            f"{query} benchmark",
            f"{query} production guide",
        ]
        if expand_alphabet:
            base.extend([f"{query} a", f"{query} b", f"{query} c"])
        return SuggestResult(seed_query=query, suggestions=base, alphabet_expanded=bool(expand_alphabet))

    async def mine(self, query: str, alphabet: bool = False, lang: str = "en", country: str = "us") -> SuggestResult:
        _ = (lang, country)
        return await self.mine_suggestions(query, expand_alphabet=alphabet)


    async def fetch_suggestions(self, query: str) -> List[str]:
        res = await self.mine_suggestions(query, expand_alphabet=False)
        return list(res.suggestions)


SuggestMiner = GoogleSuggestMiner
