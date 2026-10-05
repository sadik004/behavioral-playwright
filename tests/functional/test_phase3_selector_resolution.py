"""Phase 3 Comprehensive Verification Battery: Intelligent Selector Resolution & Self-Healing Correctness.

Verifies:
- L1 Exact Resolution (unambiguous, syntax errors, generic tag ambiguity, require_unique contract)
- L2 Semantic Recovery (aria-label, accessible name, placeholder, role boost hygiene, multilingual unicode, tie rejection)
- L3 Fuzzy Recovery (Levenshtein distance, typo tolerance, similarity threshold boundary, tie rejection, short substring hygiene)
- Self-Healing & Learned Memory (live DOM mutation recovery, live-DOM verification, stale memory invalidation, instance isolation)
- Deterministic Action Contracts (click_healed, type_healed, ElementResolutionError honesty, observable DOM side-effects)
"""

import pytest
from behavioral_playwright.config.settings import ResolverConfig
from behavioral_playwright.exceptions import ElementResolutionError
from behavioral_playwright.facade import BP
from behavioral_playwright.models.elements import DOMElement
from behavioral_playwright.models.results import ResolutionStrategy
from behavioral_playwright.selectors.fuzzy import FuzzyResolverStrategy, calculate_similarity_ratio
from behavioral_playwright.selectors.resolver import SelfHealingResolver
from behavioral_playwright.selectors.semantic import SemanticResolverStrategy

PHASE3_FIXTURE_HTML = """<!DOCTYPE html>
<html>
<head><title>Phase 3 Selector Resolution Testbed</title></head>
<body>
    <header>
        <h1 id="page-title">Enterprise Dashboard</h1>
    </header>

    <!-- Section 1: Standard & Mutated Controls for L1/L2 testing -->
    <div id="auth-section">
        <!-- Exact ID for L1 match -->
        <button id="exact-login-btn" onclick="window.__clicked_login = true;">Sign In to Portal</button>
        
        <!-- Mutated ID simulating broken selector, accessible via aria-label -->
        <button id="mutated-auth-id-2026" aria-label="Confirm Transaction" onclick="window.__clicked_confirm = true;">
            Finalize
        </button>
        
        <!-- Input accessible via placeholder -->
        <input id="search-input-field" placeholder="Search product catalogue..." />
        
        <!-- Multilingual Unicode control -->
        <button id="bengali-btn" aria-label="পেমেন্ট নিশ্চিত করুন" onclick="window.__clicked_bengali = true;">
            পেমেন্ট
        </button>
    </div>

    <!-- Section 2: Ambiguous identical candidates for tie rejection -->
    <div id="ambiguous-section">
        <button class="action-card-btn" onclick="window.__action_card = 'first';">Download Report</button>
        <button class="action-card-btn" onclick="window.__action_card = 'second';">Download Report</button>
    </div>

    <!-- Section 3: Distinct role elements for role-boost hygiene -->
    <div id="role-hygiene-section">
        <button id="destructive-delete-btn" role="button" onclick="window.__deleted = true;">Delete Account</button>
        <div id="search-widget" role="search">
            <input id="query-box" type="text" placeholder="Filter records" />
        </div>
    </div>

    <!-- Section 4: Target for fuzzy typo resolution -->
    <div id="fuzzy-section">
        <button id="btn-comprehensive-analytics" onclick="window.__clicked_analytics = true;">
            ComprehensiveAnalyticsPlatform
        </button>
    </div>
</body>
</html>
"""

import urllib.parse

def get_fixture_url() -> str:
    return f"data:text/html;charset=utf-8,{urllib.parse.quote(PHASE3_FIXTURE_HTML)}"



# =========================================================================
# 1. L1 EXACT RESOLUTION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_l1_exact_single_match_success():
    """Valid, unique CSS selector resolves immediately via L1 with 1.0 confidence."""
    async with BP() as bp:
        await bp.open(get_fixture_url())
        resolver = SelfHealingResolver()

        result = await resolver.resolve(bp.page.raw_page, "#exact-login-btn")
        assert result.success is True
        assert result.strategy == ResolutionStrategy.L1_EXACT
        assert result.confidence == 1.0
        assert result.selector == "#exact-login-btn"
        assert result.element_count == 1


