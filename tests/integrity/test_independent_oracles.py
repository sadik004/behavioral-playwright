"""First-Principles Independent Oracle Test Suite (`tests/integrity/test_independent_oracles.py`)."""
from __future__ import annotations
import math, struct
from collections import Counter

def test_shannon_entropy_oracle() -> None:
    text = "ABCD" * 25
    n = len(text)
    counts = Counter(text)
    h = -sum((c / n) * math.log2(c / n) for c in counts.values())
    assert abs(h - 2.0) < 1e-9

def test_itch50_add_order_wire_oracle() -> None:
    pkt = struct.pack(">cHH6sQcI8sI", b"A", 1, 2, (1000).to_bytes(6, "big"), 999, b"B", 100, b"AAPL    ", 1502500)
    assert len(pkt) == 36
    msg_type, locate, tracking, ts_bytes, order_ref, side, shares, stock, price4 = struct.unpack(">cHH6sQcI8sI", pkt)
    assert msg_type == b"A"
    assert stock.decode("ascii").rstrip() == "AAPL"
    assert price4 / 10000.0 == 150.25
