"""
Unit tests for humanized clicks, keyboard dynamics, kinetic scrolling, and fatigue modeling.
"""

import math
from typing import List

import pytest

from behavioral_playwright import (
    AutomationConfig,
    BehavioralHumanizer,
    ClickConfig,
    CognitiveInterferenceModel,
    DeterministicRandomSource,
    KeyboardConfig,
    LinguisticKeystrokeDynamics,
    MockPage,
    SelfHealingSelectorEngine,
    VirtualTestClock,
)


def test_click_timing_statistical_distribution() -> None:
    rng = DeterministicRandomSource(42)
    config = ClickConfig()

    samples: List[float] = []
    for _ in range(1000):
        val = rng.gauss(config.duration_mean, config.duration_std)
        samples.append(max(config.duration_min, val))

    sample_mean = sum(samples) / len(samples)
    sample_variance = sum((x - sample_mean) ** 2 for x in samples) / (len(samples) - 1)
    sample_std = math.sqrt(sample_variance)

    assert abs(sample_mean - config.duration_mean) < 0.003
    assert abs(sample_std - config.duration_std) < 0.002

    for duration in samples:
        assert duration >= config.duration_min


@pytest.mark.asyncio
async def test_keyboard_human_typing_reconstruction(mock_page: MockPage, test_clock: VirtualTestClock) -> None:
    test_kb_cfg = KeyboardConfig(
        mistake_probability=1.0,
        avg_delay_mean=0.001,
        avg_delay_std=0.0,
        min_delay=0.001,
        correction_delay_min=0.001,
        correction_delay_max=0.001,
    )
    test_cfg = AutomationConfig(keyboard=test_kb_cfg)
    rng = DeterministicRandomSource(42)
    humanizer = BehavioralHumanizer(mock_page, test_cfg, rng=rng, clock=test_clock)

    await humanizer.human_type("#test-input", "VerifyMe")
    reconstructed = mock_page.keyboard.reconstruct_typed_output()
    assert reconstructed == "VerifyMe"


def test_linguistic_keystroke_dynamics() -> None:
    dynamics = LinguisticKeystrokeDynamics()
    f_th = dynamics.calculate_linguistic_factor("t", "h")
    assert f_th == 0.70
    f_the = dynamics.calculate_linguistic_factor("h", "e", "t")
    assert f_the == 0.55
    f_neutral = dynamics.calculate_linguistic_factor("q", "x")
    assert f_neutral == 1.0


def test_qwerty_key_distance() -> None:
    dist_qp = BehavioralHumanizer.get_qwerty_key_distance("q", "p")
    dist_qw = BehavioralHumanizer.get_qwerty_key_distance("q", "w")
    assert dist_qp > dist_qw
    assert BehavioralHumanizer.get_qwerty_key_distance("q", "$") == 2.5


def test_fatigue_modeling(mock_page: MockPage, test_clock: VirtualTestClock) -> None:
    config = AutomationConfig()
    humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=test_clock)
    assert humanizer.get_fatigue_multiplier() == 1.0
    humanizer.session_start -= 1800.0  # 30 minutes later
    assert humanizer.get_fatigue_multiplier() == 1.35


@pytest.mark.asyncio
async def test_mouse_sequence_chaining(mock_page: MockPage, test_clock: VirtualTestClock) -> None:
    config = AutomationConfig()
    humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=test_clock)
    await humanizer.move_mouse_sequence([(100.0, 150.0), (200.0, 300.0)])
    assert humanizer.current_position == (200.0, 300.0)


@pytest.mark.asyncio
async def test_inertial_scroll(mock_page: MockPage, test_clock: VirtualTestClock) -> None:
    config = AutomationConfig()
    humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=test_clock)
    await humanizer.human_scroll(50.0)
    assert len(mock_page.mouse.wheels) > 0
    total_scroll = sum(w[1] for w in mock_page.mouse.wheels)
    assert abs(total_scroll - 50.0) < 1.0


@pytest.mark.asyncio
async def test_human_idle_drift(mock_page: MockPage, test_clock: VirtualTestClock) -> None:
    config = AutomationConfig()
    humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=test_clock)
    humanizer.current_position = (100.0, 100.0)
    await humanizer.human_idle_drift(duration=0.2)
    assert len(mock_page.mouse.moves) > 0


def test_cognitive_interference_stroop() -> None:
    assert CognitiveInterferenceModel.calculate_stroop_penalty("RED CANCEL BUTTON") == 0.35
    assert CognitiveInterferenceModel.calculate_stroop_penalty("Normal submit") == 0.0


def test_self_healing_selector_engine() -> None:
    healer = SelfHealingSelectorEngine()
    candidates = ["#btn-login", "input[name='login']", "#submit-button"]
    healed = healer.heal_selector("#login", candidates)
    assert healed == "#btn-login"


@pytest.mark.asyncio
async def test_mock_page_complex_css_selectors() -> None:
    page = MockPage()

    # 1. Attribute, ID, and Class compound selector
    el = await page.query_selector("button[type='submit'].submit-btn")
    assert el is not None

    # 2. Pseudo-class :disabled and :enabled
    disabled_btn = await page.query_selector("button:disabled")
    assert disabled_btn is not None
    enabled_input = await page.query_selector("input:enabled")
    assert enabled_input is not None

    # 3. Direct child combinator and :nth-child / :first-child / :last-child
    first_li = await page.query_selector("ul.items > li:first-child")
    assert first_li is not None
    second_li = await page.query_selector("ul.items > li:nth-child(2)")
    assert second_li is not None
    last_li = await page.query_selector("ul.items > li:last-child")
    assert last_li is not None

    # 4. Comma list and :not selector
    links_or_buttons = await page.query_selector_all("a.nav-link, div:not(.interactive)")
    assert len(links_or_buttons) > 0

    # 5. Non-matching selector returns None
    missing = await page.query_selector("#non-existent-element-id")
    assert missing is None

    # 6. Dynamic custom content
    page.set_content("<form id='checkout'><div class='group'><input name='card' required></div></form>")
    card_input = await page.query_selector("form#checkout .group > input[name='card']")
    assert card_input is not None


def test_multimodal_timing_click_config_injection() -> None:
    # 1. Default configuration
    default_config = AutomationConfig()
    humanizer_default = BehavioralHumanizer(
        MockPage(), default_config, rng=DeterministicRandomSource(42), clock=VirtualTestClock()
    )
    assert humanizer_default.multimodal_timing.base_delay == 0.15  # 150ms default (0.15s)
    gap_default = humanizer_default.multimodal_timing.calculate_interaction_gap(DeterministicRandomSource(42), 1.0)
    assert gap_default > 0.0

    # 2. Custom ClickConfig pre_click_delay_max
    custom_config = AutomationConfig(click=ClickConfig(pre_click_delay_max=0.35))
    humanizer_custom = BehavioralHumanizer(
        MockPage(), custom_config, rng=DeterministicRandomSource(42), clock=VirtualTestClock()
    )
    assert humanizer_custom.multimodal_timing.base_delay == 0.35  # 350ms (0.35s)
    gap_custom = humanizer_custom.multimodal_timing.calculate_interaction_gap(DeterministicRandomSource(42), 1.0)

    # 3. Ratio between custom and default matches configuration scale
    assert math.isclose(gap_custom / gap_default, 0.35 / 0.15, rel_tol=1e-3)
