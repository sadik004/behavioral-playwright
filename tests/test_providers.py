"""Phase 4 provider-adapter tests.

Three layers, per the integration mandate:
  1. Honest gating   - absent providers raise ProviderUnavailableError, never fake.
  2. Adapter logic   - exercised with deterministic injected test doubles
                       (the documented ``*_factory`` test seams).
  3. Live integration- run only for providers actually installed on this host
                       (playwright, patchright); browser-binary failures skip
                       honestly. UC live runs are opt-in via SQ_LIVE_UC=1.

Environment truth pinned by this suite (as of 2026-08-31): playwright,
patchright, undetected_chromedriver installed; curl_cffi, browser_use,
stagehand not installed.
"""
import asyncio
import struct
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import providers  # noqa: E402,F401
from providers import (  # noqa: E402
    BrowserSession,
    BrowserUseProvider,
    CurlCffiProvider,
    PatchrightProvider,
    PlaywrightProvider,
    ProviderUnavailableError,
    StagehandProvider,
    UnknownProviderError,
    UndetectedChromedriverProvider,
    create_agent_provider,
    create_browser_provider,
    create_network_provider,
    provider_matrix,
)


# ------------------------------------------------------------- registry
def test_factory_selects_registered_providers():
    assert isinstance(create_browser_provider("playwright"), PlaywrightProvider)
    assert isinstance(create_browser_provider("PATCHRIGHT"), PatchrightProvider)
    assert isinstance(
        create_browser_provider("undetected_chromedriver"), UndetectedChromedriverProvider
    )
    assert isinstance(create_network_provider("curl_cffi"), CurlCffiProvider)
    assert isinstance(create_agent_provider("browser_use"), BrowserUseProvider)
    assert isinstance(create_agent_provider("stagehand"), StagehandProvider)


def test_unknown_provider_names_list_available_choices():
    with pytest.raises(UnknownProviderError) as exc:
        create_browser_provider("phantom_browser")
    assert "patchright" in str(exc.value) and "playwright" in str(exc.value)
    with pytest.raises(UnknownProviderError):
        create_network_provider("requests")
    with pytest.raises(UnknownProviderError):
        create_agent_provider("jarvis")


def test_provider_matrix_reports_honest_local_state():
    matrix = provider_matrix()
    assert set(matrix) == {
        "browser/playwright", "browser/patchright", "browser/undetected_chromedriver",
        "network/curl_cffi", "agent/browser_use", "agent/stagehand",
    }
    assert matrix["browser/playwright"].installed is True
    assert matrix["browser/patchright"].installed is True
    assert matrix["browser/undetected_chromedriver"].installed is True
    assert matrix["network/curl_cffi"].installed is False
    assert matrix["agent/browser_use"].installed is False
    assert matrix["agent/stagehand"].installed is False


# ------------------------------------------------- honest provider gating
def test_absent_curl_cffi_raises_explicit_unavailable():
    provider = CurlCffiProvider()
    assert provider.is_available() is False
    with pytest.raises(ProviderUnavailableError) as exc:
        provider.fetch("https://example.invalid/x")
    assert "pip install curl-cffi" in str(exc.value)


def test_absent_browser_use_raises_explicit_unavailable():
    provider = BrowserUseProvider()
    assert provider.is_available() is False
    with pytest.raises(ProviderUnavailableError) as exc:
        provider.run_task("go somewhere", llm=object())
    assert "pip install browser-use" in str(exc.value)


def test_absent_stagehand_raises_explicit_unavailable():
    provider = StagehandProvider()
    assert provider.is_available() is False
    with pytest.raises(ProviderUnavailableError) as exc:
        asyncio.run(provider.start(model="openai/gpt-x", model_api_key="sk-test"))
    assert "pip install stagehand" in str(exc.value)


# --------------------------------- adapter logic via deterministic doubles
class _FakeNative:
    def __init__(self):
        self.closed = False

    def quit(self):
        self.closed = True


class _RecordingFactory:
    def __init__(self, result):
        self.calls = []
        self.result = result

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_browser_session_close_is_idempotent():
    native = _FakeNative()
    session = BrowserSession("playwright", native, native.quit)
    session.close()
    session.close()
    assert native.closed is True  # closer ran exactly once


def test_playwright_adapter_delegates_to_injected_factory():
    session = BrowserSession("playwright", _FakeNative(), lambda: None)
    factory = _RecordingFactory(session)
    provider = PlaywrightProvider(session_factory=factory)
    assert provider.launch(headless=False, slow_mo=5) is session
    assert factory.calls == [{"headless": False, "slow_mo": 5}]


def test_patchright_adapter_delegates_to_injected_factory():
    session = BrowserSession("patchright", _FakeNative(), lambda: None)
    factory = _RecordingFactory(session)
    provider = PatchrightProvider(session_factory=factory)
    assert provider.launch(headless=True) is session
    assert factory.calls == [{"headless": True}]


