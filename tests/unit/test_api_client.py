"""Unit tests for optimized API client, connection pooling, and caching."""

import pytest
from behavioral_playwright import BP
from behavioral_playwright.api.client import ApiRequestCache, ApiResponse, AsyncApiClient


def test_api_cache():
    cache = ApiRequestCache(default_ttl_seconds=10.0)
    sample_resp = ApiResponse(
        status_code=200,
        headers={"content-type": "application/json"},
        body=b'{"status": "ok"}',
        elapsed_ms=12.5,
    )

    cache.set("GET:https://api.example.com", sample_resp)
    cached = cache.get("GET:https://api.example.com")
    assert cached is not None
    assert cached.status_code == 200
    assert cached.cached is True
    assert cached.json() == {"status": "ok"}

    # Miss check
    assert cache.get("GET:https://other.com") is None


@pytest.mark.asyncio
async def test_async_api_client_and_facade():
    bp = BP()
    assert hasattr(bp, "api")

    # Offline/Double test via custom response cache
    client = AsyncApiClient(cache_ttl=60.0)
    fake_resp = ApiResponse(
        status_code=200,
        headers={"content-type": "application/json"},
        body=b'{"user": "alice", "id": 100}',
        elapsed_ms=5.0,
    )
    client.cache.set("GET:https://api.example.com/user/100", fake_resp)

    res = await client.get("https://api.example.com/user/100")
    assert res.status_code == 200
    assert res.cached is True
    assert res.json()["user"] == "alice"
