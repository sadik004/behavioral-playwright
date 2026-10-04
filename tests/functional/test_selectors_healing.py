"""Functional Validation: Selector Resolution, Semantic & Fuzzy Cascades, Self-Healing.
Tests observable selector matching and self-healing against real DOM structures.
"""

from __future__ import annotations

import pytest
from behavioral_playwright.config.settings import ResolverConfig
from behavioral_playwright.exceptions import ElementResolutionError
from behavioral_playwright.facade import BP
from behavioral_playwright.models.results import ResolutionStrategy
from behavioral_playwright.selectors.resolver import SelfHealingResolver


FIXTURE_HTML = """<!DOCTYPE html>
<html>
<head><title>Selector Test Page</title></head>
<body>
    <!-- L1 Exact CSS candidate -->
    <button id="login-button" class="btn-primary" onclick="window.__clicked_login = true;">Log In</button>

    <!-- L2 Semantic candidate: accessible name / role / aria -->
    <div role="button" aria-label="Confirm Purchase" tabindex="0" onclick="window.__clicked_confirm = true;">
        Proceed
    </div>

    <!-- L3 Fuzzy candidate: button with dynamic hash class but recognizable title / text -->
    <button class="checkout-btn_dyn_8f92a" title="Complete Checkout" onclick="window.__clicked_checkout = true;">
        Finish Order Now
    </button>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_l1_exact_selector_resolution():
    """Verify L1 Exact resolution correctly matches CSS selector on real DOM."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{FIXTURE_HTML}")
        resolver = SelfHealingResolver()
        
        result = await resolver.resolve(bp.page.raw_page, "#login-button")
        
        assert result.success is True
        assert result.strategy == ResolutionStrategy.L1_EXACT
        assert result.confidence == 1.0
        assert result.selector == "#login-button"
        assert result.element_count >= 1


@pytest.mark.asyncio
async def test_l2_semantic_selector_resolution():
    """Verify L2 Semantic resolution matches accessible name / role when exact CSS fails."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{FIXTURE_HTML}")
        resolver = SelfHealingResolver()
        
        # Exact CSS for this string does not exist, triggering cascade to L2
        result = await resolver.resolve(bp.page.raw_page, "Confirm Purchase")
        
        assert result.success is True
        assert result.strategy == ResolutionStrategy.L2_SEMANTIC
        assert result.confidence >= 0.70
        assert result.selector is not None


@pytest.mark.asyncio
async def test_l3_fuzzy_selector_resolution():
    """Verify L3 Fuzzy resolution resolves slightly misspelled or attribute-matched targets."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{FIXTURE_HTML}")
        # Configure resolver with L3 enabled
        config = ResolverConfig(strategies=["L1_EXACT", "L2_SEMANTIC", "L3_FUZZY"], fuzzy_similarity_threshold=0.6)
        resolver = SelfHealingResolver(config=config)
        
        # "Complete Checkout" is in the title attribute of checkout button
        result = await resolver.resolve(bp.page.raw_page, "Complete Checkout")
        
        assert result.success is True
        assert result.selector is not None
        assert "checkout" in result.selector.lower() or "dyn" in result.selector.lower() or "button" in result.selector.lower()


@pytest.mark.asyncio
async def test_self_healing_click_observable_effect():
    """Verify click_healed resolves an altered/semantic target and triggers real DOM mutation."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{FIXTURE_HTML}")
        
        # Click using semantic accessible label
        res = await bp.page.click_healed("Confirm Purchase")
        assert res.success is True
        
        # Verify the onclick actually executed in the browser JavaScript context
        was_clicked = await bp.page.evaluate("() => window.__clicked_confirm === true")
        assert was_clicked is True


@pytest.mark.asyncio
async def test_resolver_exhaustion_raises_on_unresolvable_element():
    """Verify resolver raises ElementResolutionError when element cannot be resolved and action is attempted."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{FIXTURE_HTML}")
        
        with pytest.raises(ElementResolutionError) as exc_info:
            await bp.page.click_healed("NonExistentPhantomElement_12345")
            
        assert "could not be resolved" in str(exc_info.value)


# =========================================================================
# DEFECT-002 REGRESSION TESTS: Selector Contract & Disambiguation
# =========================================================================

