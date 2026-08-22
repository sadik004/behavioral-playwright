import sys
import socket
import urllib.error
import pytest
from unittest.mock import MagicMock, patch

# Stub behavioral_playwright packages if not installed in local environment
class MockProviderUnavailableError(Exception):
    pass

class MockProviderError(Exception):
    pass

class MockInvalidRequestError(Exception):
    pass

for mod in [
    'behavioral_playwright',
    'behavioral_playwright.core',
    'behavioral_playwright.core.config',
    'behavioral_playwright.core.exceptions',
    'behavioral_playwright.core.circuit_breaker',
    'behavioral_playwright.core.v10_core',
    'behavioral_playwright.acquisition',
    'behavioral_playwright.acquisition.exceptions',
    'behavioral_playwright.acquisition.models',
    'behavioral_playwright.acquisition.router',
    'behavioral_playwright.acquisition.handoff',
]:
    if mod not in sys.modules:
        m = MagicMock()
        if mod == 'behavioral_playwright.acquisition.exceptions':
            m.ProviderUnavailableError = MockProviderUnavailableError
            m.InvalidRequestError = MockInvalidRequestError
        elif mod == 'behavioral_playwright.core.exceptions':
            m.ProviderError = MockProviderError
        sys.modules[mod] = m

from bp_facade12 import BP


def test_measure_response_time_invalid_scheme():
    """Verify that an invalid URL scheme raises ValueError."""
    bp = BP()
    with pytest.raises(ValueError, match="Invalid URL schema"):
        bp.network.measure_response_time("ftp://example.com")


def test_measure_response_time_success():
    """Verify real response-time timing measurement with simulated HTTP response."""
    bp = BP()
    bp.network.set_timeout(5000)
    bp.network.set_custom_headers({"X-Custom-Header": "TestValue"})

    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        duration = bp.network.measure_response_time("https://httpbin.org/get")

        assert isinstance(duration, float)
        assert duration >= 0.0
        mock_urlopen.assert_called_once()
        req_arg = mock_urlopen.call_args[0][0]
        assert req_arg.get_header("X-custom-header") == "TestValue"
        assert req_arg.get_method() == "HEAD"
        assert mock_urlopen.call_args[1]["timeout"] == 5.0


def test_measure_response_time_handles_http_error_as_valid_roundtrip():
    """Verify that HTTP 4xx/5xx responses complete network roundtrip and return latency."""
    bp = BP()
    http_error = urllib.error.HTTPError("https://example.com/404", 404, "Not Found", {}, None)

    with patch("urllib.request.urlopen", side_effect=http_error):
        duration = bp.network.measure_response_time("https://example.com/404")
        assert isinstance(duration, float)
        assert duration >= 0.0


def test_measure_response_time_timeout_propagation():
    """Verify network timeout raises exception rather than returning fake success."""
    bp = BP()
    bp.network.set_timeout(1000)

    timeout_error = urllib.error.URLError(socket.timeout("Connection timed out"))

    with patch("urllib.request.urlopen", side_effect=timeout_error):
        with pytest.raises(urllib.error.URLError):
            bp.network.measure_response_time("https://timeout.example.com")


def test_measure_response_time_connection_failure_propagation():
    """Verify DNS / Connection refused errors are propagated properly."""
    bp = BP()
    conn_error = urllib.error.URLError("Connection refused")

    with patch("urllib.request.urlopen", side_effect=conn_error):
        with pytest.raises(urllib.error.URLError):
            bp.network.measure_response_time("https://unreachable.local")


@pytest.mark.asyncio
async def test_measure_response_time_async():
    """Verify async measurement executes without blocking event loop."""
    bp = BP()
    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp):
        duration = await bp.network.measure_response_time_async("https://example.com")
        assert isinstance(duration, float)
        assert duration >= 0.0


@pytest.mark.asyncio
async def test_top_level_bp_delegation():
    """Verify top-level BP methods delegate to NetworkNamespace."""
    bp = BP()
    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp):
        dur1 = bp.measure_response_time("https://example.com")
        assert isinstance(dur1, float)

        dur2 = await bp.measure_response_time_async("https://example.com")
        assert isinstance(dur2, float)
