"""In-memory selector memory and learned resolution cache.

Maintains scoped, verified memory of successful healings.
Enforces the Phase 3 Invariant:
  Historical success must NEVER override current-page evidence.
  All recalled entries are actively verified against the live DOM before use.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, Optional

from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.elements import DOMElement
from behavioral_playwright.models.results import ResolutionResult, ResolutionStrategy

logger = get_logger("selectors.memory")


@dataclass
class MemoryEntry:
    """Represents a verified healed selector record in memory."""
    target: str
    healed_selector: str
    strategy: ResolutionStrategy
    confidence: float
    tag: str = ""
    text: str = ""
    aria_label: str = ""
    timestamp: float = field(default_factory=time.time)
    success_count: int = 1


class SelectorMemory:
    """
    Scoped selector memory for learned resolution.
    Stores successful selector healings and validates them against current page state.
    """

    def __init__(self, max_size: int = 200, ttl_seconds: float = 3600.0) -> None:
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._entries: Dict[str, MemoryEntry] = {}

    def record(
        self,
        target: str,
        result: ResolutionResult,
        element: Optional[DOMElement] = None
    ) -> None:
        """Records a successful healing result in scoped memory."""
        if not result.success or not result.is_healed or not result.selector:
            return

        # Evict oldest entry if at capacity
        if len(self._entries) >= self.max_size and target not in self._entries:
            oldest_key = next(iter(self._entries))
            del self._entries[oldest_key]

        tag = element.tag if element else ""
        text = element.text if element else ""
        aria_label = element.aria_label if element else ""

        if target in self._entries:
            entry = self._entries[target]
            entry.healed_selector = result.selector
            entry.strategy = result.strategy
            entry.confidence = result.confidence
            entry.tag = tag or entry.tag
            entry.text = text or entry.text
            entry.aria_label = aria_label or entry.aria_label
            entry.timestamp = time.time()
            entry.success_count += 1
        else:
            self._entries[target] = MemoryEntry(
                target=target,
                healed_selector=result.selector,
                strategy=result.strategy,
                confidence=result.confidence,
                tag=tag,
                text=text,
                aria_label=aria_label,
                timestamp=time.time(),
                success_count=1
            )
        logger.debug(f"[SelectorMemory] Stored healed selector for '{target}' -> '{result.selector}'")

    async def recall_and_verify(self, page: Any, target: str) -> Optional[ResolutionResult]:
        """
        Recalls a previously healed selector for target and rigorously verifies
        it against live page evidence.
        If verification fails (element gone, ambiguous, or semantic profile mutated),
        the memory entry is invalidated and None is returned.
        """
        if target not in self._entries:
            return None

        entry = self._entries[target]

        # Check TTL expiration
        if (time.time() - entry.timestamp) > self.ttl_seconds:
            logger.info(f"[SelectorMemory] Expired TTL for '{target}'; invalidating memory")
            self.invalidate(target)
            return None

        # Verify against current page reality
        try:
            if not hasattr(page, "query_selector_all"):
                return None

            matches = await page.query_selector_all(entry.healed_selector)
            if not matches or len(matches) != 1:
                logger.info(
                    f"[SelectorMemory] Current page diverged for '{target}' "
                    f"(matches: {len(matches) if matches else 0}); invalidating stale memory"
                )
                self.invalidate(target)
                return None

            el_handle = matches[0]

            # Verify tag profile if element handle supports tag inspection
            if entry.tag and hasattr(el_handle, "evaluate"):
                try:
                    raw_tag = await el_handle.evaluate("el => el.tagName.toLowerCase()")
                    actual_tag = str(raw_tag).strip().lower() if raw_tag else ""
                    if actual_tag and actual_tag != entry.tag.lower():
                        logger.info(
                            f"[SelectorMemory] Tag mismatch for '{target}' "
                            f"(expected {entry.tag}, got {actual_tag}); invalidating stale memory"
                        )
                        self.invalidate(target)
                        return None
                except Exception as tag_err:
                    logger.debug(f"[SelectorMemory] Could not inspect element tag: {tag_err}")

            # Verify aria-label if element handle supports attribute inspection
            if entry.aria_label and hasattr(el_handle, "get_attribute"):
                try:
                    actual_aria = await el_handle.get_attribute("aria-label")
                    if actual_aria and actual_aria.strip().lower() != entry.aria_label.strip().lower():
                        logger.info(
                            f"[SelectorMemory] Aria-label mismatch for '{target}'; invalidating stale memory"
                        )
                        self.invalidate(target)
                        return None
                except Exception as aria_err:
                    logger.debug(f"[SelectorMemory] Could not inspect aria-label: {aria_err}")

            # Verified against current DOM evidence
            logger.info(f"[SelectorMemory] Successfully recalled & verified healed selector for '{target}' -> '{entry.healed_selector}'")
            return ResolutionResult(
                success=True,
                strategy=ResolutionStrategy.MEMORY,
                confidence=min(1.0, entry.confidence),
                selector=entry.healed_selector,
                element_count=1,
                reason=f"Verified learned resolution from memory (originally healed via {entry.strategy.value})",
                target=target
            )
        except Exception as exc:
            logger.warning(f"[SelectorMemory] Verification raised exception ({exc}); invalidating '{target}'")
            self.invalidate(target)
            return None

    def invalidate(self, target: str) -> None:
        """Removes target entry from memory."""
        self._entries.pop(target, None)

    def clear(self) -> None:
        """Flushes all remembered selectors."""
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)

    def __bool__(self) -> bool:
        return True

    def __contains__(self, target: str) -> bool:
        return target in self._entries