def test_undetected_chromedriver_adapter_delegates_to_injected_factory():
    session = BrowserSession("undetected_chromedriver", _FakeNative(), lambda: None)
    factory = _RecordingFactory(session)
    provider = UndetectedChromedriverProvider(session_factory=factory)
    assert provider.launch(headless=True) is session
    assert factory.calls == [{"headless": True}]


def test_curl_cffi_adapter_passes_impersonate_and_method():
    fake_response = object()
    factory = _RecordingFactory(fake_response)
    provider = CurlCffiProvider(request_factory=factory)
    assert provider.fetch("https://a.example/x") is fake_response
    assert factory.calls[0]["impersonate"] == "chrome"   # documented default
    provider.fetch("https://a.example/y", method="POST", impersonate="firefox135")
    assert factory.calls[1]["impersonate"] == "firefox135"
    assert factory.calls[1]["method"] == "post"


def test_curl_cffi_adapter_rejects_unsupported_methods_and_errors_propagate():
    provider = CurlCffiProvider(request_factory=_RecordingFactory(object()))
    with pytest.raises(ValueError) as exc:
        provider.fetch("https://a.example/z", method="TRACE")
    assert "TRACE" in str(exc.value)

    def _boom(*args, **kwargs):
        raise ConnectionError("network down")

    failing = CurlCffiProvider(request_factory=_boom)
    with pytest.raises(ConnectionError):  # real errors propagate untouched
        failing.fetch("https://a.example/w")


def test_browser_use_adapter_requires_llm_and_passes_task_through():
    sentinel = object()
    factory = _RecordingFactory(sentinel)
    provider = BrowserUseProvider(agent_factory=factory)

    with pytest.raises(ValueError) as exc:
        provider.run_task("buy gpu", llm=None)
    assert "LLM" in str(exc.value)
    assert factory.calls == []  # honest contract enforced before any agent work

    fake_llm = object()
    assert provider.run_task("buy gpu", llm=fake_llm) is sentinel
    assert factory.calls == [{"task": "buy gpu", "llm": fake_llm, "browser": None}]

    with pytest.raises(ValueError):
        provider.run_task("", llm=fake_llm)


def test_stagehand_adapter_requires_model_and_key():
    sentinel = object()

    async def _factory(**kwargs):
        return sentinel

    provider = StagehandProvider(stagehand_factory=_factory)
    with pytest.raises(ValueError) as exc:
        asyncio.run(provider.start(model="openai/gpt-x", model_api_key=None))
    assert "model_api_key" in str(exc.value)

    result = asyncio.run(provider.start(
        browser=None, model="openai/gpt-x", model_api_key="sk-test"
    ))
    assert result is sentinel


# ------------------------------------------------- live integration tests
def _launch_or_skip(provider):
    """Launch a real browser; skip honestly if the binary is unavailable."""
    try:
        return provider.launch(headless=True)
    except Exception as exc:  # missing browser binary / driver issue
        pytest.skip(f"{provider.display_name} browser binary unavailable: {exc}")


def test_live_playwright_navigates_local_data_url():
    session = _launch_or_skip(PlaywrightProvider())
    try:
        page = session.native.new_page()
        page.goto("data:text/html,<title>provider-ok</title><h1>ok</h1>")
        assert page.title() == "provider-ok"
        assert page.inner_text("h1") == "ok"
        page.close()
    finally:
        session.close()


def test_live_patchright_navigates_local_data_url():
    session = _launch_or_skip(PatchrightProvider())
    try:
        page = session.native.new_page()
        page.goto("data:text/html,<title>patchright-ok</title><h1>ok</h1>")
        assert page.title() == "patchright-ok"
        page.close()
    finally:
        session.close()


@pytest.mark.skipif(
    __import__("os").environ.get("SQ_LIVE_UC") != "1",
    reason="UC live launch downloads a chromedriver binary; opt-in via SQ_LIVE_UC=1",
)
def test_live_undetected_chromedriver_launch():
    session = UndetectedChromedriverProvider().launch(headless=True)
    try:
        session.native.get("data:text/html,<title>uc-ok</title>")
        assert "uc-ok" in session.native.title
    finally:
        session.close()


def test_core_framework_runs_without_any_provider():
    """Core capability works with zero optional providers involved."""
    import itch_binary

    parser = itch_binary.ItchBinaryParser(dollar_threshold=50_000.0)
    add = b"A" + (1).to_bytes(2, "big") + b"\x00" * 2 + b"\x00" * 6
    add += (1001).to_bytes(8, "big") + b"B" + (300).to_bytes(4, "big")
    add += b"AAPL    " + (200_000).to_bytes(4, "big")
    framed = struct.pack(">H", len(add)) + add
    result = parser.parse_stream(framed)
    assert result.errors == [] and result.book_snapshot["bids"][0]["shares"] == 300

