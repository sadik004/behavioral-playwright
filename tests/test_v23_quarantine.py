"""Quarantine pins for the three V23 capabilities evaluated in the 2026-08-31
V23 port audit. Verdict for all three: **REJECT** (simulated/theater or strictly
inferior to the protected baseline) -> they are NOT integrated anywhere.

These tests exist to prevent silent fake-success:

  * They pin the fabricated constants exactly as they exist in the supplied V23
    source, so any change to the quarantined code becomes visible and deliberate.
  * They prove the V23 "Frida" interceptor never contacts any Frida API, i.e.
    its "Hooked into libssl.so" status string is fabricated.
  * They prove the fabricated V23 constants never leak into the baseline source.

Pinning a defect is documentation, not endorsement. The quarantine register
lives in ``docs/development/current-checkpoint.md``.
"""
import importlib.util
import struct
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
V15_PATH = BASE / "behavioral_evasion_ten_patches_hardened_v15.py"
V23_PATH = BASE / "bp_biomechanical_engine-v23.py"


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def v23():
    return _load_module("evasion_v23_quarantined", V23_PATH)


V23_FRIDA_HEX = "0a2d0a0b5175616e74475055536563120c4750552d51582d343039301d0000c844"


# ------------------------------------------------- 1. V23 Frida = pure theater
def test_v23_frida_interceptor_returns_only_hardcoded_theater(v23):
    result = v23.FridaMemorySnoopingInterceptor().intercept_tls_payload()
    assert result["memory_address"] == "0x7f83a1b2c3d4"        # invented address
    assert result["decrypted_payload_hex"] == V23_FRIDA_HEX    # invented payload
    assert result["intercepted_bytes"] == 32                   # claims 32 bytes...
    payload = bytes.fromhex(result["decrypted_payload_hex"])
    assert len(payload) == 33                                  # ...but carries 33
    assert len(payload) != result["intercepted_bytes"]         # self-contradictory byte count
    assert result["parsed_protobuf_struct"] == {
        "asset_class": "Equities",
        "ticker": "QuantGPUSec",
        "strike_price": 1599.99,
        "executable": True,
    }


def test_v23_frida_claims_hook_without_touching_frida(v23, monkeypatch):
    calls = []

    class _FridaSentinel:
        def __getattr__(self, item):
            calls.append(item)
            raise AssertionError(f"quarantined V23 code touched Frida API: {item}")

    monkeypatch.setitem(sys.modules, "frida", _FridaSentinel())
    result = v23.FridaMemorySnoopingInterceptor().intercept_tls_payload()
    assert calls == []                              # zero Frida API calls occurred...
    assert "Hooked into" in result["status"]        # ...while claiming a live hook
    assert "BYPASSED" in result["tls_encryption_state"]


def test_v23_frida_payload_is_internally_inconsistent(v23):
    interceptor = v23.FridaMemorySnoopingInterceptor()
    raw = bytes.fromhex(interceptor.intercept_tls_payload()["decrypted_payload_hex"])
    assert raw[0] == 0x0A and raw[1] == 0x2D        # protobuf header declares 45 bytes...
    assert len(raw) - 2 < 45                        # ...but fewer than that remain
    assert b"QuantGPUSec" in raw                    # fabricated ticker embedded in the "intercepted" bytes
    decoded_strike = struct.unpack("<f", raw[-4:])[0]
    claimed = interceptor.intercept_tls_payload()["parsed_protobuf_struct"]["strike_price"]
    assert decoded_strike == 1600.0                 # the payload's own float...
    assert claimed == 1599.99                       # ...contradicts the claimed struct


# --------------------------------------- 2. V23 ITCH = add-only, fake success
def test_v23_itch_parser_is_add_only_and_reports_fake_success(v23):
    parser = v23.NasdaqItchLOBParser()
    parser.process_itch_message("A", {"price": 100.0, "size": 100, "side": "B"})
    result = parser.process_itch_message("D", {"price": 100.0, "size": 100, "order_ref": 1})
    assert "✅" in result["status"]                 # unsupported message type still "succeeds"
    assert result["active_bids_depth"] == 1         # orders can never leave the book (stale book)


def test_v23_dollar_bar_flag_fires_without_any_trade(v23):
    parser = v23.NasdaqItchLOBParser()
    parser.process_itch_message("A", {"price": 1000.0, "size": 6000, "side": "B"})
    result = parser.process_itch_message("A", {"price": 1001.0, "size": 1, "side": "A"})
    assert result["dollar_bar_threshold_triggered"] is True
    # A $6,000,000 resting BID with zero executions "triggered a dollar bar":
    # V23 computes resting-book notional, not traded dollar volume.


# ------------------------------------ 3. V23 PiT = fabricated event timestamp
def test_v23_pit_engine_fabricates_event_time_and_mutates_input(v23):
    import time as _time
    engine = v23.PointInTimeDataContractEngine()
    record = {"ticker": "X", "price": 1.0, "market_event_epoch_ms": 1_234_567}
    result = engine.enforce_pit_contract(record, as_of_date_ms=int(_time.time() * 1000) + 10_000)
    assert result["T_event_ms"] == result["T_knowledge_ms"] - 100  # fixed fabricated delta
    assert result["T_event_ms"] != 1_234_567                       # real event field in record ignored
    assert "T_event" in record                                     # caller's dict mutated in place


# ------------------------------------------------------ leakage / integration
def test_v23_theater_constants_never_leak_into_baseline():
    baseline_source = V15_PATH.read_text(encoding="utf-8")
    for constant in ("0x7f83a1b2c3d4", "QuantGPUSec", "GPU-QX-4090", "0a2d0a0b"):
        assert constant not in baseline_source, (
            f"V23 theater constant leaked into the protected baseline: {constant}"
        )
