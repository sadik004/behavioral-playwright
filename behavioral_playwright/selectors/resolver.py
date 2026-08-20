"""Core cascading SelfHealingResolver engine."""

import time
from typing import Any, Dict, List, Optional

from behavioral_playwright.config.settings import ResolverConfig
from behavioral_playwright.exceptions import ElementResolutionError
from behavioral_playwright.logging import get_logger, log_resolution
from behavioral_playwright.models.elements import BoundingBox, DOMElement
from behavioral_playwright.models.results import ResolutionResult, ResolutionStrategy
from behavioral_playwright.selectors.fuzzy import FuzzyResolverStrategy
from behavioral_playwright.selectors.semantic import SemanticResolverStrategy
from behavioral_playwright.selectors.strategies import ResolverStrategy

logger = get_logger("selectors.resolver")

DOM_SNAPSHOT_SCRIPT = """
() => {
    const query = 'button, input, a, select, textarea, [role="button"], [role="link"], [role="textbox"], [role="checkbox"], [role="menuitem"], [role="tab"], [role="search"], [onclick], [tabindex], h1, h2, h3, h4, span.title, p.title';
    const elements = Array.from(document.querySelectorAll(query));
    return elements.map(el => {
        const rect = el.getBoundingClientRect();
        const id = el.id ? '#' + el.id : '';
        let className = '';
        if (el.className && typeof el.className === 'string') {
            const classes = el.className.trim().split(/\\s+/).filter(c => c.length > 0);
            if (classes.length > 0) className = '.' + classes.join('.');
        }
        const tag = el.tagName.toLowerCase();
        
        // Construct standard deterministic selector
        let sel = '';
        if (el.id) {
            sel = '#' + el.id;
        } else if (el.name) {
            sel = tag + '[name="' + el.name + '"]';
        } else if (el.getAttribute('data-testid')) {
            sel = tag + '[data-testid="' + el.getAttribute('data-testid') + '"]';
        } else if (className) {
            sel = tag + className;
        } else {
            sel = tag;
        }

        const isVisible = rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';

        return {
            tag: tag,
            id: el.id || '',
            class_name: el.className && typeof el.className === 'string' ? el.className.trim() : '',
            text: (el.innerText || el.textContent || '').trim().substring(0, 150),
            role: el.getAttribute('role') || '',
            aria_label: el.getAttribute('aria-label') || '',
            placeholder: el.getAttribute('placeholder') || '',
            name: el.getAttribute('name') || '',
            title: el.getAttribute('title') || '',
            alt: el.getAttribute('alt') || '',
            href: el.getAttribute('href') || '',
            selector: sel,
            is_visible: isVisible,
            bounding_box: {
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height
            }
        };
    }).filter(e => e.is_visible);
}
"""


