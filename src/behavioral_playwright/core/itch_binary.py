"""NASDAQ TotalView-ITCH 5.0 binary subset parser (honesty-hardened).

Created in Phase 3 of the V23 reconciliation. This module is intentionally
ISOLATED from the legacy V15 ``ITCHParserLOBReconstructor`` (which remains
untouched and authoritative for dict-payload simulation).

HONEST SCOPE - this parser implements ONLY the following message subset,
whose binary layouts were verified against the official NASDAQ TotalView
ITCH 5.0 specification tables:

    'A'  Add Order - No MPID Attribution   36 bytes
    'E'  Order Executed                    31 bytes
    'X'  Order Cancel                      23 bytes
    'D'  Order Delete                      19 bytes
    'U'  Order Replace                     35 bytes
    'P'  Trade Message (Non-Cross)         44 bytes

This is NOT a complete ITCH-5.0 implementation. System Event (S), Stock
Directory (R), Trading Action (H), Reg SHO (Y), Market Participant Position
(L), MWCB (V/W), IPO Quoting (K), LULD Auction Collar (J), Operational
Halt (h), NOII (I), RPII (N), Cross Trade (Q), Broken Trade (B) and DLCR
(O) messages are NOT parsed: they are reported as errors and never
silently accepted. No field absent from the wire format is fabricated.

Layout authority (verified 2026-08-31):
  * Official spec (PDF):
    https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHspecification.pdf
  * Add Order spec table reproduced field-by-field (offsets 0/1/3/5/11/19/
    20/24/32; Timestamp = "Nanoseconds since midnight"; Stock = 8-byte alpha
    right-padded with spaces): kevingivens.github.io "Parsing ITCH Messages
    in C++".
  * Endianness: "All integer fields in ITCH data feeds are big-endian
    (network byte order)" - shawfdong/itch5parser README.
  * Field sets for E/X/D/U/P verified against the bbalouki/itch parser
    test fixtures (order_reference_number / executed_shares / match_number
    / cancelled_shares / new_order_reference_number / price / stock).
  * Price4 = four implied decimal places (docs.rs `itchy` crate: "Price4
    Opaque type representing a price to four decimal places").
  * Framing: a 2-byte big-endian message length prefix precedes each
    message (its high byte is 0x00 for every ITCH-5.0 message type).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List

__all__ = [
    "ItchProtocolError",
    "ItchTruncatedError",
    "ItchUnknownTypeError",
    "ItchInvalidFieldError",
    "ItchLifecycleError",
    "ItchParseResult",
    "ItchBinaryParser",
    "EXPECTED_LENGTHS",
]


class ItchProtocolError(Exception):
    """Base class for ITCH binary protocol violations."""


class ItchTruncatedError(ItchProtocolError):
    """A message or its framing was cut off mid-stream."""


class ItchUnknownTypeError(ItchProtocolError):
    """Message type character outside the implemented subset."""


class ItchInvalidFieldError(ItchProtocolError):
    """A field violates its wire-format definition (length/encoding/value)."""


class ItchLifecycleError(ItchProtocolError):
    """An order lifecycle transition that cannot be applied deterministically."""


# Exact message lengths in bytes (excluding the 2-byte length prefix), per spec.
EXPECTED_LENGTHS: Dict[str, int] = {
    "A": 36,  # Add Order - No MPID Attribution
    "E": 31,  # Order Executed
    "X": 23,  # Order Cancel
    "D": 19,  # Order Delete
    "U": 35,  # Order Replace
    "P": 44,  # Trade Message (Non-Cross)
}

_PRICE_SCALE = 10_000.0  # Price(4): four implied decimal places
_U16 = struct.Struct(">H")
_U32 = struct.Struct(">I")
_U64 = struct.Struct(">Q")


def _u16(msg: bytes, off: int) -> int:
    return _U16.unpack_from(msg, off)[0]


def _u32(msg: bytes, off: int) -> int:
    return _U32.unpack_from(msg, off)[0]


def _u64(msg: bytes, off: int) -> int:
    return _U64.unpack_from(msg, off)[0]


def _timestamp_ns(msg: bytes) -> int:
    """6-byte big-endian unsigned integer: nanoseconds since midnight (offset 5..11)."""
    return int.from_bytes(msg[5:11], "big")


def _stock(msg: bytes, off: int) -> str:
    """8-byte ASCII alpha, right-padded with spaces (offset off..off+8)."""
    raw = msg[off:off + 8]
    try:
        return raw.decode("ascii").rstrip()
    except UnicodeDecodeError as exc:
        raise ItchInvalidFieldError(
            f"non-ASCII stock symbol bytes {raw!r} at offset {off}"
        ) from exc


def _buy_sell(msg: bytes, off: int) -> str:
    char = chr(msg[off])
    if char not in ("B", "S"):
        raise ItchInvalidFieldError(
            f"invalid Buy/Sell indicator {char!r} at offset {off} (expected 'B' or 'S')"
        )
    return char


def _common_prefix(msg: bytes) -> Dict[str, Any]:
    """Fields shared by every ITCH-5.0 message: locate(1:3), tracking(3:5), ts(5:11)."""
    return {
        "stock_locate": _u16(msg, 1),
        "tracking_number": _u16(msg, 3),
        "timestamp_ns": _timestamp_ns(msg),
    }


@dataclass
class ItchParseResult:
    """Outcome of one ``ItchBinaryParser.parse_stream`` run.

    ``messages`` holds fully decoded wire messages; ``errors`` holds every
    malformed/unknown/unprocessable chunk with an explicit reason - unknown
    message types are NEVER silently accepted. ``book_snapshot`` is the
    deterministic order-book state after the last successfully applied
    lifecycle transition.
    """

    messages: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    dollar_bars: List[Dict[str, Any]] = field(default_factory=list)
    book_snapshot: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)


class ItchBinaryParser:
    """Deterministic order-book builder over the verified ITCH-5.0 subset.

    Unknown message types, length mismatches, malformed fields and invalid
    lifecycle transitions are raised as typed exceptions per message and
    collected as explicit error records by ``parse_stream`` - never swallowed.
    Dollar bars are accumulated ONLY from actual executions ('E') and trades
    ('P'), never from resting-book notional.
    """

    SUPPORTED_TYPES: tuple = tuple(EXPECTED_LENGTHS)

    def __init__(self, dollar_threshold: float = 50_000.0) -> None:
        self.dollar_threshold = float(dollar_threshold)
        self._orders: Dict[int, Dict[str, Any]] = {}
        self.trades: List[Dict[str, Any]] = []
        self.dollar_bars: List[Dict[str, Any]] = []
        self._bar_acc: Dict[str, Any] = {
            "dollar_value": 0.0, "volume": 0, "open": None, "high": None, "low": None,
        }

    # ------------------------------------------------------------------ API
    def parse_stream(self, data: bytes) -> ItchParseResult:
        """Frame and decode a length-prefixed ITCH-5.0 byte stream."""
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes-like")
        buf = bytes(data)
        result = ItchParseResult()
        offset = 0
        index = 0
        n = len(buf)
        while offset < n:
            if n - offset < 2:
                result.errors.append({
                    "index": index, "kind": "truncated",
                    "detail": f"incomplete 2-byte length prefix: {n - offset} byte(s) remain",
                })
                break
            (msg_len,) = _U16.unpack_from(buf, offset)
            if offset + 2 + msg_len > n:
                result.errors.append({
                    "index": index, "kind": "truncated",
                    "detail": (
                        f"declared message length {msg_len} exceeds remaining "
                        f"{n - offset - 2} byte(s)"
                    ),
                })
                break
            raw = buf[offset + 2: offset + 2 + msg_len]
            try:
                message = self.parse_message(raw)
            except ItchProtocolError as exc:
                bad_type = chr(raw[0]) if raw and 32 <= raw[0] < 127 else None
                result.errors.append({
                    "index": index,
                    "kind": type(exc).__name__,
                    "detail": str(exc),
                    "message_type": bad_type,
                })
            else:
                result.messages.append(message)
                if message["type"] == "P":
                    self.trades.append({
                        "kind": "trade",
                        "order_ref": message["order_ref"],
                        "price": message["price"],
                        "shares": message["shares"],
                        "match_number": message["match_number"],
                        "stock": message["stock"],
                        "side": "buy" if message["buy_sell_indicator"] == "B" else "sell",
                    })
                    self._accumulate_bar(message["price"], message["shares"])
            index += 1
            offset += 2 + msg_len
        result.trades = list(self.trades)
        result.dollar_bars = list(self.dollar_bars)
        result.book_snapshot = self.snapshot()
        return result

    def parse_message(self, msg: bytes) -> Dict[str, Any]:
        """Decode and apply a single length-prefixed ITCH-5.0 message body."""
        if not isinstance(msg, (bytes, bytearray)):
            raise ItchInvalidFieldError("message must be bytes-like")
        msg = bytes(msg)
        if not msg:
            raise ItchTruncatedError("zero-length message")
        mtype = chr(msg[0]) if 32 <= msg[0] < 127 else None
        if mtype not in EXPECTED_LENGTHS:
            raise ItchUnknownTypeError(
                f"message type {mtype!r} is outside the implemented ITCH-5.0 subset "
                f"(supported: {', '.join(EXPECTED_LENGTHS)})"
            )
        expected = EXPECTED_LENGTHS[mtype]
        if len(msg) != expected:
            raise ItchInvalidFieldError(
                f"message type {mtype!r} must be exactly {expected} bytes, got {len(msg)}"
            )
        handler = {
            "A": self._parse_add,
            "E": self._parse_execute,
            "X": self._parse_cancel,
            "D": self._parse_delete,
            "U": self._parse_replace,
            "P": self._parse_trade,
        }[mtype]
        return handler(msg)

    def snapshot(self, depth: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Deterministic depth snapshot: bids sorted descending, asks ascending."""
        bids: List[Dict[str, Any]] = []
        asks: List[Dict[str, Any]] = []
        for ref, order in self._orders.items():
            entry = {
                "order_ref": ref,
                "price": order["price_raw"] / _PRICE_SCALE,
                "shares": order["shares"],
                "stock": order["stock"],
            }
            (bids if order["side"] == "buy" else asks).append(entry)
        bids.sort(key=lambda e: (-e["price"], e["order_ref"]))
        asks.sort(key=lambda e: (e["price"], e["order_ref"]))
        return {"bids": bids[:depth], "asks": asks[:depth]}

    # ------------------------------------------------------------- handlers
    def _parse_add(self, msg: bytes) -> Dict[str, Any]:
        ref = _u64(msg, 11)
        side_char = _buy_sell(msg, 19)
        shares = _u32(msg, 20)
        stock = _stock(msg, 24)
        price_raw = _u32(msg, 32)
        if ref in self._orders:
            raise ItchLifecycleError(f"duplicate order reference {ref}")
        self._orders[ref] = {
            "side": "buy" if side_char == "B" else "sell",
            "price_raw": price_raw,
            "shares": shares,
            "stock": stock,
            "stock_locate": _u16(msg, 1),
        }
        message = {
            "type": "A",
            "order_ref": ref,
            "buy_sell_indicator": side_char,
            "shares": shares,
            "stock": stock,
            "price": price_raw / _PRICE_SCALE,
            "price_raw": price_raw,
        }
        message.update(_common_prefix(msg))
        return message

    def _parse_execute(self, msg: bytes) -> Dict[str, Any]:
        ref = _u64(msg, 11)
        executed = _u32(msg, 19)
        match = _u64(msg, 23)
        order = self._orders.get(ref)
        if order is None:
            raise ItchLifecycleError(f"execution references unknown order {ref}")
        if executed > order["shares"]:
            raise ItchLifecycleError(
                f"execution of {executed} shares exceeds remaining "
                f"{order['shares']} on order {ref}"
            )
        price = order["price_raw"] / _PRICE_SCALE
        message = {
            "type": "E",
            "order_ref": ref,
            "executed_shares": executed,
            "match_number": match,
            "stock": order["stock"],
            "price": price,
            "price_raw": order["price_raw"],
        }
        message.update(_common_prefix(msg))
        self.trades.append({
            "kind": "execution",
            "order_ref": ref,
            "price": price,
            "shares": executed,
            "match_number": match,
            "stock": order["stock"],
            "side": order["side"],
        })
        self._accumulate_bar(price, executed)
        order["shares"] -= executed
        if order["shares"] == 0:
            del self._orders[ref]
        return message

    def _parse_cancel(self, msg: bytes) -> Dict[str, Any]:
        ref = _u64(msg, 11)
        cancelled = _u32(msg, 19)
        order = self._orders.get(ref)
        if order is None:
            raise ItchLifecycleError(f"cancel references unknown order {ref}")
        if cancelled > order["shares"]:
            raise ItchLifecycleError(
                f"cancel of {cancelled} shares exceeds remaining "
                f"{order['shares']} on order {ref}"
            )
        message = {"type": "X", "order_ref": ref, "cancelled_shares": cancelled}
        message.update(_common_prefix(msg))
        order["shares"] -= cancelled
        if order["shares"] == 0:
            del self._orders[ref]
        return message

    def _parse_delete(self, msg: bytes) -> Dict[str, Any]:
        ref = _u64(msg, 11)
        if ref not in self._orders:
            raise ItchLifecycleError(f"delete references unknown order {ref}")
        message = {"type": "D", "order_ref": ref}
        message.update(_common_prefix(msg))
        del self._orders[ref]
        return message

    def _parse_replace(self, msg: bytes) -> Dict[str, Any]:
        orig = _u64(msg, 11)
        new = _u64(msg, 19)
        shares = _u32(msg, 27)
        price_raw = _u32(msg, 31)
        order = self._orders.get(orig)
        if order is None:
            raise ItchLifecycleError(f"replace references unknown order {orig}")
        if new in self._orders:
            raise ItchLifecycleError(f"replace produces duplicate order reference {new}")
        self._orders[new] = {**order, "shares": shares, "price_raw": price_raw}
        del self._orders[orig]
        message = {
            "type": "U",
            "original_order_ref": orig,
            "new_order_ref": new,
            "shares": shares,
            "price": price_raw / _PRICE_SCALE,
            "price_raw": price_raw,
            "stock": order["stock"],
            "side": order["side"],
        }
        message.update(_common_prefix(msg))
        return message

    def _parse_trade(self, msg: bytes) -> Dict[str, Any]:
        ref = _u64(msg, 11)
        side_char = _buy_sell(msg, 19)
        shares = _u32(msg, 20)
        stock = _stock(msg, 24)
        price_raw = _u32(msg, 32)
        match = _u64(msg, 36)
        message = {
            "type": "P",
            "order_ref": ref,
            "buy_sell_indicator": side_char,
            "shares": shares,
            "stock": stock,
            "price": price_raw / _PRICE_SCALE,
            "price_raw": price_raw,
            "match_number": match,
        }
        message.update(_common_prefix(msg))
        return message

    # ------------------------------------------------------------ bar logic
    def _accumulate_bar(self, price: float, shares: int) -> None:
        acc = self._bar_acc
        acc["dollar_value"] += price * shares
        acc["volume"] += shares
        if acc["open"] is None:
            acc["open"] = price
        acc["high"] = price if acc["high"] is None else max(acc["high"], price)
        acc["low"] = price if acc["low"] is None else min(acc["low"], price)
        if acc["dollar_value"] >= self.dollar_threshold:
            self.dollar_bars.append({
                "open": acc["open"],
                "high": acc["high"],
                "low": acc["low"],
                "close": price,
                "volume": acc["volume"],
                "dollar_value": acc["dollar_value"],
            })
            self._bar_acc = {
                "dollar_value": 0.0, "volume": 0, "open": None, "high": None, "low": None,
            }
