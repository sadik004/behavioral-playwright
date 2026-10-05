"""Unit tests for SelectorMemory and live-DOM verification invariants."""

import time
import pytest
from behavioral_playwright.browser.mock_provider import MockElementHandle, MockPage
from behavioral_playwright.models.elements import DOMElement
from behavioral_playwright.models.results import ResolutionResult, ResolutionStrategy
from behavioral_playwright.selectors.memory import SelectorMemory


@pytest.mark.asyncio
async def test_selector_memory_record_and_recall_verified():
    memory = SelectorMemory()
    page = MockPage()
    page._elements = [
        MockElementHandle(tag="button", attributes={"id": "healed-auth-99"}, text="Sign In")
    ]

    initial_result = ResolutionResult(
        success=True,
        strategy=ResolutionStrategy.L2_SEMANTIC,
        confidence=0.92,
        selector="button#healed-auth-99",
        element_count=1,
        target="Sign In"
    )
    el = DOMElement(tag="button", id="healed-auth-99", text="Sign In", selector="button#healed-auth-99")

    memory.record("Sign In", initial_result, el)
    assert len(memory) == 1
    assert "Sign In" in memory

    recalled = await memory.recall_and_verify(page, "Sign In")
    assert recalled is not None
    assert recalled.success is True
    assert recalled.strategy == ResolutionStrategy.MEMORY
    assert recalled.selector == "button#healed-auth-99"
    assert "Verified learned resolution" in recalled.reason


@pytest.mark.asyncio
async def test_selector_memory_stale_element_divergence_invalidated():
    """Historical success must NEVER override current-page evidence: missing element invalidates memory."""
    memory = SelectorMemory()
    page = MockPage()
    # Live page does NOT contain the healed element
    page._elements = []

    initial_result = ResolutionResult(
        success=True,
        strategy=ResolutionStrategy.L2_SEMANTIC,
        confidence=0.90,
        selector="button#deleted-btn",
        element_count=1,
        target="Submit"
    )
    memory.record("Submit", initial_result, DOMElement(tag="button", id="deleted-btn"))

    recalled = await memory.recall_and_verify(page, "Submit")
    assert recalled is None
    # Memory entry should have been invalidated
    assert "Submit" not in memory
    assert len(memory) == 0


@pytest.mark.asyncio
async def test_selector_memory_tag_mismatch_rejected():
    """If element tag mutates on current page, memory is rejected and invalidated."""
    memory = SelectorMemory()
    page = MockPage()
    # Element exists with same ID but mutated tag: was 'button', now 'input'
    page._elements = [
        MockElementHandle(tag="input", attributes={"id": "action-target"}, text="")
    ]

    initial_result = ResolutionResult(
        success=True,
        strategy=ResolutionStrategy.L2_SEMANTIC,
        confidence=0.88,
        selector="#action-target",
        element_count=1,
        target="Action"
    )
    memory.record("Action", initial_result, DOMElement(tag="button", id="action-target"))

    recalled = await memory.recall_and_verify(page, "Action")
    assert recalled is None
    assert "Action" not in memory


@pytest.mark.asyncio
async def test_selector_memory_ambiguous_matches_on_current_page_invalidated():
    """If healed selector becomes ambiguous (multiple matches) on current page, reject memory."""
    memory = SelectorMemory()
    page = MockPage()
    page._elements = [
        MockElementHandle(tag="button", attributes={"class": "dup-btn"}, text="Save"),
        MockElementHandle(tag="button", attributes={"class": "dup-btn"}, text="Save")
    ]

    initial_result = ResolutionResult(
        success=True,
        strategy=ResolutionStrategy.L2_SEMANTIC,
        confidence=0.85,
        selector=".dup-btn",
        element_count=1,
        target="Save"
    )
    memory.record("Save", initial_result, DOMElement(tag="button", class_name="dup-btn"))

    recalled = await memory.recall_and_verify(page, "Save")
    assert recalled is None
    assert "Save" not in memory


@pytest.mark.asyncio
async def test_selector_memory_isolation_per_instance():
    """Verify memory is strictly instance-scoped (no cross-session or cross-page contamination)."""
    memory_a = SelectorMemory()
    memory_b = SelectorMemory()

    res = ResolutionResult(
        success=True,
        strategy=ResolutionStrategy.L2_SEMANTIC,
        confidence=0.90,
        selector="#btn-a",
        target="Checkout"
    )
    memory_a.record("Checkout", res, DOMElement(tag="button", id="btn-a"))

    assert "Checkout" in memory_a
    assert "Checkout" not in memory_b
    assert len(memory_b) == 0


@pytest.mark.asyncio
async def test_selector_memory_ttl_expiration():
    """Verify TTL expiry discards entries."""
    memory = SelectorMemory(ttl_seconds=0.01)
    page = MockPage()
    page._elements = [
        MockElementHandle(tag="button", attributes={"id": "quick-exp"}, text="Quick")
    ]

    res = ResolutionResult(
        success=True,
        strategy=ResolutionStrategy.L2_SEMANTIC,
        confidence=0.90,
        selector="#quick-exp",
        target="Quick"
    )
    memory.record("Quick", res, DOMElement(tag="button", id="quick-exp"))

    time.sleep(0.02)
    recalled = await memory.recall_and_verify(page, "Quick")
    assert recalled is None
    assert "Quick" not in memory