class SelfHealingResolver:
    """
    Cascading self-healing element resolution engine.
    Orchestrates L1 (Exact) -> L2 (Semantic) -> L3 (Fuzzy) resolution tiers.
    """

    def __init__(
        self,
        config: Optional[ResolverConfig] = None,
        custom_strategies: Optional[List[ResolverStrategy]] = None
    ) -> None:
        self.config = config or ResolverConfig()
        self.semantic_strategy = SemanticResolverStrategy(
            confidence_threshold=self.config.confidence_threshold
        )
        self.fuzzy_strategy = FuzzyResolverStrategy(
            similarity_threshold=self.config.fuzzy_similarity_threshold
        )
        self.custom_strategies = custom_strategies or []

    async def get_dom_candidates(self, page: Any) -> List[DOMElement]:
        """Captures active interactive DOM nodes as lightweight DOMElement objects."""
        try:
            raw_elements = await page.evaluate(DOM_SNAPSHOT_SCRIPT)
            if not isinstance(raw_elements, list):
                return []

            candidates = []
            for item in raw_elements:
                if not isinstance(item, dict):
                    continue
                bbox = None
                if "bounding_box" in item and isinstance(item["bounding_box"], dict):
                    b = item["bounding_box"]
                    bbox = BoundingBox(
                        x=float(b.get("x", 0)),
                        y=float(b.get("y", 0)),
                        width=float(b.get("width", 0)),
                        height=float(b.get("height", 0)),
                    )
                candidates.append(DOMElement(
                    tag=item.get("tag", ""),
                    id=item.get("id", ""),
                    class_name=item.get("class_name", ""),
                    text=item.get("text", ""),
                    role=item.get("role", ""),
                    aria_label=item.get("aria_label", ""),
                    placeholder=item.get("placeholder", ""),
                    name=item.get("name", ""),
                    title=item.get("title", ""),
                    alt=item.get("alt", ""),
                    href=item.get("href", ""),
                    selector=item.get("selector", ""),
                    is_visible=item.get("is_visible", True),
                    bounding_box=bbox
                ))
            return candidates[:self.config.max_candidates]
        except Exception as e:
            logger.warning(f"[Resolver] Error capturing DOM snapshot: {e}")
            return []

    async def resolve(self, page: Any, target: str) -> ResolutionResult:
        """
        Resolves an element by target (CSS selector, text, accessible name, or label)
        using cascading L1 -> L2 -> L3 strategies.
        """
        start_time = time.time()

        # -------------------------------------------------------------
        # Level 1: Exact CSS / DOM Selector Match
        # -------------------------------------------------------------
        if "L1_EXACT" in self.config.strategies:
            try:
                # Check if target is a valid CSS selector and exists on page
                exact_matches = await page.query_selector_all(target)
                if exact_matches and len(exact_matches) > 0:
                    elapsed_ms = (time.time() - start_time) * 1000.0
                    res = ResolutionResult(
                        success=True,
                        strategy=ResolutionStrategy.L1_EXACT,
                        confidence=1.0,
                        selector=target,
                        element_count=len(exact_matches),
                        reason=f"L1 Exact selector matched {len(exact_matches)} element(s)",
                        target=target,
                        elapsed_ms=elapsed_ms
                    )
                    log_resolution(
                        logger, target=target, strategy="L1_EXACT", candidates=len(exact_matches),
                        confidence=1.0, success=True, elapsed_ms=elapsed_ms, selector=target
                    )
                    return res
            except Exception:
                # Target was not a valid CSS selector or query failed; cascade to self-healing
                pass

        logger.info(f"[Resolver] L1 Exact match failed for '{target}'. Initiating Self-Healing cascade...")

        # Capture live DOM candidates for self-healing
        candidates = await self.get_dom_candidates(page)

        # -------------------------------------------------------------
        # Level 2: Semantic & Accessibility Recovery
        # -------------------------------------------------------------
        if "L2_SEMANTIC" in self.config.strategies and candidates:
            semantic_res = await self.semantic_strategy.resolve(page, target, candidates)
            if semantic_res and semantic_res.confidence >= self.config.confidence_threshold:
                semantic_res.elapsed_ms = (time.time() - start_time) * 1000.0
                log_resolution(
                    logger, target=target, strategy="L2_SEMANTIC", candidates=len(candidates),
                    confidence=semantic_res.confidence, success=True, elapsed_ms=semantic_res.elapsed_ms,
                    selector=semantic_res.selector
                )
                return semantic_res

        # -------------------------------------------------------------
        # Level 3: Deterministic Fuzzy String & Attribute Matching
        # -------------------------------------------------------------
        if "L3_FUZZY" in self.config.strategies and candidates:
            fuzzy_res = await self.fuzzy_strategy.resolve(page, target, candidates)
            if fuzzy_res and fuzzy_res.confidence >= self.config.fuzzy_similarity_threshold:
                fuzzy_res.elapsed_ms = (time.time() - start_time) * 1000.0
                log_resolution(
                    logger, target=target, strategy="L3_FUZZY", candidates=len(candidates),
                    confidence=fuzzy_res.confidence, success=True, elapsed_ms=fuzzy_res.elapsed_ms,
                    selector=fuzzy_res.selector
                )
                return fuzzy_res

        # -------------------------------------------------------------
        # Custom / Pluggable Strategies (e.g. L4 Future Extension)
        # -------------------------------------------------------------
        for custom_strat in self.custom_strategies:
            custom_res = await custom_strat.resolve(page, target, candidates)
            if custom_res and custom_res.success:
                custom_res.elapsed_ms = (time.time() - start_time) * 1000.0
                log_resolution(
                    logger, target=target, strategy=str(custom_strat.strategy_name),
                    candidates=len(candidates), confidence=custom_res.confidence, success=True,
                    elapsed_ms=custom_res.elapsed_ms, selector=custom_res.selector
                )
                return custom_res

        # Resolution Exhaustion
        elapsed_ms = (time.time() - start_time) * 1000.0
        failed_res = ResolutionResult(
            success=False,
            strategy=ResolutionStrategy.L3_FUZZY,
            confidence=0.0,
            selector=None,
            element_count=0,
            reason=f"Element '{target}' could not be resolved by any active strategy tier.",
            target=target,
            candidates=candidates,
            elapsed_ms=elapsed_ms
        )
        log_resolution(
            logger, target=target, strategy="NONE", candidates=len(candidates),
            confidence=0.0, success=False, elapsed_ms=elapsed_ms, selector=None
        )
        return failed_res

    async def resolve_and_click(self, page: Any, target: str) -> ResolutionResult:
        """Resolves target element through healing cascade and executes a click."""
        result = await self.resolve(page, target)
        if not result.success or not result.selector:
            raise ElementResolutionError(f"Cannot click: element '{target}' could not be resolved.")
        await page.click(result.selector)
        return result

    async def resolve_and_type(self, page: Any, target: str, text: str) -> ResolutionResult:
        """Resolves target input element through healing cascade and fills text."""
        result = await self.resolve(page, target)
        if not result.success or not result.selector:
            raise ElementResolutionError(f"Cannot type: element '{target}' could not be resolved.")
        await page.fill(result.selector, text)
        return result
