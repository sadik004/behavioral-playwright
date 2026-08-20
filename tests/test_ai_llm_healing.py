"""
Unit tests for LLM provider, reasoning, 4-tier Self-Healing Resolver, ActionValidator, and VisualVerification.
"""

import json
import os

import pytest

from behavioral_playwright import (
    ActionValidator,
    AIConfig,
    AutomationConfig,
    BehavioralHumanizer,
    DeterministicRandomSource,
    LLMProvider,
    LLMReasoning,
    MockPage,
    VirtualTestClock,
)


@pytest.mark.asyncio
async def test_ai_llm_mocking() -> None:
    config = AutomationConfig(ai=AIConfig(enabled=True))
    os.environ["STEALTH_TEST_MODE"] = "true"
    provider = LLMProvider(config)
    res_login = await provider.generate_response("Reason about login button")
    parsed = json.loads(res_login)
    assert parsed["action"] == "click"
    assert parsed["confidence"] == 0.95


@pytest.mark.asyncio
async def test_ai_llm_malformed_response() -> None:
    config = AutomationConfig(ai=AIConfig(enabled=True))
    os.environ["STEALTH_TEST_MODE"] = "true"
    provider = LLMProvider(config)
    reasoning = LLMReasoning(provider)
    res = await reasoning.propose_healing_action("trigger_malformed_json_btn", "<div>", [])
    assert "selector" in res


@pytest.mark.asyncio
async def test_ai_timeout_retry() -> None:
    config = AutomationConfig(ai=AIConfig(enabled=True, retry=1, timeout=0.1))
    os.environ["STEALTH_LLM_API_KEY"] = "dummy_invalid_key_to_force"
    os.environ["STEALTH_LLM_BASE_URL"] = "http://127.0.0.1:9999/invalid"
    os.environ["STEALTH_TEST_MODE"] = "false"
    provider = LLMProvider(config)
    res = await provider.generate_response("test_retry")
    assert len(res) > 0
    parsed = json.loads(res)
    assert "action" in parsed
    os.environ["STEALTH_TEST_MODE"] = "true"
    os.environ.pop("STEALTH_LLM_API_KEY", None)


@pytest.mark.asyncio
async def test_ai_selector_self_healing(mock_page: MockPage, test_clock: VirtualTestClock) -> None:
    config = AutomationConfig(ai=AIConfig(enabled=True, self_healing_enabled=True, ocr_cv_enabled=True))
    humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=test_clock)
    assert humanizer.ai_resolver is not None

    # L1: Deterministic Levenshtein
    resolved_l1 = await humanizer.ai_resolver.resolve_element(mock_page, "#btn-login-dynamic")
    assert resolved_l1 is not None
    assert resolved_l1["strategy"] == "deterministic_levenshtein"
    assert resolved_l1["selector"] == "#btn-login"

    # L2: DOM Accessibility
    resolved_l2 = await humanizer.ai_resolver.resolve_element(
        mock_page, "completely_different_selector_that_fails_levenshtein_but_contains_textbox"
    )
    assert resolved_l2 is not None
    assert resolved_l2["strategy"] == "dom_accessibility"
    assert resolved_l2["selector"] == "#text-input"


def test_ai_confidence_validation() -> None:
    config = AutomationConfig(ai=AIConfig(enabled=True, confidence_threshold=0.80))
    validator = ActionValidator(config)
    low_confidence = {"selector": "#btn", "confidence": 0.50, "strategy": "llm_reasoning"}
    high_confidence = {"selector": "#btn", "confidence": 0.90, "strategy": "llm_reasoning"}
    assert not validator.validate_proposal(low_confidence)
    assert validator.validate_proposal(high_confidence)


@pytest.mark.asyncio
async def test_ai_visual_verification(mock_page: MockPage, test_clock: VirtualTestClock) -> None:
    config = AutomationConfig(ai=AIConfig(enabled=True, ocr_cv_enabled=True))
    humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=test_clock)
    assert humanizer.ai_verification is not None

    state_before = await humanizer.ai_verification.record_state_before(mock_page)
    assert state_before["url"] == mock_page.url
    res = await humanizer.ai_verification.verify_state_after(mock_page, state_before, "Mocked DOM Content")
    assert res["success"] is True
    assert res["text_verified"] is True


@pytest.mark.asyncio
async def test_targeted_interactive_dom_search_healing(test_clock: VirtualTestClock) -> None:
    # Build DOM with heavy non-interactive elements and specific interactive targets
    noisy_html = (
        "<html><body>"
        "<div class='container'>"
        + "".join(f"<p class='para-{i}'>Unrelated paragraph content {i} <span class='s'>text</span></p>" for i in range(50))
        + "<section class='checkout'>"
        "<button id='btn-submit-order' class='btn primary' role='button'>Place Order</button>"
        "<input id='coupon-input' name='coupon_code' placeholder='Promo'>"
        "<select name='country_select'><option value='us'>US</option></select>"
        "<textarea name='order_notes'></textarea>"
        "<a href='/checkout' role='button' class='link-btn'>Proceed</a>"
        "</section>"
        + "".join(f"<div class='footer-col'><h6>Header {j}</h6><ul><li>Item A</li><li>Item B</li></ul></div>" for j in range(20))
        + "</div></body></html>"
    )
    page = MockPage(initial_html=noisy_html)
    config = AutomationConfig(ai=AIConfig(enabled=True, self_healing_enabled=True, ocr_cv_enabled=True))
    humanizer = BehavioralHumanizer(page, config, rng=DeterministicRandomSource(42), clock=test_clock)
    assert humanizer.ai_resolver is not None

    # L1 Fuzzy match on slightly altered selector targeting the button
    resolved_btn = await humanizer.ai_resolver.resolve_element(page, "#btn-submit-order-dynamic")
    assert resolved_btn is not None
    assert resolved_btn["strategy"] == "deterministic_levenshtein"
    assert resolved_btn["selector"] == "#btn-submit-order"

    # L2 DOM Accessibility match on input by role/name
    resolved_coupon = await humanizer.ai_resolver.resolve_element(page, "damaged_selector_coupon_code_field")
    assert resolved_coupon is not None
    assert resolved_coupon["strategy"] == "dom_accessibility"
    assert resolved_coupon["selector"] == "#coupon-input"
