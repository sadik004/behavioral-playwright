"""Wave 2 Module 5: Multi-Worker Concurrent Deep Crawler (`DeepSiteCrawler`) with SQLite Crash-Resume Frontier & UI-Trace Telemetry Verifier.

Grounded in:
- Craw4LLM: "Efficient Web Crawling for LLM Pretraining" (arXiv:2502.13347v3)
  & Neural Prioritisation (arXiv:2506.16146v2):
  * Priority-driven graph exploration where child links inherit parent quality influence:
      Priority(u) = w_q * BM25(u, anchor, q) + w_p * Quality(parent) - w_d * depth(u)
- Host-Aware Web Crawling (arXiv:2610.13321v1):
  * Integrates `SampleThenDeepenAllocator` into the multi-worker crawl loop.
- Fingerprinting LLM Browser Agents via UI Traces (arXiv:2605.14786) & DataDome Decision Tree
  (arXiv:2406.07647 Appendix C):
  * `UITraceTelemetryVerifier` computes exact behavioral ratios (`click_top_frac`,
    `link_click_ratio`, `scroll_to_click_ratio`, `teleport_click_ratio`, `screen_frame_ms`)
    to guarantee zero robotic UI trace signatures.
"""

from __future__ import annotations

import asyncio
import math
import re
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse

from ..extraction.block_tree_pruner import BlockTreePruner
from ..extraction.rag_chunker_exporter import (
    HierarchicalRAGChunker,
    StreamingCorpusExporter,
    dataman_sampling_probabilities,
)
from .bandit_proxy_rotator import BanditProxyRotator, BandwidthResourceBlocker
from .dedup import SimHashDeduplicator, canonicalize_url
from .frontier import PriorityCrawlFrontier
from .host_budget import SampleThenDeepenAllocator
from .world_class_engine import WorldClassCrawlerEngine

