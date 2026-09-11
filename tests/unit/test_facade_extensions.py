"""Unit tests for extended BP facade namespaces (proxy, fingerprint, storage)."""

import os
import tempfile
from behavioral_playwright import BP


def test_bp_facade_extended_namespaces():
    bp = BP()

    # 1. Proxy namespace
    assert hasattr(bp, "proxy")
    p = bp.proxy.add_proxy("10.0.0.1", 8080)
    assert p.host == "10.0.0.1"
    fetched = bp.proxy.get_proxy()
    assert fetched.host == "10.0.0.1"

    # 2. Fingerprint namespace
    assert hasattr(bp, "fingerprint")
    prof = bp.fingerprint.generate()
    assert prof.user_agent != ""
    assert prof.screen.width > 0
    script = bp.fingerprint.generate_evasion_script(prof)
    assert "WebGLRenderingContext" in script

    # 3. Storage namespace
    assert hasattr(bp, "storage")
    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, "test.json")
        bp.storage.export([{"msg": "hello"}], target)
        assert os.path.exists(target)
