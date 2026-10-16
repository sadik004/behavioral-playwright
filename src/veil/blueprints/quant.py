"""Quantitative Point-in-Time and ITCH 5.0 Feed Blueprint (`src/veil/blueprints/quant.py`).

Provides institutional quantitative finance capabilities:
- Strict Point-in-Time (PiT) alignment eliminating look-ahead bias
- High-performance binary parsing of NASDAQ TotalView-ITCH 5.0 market feeds
"""

from __future__ import annotations

import struct
from typing import Any, Dict, List, Optional

from veil.core.itch_binary import ItchBinaryParser, ItchParseResult
from veil.core.quant_engine import EDGARPiTAligner


class QuantPiTAndITCHBlueprint:
    """Blueprint for zero-leakage Point-in-Time data alignment and NASDAQ ITCH 5.0 message parsing."""

    def __init__(self) -> None:
        self.pit_aligner = EDGARPiTAligner()
        self.itch_parser = ItchBinaryParser()

    def align_financial_filing(
        self,
        symbol: str,
        cik: str,
        period_of_report_epoch: int,
        sec_dissemination_epoch: int,
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Aligns corporate filing metrics to Point-in-Time timestamp without look-ahead bias."""
        payload = {
            "symbol": symbol,
            "cik": cik,
            "period_of_report_epoch": period_of_report_epoch,
            "sec_dissemination_epoch": sec_dissemination_epoch,
            "metrics": metrics,
        }
        return self.pit_aligner.align_filing_metadata(payload)

    def parse_itch_messages(self, packet_bytes: bytes) -> List[ItchParseResult]:
        """Parses a sequence of 2-byte framed NASDAQ TotalView-ITCH 5.0 binary messages."""
        return self.itch_parser.parse_stream(packet_bytes)

    @staticmethod
    def build_test_itch_add_order(
        stock: str = "AAPL    ",
        order_ref: int = 1001,
        shares: int = 100,
        price_dollars: float = 175.50,
        buy_sell: str = "B",
        timestamp_ns: int = 34200000000000,
    ) -> bytes:
        """Constructs a valid wire-format 2-byte framed ITCH 5.0 'A' (Add Order) message."""
        # Message type 'A', length is 36 bytes (excluding 2-byte framing prefix)
        msg_len = 36
        stock_padded = stock.ljust(8)[:8].encode("ascii")
        price4 = int(round(price_dollars * 10000))
        # Layout: Length (2B), Type (1B), StockLocate (2B), Tracking (2B), Timestamp (6B),
        # OrderRef (8B), BuySell (1B), Shares (4B), Stock (8B), Price (4B)
        ts_high = (timestamp_ns >> 32) & 0xFFFF
        ts_low = timestamp_ns & 0xFFFFFFFF

        body = struct.pack(
            ">cHHHIQcI8sI",
            b"A",
            1,  # Stock Locate
            0,  # Tracking Number
            ts_high,
            ts_low,
            order_ref,
            buy_sell.encode("ascii"),
            shares,
            stock_padded,
            price4,
        )
        return struct.pack(">H", msg_len) + body


__all__ = ["QuantPiTAndITCHBlueprint"]