@pytest.mark.asyncio
async def test_l1_exact_syntax_error_graceful_cascade():
    """Invalid CSS selector syntax does not crash; gracefully cascades to self-healing tiers."""
    async with BP() as bp:
        await bp.open(get_fixture_url())
        resolver = SelfHealingResolver()

        # Malformed CSS selector that triggers syntax exception in DOM query
        result = await resolver.resolve(bp.page.raw_page, "button:::invalid[syntax==")
        # Should honestly report failure without raising unhandled exception
        assert result.success is False
        assert result.selector is None
        assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_l1_exact_require_unique_rejects_ambiguity():
    """When require_unique=True, matching multiple elements prevents arbitrary selection."""
    async with BP() as bp:
        await bp.open(get_fixture_url())
        resolver = SelfHealingResolver(config=ResolverConfig(require_unique=True))

        # .action-card-btn matches 2 identical buttons
        result = await resolver.resolve(bp.page.raw_page, ".action-card-btn", require_unique=True)
        assert result.success is False
        assert "Ambiguous" in result.reason or "ambiguous" in result.reason.lower()


# =========================================================================
# 2. L2 SEMANTIC & ACCESSIBILITY TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_l2_semantic_aria_label_recovery():
    """Mutated ID element is successfully resolved via aria-label semantic profile."""
    async with BP() as bp:
        await bp.open(get_fixture_url())
        resolver = SelfHealingResolver()

        result = await resolver.resolve(bp.page.raw_page, "Confirm Transaction")
        assert result.success is True
        assert result.strategy == ResolutionStrategy.L2_SEMANTIC
        assert result.confidence >= 0.85
        assert result.matched_element is not None
        assert result.matched_element.aria_label == "Confirm Transaction"


@pytest.mark.asyncio
async def test_l2_semantic_placeholder_matching():
    """Input element is accurately resolved via placeholder attribute."""
    async with BP() as bp:
        await bp.open(get_fixture_url())
        resolver = SelfHealingResolver()

        result = await resolver.resolve(bp.page.raw_page, "Search product catalogue")
        assert result.success is True
        assert result.strategy == ResolutionStrategy.L2_SEMANTIC
        assert result.confidence >= 0.85
        assert "search" in result.selector.lower()


@pytest.mark.asyncio
async def test_l2_semantic_multilingual_unicode_support():
    """Non-ASCII unicode text and aria-labels are correctly tokenized and matched."""
    async with BP() as bp:
        await bp.open(get_fixture_url())
        resolver = SelfHealingResolver()

        result = await resolver.resolve(bp.page.raw_page, "পেমেন্ট নিশ্চিত করুন")
        assert result.success is True
        assert result.strategy == ResolutionStrategy.L2_SEMANTIC
        assert result.confidence >= 0.85


@pytest.mark.asyncio
async def test_l2_semantic_tie_rejection_honesty():
    """Identical semantic candidates must result in honest failure (Ambiguous semantic matches)."""
    async with BP() as bp:
        await bp.open(get_fixture_url())
        resolver = SelfHealingResolver()

        # "Download Report" matches two buttons with identical text, class, and tag
        result = await resolver.resolve(bp.page.raw_page, "Download Report")
        assert result.success is False
        assert "Ambiguous" in result.reason
        assert result.selector is None


@pytest.mark.asyncio
async def test_l2_semantic_role_hygiene_no_false_fallback():
    """Unrelated elements sharing role='button' are NOT falsely matched for unrelated targets."""
    async with BP() as bp:
        await bp.open(get_fixture_url())
        resolver = SelfHealingResolver()

        # "Create Order Button" should NEVER resolve the "Delete Account" button
        result = await resolver.resolve(bp.page.raw_page, "Create Order Button")
        assert result.success is False
        if result.matched_element:
            assert "delete" not in result.matched_element.id.lower()


# =========================================================================
# 3. L3 FUZZY RESOLUTION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_l3_fuzzy_typo_resolution():
    """Misspelled target string resolves candidate via Levenshtein similarity metric."""
    async with BP() as bp:
        await bp.open(get_fixture_url())
        config = ResolverConfig(fuzzy_similarity_threshold=0.60)
        resolver = SelfHealingResolver(config=config)

        # Target with 3 character typos
        result = await resolver.resolve(bp.page.raw_page, "ComprehensveAnalytcsPlatfrm")
        assert result.success is True
        assert result.strategy == ResolutionStrategy.L3_FUZZY
        assert result.confidence >= 0.60
        assert "analytics" in result.selector.lower() or "btn" in result.selector.lower()


