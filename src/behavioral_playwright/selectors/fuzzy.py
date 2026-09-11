"""L3 Fuzzy text and attribute matching strategy using Levenshtein distance."""

import re
from typing import Any, List, Optional, Tuple

from behavioral_playwright.models.elements import DOMElement
from behavioral_playwright.models.results import ResolutionResult, ResolutionStrategy
from behavioral_playwright.selectors.strategies import ResolverStrategy


def normalize_text(text: str) -> str:
    """Normalizes string by removing selector noise, lowering case, and collapsing whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"^(button|a|input|select|div|span)[\.#]", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def calculate_levenshtein_distance(s1: str, s2: str) -> int:
    """Computes Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return calculate_levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def calculate_similarity_ratio(s1: str, s2: str) -> float:
    """
    Computes a normalized similarity ratio [0.0 - 1.0] based on Levenshtein distance.
    1.0 indicates an exact match, 0.0 indicates complete divergence.
    """
    n1 = normalize_text(s1)
    n2 = normalize_text(s2)
    if not n1 and not n2:
        return 1.0
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
    if n1 in n2 or n2 in n1:
        shorter = min(len(n1), len(n2))
        longer = max(len(n1), len(n2))
        return round(0.70 + (0.30 * (shorter / longer)), 3)

    dist = calculate_levenshtein_distance(n1, n2)
    max_len = max(len(n1), len(n2))
    return round(max(0.0, 1.0 - (dist / max_len)), 3)


class FuzzyResolverStrategy(ResolverStrategy):
    """L3 Fuzzy resolution matching target text against candidate attributes."""

    def __init__(self, similarity_threshold: float = 0.60) -> None:
        self.similarity_threshold = similarity_threshold

    @property
    def strategy_name(self) -> ResolutionStrategy:
        return ResolutionStrategy.L3_FUZZY

    async def resolve(
        self,
        page: Any,
        target: str,
        candidates: Optional[List[DOMElement]] = None
    ) -> Optional[ResolutionResult]:
        if not candidates:
            return None

        ranked_matches: List[Tuple[float, DOMElement]] = []

        for el in candidates:
            comparisons = [
                el.get_accessible_name(),
                el.text,
                el.placeholder,
                el.aria_label,
                el.id,
                el.name,
                el.title
            ]

            best_score = 0.0
            for text_val in comparisons:
                if text_val:
                    score = calculate_similarity_ratio(target, text_val)
                    if score > best_score:
                        best_score = score

            if best_score >= self.similarity_threshold:
                ranked_matches.append((best_score, el))

        if not ranked_matches:
            return None

        ranked_matches.sort(key=lambda x: x[0], reverse=True)
        top_score, top_element = ranked_matches[0]

        return ResolutionResult(
            success=True,
            strategy=self.strategy_name,
            confidence=top_score,
            selector=top_element.selector or top_element.tag,
            element_count=len(ranked_matches),
            reason=f"Fuzzy match resolved with similarity {top_score:.2f}",
            target=target,
            matched_element=top_element,
            candidates=[el for _, el in ranked_matches]
        )
