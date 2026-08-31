"""Phase 3 regression tests: ITCH-5.0 binary subset parser (itch_binary.py).

Golden fixtures are built with explicitly documented field values (each byte
sequence's length is asserted against the spec-verified message lengths).
Message layouts were verified against the official NASDAQ TotalView-ITCH 5.0
specification tables (see itch_binary.py module docstring for provenance).

Honest scope: this suite covers Add Order (A), Order Executed (E), Order
Cancel (X), Order Delete (D), Order Replace (U) and Trade (P) ONLY.
"""
import struct
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import itch_binary  # noqa: E402
from itch_binary import (  # noqa: E402
    EXPECTED_LENGTHS,
    ItchBinaryParser,
    ItchInvalidFieldError,
    ItchLifecycleError,
    ItchUnknownTypeError,
)

LOCATE = 1
TRACKING = 2
TS_930 = 34_200 * 1_000_000_000  # 09:30:00 in nanoseconds since midnight


def _prefix(ts: int = TS_930, locate: int = LOCATE, tracking: int = TRACKING) -> bytes:
    return struct.pack(">HH", locate, tracking) + ts.to_bytes(6, "big")


def _frame(msg: bytes) -> bytes:
    """Official framing: 2-byte big-endian length prefix + message body."""
    return struct.pack(">H", len(msg)) + msg


def _add(ref: int = 1001, side: bytes = b"B", shares: int = 100,
         stock: bytes = b"AAPL    ", price_raw: int = 1_855_000,
         ts: int = TS_930) -> bytes:
    """Add Order 'A' - 36 bytes (verified layout)."""
    return (b"A" + _prefix(ts=ts) + struct.pack(">Q", ref) + side
            + struct.pack(">I", shares) + stock + struct.pack(">I", price_raw))


def _execute(ref: int = 1001, executed: int = 40, match: int = 9001,
             ts: int = TS_930) -> bytes:
    """Order Executed 'E' - 31 bytes (verified layout)."""
    return (b"E" + _prefix(ts=ts) + struct.pack(">Q", ref)
            + struct.pack(">I", executed) + struct.pack(">Q", match))


def _cancel(ref: int = 1001, cancelled: int = 25, ts: int = TS_930) -> bytes:
    """Order Cancel 'X' - 23 bytes (verified layout)."""
    return b"X" + _prefix(ts=ts) + struct.pack(">Q", ref) + struct.pack(">I", cancelled)


def _delete(ref: int = 1001, ts: int = TS_930) -> bytes:
    """Order Delete 'D' - 19 bytes (verified layout)."""
    return b"D" + _prefix(ts=ts) + struct.pack(">Q", ref)


def _replace(orig: int = 1001, new: int = 1002, shares: int = 150,
             price_raw: int = 1_860_000, ts: int = TS_930) -> bytes:
    """Order Replace 'U' - 35 bytes (verified layout)."""
    return (b"U" + _prefix(ts=ts) + struct.pack(">Q", orig)
            + struct.pack(">Q", new) + struct.pack(">I", shares)
            + struct.pack(">I", price_raw))


def _trade(ref: int = 2001, side: bytes = b"S", shares: int = 300,
           stock: bytes = b"MSFT    ", price_raw: int = 4_156_000,
           match: int = 9002, ts: int = TS_930) -> bytes:
    """Trade (Non-Cross) 'P' - 44 bytes (verified layout)."""
    return (b"P" + _prefix(ts=ts) + struct.pack(">Q", ref) + side
            + struct.pack(">I", shares) + stock + struct.pack(">I", price_raw)
            + struct.pack(">Q", match))


# Hand-written golden Add Order fixture (byte-level reference, ts=0):
GOLDEN_ADD_ORDER = bytes.fromhex(
    "41"                # message type 'A' (Add Order - No MPID Attribution)
    "0001"              # Stock Locate = 1          (offset 1, 2 bytes, BE)
    "0002"              # Tracking Number = 2       (offset 3, 2 bytes, BE)
    "000000000000"      # Timestamp = 0 ns          (offset 5, 6 bytes, BE)
    "0000000000000001"  # Order Reference = 1       (offset 11, 8 bytes, BE)
    "42"                # Buy/Sell Indicator = 'B'  (offset 19, 1 byte)
    "00000064"          # Shares = 100              (offset 20, 4 bytes, BE)
    "4141504c20202020"  # Stock = 'AAPL    '        (offset 24, 8 bytes alpha)
    "001c4e18"          # Price = 1855000 -> 185.5000 (offset 32, 4 bytes, BE)
)


