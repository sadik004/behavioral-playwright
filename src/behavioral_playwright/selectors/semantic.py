"""L2 Semantic and accessibility-based element recovery strategy."""

import re
from typing import Any, List, Optional, Tuple

from behavioral_playwright.models.elements import DOMElement
from behavioral_playwright.models.results import ResolutionResult, ResolutionStrategy
from behavioral_playwright.selectors.strategies import ResolverStrategy


def _extract_tokens(s: str) -> str:
    """Extracts alphanumeric words from selector or text strings."""
    if not s:
        return ""
    # Strip common selector prefixes / noise words
    s = re.sub(r"^(button|a|input|select|div|span)[\.#]", "", s.strip(), flags=re.IGNORECASE)
    words = re.findall(r"[a-zA-Z0-9]+", s.lower())
    # Filter out pure noise terms
    meaningful = [w for w in words if w not in ["btn", "button", "v1", "v2", "v3", "v4", "link", "custom", "item", "wrapper", "dynamic", "hash"]]
    if meaningful:
        return " ".join(meaningful)
    return " ".join(words)


class SemanticResolverStrategy(ResolverStrategy):
    """
    L2 Semantic recovery utilizing standard W3C Accessibility semantics:
    role, aria-label, accessible name, placeholder, input name, title, and alt.
    """

    def __init__(self, confidence_threshold: float = 0.65) -> None:
        self.confidence_threshold = confidence_threshold

    @property
    def strategy_name(self) -> ResolutionStrategy:
        return ResolutionStrategy.L2_SEMANTIC

    def score_element(self, target: str, el: DOMElement) -> float:
        """Computes semantic matching score for a candidate DOMElement against target."""
        target_tokens = _extract_tokens(target)
        if not target_tokens:
            return 0.0

        target_words = set(target_tokens.split())
        score = 0.0

        comparisons = [
            (el.aria_label, 0.95),
            (el.get_accessible_name(), 0.90),
            (el.text, 0.85),
            (el.placeholder, 0.90),
            (el.name, 0.85),
            (el.title, 0.80),
            (el.alt, 0.80)
        ]

        for text_val, weight in comparisons:
            if not text_val:
                continue
            cand_tokens = _extract_tokens(text_val)
            cand_words = set(cand_tokens.split())

            if not cand_words:
                continue

            # Exact token string match
            if target_tokens == cand_tokens:
                score = max(score, weight)
            # Full subset containment
            elif target_words.issubset(cand_words) or cand_words.issubset(target_words):
                overlap = len(target_words & cand_words) / max(1, len(target_words | cand_words))
                score = max(score, weight * (0.80 + 0.20 * overlap))
            # Partial overlap
            elif len(target_words & cand_words) > 0:
                overlap = len(target_words & cand_words) / max(1, len(target_words | cand_words))
                if overlap >= 0.50:
                    score = max(score, weight * overlap)

        # Role and Tag boost
        if el.role and el.role.lower() in target.lower():
            score = max(score, 0.70)

        if el.tag in ["button", "a", "input", "textarea", "select"] and score > 0.0:
            score = min(1.0, score + 0.05)

        return round(score, 2)

    async def resolve(
        self,
        page: Any,
        target: str,
        candidates: Optional[List[DOMElement]] = None
    ) -> Optional[ResolutionResult]:
        if not candidates:
            return None

        scored_candidates: List[Tuple[float, DOMElement]] = []

        for el in candidates:
            score = self.score_element(target, el)
            if score >= self.confidence_threshold:
                scored_candidates.append((score, el))

        if not scored_candidates:
            return None

        # Sort descending by semantic confidence score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_score, top_element = scored_candidates[0]

        return ResolutionResult(
            success=True,
            strategy=self.strategy_name,
            confidence=top_score,
            selector=top_element.selector or top_element.tag,
            element_count=len(scored_candidates),
            reason=f"Semantic recovery matched accessible property (score: {top_score:.2f})",
            target=target,
            matched_element=top_element,
            candidates=[el for _, el in scored_candidates]
        )
