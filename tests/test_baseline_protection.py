"""Baseline protection tests for the protected personal baseline
(``behavioral_evasion_ten_patches_hardened_v15.py``).

Provenance: created during the 2026-08-31 V23 port audit. There was NO
pre-existing test suite on disk (baseline count: 0 tests). These tests protect
the existing working capabilities referenced by the audit:

  * ``ITCHParserLOBReconstructor``  -- order lifecycle + dollar-bar generation
  * ``EDGARPiTAligner``             -- dual-timestamp contract, look-ahead rejection
  * ``QuantDataContractSentinel``   -- mandatory event/knowledge timestamps
  * ``PITQuantEngine``              -- as-of filtering (pandas + native fallback)
  * ``FridaNativeHookEngine``       -- honest degradation when Frida is absent

Rules enforced by this suite:
  REAL RESULT -> return it; REAL FAILURE -> raise/report it;
  UNIMPLEMENTED -> quarantine it; NEVER -> fabricate successful output.

Nothing here rewrites or replaces baseline components; the baseline modules are
loaded read-only via ``importlib`` (their filenames are not import identifiers).
"""
import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import BaseModel

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
def v15():
    return _load_module("protected_baseline_v15", V15_PATH)


ISIN = "US0378331005"


class MinimalQuote(BaseModel):
    ticker: str
    price: float
    event_timestamp: float
    knowledge_timestamp: float


# --------------------------------------------------------------- ITCH / LOB
def test_itch_add_orders_build_sorted_book(v15):
    rec = v15.ITCHParserLOBReconstructor()
    rec.parse_itch_message("A", {"isin": ISIN, "price": 185.50, "shares": 100, "order_id": "O1", "side": "B"})
    rec.parse_itch_message("A", {"isin": ISIN, "price": 185.60, "shares": 150, "order_id": "O2", "side": "B"})
    rec.parse_itch_message("A", {"isin": ISIN, "price": 185.80, "shares": 200, "order_id": "O3", "side": "S"})
    rec.parse_itch_message("A", {"isin": ISIN, "price": 185.70, "shares": 120, "order_id": "O4", "side": "S"})
    snap = rec.get_order_book_snapshot(ISIN, depth=5)
    assert [o["price"] for o in snap["bids"]] == [185.60, 185.50]  # best (highest) first
    assert [o["price"] for o in snap["asks"]] == [185.70, 185.80]  # best (lowest) first


def test_itch_execute_reduces_order_shares(v15):
    rec = v15.ITCHParserLOBReconstructor()
    rec.parse_itch_message("A", {"isin": ISIN, "price": 185.50, "shares": 100, "order_id": "O1", "side": "B"})
    rec.parse_itch_message("E", {"isin": ISIN, "order_id": "O1", "shares": 40})
    assert rec.get_order_book_snapshot(ISIN)["bids"][0]["shares"] == 60


def test_itch_cancel_removes_order(v15):
    rec = v15.ITCHParserLOBReconstructor()
    rec.parse_itch_message("A", {"isin": ISIN, "price": 185.50, "shares": 100, "order_id": "O1", "side": "B"})
    rec.parse_itch_message("C", {"isin": ISIN, "order_id": "O1"})
    assert rec.get_order_book_snapshot(ISIN)["bids"] == []


def test_itch_unknown_isin_snapshot_is_empty(v15):
    rec = v15.ITCHParserLOBReconstructor()
    assert rec.get_order_book_snapshot("US0000000000") == {"bids": [], "asks": []}


def test_dollar_bars_aggregate_ohlcv_on_threshold_cross(v15):
    rec = v15.ITCHParserLOBReconstructor()
    trades = [
        {"price": 185.50, "shares": 200},  # $37,100.00
        {"price": 185.55, "shares": 150},  # cumulative $64,932.50 -> bar closes
        {"price": 185.60, "shares": 300},  # cumulative $55,680.00 -> second bar closes
    ]
    bars = rec.generate_dollar_bars(trades, dollar_threshold=50_000.0)
    assert len(bars) == 2
    first = bars[0]
    assert first["open"] == pytest.approx(185.50)
    assert first["high"] == pytest.approx(185.55)
    assert first["low"] == pytest.approx(185.50)
    assert first["close"] == pytest.approx(185.55)
    assert first["volume"] == pytest.approx(350.0)
    assert first["dollar_value"] == pytest.approx(64_932.50)
    assert bars[1]["volume"] == pytest.approx(300.0)
    assert bars[1]["dollar_value"] == pytest.approx(55_680.00)


