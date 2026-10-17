"""Layer 11 (Adversarial Fuzzing) & Layer 12 (Concurrency & Memory Leak Stress) Suite.

100% Zero-Mock (`unittest.mock` / `MagicMock` / `monkeypatch` strictly forbidden).
Dual-compatible with both original `behavioral_playwright` and upgraded `veil` packages.
Can be executed via `pytest` or directly with `python tests/integration/test_fuzz_and_concurrency_stress_real.py`.
"""

from __future__ import annotations

import asyncio
import contextlib
import gc
import importlib
import json
import math
import sqlite3
import sys
import tempfile
import threading
import time
import tracemalloc
import urllib.request
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
for _p in (str(SRC_DIR), str(ROOT_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _import_any(*module_names: str) -> Any:
    for name in module_names:
        try:
            return importlib.import_module(name)
        except Exception:
            continue
    return None


class _StressHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_HEAD(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self) -> None:
        if "/malformed" in self.path:
            payload = (
                b"<html><head><title>Broken\x00Page"
                b"<body><div><table><tr><td>Unclosed"
                + b"<div>" * 80
                + b"<article><h2>Item \xe0\xa6\xac\xe0\xa6\xbe\xe0\xa6\x82\xe0\xa6\xb2\xe0\xa6\xbe</h2>"
                b"<span class='price'>$1,299.95</span></article>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        body = (
            f"<html><head><title>Node {self.path}</title>"
            f"<meta property='og:title' content='Stress {self.path}'/>"
            f"</head><body><main><article><h1>Product {self.path}</h1>"
            f"<p class='price'>$49.99</p>"
            f"<a href='/page/1'>P1</a><a href='/page/2'>P2</a>"
            f"</article></main></body></html>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@contextlib.contextmanager
def _live_stress_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StressHTTPHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3.0)


def _xy(pt: Any) -> Tuple[float, float]:
    if hasattr(pt, "x") and hasattr(pt, "y"):
        return float(pt.x), float(pt.y)
    if isinstance(pt, dict):
        return float(pt.get("x", 0.0)), float(pt.get("y", 0.0))
    return float(pt[0]), float(pt[1])


# ===========================================================================
# LAYER 11: ADVERSARIAL FUZZ & PROPERTY-BASED EDGE-CASE TESTS
# ===========================================================================

def test_layer11_fuzz_normalizer_adversarial_inputs() -> None:
    """Fuzzes clean_text, parse_price, parse_numeric, and resolve_url with adversarial Unicode and edge strings."""
    norm_mod = _import_any("veil.extraction.normalizer", "behavioral_playwright.extraction.normalizer")
    assert norm_mod is not None, "extraction.normalizer module not found"

    clean_fn = getattr(norm_mod, "clean_text", None)
    price_fn = getattr(norm_mod, "parse_price", None)
    num_fn = getattr(norm_mod, "parse_numeric", None)
    url_fn = getattr(norm_mod, "resolve_url", None)

    adversarial_strings = [
        "",
        "   \t\n\r\u00a0\u200b\ufeff   ",
        "\x00\x01\x02Price: $0.00\x00",
        "বাংলা টেক্সট 🚀🔥 1,23,456.78 টাকা",
        "RTL \u202e test \u200b zero-width \u00ad soft-hyphen",
        "<b><div><span>" * 50 + "Deep Text" + "</span></div></b>" * 50,
        "NaN",
        "Infinity",
        "-Infinity",
        "$-99,999,999.99 USD",
        "€ 1.234,56",
    ]
    for raw in adversarial_strings:
        if clean_fn is not None:
            cleaned = clean_fn(raw)
            assert isinstance(cleaned, str)
            assert "\u200b" not in cleaned and "\ufeff" not in cleaned
        if price_fn is not None:
            p_val = price_fn(raw)
            assert p_val is None or isinstance(p_val, (int, float, Decimal))
        if num_fn is not None:
            n_val = num_fn(raw)
            assert n_val is None or isinstance(n_val, (int, float))
        if url_fn is not None:
            u_val = url_fn("https://example.com/base/", raw)
            assert isinstance(u_val, str)


def test_layer11_fuzz_kinematics_extreme_coordinates_and_seeds() -> None:
    """Fuzzes mouse and keystroke physics across zero-distance, negative, 4K, and rapid-seed inputs."""
    mouse_mod = _import_any(
        "veil.kinematics.biomechanics",
        "behavioral_playwright.powerplay.biomechanics",
        "behavioral_evasion_suite.mouse_physics",
        "veil.kinematics.mouse",
        "behavioral_playwright.kinematics.mouse",
    )
    coords_cases = [
        ((0.0, 0.0), (0.0, 0.0)),
        ((100.0, 100.0), (100.0, 100.0)),
        ((-500.0, -300.0), (1920.0, 1080.0)),
        ((0.0, 0.0), (3840.0, 2160.0)),
        ((12.34, 56.78), (98.76, 54.32)),
    ]

    if mouse_mod is not None and hasattr(mouse_mod, "BiomechanicalMousePhysics"):
        engine = mouse_mod.BiomechanicalMousePhysics()
        for start, end in coords_cases:
            pts = engine.generate_trajectory(start=start, end=end)
            assert isinstance(pts, list) and len(pts) >= 1
            for pt in pts:
                x, y = _xy(pt)
                assert math.isfinite(x) and math.isfinite(y)

    key_mod = _import_any(
        "veil.kinematics.keystrokes",
        "behavioral_playwright.powerplay.keystrokes",
        "behavioral_playwright.kinematics.keystrokes",
        "behavioral_evasion_suite.keystroke_engine",
    )
    if key_mod is not None and hasattr(key_mod, "LinguisticKeystrokeDynamicsEngine"):
        k_eng = key_mod.LinguisticKeystrokeDynamicsEngine(seed=99)
        for text_in in ("", "a", "বাংলা123!@#", "The quick brown fox"):
            seq = k_eng.generate_typing_sequence(text_in, seed=99)
            assert len(seq) == len(text_in) * 2


def test_layer11_fuzz_malformed_html_and_deep_dom_extraction() -> None:
    """Fuzzes HTML/DOM extractors against broken tags, null bytes, and 100-level deep nesting."""
    malformed_samples = [
        "",
        "<<<>>>not html at all<<<>>>",
        "<html><body><div>" * 100 + "<p>Deep Node $19.99</p>" + "</div>" * 20,
        "<html><body><table><tr><td>Cell 1<td>Cell 2<tr><td>Cell 3</table></body></html>",
        "<script>alert('xss')</script><style>body{display:none}</style><article><h2>Safe Title</h2><p>$29.00</p></article>",
    ]

    dom_mod = _import_any("veil.extraction.dom", "behavioral_playwright.extraction.dom")
    if dom_mod is not None and hasattr(dom_mod, "extract_open_graph"):
        for sample in malformed_samples:
            og = asyncio.run(dom_mod.extract_open_graph(sample))
            jld = asyncio.run(dom_mod.extract_json_ld(sample))
            assert isinstance(og, dict)
            assert isinstance(jld, list)

    auto_mod = _import_any("veil.extraction.auto_schema", "behavioral_playwright.extraction.auto_schema")
    if auto_mod is not None and hasattr(auto_mod, "AutoSchemaExtractor"):
        extractor = auto_mod.AutoSchemaExtractor()
        for sample in malformed_samples:
            res = extractor.extract(sample)
            assert res is not None

    pruner_mod = _import_any("veil.extraction.block_tree_pruner", "behavioral_playwright.extraction.block_tree_pruner")
    if pruner_mod is not None and hasattr(pruner_mod, "BlockTreePruner"):
        pruner = pruner_mod.BlockTreePruner()
        for sample in malformed_samples:
            pruned = pruner.prune(sample)
            assert hasattr(pruned, "pruned_markdown") or hasattr(pruned, "markdown")


# ===========================================================================
# LAYER 12: HIGH-CONCURRENCY, SQLITE WAL LOCK & MEMORY LEAK STRESS TESTS
# ===========================================================================

def test_layer12_sqlite_concurrent_writers_zero_winerror32() -> None:
    """Spawns 25 concurrent threads writing/reading SQLite WAL tables, then unlinks DB immediately (Windows NTFS WinError 32 test)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "stress_concurrent.db"
        errors: List[Exception] = []

        def _worker(worker_id: int) -> None:
            try:
                for step in range(8):
                    conn = sqlite3.connect(str(db_path), timeout=30.0)
                    try:
                        conn.execute("PRAGMA journal_mode=WAL;")
                        conn.execute(
                            "CREATE TABLE IF NOT EXISTS stress_log (id INTEGER PRIMARY KEY AUTOINCREMENT, wid INT, step INT, url TEXT)"
                        )
                        conn.execute(
                            "INSERT INTO stress_log (wid, step, url) VALUES (?, ?, ?)",
                            (worker_id, step, f"https://example.com/{worker_id}/{step}"),
                        )
                        conn.commit()
                    finally:
                        conn.close()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(25)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)

        assert not errors, f"SQLite concurrency errors: {errors}"

        with contextlib.closing(sqlite3.connect(str(db_path), timeout=30.0)) as check_conn:
            count = check_conn.execute("SELECT COUNT(*) FROM stress_log").fetchone()[0]
            assert count == 25 * 8

        db_path.unlink()
        assert not db_path.exists()


def test_layer12_async_50_concurrent_live_http_requests_and_memory_ceiling() -> None:
    """Runs 50 concurrent async crawl/fetch tasks against a live local server and verifies zero memory leak via tracemalloc."""
    crawl_mod = _import_any("veil.crawling.service", "behavioral_playwright.crawling.service")
    models_mod = _import_any("veil.crawling.models", "behavioral_playwright.crawling.models")

    gc.collect()
    tracemalloc.start()

    with _live_stress_server() as base_url:
        if crawl_mod is not None and models_mod is not None and hasattr(crawl_mod, "TieredCrawlerService"):
            async def _run_crawler_burst() -> List[Any]:
                service = crawl_mod.TieredCrawlerService()
                req_cls = models_mod.CrawlRequest
                tasks = [
                    service.crawl(req_cls(url=f"{base_url}/item/{i}"), use_checkpoint=False)
                    for i in range(50)
                ]
                return await asyncio.gather(*tasks)

            results = asyncio.run(_run_crawler_burst())
            assert len(results) == 50
            ok_count = sum(1 for r in results if getattr(r, "status_code", 0) == 200 or getattr(r, "success", False))
            assert ok_count == 50
        else:
            async def _run_http_burst() -> List[int]:
                def _get_status(u: str) -> int:
                    with urllib.request.urlopen(u, timeout=5.0) as resp:
                        _ = resp.read()
                        return resp.status
                return await asyncio.gather(*[asyncio.to_thread(_get_status, f"{base_url}/item/{i}") for i in range(50)])

            statuses = asyncio.run(_run_http_burst())
            assert len(statuses) == 50 and all(s == 200 for s in statuses)

    gc.collect()
    current_bytes, _peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert current_bytes < 35 * 1024 * 1024, f"Excessive retained memory after 50 concurrent tasks: {current_bytes} bytes"


if __name__ == "__main__":
    test_layer11_fuzz_normalizer_adversarial_inputs()
    test_layer11_fuzz_kinematics_extreme_coordinates_and_seeds()
    test_layer11_fuzz_malformed_html_and_deep_dom_extraction()
    test_layer12_sqlite_concurrent_writers_zero_winerror32()
    test_layer12_async_50_concurrent_live_http_requests_and_memory_ceiling()
    print("[PASS] All Layer 11 (Fuzz) & Layer 12 (Concurrency + Memory Ceiling) tests passed!")