def test_golden_add_order_decodes_exactly():
    assert len(GOLDEN_ADD_ORDER) == EXPECTED_LENGTHS["A"] == 36
    parser = ItchBinaryParser()
    result = parser.parse_stream(_frame(GOLDEN_ADD_ORDER))
    assert result.errors == []
    assert len(result.messages) == 1
    msg = result.messages[0]
    assert msg["type"] == "A"
    assert msg["stock_locate"] == 1
    assert msg["tracking_number"] == 2
    assert msg["timestamp_ns"] == 0
    assert msg["order_ref"] == 1
    assert msg["buy_sell_indicator"] == "B"
    assert msg["shares"] == 100
    assert msg["stock"] == "AAPL"
    assert msg["price"] == pytest.approx(185.50)
    assert msg["price_raw"] == 1_855_000


def test_all_implemented_message_lengths_match_spec():
    assert EXPECTED_LENGTHS == {"A": 36, "E": 31, "X": 23, "D": 19, "U": 35, "P": 44}
    builders = [_add(), _execute(), _cancel(), _delete(), _replace(), _trade()]
    for msg in builders:
        assert len(msg) == EXPECTED_LENGTHS[chr(msg[0])]


def test_common_prefix_fields_decode_from_every_type():
    # Cancel/Delete/Replace require prior book state; each type gets a fresh
    # parser so lifecycle state is deterministic per message type.
    for msg in [_add(), _cancel(), _delete(), _replace(), _trade()]:
        parser = ItchBinaryParser()
        if chr(msg[0]) in ("X", "D", "U"):
            parser.parse_message(_add(ref=1001))
        decoded = parser.parse_message(msg)
        assert decoded["stock_locate"] == LOCATE
        assert decoded["tracking_number"] == TRACKING
        assert decoded["timestamp_ns"] == TS_930


def test_add_execute_lifecycle_and_snapshot():
    parser = ItchBinaryParser()
    result = parser.parse_stream(
        _frame(_add(ref=1001, side=b"B", price_raw=1_855_000))
        + _frame(_add(ref=1002, side=b"S", price_raw=1_860_000))
        + _frame(_execute(ref=1001, executed=40))
    )
    assert result.errors == []
    assert len(result.messages) == 3
    snap = result.book_snapshot
    assert snap["bids"][0]["order_ref"] == 1001
    assert snap["bids"][0]["shares"] == 60
    assert snap["bids"][0]["price"] == pytest.approx(185.50)
    assert snap["asks"][0]["order_ref"] == 1002
    assert len(result.trades) == 1
    assert result.trades[0]["kind"] == "execution"
    assert result.trades[0]["shares"] == 40
    assert result.trades[0]["match_number"] == 9001
    # Fully executing the remainder removes the order deterministically:
    parser.parse_stream(_frame(_execute(ref=1001, executed=60, match=9003)))
    assert all(o["order_ref"] != 1001 for o in parser.snapshot()["bids"])


def test_cancel_then_delete_removes_order():
    parser = ItchBinaryParser()
    result = parser.parse_stream(
        _frame(_add(ref=1001, shares=100)) + _frame(_cancel(ref=1001, cancelled=25))
    )
    assert result.errors == []
    assert result.book_snapshot["bids"][0]["shares"] == 75
    parser.parse_message(_delete(ref=1001))
    assert parser.snapshot()["bids"] == []


def test_replace_swaps_order_reference_price_and_size():
    parser = ItchBinaryParser()
    result = parser.parse_stream(
        _frame(_add(ref=1001, side=b"B", price_raw=1_855_000))
        + _frame(_replace(orig=1001, new=1002, shares=150, price_raw=1_860_000))
    )
    assert result.errors == []
    replaced = result.messages[-1]
    assert replaced["type"] == "U"
    assert replaced["original_order_ref"] == 1001
    assert replaced["new_order_ref"] == 1002
    assert replaced["shares"] == 150
    assert replaced["price"] == pytest.approx(186.00)
    snap = result.book_snapshot
    assert [o["order_ref"] for o in snap["bids"]] == [1002]
    assert snap["bids"][0]["shares"] == 150
    assert snap["bids"][0]["price"] == pytest.approx(186.00)


def test_trade_message_is_extracted_without_book_impact():
    parser = ItchBinaryParser()
    result = parser.parse_stream(
        _frame(_add(ref=1001, side=b"B", shares=100)) + _frame(_trade())
    )
    assert result.errors == []
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade["kind"] == "trade"
    assert trade["price"] == pytest.approx(415.60)
    assert trade["shares"] == 300
    assert trade["match_number"] == 9002
    assert trade["stock"] == "MSFT"
    # A 'P' trade never mutates the resting book:
    assert [o["order_ref"] for o in result.book_snapshot["bids"]] == [1001]