TAG_AMBIGUITY_FIXTURE = """<!DOCTYPE html>
<html>
<head><title>Tag Disambiguation Test</title></head>
<body>
    <!-- Scenario 1: Exactly one textarea element -->
    <div id="notes-container">
        <textarea id="single-note" placeholder="Write single note"></textarea>
    </div>

    <!-- Scenario 2 & 3: Multiple buttons with different attributes/text -->
    <div id="action-bar">
        <button id="btn-save" title="Save All Changes" onclick="window.__action = 'saved';">Save</button>
        <button id="btn-cancel" title="Discard Current Draft" onclick="window.__action = 'cancelled';">Cancel</button>
        <button id="btn-reset" title="Reset All Fields" onclick="window.__action = 'reset';">Reset</button>
    </div>

    <!-- Scenario 4: Ambiguous identical elements with no safe distinction -->
    <div id="identical-container">
        <button class="duplicate-btn" onclick="window.__dup_count = (window.__dup_count || 0) + 1;">Clone Item</button>
        <button class="duplicate-btn" onclick="window.__dup_count = (window.__dup_count || 0) + 1;">Clone Item</button>
    </div>

    <!-- Scenario 5: Multiple inputs where specific strategy must win over generic input tag -->
    <div id="form-container">
        <input id="user-field" type="text" placeholder="Your username" />
        <input type="email" placeholder="Your work email" />
    </div>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_defect_002_case1_exactly_one_matching_element():
    """Case 1: Exactly one matching element for a generic tag must resolve unambiguously."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{TAG_AMBIGUITY_FIXTURE}")
        resolver = SelfHealingResolver()

        # Only one <textarea> exists in the document
        result = await resolver.resolve(bp.page.raw_page, "textarea")
        assert result.success is True
        assert result.element_count == 1
        assert result.selector == "textarea"


@pytest.mark.asyncio
async def test_defect_002_case2_multiple_matching_elements_disambiguated():
    """Case 2: Multiple matching elements must be ranked and disambiguated rather than picking arbitrary elements."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{TAG_AMBIGUITY_FIXTURE}")
        resolver = SelfHealingResolver()

        # "Cancel" should uniquely resolve the Cancel button among the 3 buttons
        result = await resolver.resolve(bp.page.raw_page, "Cancel")
        assert result.success is True
        assert result.matched_element is not None
        assert result.matched_element.text == "Cancel"
        assert result.selector == "#btn-cancel"

        # Observable action: clicking "Cancel" mutates window.__action to 'cancelled'
        await bp.page.click_healed("Cancel")
        action = await bp.page.evaluate("() => window.__action")
        assert action == "cancelled"


@pytest.mark.asyncio
async def test_defect_002_case3_multiple_elements_with_different_attributes():
    """Case 3: Multiple elements with different attributes are safely resolved by distinguishing attribute."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{TAG_AMBIGUITY_FIXTURE}")
        resolver = SelfHealingResolver()

        # Resolve via unique title attribute
        result = await resolver.resolve(bp.page.raw_page, "Save All Changes")
        assert result.success is True
        assert result.matched_element is not None
        assert result.matched_element.title == "Save All Changes"
        assert result.selector == "#btn-save"


@pytest.mark.asyncio
async def test_defect_002_case4_ambiguous_elements_no_safe_distinction():
    """Case 4: Ambiguous elements where no safe distinction exists must return success=False according to contract."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{TAG_AMBIGUITY_FIXTURE}")
        resolver = SelfHealingResolver()

        # Both clone buttons have identical text "Clone Item", identical class, identical tag
        result_clone = await resolver.resolve(bp.page.raw_page, "Clone Item")
        assert result_clone.success is False
        assert "Ambiguous" in result_clone.reason

        # Generic tag "button" with multiple buttons on page and no context must not arbitrarily pick one
        result_generic_button = await resolver.resolve(bp.page.raw_page, "button")
        assert result_generic_button.success is False
        assert "Ambiguous" in result_generic_button.reason


@pytest.mark.asyncio
async def test_defect_002_case5_specific_strategy_wins_over_generic_tag_fallback():
    """Case 5: A more specific strategy (placeholder) must win over generic tag fallback ('input')."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{TAG_AMBIGUITY_FIXTURE}")
        resolver = SelfHealingResolver()

        result = await resolver.resolve(bp.page.raw_page, "Your work email")
        assert result.success is True
        # Selector must NOT be bare "input"
        assert result.selector != "input"
        assert "email" in result.selector.lower()

        # Observable behavior: typing fills the email input, leaving user-field empty
        await bp.page.type_healed("Your work email", "engineer@enterprise.org")
        email_val = await bp.page.evaluate("() => document.querySelector('input[type=\"email\"]').value")
        user_val = await bp.page.evaluate("() => document.getElementById('user-field').value")
        assert email_val == "engineer@enterprise.org"
        assert user_val == ""

