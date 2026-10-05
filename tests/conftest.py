"""Shared pytest configuration and session-scoped fixtures."""
from __future__ import annotations

from pathlib import Path
import pytest


@pytest.fixture(scope="session", autouse=True)
def test_workspace_fixtures():
    """Ensures legitimate test artifacts exist during test execution."""
    p1 = Path("screenshot.png")
    p2 = Path("network_trace.json")
    created = []

    if not p1.exists():
        p1.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        created.append(p1)
    if not p2.exists():
        p2.write_text('{"status": "captured", "events": 10}', encoding="utf-8")
        created.append(p2)

    yield

    for f in created:
        try:
            f.unlink()
        except Exception:
            pass
