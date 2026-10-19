from __future__ import annotations

import struct
from typing import Any, Dict, Optional

from veil.core.itch_binary import ItchBinaryParser, ItchParseResult
from veil.core.quant_engine import EDGARPiTAligner


class QuantPiTAndITCHBlueprint:
    def __init__(self, dollar_threshold: float = 50000.0) -> None:
        self.aligner = EDGARPiTAligner()
        self.parser = ItchBinaryParser(dollar_threshold=dollar_threshold)

    def align_financial_filing(
        self,
        ticker_or_symbol: str = "AAPL",
        cik: str = "0000320193",
        period_end_ts: Optional[int] = None,
        filing_acceptance_ts: Optional[int] = None,
        metrics: Optional[Dict[str, Any]] = None,
        *,
        symbol: Optional[str] = None,
        period_of_report_epoch: Optional[int] = None,
        sec_dissemination_epoch: Optional[int] = None,
    ) -> Dict[str, Any]:
        sym = symbol or ticker_or_symbol
        p_epoch = period_of_report_epoch if period_of_report_epoch is not None else (period_end_ts or 1700000000)
        s_epoch = sec_dissemination_epoch if sec_dissemination_epoch is not None else (filing_acceptance_ts or 1700003600)
        res = self.aligner.align_filing(sym, cik, p_epoch, s_epoch, metrics or {})
        res["event_timestamp"] = int(p_epoch)
        return res

    def build_test_itch_add_order(
        self,
        stock: str = "AAPL    ",
        order_ref: int = 101,
        shares: int = 100,
        price_dollars: float = 180.0,
        buy_sell: str = "B",
    ) -> bytes:
        ts_930 = 34_200 * 1_000_000_000
        prefix = struct.pack(">HH", 1, 2) + ts_930.to_bytes(6, "big")
        stock_bytes = stock.encode("ascii")[:8].ljust(8, b" ")
        side_byte = (buy_sell or "B")[0].encode("ascii")
        price_int = int(round(price_dollars * 10000))
        msg_a = (
            b"A"
            + prefix
            + struct.pack(">Q", int(order_ref))
            + side_byte
            + struct.pack(">I", int(shares))
            + stock_bytes
            + struct.pack(">I", price_int)
        )
        return struct.pack(">H", len(msg_a)) + msg_a

    def parse_itch_messages(self, raw_bytes: bytes) -> ItchParseResult:
        return self.parser.parse_stream(raw_bytes)
