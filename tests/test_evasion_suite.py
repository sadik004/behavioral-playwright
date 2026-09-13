#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-End Unit & Integration Verification Suite for all Evasion Modules.
"""
import sys
import os
import asyncio
from pydantic import BaseModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from behavioral_evasion_suite import (
    OSResourceGuard,
    BiomechanicalMousePhysics,
    StatusGranularCircuitBreaker,
    QualitySentinel,
    BasePersistencePipeline,
    PowerHandMaster,
    PowerHandPlaywrightRunner,
    IdentityAnchor
)


def test_os_resource_guard():
    guard = OSResourceGuard()
    cap = guard.check_os_limits(concurrency_estimate=100)
    assert cap > 0
    print("  [✓] OS Resource Guard verified")


def test_biomechanical_mouse():
    mouse = BiomechanicalMousePhysics()
    traj = mouse.generate_trajectory((0, 0), (300, 300), steps=20)
    assert len(traj) > 20
    print("  [✓] Biomechanical Mouse Physics verified")


def test_circuit_breaker():
    cb = StatusGranularCircuitBreaker(threshold=2, cooldown_window=1.0)
    assert cb.allow_request() is True
    cb.register_failure("ip_ban_429_403")
    cb.register_failure("ip_ban_429_403")
    assert cb.state == "OPEN"
    print("  [✓] Status Granular Circuit Breaker verified")


def test_quality_sentinel():
    class Item(BaseModel):
        id: int
        name: str

    qs = QualitySentinel(max_allowed_failure_ratio=0.5, window_size=3)
    ok = qs.monitor_data_quality("https://test.local", {"id": 1, "name": "Laptop"}, Item)
    assert ok is True
    print("  [✓] Quality Sentinel schema validation verified")


def test_persistence_pipeline():
    async def run():
        pipe = BasePersistencePipeline(output_path="/tmp/test_pipe.ndjson")
        pipe.open()
        await pipe.append_record({"test": "data", "val": 42})
        await pipe.close()
        if os.path.exists("/tmp/test_pipe.ndjson"):
            os.remove("/tmp/test_pipe.ndjson")

    asyncio.run(run())
    print("  [✓] Persistence Pipeline verified")


def test_powerhand_dry_run():
    runner = PowerHandPlaywrightRunner(seed=42069)
    res = asyncio.run(runner.execute_stealth_session("https://bot.sannysoft.com"))
    assert "success" in res["status"]
    print(f"  [✓] PowerHand Runner dry-run verified: {res}")


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 RUNNING COMPREHENSIVE EVASION SUITE INTEGRATION TESTS")
    print("=" * 70)
    test_os_resource_guard()
    test_biomechanical_mouse()
    test_circuit_breaker()
    test_quality_sentinel()
    test_persistence_pipeline()
    test_powerhand_dry_run()
    print("=" * 70)
    print("🏆 ALL INTEGRATION TESTS PASSED!")
    print("=" * 70)
