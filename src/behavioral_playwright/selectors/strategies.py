"""Abstract base strategy for element resolution."""

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from behavioral_playwright.models.elements import DOMElement
from behavioral_playwright.models.results import ResolutionResult, ResolutionStrategy


class ResolverStrategy(ABC):
    """Base interface for cascading element resolution strategies."""

    @property
    @abstractmethod
    def strategy_name(self) -> ResolutionStrategy:
        """Returns the identifier of this resolution strategy."""
        pass

    @abstractmethod
    async def resolve(
        self,
        page: Any,
        target: str,
        candidates: Optional[List[DOMElement]] = None
    ) -> Optional[ResolutionResult]:
        """
        Attempts to resolve the target using this strategy.
        Returns a ResolutionResult if successful, or None if strategy cannot resolve.
        """
        pass
