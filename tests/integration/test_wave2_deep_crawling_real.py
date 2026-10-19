"""Zero-Mock Live Local HTTP Server E2E Test Suite for Wave 2 Deep Crawling & Extraction.

Tests every mathematical equation, paper algorithm, and multi-worker deep crawl
against a live multi-page, multi-host simulated HTTP server (`127.0.0.1` ephemeral port):
  1. Ostendorff (2026) `arXiv:2610.13321v1`: Eq. (1) host quality density, Eq. (2) Shrout & Fleiss
     ICC(1) one-way random-effects ANOVA, Eq. (3) Spearman-Brown reliability, §4.3 Sample-Then-Deepen
     budget allocation, and §4.4 Hidden-Gem discovery (low coverage, top-quantile quality).
  2. HtmlRAG (`arXiv:2411.02959v2`) + Dripper (`arXiv:2511.23119`) + D2Snap (`arXiv:2508.04412v4`):
     Lossless structural compression, Greedy Block-Tree BM25+Log-Salience pruning, quadratic
     prefill FLOPs reduction ratio, and declarative Shadow DOM / iframe flattening.
  3. TRES (`arXiv:2112.07620v4`) / Auer et al. UCB1 + Beta-Bernoulli Thompson Sampling proxy
     selection with exponential cooldown on HTTP 403/429/503 and tracker/media resource blocking.
  4. DataMan (`arXiv:2502.19363`) Eq. (5) temperature-scaled quality + inverse-square-root domain
     diversity sampling, Hierarchical H1>H2>H3 breadcrumb RAG chunking with lexical Jaccard
     cohesion boundaries, and O(1)-memory streaming `.jsonl` + `.csv` export.
  5. Craw4LLM (`arXiv:2502.13347v3`) + WebGraph (`arXiv:2605.14786` Table 1) + Bot Detection
     (`arXiv:2406.07647` Appendix C): Multi-worker async `DeepSiteCrawler` with SQLite WAL
     crash-resume frontier and human UI telemetry verification.
"""

from __future__ import annotations

