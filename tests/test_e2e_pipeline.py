"""
End-to-End integration tests using provider cascading fallback and AI orchestration.
"""

from unittest.mock import patch

import pytest

from behavioral_playwright import (
    AIConfig,
    AutomationConfig,
    BehavioralHumanizer,
    BrowserConfig,
    BrowserProviderFactory,
    CircuitBreaker,
    DeterministicRandomSource,
    ExploitPoCExporter,
    MockPage,
    NavigationManager,
    NetworkConfig,
    SystemClock,
    VirtualTestClock,
)


@pytest.mark.asyncio
async def test_complete_ai_mock_e2e_pipeline(mock_page: MockPage, test_clock: VirtualTestClock) -> None:
    config = AutomationConfig(ai=AIConfig(enabled=True, self_healing_enabled=True, ocr_cv_enabled=True))
    humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=test_clock)

    click_ok = await humanizer.execute_safe_click("#btn-login", "Mocked DOM Content")
    assert click_ok is True

    click_healed = await humanizer.execute_safe_click("#broken-selector-dynamic", "Mocked DOM Content")
    assert click_healed is True

    type_healed = await humanizer.execute_safe_type("#username-broken", "my_user", "Mocked DOM Content")
    assert type_healed is True


@pytest.mark.asyncio
async def test_real_or_mock_integration_pipeline() -> None:
    config = AutomationConfig(
        browser=BrowserConfig(headless=True),
        network=NetworkConfig(max_attempts=1),
    )

    context, provider = await BrowserProviderFactory.launch_stabilized_lifecycle(config)
    try:
        page = context.pages[0] if context.pages else await context.new_page()

        cb = CircuitBreaker(clock=SystemClock())
        navigator = NavigationManager(config, cb)

        success = await navigator.safe_goto(page, "https://bot-detector.rebrowser.net")
        assert success is True

        humanizer = BehavioralHumanizer(page, config)
        try:
            await humanizer.human_type("#text-input", "QuantumTest")
        except Exception:
            await humanizer.move_mouse_to(150.0, 250.0, steps=10)
    finally:
        await provider.shutdown()


def test_exploit_poc_exporter_permission_error_handling() -> None:
    url = "https://example.com/api/login"
    headers = {"Content-Type": "application/json", "Sec-CH-UA": "ignore"}
    cookies = {"session": "token_abc"}

    # 1. Normal execution
    code_normal = ExploitPoCExporter.export_poc(url, "POST", headers, cookies, payload='{"user":"a"}')
    assert "requests.request" in code_normal
    assert "https://example.com/api/login" in code_normal

    # 2. PermissionError on directory creation
    with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access Denied")):
        code_perm_dir = ExploitPoCExporter.export_poc(url, "POST", headers, cookies, payload='{"user":"b"}')
        assert "requests.request" in code_perm_dir
        assert "https://example.com/api/login" in code_perm_dir

    # 3. PermissionError on file writing
    with patch("builtins.open", side_effect=PermissionError("Read-only filesystem")):
        code_perm_file = ExploitPoCExporter.export_poc(
            url, "GET", headers, cookies, output_path="./scratch/test_perm.py"
        )
        assert "requests.request" in code_perm_file