def test_dollar_bars_below_threshold_emit_no_bar(v15):
    rec = v15.ITCHParserLOBReconstructor()
    trades = [{"price": 10.0, "shares": 1}, {"price": 10.5, "shares": 2}]
    assert rec.generate_dollar_bars(trades, dollar_threshold=50_000.0) == []


# ------------------------------------------------------------------- PIT
def test_edgar_pit_aligner_maps_dual_timestamps(v15):
    aligner = v15.EDGARPiTAligner()
    filing = {
        "cik": "0000320193",
        "period_of_report_epoch": 1_787_630_000,
        "sec_dissemination_epoch": 1_787_630_500,
    }
    aligned = aligner.align_filing_metadata(dict(filing))
    assert aligned["event_timestamp"] == 1_787_630_000
    assert aligned["knowledge_timestamp"] == 1_787_630_500


def test_edgar_pit_aligner_raises_on_temporal_breach(v15):
    aligner = v15.EDGARPiTAligner()
    bad = {
        "cik": "0000320193",
        "period_of_report_epoch": 1_787_630_500,
        "sec_dissemination_epoch": 1_787_630_000,  # dissemination before the period: look-ahead
    }
    with pytest.raises(ValueError):
        aligner.align_filing_metadata(dict(bad))


def test_sentinel_rejects_records_without_dual_timestamps(v15):
    sentinel = v15.QuantDataContractSentinel()
    with pytest.raises(ValueError):
        sentinel.validate_data_contract({"ticker": "AAPL", "price": 182.5}, MinimalQuote)


def test_sentinel_accepts_contract_compliant_record(v15):
    sentinel = v15.QuantDataContractSentinel()
    record = {
        "ticker": "AAPL",
        "price": 182.5,
        "event_timestamp": 1000.0,
        "knowledge_timestamp": 1001.0,
    }
    assert sentinel.validate_data_contract(record, MinimalQuote) is True


PIT_EVENTS = [
    {"ticker": "AAPL", "event_time": "2026-08-25 03:00:00",
     "knowledge_time": "2026-08-25 03:05:00", "metric_value": 182.5},
    {"ticker": "AAPL", "event_time": "2026-08-25 03:30:00",
     "knowledge_time": "2026-08-25 04:05:00", "metric_value": 184.2},  # look-ahead row
    {"ticker": "MSFT", "event_time": "2026-08-25 03:10:00",
     "knowledge_time": "2026-08-25 03:15:00", "metric_value": 415.6},
]


def test_pit_quant_engine_excludes_look_ahead_rows_pandas_path(v15):
    feed = v15.PITQuantEngine().generate_quant_ready_feed(
        [dict(e) for e in PIT_EVENTS], "2026-08-25 03:50:00"
    )
    assert set(feed["ticker"]) == {"AAPL", "MSFT"}  # pandas path -> DataFrame
    aapl = feed[feed["ticker"] == "AAPL"].iloc[0]
    assert float(aapl["metric_value"]) == 182.5  # 04:05 knowledge row excluded by as-of cutoff


def test_pit_quant_engine_native_fallback_no_pandas(v15, monkeypatch):
    monkeypatch.setitem(sys.modules, "pandas", None)  # forces ImportError inside the method
    feed = v15.PITQuantEngine().generate_quant_ready_feed(
        [dict(e) for e in PIT_EVENTS], "2026-08-25 03:50:00"
    )
    assert sorted(ev["metric_value"] for ev in feed) == [182.5, 415.6]  # 184.2 excluded


# ----------------------------------------------------------------- FRIDA
def test_frida_engine_degrades_honestly_when_frida_absent(v15):
    """Without the frida provider installed, hooking must fail honestly
    (return False) and must never report a fake successful hook."""
    if importlib.util.find_spec("frida") is not None:
        pytest.skip("frida installed on this host; absent-provider path not exercised")
    engine = v15.FridaNativeHookEngine(target_process="com.example.audit")
    result = engine.spawn_and_hook(lambda message, data: None)
    assert result is False  # REAL FAILURE -> reported, never a fake success
