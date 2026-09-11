"""Selectors and self-healing resolution module."""

from behavioral_playwright.selectors.fuzzy import FuzzyResolverStrategy
from behavioral_playwright.selectors.resolver import SelfHealingResolver
from behavioral_playwright.selectors.semantic import SemanticResolverStrategy
from behavioral_playwright.selectors.strategies import ResolverStrategy

__all__ = [
    "FuzzyResolverStrategy",
    "ResolverStrategy",
    "SelfHealingResolver",
    "SemanticResolverStrategy",
]