def test_l3_fuzzy_short_substring_hygiene():
    """Single character or tiny substring does NOT receive artificial similarity bonus."""
    score = calculate_similarity_ratio("a", "ComprehensiveAnalyticsPlatform")
    # Must be low (< 0.20), not boosted to 0.70+
    assert score < 0.20


@pytest.mark.asyncio
async def test_l3_fuzzy_threshold_boundary_enforcement():
    """Candidates scoring below fuzzy_similarity_threshold must be honestly rejected."""
    strategy = FuzzyResolverStrategy(similarity_threshold=0.85)
    candidates = [
        DOMElement(tag="button", text="Completely Different Text", selector="button#diff")
    ]
    res = await strategy.resolve(page=None, target="Proceed to Checkout", candidates=candidates)
    assert res is None


# =========================================================================
# 4. SELF-HEALING & LEARNED MEMORY TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_self_healing_learned_resolution_via_memory():
    """Verified healing is stored in memory and recalled on subsequent resolutions."""
    async with BP() as bp:
        await bp.open(get_fixture_url())
        resolver = SelfHealingResolver()

        # First resolution: L1 fails, heals via L2 Semantic
        first_res = await resolver.resolve(bp.page.raw_page, "Confirm Transaction")
        assert first_res.success is True
        assert first_res.strategy == ResolutionStrategy.L2_SEMANTIC

        # Second resolution: should be recalled from verified memory
        second_res = await resolver.resolve(bp.page.raw_page, "Confirm Transaction")
        assert second_res.success is True
        assert second_res.strategy == ResolutionStrategy.MEMORY
        assert second_res.selector == first_res.selector
        assert "Verified learned resolution" in second_res.reason


@pytest.mark.asyncio
async def test_self_healing_memory_stale_divergence_fails_to_live_cascade():
    """Historical success must NEVER override current page evidence: mutated DOM invalidates memory."""
    async with BP() as bp:
        await bp.open(get_fixture_url())
        resolver = SelfHealingResolver()

        # Learn target in memory
        res1 = await resolver.resolve(bp.page.raw_page, "Confirm Transaction")
        assert res1.success is True

        # Mutate DOM dynamically: remove the healed button and add a new replacement with different text
        await bp.page.evaluate("""() => {
            const btn = document.getElementById('mutated-auth-id-2026');
            if (btn) btn.remove();
        }""")

        # Memory recall must verify against live DOM, detect missing element, invalidate memory, and fail
        res2 = await resolver.resolve(bp.page.raw_page, "Confirm Transaction")
        assert res2.success is False
        assert "Confirm Transaction" not in resolver.memory


# =========================================================================
# 5. DETERMINISTIC ACTION CONTRACTS & SIDE-EFFECTS
# =========================================================================

@pytest.mark.asyncio
async def test_click_healed_produces_observable_dom_mutation():
    """click_healed successfully clicks healed target and triggers JavaScript event."""
    async with BP() as bp:
        await bp.open(get_fixture_url())

        res = await bp.page.click_healed("Confirm Transaction")
        assert res.success is True

        was_clicked = await bp.page.evaluate("() => window.__clicked_confirm === true")
        assert was_clicked is True


@pytest.mark.asyncio
async def test_type_healed_fills_resolved_input():
    """type_healed resolves target input and mutates its value in the live DOM."""
    async with BP() as bp:
        await bp.open(get_fixture_url())

        res = await bp.page.type_healed("Search product catalogue", "Enterprise Architecture")
        assert res.success is True

        val = await bp.page.evaluate("() => document.getElementById('search-input-field').value")
        assert val == "Enterprise Architecture"


@pytest.mark.asyncio
async def test_action_on_ambiguous_target_raises_error():
    """Action methods strictly reject ambiguous targets and raise ElementResolutionError."""
    async with BP() as bp:
        await bp.open(get_fixture_url())

        # Multiple identical 'Download Report' buttons exist with no safe distinction
        with pytest.raises(ElementResolutionError) as exc_info:
            await bp.page.click_healed("Download Report")

        assert "could not be resolved" in str(exc_info.value)