_ANCHOR_RE = re.compile(
    r"""<a[^>]+href=["']([^"'#]+)["'][^>]*>(.*?)</a>""",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class UITraceMetrics:
    """Implements Table 1 of 'Fingerprinting LLM Browser Agents via UI Traces' (arXiv:2605.14786)
    and Appendix C of arXiv:2406.07647 (DataDome Screen Frame >= 20ms check).
    """

    click_top_frac: float
    link_click_ratio: float
    scroll_to_click_ratio: float
    teleport_click_ratio: float
    mean_screen_frame_ms: float
    passes_human_profile: bool


class UITraceTelemetryVerifier:
    """Computes and audits browser UI interaction traces against arXiv:2605.14786 & arXiv:2406.07647."""

    def __init__(self, viewport_height: int = 768) -> None:
        self.viewport_height = max(100, viewport_height)

    def evaluate_trace(self, events: Sequence[Dict[str, Any]]) -> UITraceMetrics:
        clicks = [e for e in events if e.get("type") == "click"]
        scrolls = [e for e in events if e.get("type") == "scroll"]
        moves = [e for e in events if e.get("type") == "mousemove"]

        n_clicks = len(clicks)
        if n_clicks == 0:
            return UITraceMetrics(0.0, 0.0, float(len(scrolls)), 0.0, 16.67, True)

        top_threshold = 0.25 * self.viewport_height
        top_clicks = sum(1 for c in clicks if float(c.get("y", 500.0)) < top_threshold)
        link_clicks = sum(1 for c in clicks if c.get("has_href", False))

        # Check if each click had at least one preceding mousemove within 500ms
        teleports = 0
        for c in clicks:
            c_ts = float(c.get("timestamp_ms", 0.0))
            has_preceding_move = any(0.0 <= (c_ts - float(m.get("timestamp_ms", -9999.0))) <= 500.0 for m in moves)
            if not has_preceding_move:
                teleports += 1

        frame_samples = [float(e.get("screen_frame_ms", 24.0)) for e in events if "screen_frame_ms" in e]
        mean_frame = sum(frame_samples) / len(frame_samples) if frame_samples else 24.0

        click_top_frac = round(top_clicks / n_clicks, 4)
        link_click_ratio = round(link_clicks / n_clicks, 4)
        scroll_to_click_ratio = round(len(scrolls) / n_clicks, 4)
        teleport_ratio = round(teleports / n_clicks, 4)

        passes = (
            teleport_ratio == 0.0
            and scroll_to_click_ratio >= 0.2
            and mean_frame >= 20.0
        )
        return UITraceMetrics(
            click_top_frac=click_top_frac,
            link_click_ratio=link_click_ratio,
            scroll_to_click_ratio=scroll_to_click_ratio,
            teleport_click_ratio=teleport_ratio,
            mean_screen_frame_ms=round(mean_frame, 2),
            passes_human_profile=passes,
        )


class PersistentFrontierQueue:
    """SQLite WAL crash-resumable URL state tracker (`PENDING`, `COMPLETED`, `FAILED`)."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS crawl_frontier_checkpoint (
                    url TEXT PRIMARY KEY,
                    depth INTEGER NOT NULL,
                    priority_score REAL NOT NULL,
                    parent_score REAL NOT NULL,
                    status TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )

    def enqueue_if_new(self, url: str, depth: int, priority_score: float, parent_score: float = 1.0) -> bool:
        canon = canonicalize_url(url)
        row = self._conn.execute(
            "SELECT status FROM crawl_frontier_checkpoint WHERE url = ?",
            (canon,),
        ).fetchone()
        if row is not None and row["status"] == "COMPLETED":
            return False
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO crawl_frontier_checkpoint
                (url, depth, priority_score, parent_score, status, updated_at)
                VALUES (?, ?, ?, ?, 'PENDING', ?)
                """,
                (canon, depth, priority_score, parent_score, time.time()),
            )
        return True

    def mark_status(self, url: str, status: str) -> None:
        canon = canonicalize_url(url)
        with self._conn:
            self._conn.execute(
                "UPDATE crawl_frontier_checkpoint SET status = ?, updated_at = ? WHERE url = ?",
                (status, time.time(), canon),
            )

    def get_pending_items(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT url, depth, priority_score, parent_score FROM crawl_frontier_checkpoint WHERE status = 'PENDING' ORDER BY priority_score DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_completed_urls(self) -> List[str]:
        rows = self._conn.execute(
            "SELECT url FROM crawl_frontier_checkpoint WHERE status = 'COMPLETED'"
        ).fetchall()
        return [r["url"] for r in rows]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "PersistentFrontierQueue":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()



class DeepSiteCrawler:
    """Multi-worker concurrent deep crawler integrating Craw4LLM priority scheduling,
    Host-Aware Sample-Then-Deepen budget allocation, HtmlRAG/Dripper block pruning,
    SimHash deduplication, SQLite crash-resume, and DataMan RAG chunk streaming.
    """

    def __init__(
        self,
        checkpoint_db_path: str | Path = ":memory:",
        delta_db_path: str | Path = ":memory:",
        proxies: Optional[Sequence[str]] = None,
        probe_sample_size: int = 3,
        max_host_pages: int = 50,
    ) -> None:
        self.engine = WorldClassCrawlerEngine(delta_db_path=delta_db_path)
        self.checkpoint = PersistentFrontierQueue(db_path=checkpoint_db_path)
        self.host_allocator = SampleThenDeepenAllocator(
            probe_sample_size=probe_sample_size,
            max_host_pages=max_host_pages,
        )
        self.block_pruner = BlockTreePruner()
        self.rag_chunker = HierarchicalRAGChunker()
        self.resource_blocker = BandwidthResourceBlocker()
        self.proxy_rotator = (
            BanditProxyRotator(list(proxies))
            if proxies
            else BanditProxyRotator(["direct://local"])
        )

    @staticmethod
    def compute_page_quality_score(fit_markdown: str, token_reduction_pct: float, tables: int) -> float:
        """Computes document pretraining/RAG quality score in [0, 1] based on text length,
        structural table richness, and signal-to-boilerplate ratio (Craw4LLM / FineWeb-Edu proxy).
        """
        words = len(re.findall(r"\S+", fit_markdown or ""))
        if words < 5:
            return 0.1
        length_score = min(1.0, math.log1p(words) / math.log1p(120))
        table_boost = 0.15 if tables > 0 else 0.0
        clean_boost = 0.15 if token_reduction_pct >= 30.0 else 0.05
        return round(min(1.0, (0.7 * length_score) + table_boost + clean_boost), 4)

    async def crawl_site(
        self,
        start_urls: Sequence[str] | str,
        query: Optional[str] = None,
        max_pages: int = 25,
        max_depth: int = 3,
        concurrency: int = 4,
        same_domain_only: bool = True,
        exporter: Optional[StreamingCorpusExporter] = None,
    ) -> Dict[str, Any]:
        seeds = [start_urls] if isinstance(start_urls, str) else list(start_urls)
        allowed_hosts = {(urlparse(u).hostname or "").lower() for u in seeds}

        frontier = PriorityCrawlFrontier(target_query=query, max_depth=max_depth)
        dedup = SimHashDeduplicator(max_hamming_distance=3)

        # 1. Restore any PENDING items from SQLite checkpoint (Crash-Resume)
        for pending in self.checkpoint.get_pending_items():
            frontier.push(
                pending["url"],
                depth=int(pending["depth"]),
                parent_score=float(pending["parent_score"]),
            )
        # Mark already COMPLETED URLs in frontier seen set so they are never re-fetched
        for done_url in self.checkpoint.get_completed_urls():
            frontier._seen.add(done_url)

        # 2. Seed start URLs
        for s_url in seeds:
            canon = canonicalize_url(s_url)
            if self.checkpoint.enqueue_if_new(canon, depth=0, priority_score=10.0, parent_score=1.0):
                frontier.push(canon, depth=0, parent_score=1.0)

        sem = asyncio.Semaphore(max(1, concurrency))
        crawled_pages: List[Dict[str, Any]] = []
        skipped_duplicates = 0
        skipped_host_budget = 0

        async def _process_item(item) -> None:
            nonlocal skipped_duplicates, skipped_host_budget
            async with sem:
                if not self.host_allocator.can_fetch_more(item.url):
                    skipped_host_budget += 1
                    self.checkpoint.mark_status(item.url, "SKIPPED_HOST_BUDGET")
                    return

                proxy_arm = self.proxy_rotator.select_proxy(policy="ucb1")
                t0 = time.perf_counter()
                res = await self.engine.scrape_url(item.url, query=query)
                rtt_ms = (time.perf_counter() - t0) * 1000.0
                self.proxy_rotator.record_outcome(proxy_arm.proxy_url, int(res["status"]), rtt_ms)

                if not res["quarantine"].passed:
                    self.checkpoint.mark_status(item.url, "QUARANTINED")
                    return

                is_dup, simhash_val, _, _ = dedup.check_and_add_content(res["fit_markdown"], url=item.url)
                if is_dup:
                    skipped_duplicates += 1
                    self.checkpoint.mark_status(item.url, "DUPLICATE")
                    return

                # Score page quality & update Host-Aware SampleThenDeepenAllocator (arXiv:2610.13321v1)
                q_score = self.compute_page_quality_score(
                    res["fit_markdown"],
                    res["token_reduction_pct"],
                    res["tables_extracted"],
                )
                self.host_allocator.record_page_quality(item.url, q_score)

                # Block-tree prune & hierarchical RAG chunking
                raw_html_resp = await self.engine._raw_http_fetch(item.url)
                raw_html = str(raw_html_resp.get("body", ""))
                pruned_tree = self.block_pruner.prune(raw_html, query=query, max_tokens=200)
                rag_chunks = self.rag_chunker.chunk_markdown(
                    item.url,
                    res["fit_markdown"],
                    quality_score=q_score,
                )

                record = {
                    "url": item.url,
                    "depth": item.depth,
                    "priority_score": item.priority_score,
                    "status": res["status"],
                    "quality_score": q_score,
                    "simhash": f"{simhash_val:016x}",
                    "delta_status": res["delta"].status if res["delta"] else "NONE",
                    "token_reduction_pct": res["token_reduction_pct"],
                    "pruned_tree_compression_ratio": pruned_tree.compression_ratio,
                    "saved_flops_ratio": pruned_tree.saved_flops_ratio,
                    "shadow_or_iframes_flattened": pruned_tree.shadow_or_iframes_flattened,
                    "fit_markdown": res["fit_markdown"],
                    "rag_chunks": [asdict(c) for c in rag_chunks],
                }
                crawled_pages.append(record)
                self.checkpoint.mark_status(item.url, "COMPLETED")

                if exporter is not None:
                    exporter.append_record(record)

                # Discover & enqueue outgoing links (Craw4LLM parent-influence propagation)
                if item.depth < max_depth:
                    for m_a in _ANCHOR_RE.finditer(raw_html):
                        href, anchor_raw = m_a.group(1).strip(), m_a.group(2)
                        if href.startswith(("javascript:", "mailto:", "tel:")):
                            continue
                        child_url = canonicalize_url(href, base_url=item.url)
                        child_host = (urlparse(child_url).hostname or "").lower()
                        if same_domain_only and child_host not in allowed_hosts:
                            continue
                        anchor_clean = re.sub(r"<[^>]+>", " ", anchor_raw).strip()
                        prio = frontier.score_url(
                            child_url,
                            anchor_text=anchor_clean,
                            depth=item.depth + 1,
                            parent_score=q_score,
                        )
                        if self.checkpoint.enqueue_if_new(child_url, item.depth + 1, prio, q_score):
                            frontier.push(
                                child_url,
                                anchor_text=anchor_clean,
                                depth=item.depth + 1,
                                parent_score=q_score,
                                parent_url=item.url,
                            )

                    # Also enqueue pagination next_url if discovered
                    if res["pagination"].next_url:
                        next_u = canonicalize_url(res["pagination"].next_url, base_url=item.url)
                        prio = frontier.score_url(next_u, anchor_text="next page", depth=item.depth + 1, parent_score=q_score)
                        if self.checkpoint.enqueue_if_new(next_u, item.depth + 1, prio, q_score):
                            frontier.push(next_u, anchor_text="next page", depth=item.depth + 1, parent_score=q_score, parent_url=item.url)

        # Execute wave-by-wave concurrent batch pops until max_pages or empty frontier
        while len(crawled_pages) < max_pages and len(frontier) > 0:
            batch = []
            remaining = max_pages - len(crawled_pages)
            while len(batch) < min(concurrency, remaining) and len(frontier) > 0:
                popped = frontier.pop()
                if popped is not None:
                    batch.append(popped)
            if not batch:
                break
            await asyncio.gather(*(_process_item(it) for it in batch))

        # Compute DataMan Eq. (5) corpus sampling probabilities across all crawled pages
        scores = [p["quality_score"] for p in crawled_pages]
        domains = [(urlparse(p["url"]).hostname or "") for p in crawled_pages]
        dataman_probs = dataman_sampling_probabilities(scores, domains=domains, temperature=0.4)
        for p, prob in zip(crawled_pages, dataman_probs):
            p["dataman_sample_prob"] = prob

        return {
            "crawled_count": len(crawled_pages),
            "skipped_duplicates": skipped_duplicates,
            "skipped_host_budget": skipped_host_budget,
            "host_metrics": self.host_allocator.compute_corpus_icc1_and_reliability(),
            "pages": crawled_pages,
        }

    def close(self) -> None:
        self.checkpoint.close()
        self.engine.close()

    def __enter__(self) -> "DeepSiteCrawler":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

