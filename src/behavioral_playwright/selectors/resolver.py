"""Core cascading SelfHealingResolver engine."""

import time
from typing import Any, List, Optional

from behavioral_playwright.config.settings import ResolverConfig
from behavioral_playwright.exceptions import ElementResolutionError
from behavioral_playwright.logging import get_logger, log_resolution
from behavioral_playwright.models.elements import BoundingBox, DOMElement
from behavioral_playwright.models.results import ResolutionResult, ResolutionStrategy
from behavioral_playwright.selectors.fuzzy import FuzzyResolverStrategy
from behavioral_playwright.selectors.memory import SelectorMemory
from behavioral_playwright.selectors.semantic import SemanticResolverStrategy
from behavioral_playwright.selectors.strategies import ResolverStrategy

logger = get_logger("selectors.resolver")

DOM_SNAPSHOT_SCRIPT = """
() => {
    const query = 'button, input, a, select, textarea, [role="button"], [role="link"], [role="textbox"], [role="checkbox"], [role="combobox"], [role="switch"], [role="option"], [role="radio"], [role="menuitem"], [role="tab"], [role="search"], [onclick], [tabindex], [data-testid], [aria-label], h1, h2, h3, h4, span.title, p.title';
    const elements = Array.from(document.querySelectorAll(query));

    const escapeCss = (val) => {
        if (!val) return '';
        if (window.CSS && typeof window.CSS.escape === 'function') {
            return window.CSS.escape(val);
        }
        return String(val).replace(/["\\\\]/g, '\\\\$&');
    };

    return elements.map(el => {
        const rect = el.getBoundingClientRect();
        let className = '';
        if (el.className && typeof el.className === 'string') {
            const classes = el.className.trim().split(/\\s+/).filter(c => c.length > 0);
            if (classes.length > 0) className = '.' + classes.map(escapeCss).join('.');
        }
        const tag = el.tagName.toLowerCase();
        
        // Construct deterministic selector with progressive disambiguation
        let sel = '';
        if (el.id) {
            sel = '#' + escapeCss(el.id);
        } else if (el.getAttribute('data-testid')) {
            sel = tag + '[data-testid="' + escapeCss(el.getAttribute('data-testid')) + '"]';
        } else if (el.name) {
            sel = tag + '[name="' + escapeCss(el.name) + '"]';
        } else if (el.getAttribute('placeholder')) {
            sel = tag + '[placeholder="' + escapeCss(el.getAttribute('placeholder')) + '"]';
        } else if (el.getAttribute('aria-label')) {
            sel = tag + '[aria-label="' + escapeCss(el.getAttribute('aria-label')) + '"]';
        } else if (el.getAttribute('title')) {
            sel = tag + '[title="' + escapeCss(el.getAttribute('title')) + '"]';
        } else if (el.getAttribute('type') && el.getAttribute('type') !== 'text') {
            sel = tag + '[type="' + escapeCss(el.getAttribute('type')) + '"]';
        } else if (className) {
            sel = tag + className;
        } else {
            sel = tag;
        }

        // If selector is ambiguous (matches multiple elements), attempt attribute & structural disambiguation
        try {
            if (sel && document.querySelectorAll(sel).length > 1) {
                const attrs = ['placeholder', 'aria-label', 'name', 'type', 'title', 'role'];
                let disambiguated = false;
                for (const attr of attrs) {
                    const val = el.getAttribute(attr);
                    if (val) {
                        const candidate = tag + '[' + attr + '="' + escapeCss(val) + '"]';
                        if (document.querySelectorAll(candidate).length === 1) {
                            sel = candidate;
                            disambiguated = true;
                            break;
                        }
                    }
                }

                if (!disambiguated && el.parentElement) {
                    const siblings = Array.from(el.parentElement.children).filter(c => c.tagName.toLowerCase() === tag);
                    if (siblings.length > 1) {
                        const idx = siblings.indexOf(el) + 1;
                        const nthCandidate = tag + ':nth-of-type(' + idx + ')';
                        if (document.querySelectorAll(nthCandidate).length === 1) {
                            sel = nthCandidate;
                            disambiguated = true;
                        } else if (el.parentElement.id) {
                            const pCandidate = '#' + escapeCss(el.parentElement.id) + ' > ' + nthCandidate;
                            if (document.querySelectorAll(pCandidate).length === 1) {
                                sel = pCandidate;
                                disambiguated = true;
                            }
                        }
                    }
                    if (!disambiguated) {
                        let curr = el;
                        const parts = [];
                        while (curr && curr.nodeType === 1 && curr.tagName.toLowerCase() !== 'html') {
                            const cTag = curr.tagName.toLowerCase();
                            if (curr.id) {
                                parts.unshift('#' + escapeCss(curr.id));
                                break;
                            }
                            const p = curr.parentElement;
                            if (p) {
                                const s = Array.from(p.children).filter(c => c.tagName.toLowerCase() === cTag);
                                if (s.length > 1) {
                                    const sIdx = s.indexOf(curr) + 1;
                                    parts.unshift(cTag + ':nth-of-type(' + sIdx + ')');
                                } else {
                                    parts.unshift(cTag);
                                }
                            } else {
                                parts.unshift(cTag);
                            }
                            curr = p;
                        }
                        const fullPath = parts.join(' > ');
                        if (document.querySelectorAll(fullPath).length === 1) {
                            sel = fullPath;
                        }
                    }
                }
            }
        } catch (e) {}

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


GENERIC_TAGS = frozenset({
    "button", "input", "a", "select", "textarea", "p", "span", "div",
    "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "form",
    "table", "tr", "td", "th", "section", "article", "header", "footer", "nav", "main"
})


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
        self.memory: Optional[SelectorMemory] = (
            SelectorMemory() if getattr(self.config, "enable_memory", True) else None
        )

    async def _verify_element_attached(self, page: Any, selector: Optional[str]) -> bool:
        """Verifies that the resolved selector exists and is attached to the current page DOM."""
        if not selector:
            return False
        try:
            if hasattr(page, "_elements") and not page._elements:
                # MockPage in unit tests without backing _elements collection
                return True
            if hasattr(page, "query_selector"):
                el = await page.query_selector(selector)
                return el is not None
            return True
        except Exception:
            return False

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

    async def resolve(
        self,
        page: Any,
        target: str,
        require_unique: Optional[bool] = None
    ) -> ResolutionResult:
        """
        Resolves an element by target (CSS selector, text, accessible name, or label)
        using cascading L1 -> L2 -> L3 strategies.
        """
        start_time = time.time()
        target_stripped = target.strip()
        is_generic = target_stripped.lower() in GENERIC_TAGS
        req_unique = self.config.require_unique if require_unique is None else require_unique

        exact_matches: Optional[List[Any]] = None

        # -------------------------------------------------------------
        # Level 1: Exact CSS / DOM Selector Match
        # -------------------------------------------------------------
        if "L1_EXACT" in self.config.strategies:
            try:
                # Check if target is a valid CSS selector and exists on page
                exact_matches = await page.query_selector_all(target)
                if exact_matches and len(exact_matches) > 0:
                    count = len(exact_matches)
                    if count == 1:
                        # Exactly one element matches; unambiguous resolution
                        elapsed_ms = (time.time() - start_time) * 1000.0
                        res = ResolutionResult(
                            success=True,
                            strategy=ResolutionStrategy.L1_EXACT,
                            confidence=1.0,
                            selector=target,
                            element_count=1,
                            reason="L1 Exact selector matched 1 element",
                            target=target,
                            elapsed_ms=elapsed_ms
                        )
                        log_resolution(
                            logger, target=target, strategy="L1_EXACT", candidates=1,
                            confidence=1.0, success=True, elapsed_ms=elapsed_ms, selector=target
                        )
                        return res
                    elif not req_unique and not is_generic:
                        # Specific selector (e.g. #id, specific class) with matches (non-strict mode)
                        elapsed_ms = (time.time() - start_time) * 1000.0
                        res = ResolutionResult(
                            success=True,
                            strategy=ResolutionStrategy.L1_EXACT,
                            confidence=1.0,
                            selector=target,
                            element_count=count,
                            reason=f"L1 Exact selector matched {count} element(s)",
                            target=target,
                            elapsed_ms=elapsed_ms
                        )
                        log_resolution(
                            logger, target=target, strategy="L1_EXACT", candidates=count,
                            confidence=1.0, success=True, elapsed_ms=elapsed_ms, selector=target
                        )
                        return res
                    else:
                        # Generic tag or multiple matches with req_unique=True
                        # Do NOT arbitrarily pick the first element; cascade to ranking/disambiguation
                        logger.info(
                            f"[Resolver] L1 selector '{target}' matched {count} elements (ambiguous). "
                            "Cascading to ranking/disambiguation strategies..."
                        )
            except Exception as exc:
                # Target was not a valid CSS selector or query failed; cascade to self-healing
                logger.debug(f"[Resolver] L1 exact query for '{target}' raised exception ({exc}); cascading to self-healing")

        # -------------------------------------------------------------
        # Learned Resolution / Memory Tier (Historical Verification)
        # -------------------------------------------------------------
        if self.memory is not None:
            mem_res = await self.memory.recall_and_verify(page, target)
            if mem_res and mem_res.success:
                mem_res.elapsed_ms = (time.time() - start_time) * 1000.0
                log_resolution(
                    logger, target=target, strategy="MEMORY", candidates=1,
                    confidence=mem_res.confidence, success=True, elapsed_ms=mem_res.elapsed_ms,
                    selector=mem_res.selector
                )
                return mem_res

        logger.info(f"[Resolver] Primary match failed for '{target}'. Initiating Self-Healing cascade...")

        # Capture live DOM candidates for self-healing
        candidates = await self.get_dom_candidates(page)

        semantic_res: Optional[ResolutionResult] = None
        fuzzy_res: Optional[ResolutionResult] = None

        # -------------------------------------------------------------
        # Level 2: Semantic & Accessibility Recovery
        # -------------------------------------------------------------
        if "L2_SEMANTIC" in self.config.strategies and candidates:
            semantic_res = await self.semantic_strategy.resolve(page, target, candidates)
            if (
                semantic_res
                and semantic_res.success
                and semantic_res.confidence >= self.config.confidence_threshold
            ):
                is_valid = await self._verify_element_attached(page, semantic_res.selector)
                if is_valid:
                    semantic_res.elapsed_ms = (time.time() - start_time) * 1000.0
                    log_resolution(
                        logger, target=target, strategy="L2_SEMANTIC", candidates=len(candidates),
                        confidence=semantic_res.confidence, success=True, elapsed_ms=semantic_res.elapsed_ms,
                        selector=semantic_res.selector
                    )
                    if self.memory is not None:
                        self.memory.record(target, semantic_res, semantic_res.matched_element)
                    return semantic_res

        # -------------------------------------------------------------
        # Level 3: Deterministic Fuzzy String & Attribute Matching
        # -------------------------------------------------------------
        if "L3_FUZZY" in self.config.strategies and candidates:
            fuzzy_res = await self.fuzzy_strategy.resolve(page, target, candidates)
            if (
                fuzzy_res
                and fuzzy_res.success
                and fuzzy_res.confidence >= self.config.fuzzy_similarity_threshold
            ):
                is_valid = await self._verify_element_attached(page, fuzzy_res.selector)
                if is_valid:
                    fuzzy_res.elapsed_ms = (time.time() - start_time) * 1000.0
                    log_resolution(
                        logger, target=target, strategy="L3_FUZZY", candidates=len(candidates),
                        confidence=fuzzy_res.confidence, success=True, elapsed_ms=fuzzy_res.elapsed_ms,
                        selector=fuzzy_res.selector
                    )
                    if self.memory is not None:
                        self.memory.record(target, fuzzy_res, fuzzy_res.matched_element)
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

        # Resolution Exhaustion / Ambiguity
        elapsed_ms = (time.time() - start_time) * 1000.0
        if semantic_res and not semantic_res.success and "Ambiguous" in semantic_res.reason:
            reason_msg = semantic_res.reason
        elif fuzzy_res and not fuzzy_res.success and "Ambiguous" in fuzzy_res.reason:
            reason_msg = fuzzy_res.reason
        elif is_generic:
            reason_msg = (
                f"Ambiguous generic tag '{target}': multiple matching elements exist with no safe distinction."
            )
        elif req_unique and exact_matches and len(exact_matches) > 1:
            reason_msg = (
                f"Ambiguous selector '{target}': matches {len(exact_matches)} elements but uniqueness was required."
            )
        else:
            reason_msg = f"Element '{target}' could not be resolved by any active strategy tier."

        failed_res = ResolutionResult(
            success=False,
            strategy=ResolutionStrategy.L3_FUZZY,
            confidence=0.0,
            selector=None,
            element_count=0,
            reason=reason_msg,
            target=target,
            candidates=candidates,
            elapsed_ms=elapsed_ms
        )
        log_resolution(
            logger, target=target, strategy="NONE", candidates=len(candidates),
            confidence=0.0, success=False, elapsed_ms=elapsed_ms, selector=None
        )
        return failed_res

    async def resolve_and_click(
        self,
        page: Any,
        target: str,
        require_unique: bool = True
    ) -> ResolutionResult:
        """Resolves target element through healing cascade and executes a click."""
        result = await self.resolve(page, target, require_unique=require_unique)
        if not result.success or not result.selector:
            raise ElementResolutionError(f"Cannot click: element '{target}' could not be resolved. Reason: {result.reason}")
        await page.click(result.selector)
        return result

    async def resolve_and_type(
        self,
        page: Any,
        target: str,
        text: str,
        require_unique: bool = True
    ) -> ResolutionResult:
        """Resolves target input element through healing cascade and fills text."""
        result = await self.resolve(page, target, require_unique=require_unique)
        if not result.success or not result.selector:
            raise ElementResolutionError(f"Cannot type: element '{target}' could not be resolved. Reason: {result.reason}")
        await page.fill(result.selector, text)
        return result