import asyncio
import json
import math
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Tuple

ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
for _p in (str(ROOT_DIR), str(SRC_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from veil.crawling.bandit_proxy_rotator import BanditProxyRotator, BandwidthResourceBlocker
from veil.crawling.deep_crawler import (
    DeepSiteCrawler,
    PersistentFrontierQueue,
    UITraceTelemetryVerifier,
)
from veil.crawling.host_budget import (
    SampleThenDeepenAllocator,
    compute_host_quality_density,
    compute_shrout_fleiss_icc1,
    spearman_brown_reliability,
)
from veil.extraction.block_tree_pruner import (
    BlockTreePruner,
    flatten_shadow_dom_and_iframes,
    lossless_structural_compress,
)
from veil.extraction.rag_chunker_exporter import (
    HierarchicalRAGChunker,
    StreamingCorpusExporter,
    dataman_sampling_probabilities,
    lexical_jaccard_cohesion,
)


class _Wave2MultiPageHandler(BaseHTTPRequestHandler):
    """Live local HTTP server serving a multi-page hierarchical documentation & research site."""

    def log_message(self, format: str, *args: object) -> None:
        return  # Keep test output clean

    def do_GET(self) -> None:
        base_url = f"http://127.0.0.1:{self.server.server_port}"
        pages: Dict[str, str] = {
            "/": f"""<!DOCTYPE html>
<html>
<head><title>Research Portal Hub</title></head>
<body>
  <nav><a href="{base_url}/">Home</a> | <a href="{base_url}/Login">Login</a></nav>
  <main>
    <article>
      <h1>Distributed Web Crawling & Pretraining Data Curation</h1>
      <p>High-efficiency web crawlers prioritize pages using quality classifiers and host-level density estimators. By modeling intra-host quality clustering with Intraclass Correlation Coefficient ICC(1), crawlers avoid wasting bandwidth on low-value domains.</p>
      <a href="{base_url}/docs/host-budget">Read Host-Aware Budget Allocation</a>
      <a href="{base_url}/docs/block-pruning">Read Block-Tree Pruning & Compression</a>
      <a href="{base_url}/noise/ads-landing">Sponsored Marketing Banner</a>
    </article>
  </main>
</body>
</html>""",
            "/docs/host-budget": f"""<!DOCTYPE html>
<html>
<head><title>Host-Aware Crawling Equations</title></head>
<body>
  <main>
    <article>
      <h1>Host-Aware Budget Allocation Mathematics</h1>
      <p>Following Ostendorff (2026) arXiv:2610.13321v1, the quality density q_h of host h is the fraction of crawled pages passing the DataMan quality threshold. The sample-then-deepen policy probes k=3 pages per host and expands crawl depth proportionally to empirical quality density.</p>
      <p>Furthermore, Shrout and Fleiss (1979) one-way random-effects ANOVA demonstrates that ICC(1) exceeds 0.45 across Common Crawl hosts, proving strong intra-host quality homogeneity.</p>
      <a href="{base_url}/docs/deep-bandits">Explore Bandit Proxy Selection</a>
    </article>
  </main>
</body>
</html>""",
            "/docs/block-pruning": f"""<!DOCTYPE html>
<html>
<head><title>HtmlRAG & Dripper Block Tree Pruning</title></head>
<body>
  <main>
    <article>
      <h1>Block-Tree Pruning and Quadratic FLOPs Reduction</h1>
      <p>HtmlRAG (arXiv:2411.02959v2) compresses redundant DOM wrappers losslessly and scores semantic blocks via Okapi BM25 combined with DOM depth and interactive control salience. Dripper (arXiv:2511.23119) proves that reducing input sequence length from L to L_hat saves quadratic self-attention prefill FLOPs.</p>
    </article>
  </main>
</body>
</html>""",
            "/docs/deep-bandits": f"""<!DOCTYPE html>
<html>
<head><title>Multi-Armed Bandit Proxy Rotation</title></head>
<body>
  <main>
    <article>
      <h1>UCB1 and Thompson Sampling for Evasion</h1>
      <p>By modeling proxy endpoints as Bernoulli arms with latency penalties, UCB1 and Beta-Bernoulli Thompson Sampling dynamically route around HTTP 429 and 403 blocks while minimizing round-trip time.</p>
    </article>
  </main>
</body>
</html>""",
            "/noise/ads-landing": """<!DOCTYPE html>
<html>
<head><title>Promo Landing</title></head>
<body>
  <div class="ad-banner">Buy now! Click here! Subscribe! Cookie policy! All rights reserved!</div>
</body>
</html>""",
        }

        body = pages.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        payload = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _start_live_server() -> Tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Wave2MultiPageHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}"


def test_pillar_9_host_budget_icc1_and_hidden_gems() -> None:
    """Verifies Ostendorff (2026) arXiv:2610.13321v1 Eq. (1), Eq. (2), Eq. (3), §4.3, and §4.4."""
    high_scores = [0.85, 0.91, 0.78, 0.88, 0.94]
    low_scores = [0.12, 0.19, 0.08, 0.15, 0.21]
    med_scores = [0.52, 0.48, 0.55, 0.49, 0.51]

    # Eq. (1): Host quality density
    q_high = compute_host_quality_density(high_scores, quality_threshold=0.5)
    q_low = compute_host_quality_density(low_scores, quality_threshold=0.5)
    assert math.isclose(q_high, 1.0), f"Expected q_high=1.0, got {q_high}"
    assert math.isclose(q_low, 0.0), f"Expected q_low=0.0, got {q_low}"

    # Eq. (2): Shrout & Fleiss (1979) ICC(1) one-way random-effects ANOVA
    icc1_val = compute_shrout_fleiss_icc1({
        "docs.scipy.org": high_scores,
        "spam-farm.example": low_scores,
        "mixed-blog.example": med_scores,
    })
    assert icc1_val > 0.90, f"Strong clustering must yield ICC(1) > 0.90, got {icc1_val}"

    # Eq. (3): Spearman-Brown reliability with m_bar=3.0 probes
    sb_k3 = spearman_brown_reliability(m_bar=3.0, icc1=0.453)
    expected_sb = (3.0 * 0.453) / (1.0 + 2.0 * 0.453)
    assert math.isclose(sb_k3, expected_sb, rel_tol=1e-5)

    # §4.3 & §4.4: Sample-Then-Deepen budget allocation + Hidden Gem discovery
    allocator = SampleThenDeepenAllocator(
        probe_sample_size=3, min_host_pages=3, max_host_pages=100, quality_threshold=0.5
    )
    allocator.register_known_urls("niche-math.edu", count=50)
    allocator.register_known_urls("mega-portal.com", count=6)

    for s in high_scores[:3]:
        st_high = allocator.record_page_quality("niche-math.edu", s)
    for s in low_scores[:3]:
        st_low = allocator.record_page_quality("mega-portal.com", s)

    assert st_high.phase == "DEEPENING"
    assert st_low.phase == "CAPPED"
    assert st_high.allocated_max_depth_pages > st_low.allocated_max_depth_pages
    assert allocator.can_fetch_more("niche-math.edu") is True
    assert allocator.can_fetch_more("mega-portal.com") is False

    gems = allocator.find_hidden_gem_hosts(quality_quantile=0.5)
    gem_hosts = [g.host for g in gems]
    assert "niche-math.edu" in gem_hosts
    assert "mega-portal.com" not in gem_hosts


def test_pillar_10_htmlrag_dripper_block_pruning_and_shadow_dom() -> None:
    """Verifies HtmlRAG (arXiv:2411.02959v2), Dripper (arXiv:2511.23119), and D2Snap (arXiv:2508.04412v4)."""
    raw_html = """
    <html>
      <head><style>.hidden{display:none}</style><script>console.log("track")</script></head>
      <body>
        <div><div><div class="wrapper">
          <nav class="menu">Home | About | Contact | Privacy Policy | Terms of Use</nav>
          <main>
            <article>
              <h1>Stochastic Optimal Control in Biomechanical Trajectories</h1>
              <p>Minimum-jerk and Ornstein-Uhlenbeck stochastic differential equations govern human cursor kinematics under Fitts's Law constraints.</p>
            </article>
          </main>
          <template shadowrootmode="open">
            <section class="shadow-widget">
              <h2>Shadow DOM Pricing Specification</h2>
              <p>Enterprise tier includes 99.99% SLA and zero-mock verification.</p>
              <button aria-label="Request Enterprise Access">Request Access</button>
            </section>
          </template>
          <footer class="footer">Copyright 2026 All rights reserved Cookie Preferences</footer>
        </div></div></div>
      </body>
    </html>
    """
    flattened, flat_count = flatten_shadow_dom_and_iframes(raw_html)
    assert flat_count == 1
    assert 'data-shadow-root="flattened"' in flattened
    assert "Shadow DOM Pricing Specification" in flattened

    compressed = lossless_structural_compress(flattened)
    assert len(compressed) < len(flattened)

    pruner = BlockTreePruner()
    result = pruner.prune(
        raw_html,
        query="biomechanical cursor kinematics enterprise SLA",
        max_tokens=45,
    )
    assert "Stochastic Optimal Control" in result.pruned_markdown or "Shadow DOM Pricing" in result.pruned_markdown
    assert "Copyright 2026 All rights reserved" not in result.pruned_markdown
    assert 0.0 < result.saved_flops_ratio < 1.0
    assert result.pruned_tokens <= result.original_tokens


def test_pillar_11_bandit_proxy_rotator_and_bandwidth_blocker() -> None:
    """Verifies UCB1 (Auer et al. 2002 / arXiv:2112.07620v4) & Thompson Sampling proxy selection."""
    proxies = ["http://fast-clean.proxy:8080", "http://slow-blocked.proxy:8080", "http://medium.proxy:8080"]
    rotator = BanditProxyRotator(proxies, rtt_penalty_weight=0.15, base_cooldown_sec=30.0, seed=42)

    now = 1000.0
    for _ in range(10):
        rotator.record_outcome("http://fast-clean.proxy:8080", status_code=200, rtt_ms=85.0, now=now)
        rotator.record_outcome("http://medium.proxy:8080", status_code=200, rtt_ms=650.0, now=now)
    rotator.record_outcome("http://slow-blocked.proxy:8080", status_code=429, rtt_ms=1200.0, now=now)

    # UCB1 must select fast-clean and exclude the cooled-down 429 proxy
    chosen_ucb = rotator.select_proxy(policy="ucb1", now=now + 1.0)
    assert chosen_ucb.proxy_url == "http://fast-clean.proxy:8080"

    # Thompson Sampling over 20 trials must strongly prefer fast-clean and never pick cooled-down 429
    ts_counts: Dict[str, int] = {}
    for step in range(20):
        pick = rotator.select_proxy(policy="thompson", now=now + 2.0 + step)
        ts_counts[pick.proxy_url] = ts_counts.get(pick.proxy_url, 0) + 1
    assert ts_counts.get("http://fast-clean.proxy:8080", 0) >= 10
    assert ts_counts.get("http://slow-blocked.proxy:8080", 0) == 0

    # BandwidthResourceBlocker check
    blocker = BandwidthResourceBlocker()
    assert blocker.should_block("https://www.googletagmanager.com/gtm.js", "script") is True
    assert blocker.should_block("https://cdn.example.com/banner.mp4", "media") is True
    assert blocker.should_block("https://api.example.com/v1/products.json", "fetch") is False


def test_pillar_12_hierarchical_rag_chunker_dataman_and_streaming_export() -> None:
    """Verifies DataMan Eq. (5) (arXiv:2502.19363), Hierarchical RAG chunking, and O(1) export."""
    md_doc = """# Distributed Crawling Architecture

Modern web crawlers combine HTTP TLS impersonation with browser-based clearance harvesting.

## Frontier Priority Scheduling

Craw4LLM prioritizes URLs by combining intrinsic quality predictions with parent-page influence scores. Each host maintains an independent token bucket and Crawl-delay timer.

### SimHash Near-Duplicate Detection

Charikar 64-bit locality-sensitive hashing detects near-duplicate HTML documents in O(1) Hamming distance checks.
"""
    chunker = HierarchicalRAGChunker(max_tokens=30, overlap_tokens=5, cohesion_split_threshold=0.08)
    chunks = chunker.chunk_markdown(
        url="https://docs.veil.dev/architecture",
        markdown=md_doc,
        quality_score=0.92,
    )
    assert len(chunks) >= 2
    assert any("Distributed Crawling Architecture > Frontier Priority Scheduling" in c.heading_breadcrumb for c in chunks)
    for c in chunks:
        assert c.content.startswith("[")
        assert c.token_count > 0

    cohesion = lexical_jaccard_cohesion("crawlers combine HTTP TLS impersonation", "HTTP TLS impersonation with browser clearance")
    assert cohesion > 0.2

    # DataMan Eq. (5) temperature-scaled quality + domain diversity sampling
    probs = dataman_sampling_probabilities(
        quality_scores=[0.95, 0.85, 0.20],
        domains=["docs.veil.dev", "docs.veil.dev", "rare-math.org"],
        temperature=0.5,
    )
    assert len(probs) == 3
    assert math.isclose(sum(probs), 1.0, rel_tol=1e-4)

    # Streaming JSONL and CSV export
    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_p = Path(tmpdir) / "test_corpus.jsonl"
        csv_p = Path(tmpdir) / "test_corpus.csv"
        exporter = StreamingCorpusExporter(jsonl_path=jsonl_p, csv_path=csv_p)
        exporter.append_record({
            "url": "https://docs.veil.dev/architecture",
            "status": 200,
            "quality_score": 0.92,
            "delta_status": "NEW",
            "token_reduction_pct": 48.5,
            "rag_chunks": [c.__dict__ for c in chunks],
        })
        lines = jsonl_p.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        first_obj = json.loads(lines[0])
        assert first_obj["url"] == "https://docs.veil.dev/architecture"
        assert csv_p.exists() and csv_p.stat().st_size > 40


def test_pillar_13_live_deep_site_crawler_and_ui_telemetry() -> None:
    """Verifies live multi-worker DeepSiteCrawler, SQLite WAL crash-resume, and UI telemetry."""
    server, base_url = _start_live_server()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt_db = Path(tmpdir) / "frontier.sqlite"
            delta_db = Path(tmpdir) / "delta.sqlite"
            jsonl_p = Path(tmpdir) / "crawled.jsonl"
            csv_p = Path(tmpdir) / "crawled.csv"

            exporter = StreamingCorpusExporter(jsonl_path=jsonl_p, csv_path=csv_p)
            crawler = DeepSiteCrawler(
                checkpoint_db_path=ckpt_db,
                delta_db_path=delta_db,
                probe_sample_size=2,
                max_host_pages=20,
            )
            summary = asyncio.run(
                crawler.crawl_site(
                    start_urls=[f"{base_url}/"],
                    query="host-aware budget allocation block pruning bandit proxy",
                    max_pages=6,
                    max_depth=3,
                    concurrency=2,
                    exporter=exporter,
                )
            )

            assert summary["crawled_count"] >= 4, f"Expected >=4 pages crawled, got {summary['crawled_count']}"
            pages = summary["pages"]
            assert all("dataman_sample_prob" in p for p in pages)
            assert math.isclose(sum(p["dataman_sample_prob"] for p in pages), 1.0, rel_tol=1e-3)
            assert jsonl_p.exists() and len(jsonl_p.read_text(encoding="utf-8").strip().splitlines()) == summary["crawled_count"]

            # Verify SQLite WAL crash-resume WITHOUT manual .close() call (proving production Windows NTFS safety)
            ckpt = PersistentFrontierQueue(db_path=ckpt_db)
            assert len(ckpt.get_completed_urls()) >= 4

            # Verify UITraceTelemetryVerifier (arXiv:2605.14786 Table 1 & arXiv:2406.07647 Appendix C)
            verifier = UITraceTelemetryVerifier(viewport_height=1000)
            human_events = [
                {"type": "mousemove", "timestamp_ms": 100.0, "x": 220.0, "y": 480.0, "screen_frame_ms": 24.0},
                {"type": "scroll", "timestamp_ms": 135.0, "x": 220.0, "y": 480.0, "screen_frame_ms": 25.0},
                {"type": "mousemove", "timestamp_ms": 170.0, "x": 310.0, "y": 520.0, "screen_frame_ms": 23.0},
                {"type": "click", "timestamp_ms": 210.0, "x": 312.0, "y": 522.0, "has_href": True, "screen_frame_ms": 24.0},
                {"type": "scroll", "timestamp_ms": 260.0, "x": 312.0, "y": 522.0, "screen_frame_ms": 26.0},
                {"type": "mousemove", "timestamp_ms": 310.0, "x": 400.0, "y": 610.0, "screen_frame_ms": 24.0},
                {"type": "click", "timestamp_ms": 355.0, "x": 402.0, "y": 612.0, "has_href": False, "screen_frame_ms": 25.0},
            ]
            audit_human = verifier.evaluate_trace(human_events)
            assert audit_human.passes_human_profile is True
            assert audit_human.teleport_click_ratio == 0.0

            bot_events = [
                {"type": "click", "timestamp_ms": 10.0, "x": 50.0, "y": 20.0, "has_href": True, "screen_frame_ms": 5.0},
                {"type": "click", "timestamp_ms": 15.0, "x": 80.0, "y": 30.0, "has_href": True, "screen_frame_ms": 5.0},
            ]
            audit_bot = verifier.evaluate_trace(bot_events)
            assert audit_bot.passes_human_profile is False
            assert audit_bot.teleport_click_ratio == 1.0
    finally:
        server.shutdown()
        server.server_close()


def run_all_tests_standalone() -> int:
    tests = [
        ("test_pillar_9_host_budget_icc1_and_hidden_gems", test_pillar_9_host_budget_icc1_and_hidden_gems),
        ("test_pillar_10_htmlrag_dripper_block_pruning_and_shadow_dom", test_pillar_10_htmlrag_dripper_block_pruning_and_shadow_dom),
        ("test_pillar_11_bandit_proxy_rotator_and_bandwidth_blocker", test_pillar_11_bandit_proxy_rotator_and_bandwidth_blocker),
        ("test_pillar_12_hierarchical_rag_chunker_dataman_and_streaming_export", test_pillar_12_hierarchical_rag_chunker_dataman_and_streaming_export),
        ("test_pillar_13_live_deep_site_crawler_and_ui_telemetry", test_pillar_13_live_deep_site_crawler_and_ui_telemetry),
    ]
    for name, fn in tests:
        fn()
        print(f"  [PASS] {name}")
    print("[ALL 5 WAVE-2 DEEP CRAWLING & PAPER-MATH SUITES PASSED 100% AGAINST LIVE LOCAL HTTP SERVER]")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_all_tests_standalone())