def test_dollar_bars_use_only_executed_trades_not_resting_notional():
    parser = ItchBinaryParser(dollar_threshold=50_000.0)
    # A resting bid worth $10,000,000 must NOT trigger any dollar bar:
    result = parser.parse_stream(
        _frame(_add(ref=1001, shares=1_000_000, price_raw=100_000))
    )
    assert result.errors == []
    assert result.dollar_bars == []
    # Actual trades cross the $50,000 threshold: 30,000 + 25,000 = 55,000
    result = parser.parse_stream(
        _frame(_trade(ref=3001, shares=300, price_raw=1_000_000, match=9101))
        + _frame(_trade(ref=3002, shares=250, price_raw=1_000_000, match=9102))
    )
    assert result.errors == []
    assert len(result.dollar_bars) == 1
    bar = result.dollar_bars[0]
    assert bar["open"] == pytest.approx(100.00)
    assert bar["high"] == pytest.approx(100.00)
    assert bar["low"] == pytest.approx(100.00)
    assert bar["close"] == pytest.approx(100.00)
    assert bar["volume"] == 550
    assert bar["dollar_value"] == pytest.approx(55_000.0)


# ------------------------------------------------------- negative scenarios
def test_unknown_message_type_is_reported_never_accepted():
    parser = ItchBinaryParser()
    garbage = b"Z" + b"\x00" * 9  # 'Z' is NOT in the implemented subset
    result = parser.parse_stream(_frame(garbage))
    assert result.messages == []
    assert len(result.errors) == 1
    err = result.errors[0]
    assert err["kind"] == "ItchUnknownTypeError"
    assert err["message_type"] == "Z"
    assert "outside the implemented" in err["detail"]


def test_truncated_message_body_is_reported():
    parser = ItchBinaryParser()
    cut = _frame(_add())[:-5]  # declared 36 bytes, only 31 present
    result = parser.parse_stream(cut)
    assert result.messages == []
    assert result.errors[0]["kind"] == "truncated"
    assert "exceeds remaining" in result.errors[0]["detail"]


def test_incomplete_length_prefix_is_reported():
    parser = ItchBinaryParser()
    result = parser.parse_stream(b"\x00")  # 1 byte: no full 2-byte prefix
    assert result.messages == []
    assert result.errors[0]["kind"] == "truncated"
    assert "length prefix" in result.errors[0]["detail"]


def test_invalid_message_length_is_reported():
    parser = ItchBinaryParser()
    bad = b"A" + b"\x00" * 9  # type 'A' but only 10 bytes (spec: 36)
    result = parser.parse_stream(_frame(bad))
    assert result.messages == []
    assert result.errors[0]["kind"] == "ItchInvalidFieldError"
    assert "exactly 36 bytes" in result.errors[0]["detail"]


def test_malformed_field_is_reported():
    parser = ItchBinaryParser()
    malformed = _add(side=b"Q")  # 'Q' is not a valid Buy/Sell indicator
    result = parser.parse_stream(_frame(malformed))
    assert result.messages == []
    assert result.errors[0]["kind"] == "ItchInvalidFieldError"
    assert "Buy/Sell" in result.errors[0]["detail"]


def test_execution_against_unknown_order_is_reported():
    parser = ItchBinaryParser()
    result = parser.parse_stream(_frame(_execute(ref=999_999)))
    assert result.messages == []
    assert result.errors[0]["kind"] == "ItchLifecycleError"
    assert "unknown order" in result.errors[0]["detail"]


def test_duplicate_add_and_over_execution_are_reported():
    parser = ItchBinaryParser()
    result = parser.parse_stream(
        _frame(_add(ref=1001, shares=10)) + _frame(_add(ref=1001, shares=10))
    )
    assert len(result.messages) == 1
    assert result.errors[0]["kind"] == "ItchLifecycleError"
    assert "duplicate order reference" in result.errors[0]["detail"]

    over = parser.parse_stream(_frame(_execute(ref=1001, executed=11)))
    assert over.messages == []
    assert over.errors[0]["kind"] == "ItchLifecycleError"
    assert "exceeds remaining" in over.errors[0]["detail"]


def test_stream_recovery_after_error_chunks():
    """A malformed chunk must not corrupt or halt decoding of valid neighbours."""
    parser = ItchBinaryParser()
    result = parser.parse_stream(
        _frame(_add(ref=1001, side=b"B", shares=100))
        + _frame(b"Z" + b"\x00" * 9)          # unknown type -> error
        + _frame(_trade(match=9005))          # valid, must still decode
    )
    assert len(result.messages) == 2
    assert len(result.errors) == 1
    assert result.errors[0]["message_type"] == "Z"
    assert len(result.trades) == 1
    assert result.book_snapshot["bids"][0]["order_ref"] == 1001


def test_parse_message_raises_typed_errors_directly():
    parser = ItchBinaryParser()
    with pytest.raises(ItchUnknownTypeError):
        parser.parse_message(b"Q" + b"\x00" * 42)
    with pytest.raises(ItchLifecycleError):
        parser.parse_message(_delete(ref=424242))
    with pytest.raises(ItchInvalidFieldError):
        parser.parse_message(b"E" + b"\x00" * 10)  # wrong length for 'E'


