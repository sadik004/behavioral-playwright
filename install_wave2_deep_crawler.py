#!/usr/bin/env python3
"""One-Command Installer & Live Verifier for Wave 1 + Wave 2 Deep Crawling & Extraction Upgrade.

Grounded in the full Google Drive repository structure (`1lvsDxGVuAMoSRBkpa9WdXdm4KY33DCna`):
1. Restores the complete `src/veil/__init__.py`, `src/veil/crawling/__init__.py`, and
   `src/veil/extraction/__init__.py` (preventing empty `__init__.py` overwrites) while
   exporting all 13 Wave-1 & Wave-2 pillars.
2. Upgrades `src/veil/crawling/checkpoint.py`, `src/veil/crawling/delta_store.py`, and
   `src/veil/crawling/deep_crawler.py` with Windows NTFS-safe scoped SQLite sessions (`_session()`).
3. Upgrades `src/veil/blueprints/firecrawl.py` (`FirecrawlReplacementBlueprint`) and
   `scripts/verify_all_features_real.py` + `tests/integration/test_all_features_real.py`
   to integrate all 13 pillars into the master verification scorecard.
4. Generates both leaf module aliases (`_sys.modules[__name__]`) and package `__init__.py`
   aliases in `src/behavioral_playwright/` to preserve 100% `test_legacy_symbol_parity.py` pass rate.

Usage:
    python install_wave2_deep_crawler.py --repo-root .
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

LEAF_SHIM_TEMPLATE = '''"""Backward-compatible alias forwarding to `{mod_target}`."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("{mod_target}")
'''

PKG_SHIM_TEMPLATE = '''"""Backward-compatible package alias forwarding to `{mod_target}`."""
import importlib as _importlib

_mod = _importlib.import_module("{mod_target}")
for _k, _v in _mod.__dict__.items():
    if _k not in ("__name__", "__loader__", "__package__", "__spec__", "__path__", "__file__", "__cached__"):
        globals()[_k] = _v
'''

CHECKPOINT_PY_CODE = '''"""SQLite Crash-Resilient Crawl Checkpoint Store (`src/veil/crawling/checkpoint.py`).

Production Windows NTFS Safe:
- Uses scoped atomic SQLite connections (`_session()`) for file-backed databases so
  OS file handles (`WinError 32`) are never held open across concurrent network I/O.
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Union

from veil.crawling.models import CrawlerTier, CrawlResponse, EscalationRecord

_CHECKPOINT_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS crawl_checkpoints (
    crawl_id TEXT,
    url TEXT,
    status_code INTEGER,
    body TEXT,
    headers_json TEXT,
    resolved_tier TEXT,
    is_success INTEGER,
    challenge_detected TEXT,
    escalation_history_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (crawl_id, url)
);
CREATE INDEX IF NOT EXISTS idx_checkpoint_crawl_id ON crawl_checkpoints(crawl_id);
"""


class CheckpointStore:
    """Thread-safe, WAL-enabled SQLite persistence store for crawl checkpoints."""

    def __init__(self, db_path: Union[str, Path] = ":memory:") -> None:
        self.db_path = str(db_path)
        self._lock = threading.Lock()
        self._is_memory = self.db_path == ":memory:" or self.db_path.startswith("file::memory:")
        self._mem_conn: Optional[sqlite3.Connection] = None
        if self._is_memory:
            self._mem_conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    @contextlib.contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        if self._is_memory:
            if self._mem_conn is None:
                self._mem_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            yield self._mem_conn
            return

        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._lock, self._session() as conn:
            conn.executescript(_CHECKPOINT_SCHEMA)
            conn.commit()

    def save_response(self, crawl_id: str, response: CrawlResponse) -> None:
        headers_str = json.dumps(response.headers)
        escalation_list = [
            {
                "tier": rec.tier.value if hasattr(rec.tier, "value") else str(rec.tier),
                "status_code": rec.status_code,
                "reason": rec.reason,
                "latency_ms": rec.latency_ms,
                "error": rec.error,
            }
            for rec in response.escalation_history
        ]
        tier_val = (
            response.resolved_tier.value
            if hasattr(response.resolved_tier, "value")
            else str(response.resolved_tier)
        )

        with self._lock, self._session() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO crawl_checkpoints (
                    crawl_id, url, status_code, body, headers_json,
                    resolved_tier, is_success, challenge_detected,
                    escalation_history_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    crawl_id,
                    response.url,
                    response.status_code,
                    response.body,
                    headers_str,
                    tier_val,
                    1 if response.is_success else 0,
                    response.challenge_detected,
                    json.dumps(escalation_list),
                ),
            )
            conn.commit()

    def get_response(self, crawl_id: str, url: str) -> Optional[CrawlResponse]:
        with self._lock, self._session() as conn:
            cursor = conn.execute(
                """
                SELECT status_code, body, headers_json, resolved_tier,
                       is_success, challenge_detected, escalation_history_json
                FROM crawl_checkpoints
                WHERE crawl_id = ? AND url = ?
                """,
                (crawl_id, url),
            )
            row = cursor.fetchone()

        if not row:
            return None

        status_code, body, hdrs_json, tier_str, is_success, challenge, esc_json = row
        headers = json.loads(hdrs_json) if hdrs_json else {}
        esc_raw = json.loads(esc_json) if esc_json else []

        esc_records = [
            EscalationRecord(
                tier=CrawlerTier(e["tier"]) if e["tier"] in [t.value for t in CrawlerTier] else CrawlerTier.HTTP_FAST,
                status_code=e.get("status_code"),
                reason=e.get("reason"),
                latency_ms=e.get("latency_ms", 0.0),
                error=e.get("error"),
            )
            for e in esc_raw
        ]

        resolved_tier = CrawlerTier.HTTP_FAST
        for t in CrawlerTier:
            if t.value == tier_str:
                resolved_tier = t
                break

        return CrawlResponse(
            url=url,
            status_code=status_code,
            body=body,
            headers=headers,
            resolved_tier=resolved_tier,
            escalation_history=esc_records,
            is_success=bool(is_success),
            challenge_detected=challenge,
        )

    def is_completed(self, crawl_id: str, url: str) -> bool:
        with self._lock, self._session() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM crawl_checkpoints WHERE crawl_id = ? AND url = ? AND is_success = 1",
                (crawl_id, url),
            )
            return cursor.fetchone() is not None

    def get_completed_urls(self, crawl_id: str) -> Set[str]:
        with self._lock, self._session() as conn:
            cursor = conn.execute(
                "SELECT url FROM crawl_checkpoints WHERE crawl_id = ? AND is_success = 1",
                (crawl_id,),
            )
            return {row[0] for row in cursor.fetchall()}

    def clear(self, crawl_id: Optional[str] = None) -> None:
        with self._lock, self._session() as conn:
            if crawl_id:
                conn.execute("DELETE FROM crawl_checkpoints WHERE crawl_id = ?", (crawl_id,))
            else:
                conn.execute("DELETE FROM crawl_checkpoints")
            conn.commit()

    def close(self) -> None:
        with self._lock:
            if self._mem_conn is not None:
                self._mem_conn.close()
                self._mem_conn = None

    def __enter__(self) -> "CheckpointStore":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


__all__ = ["CheckpointStore"]
'''

FIRECRAWL_PY_CODE = '''"""Firecrawl & Crawl4AI Drop-in Replacement Client Blueprint (`src/veil/blueprints/firecrawl.py`)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

from veil.crawling.checkpoint import CheckpointStore
from veil.crawling.deep_crawler import DeepSiteCrawler
from veil.crawling.models import CrawlerTier, CrawlRequest
from veil.crawling.service import AutoRuleSchemaExtractor, TieredCrawlerService
from veil.crawling.world_class_engine import WorldClassCrawlerEngine
from veil.extraction.block_tree_pruner import BlockTreePruner
from veil.extraction.hydration import extract_hydration_state
from veil.extraction.markdown import html_to_fit_markdown
from veil.extraction.rag_chunker_exporter import HierarchicalRAGChunker, StreamingCorpusExporter


class FirecrawlReplacementBlueprint:
    """Self-contained drop-in replacement for Firecrawl and Crawl4AI."""

    def __init__(
        self,
        crawler: Optional[TieredCrawlerService] = None,
        checkpoint_store: Optional[CheckpointStore] = None,
        max_concurrency: int = 10,
    ) -> None:
        self.checkpoint = checkpoint_store or CheckpointStore(":memory:")
        self.crawler = crawler or TieredCrawlerService(
            max_concurrency=max_concurrency, checkpoint_store=self.checkpoint
        )
        self.block_pruner = BlockTreePruner()
        self.rag_chunker = HierarchicalRAGChunker()
        self.world_engine = WorldClassCrawlerEngine()

    @staticmethod
    def html_to_markdown(html: str) -> str:
        if not html:
            return ""
        text = re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        for level in range(6, 0, -1):
            pattern = rf"<h{level}[^>]*>(.*?)</h{level}>"
            replacement = rf"\\n\\n{'#' * level} \\1\\n\\n"
            text = re.sub(pattern, replacement, text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"</th>\\s*<th[^>]*>", " | ", text, flags=re.IGNORECASE)
        text = re.sub(r"</td>\\s*<td[^>]*>", " | ", text, flags=re.IGNORECASE)
        text = re.sub(r"<tr[^>]*>\\s*<td>", "| ", text, flags=re.IGNORECASE)
        text = re.sub(r"</td>\\s*</tr>", " |", text, flags=re.IGNORECASE)
        text = re.sub(r'<a\\s+[^>]*href=["\\']([^"\\']+)["\\'][^>]*>(.*?)</a>', r"[\\2](\\1)", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<(strong|b)>(.*?)</\\1>", r"**\\2**", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<(em|i)>(.*?)</\\1>", r"*\\2*", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<li[^>]*>(.*?)</li>", r"\\n- \\1", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        lines = [re.sub(r"[ \\t]+", " ", line).strip() for line in text.split("\\n")]
        return "\\n".join(line for line in lines if line)

    def extract_metadata(self, html: str, source_url: str) -> Dict[str, Any]:
        title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_m.group(1).strip() if title_m else ""
        desc_m = re.search(r'<meta[^>]*name=["\\']description["\\'][^>]*content=["\\'](.*?)["\\']', html, re.IGNORECASE)
        desc = desc_m.group(1).strip() if desc_m else ""
        og_title_m = re.search(r'<meta[^>]*property=["\\']og:title["\\'][^>]*content=["\\'](.*?)["\\']', html, re.IGNORECASE)
        og_title = og_title_m.group(1).strip() if og_title_m else ""
        return {
            "title": title,
            "description": desc,
            "ogTitle": og_title,
            "sourceURL": source_url,
            "language": "en",
        }

    async def scrape(
        self,
        url: str,
        formats: Optional[List[str]] = None,
        query: Optional[str] = None,
        max_tokens: int = 250,
    ) -> Dict[str, Any]:
        fmts = formats or ["markdown", "html"]
        req = CrawlRequest(url=url, initial_tier=CrawlerTier.HTTP_FAST)
        resp = await self.crawler.crawl(req)
        metadata = self.extract_metadata(resp.body, url)
        metadata["statusCode"] = resp.status_code

        data: Dict[str, Any] = {"metadata": metadata}
        if "markdown" in fmts:
            data["markdown"] = self.html_to_markdown(resp.body)
        if "fit_markdown" in fmts:
            distilled = html_to_fit_markdown(resp.body, query=query)
            data["fit_markdown"] = distilled.fit_markdown
            data["token_reduction_pct"] = distilled.token_reduction_pct
        if "html" in fmts:
            data["html"] = resp.body
        if "schema" in fmts:
            data["schema"] = AutoRuleSchemaExtractor.infer_and_extract(resp.body)
        if "hydration" in fmts:
            data["hydration"] = extract_hydration_state(resp.body)
        if "pruned_blocks" in fmts:
            pruned = self.block_pruner.prune(resp.body, query=query, max_tokens=max_tokens)
            data["pruned_blocks"] = {
                "pruned_markdown": pruned.pruned_markdown,
                "compression_ratio": pruned.compression_ratio,
                "saved_flops_ratio": pruned.saved_flops_ratio,
                "shadow_or_iframes_flattened": pruned.shadow_or_iframes_flattened,
            }
        if "rag_chunks" in fmts:
            md_source = data.get("fit_markdown") or self.html_to_markdown(resp.body)
            chunks = self.rag_chunker.chunk_markdown(url, md_source)
            data["rag_chunks"] = [c.__dict__ for c in chunks]

        return {"success": resp.is_success, "data": data}

    async def map(self, base_url: str, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
        mapped = await self.world_engine.map_site(base_url, search_query=search_query)
        return [m.__dict__ for m in mapped]

    async def crawl(
        self,
        start_url: str,
        limit: int = 5,
        formats: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        fmts = formats or ["markdown"]
        visited_urls: List[str] = []
        queue = [start_url]
        pages_data: List[Dict[str, Any]] = []

        while queue and len(visited_urls) < limit:
            current = queue.pop(0)
            if current in visited_urls:
                continue
            visited_urls.append(current)
            scrape_res = await self.scrape(current, formats=fmts)
            pages_data.append(scrape_res.get("data", {}))
            body = scrape_res.get("data", {}).get("html", "")
            links = re.findall(r'href=["\\'](http[^"\\']+)["\\']', body)
            for link in links:
                if link not in visited_urls and link not in queue:
                    queue.append(link)

        return {"success": True, "total_pages": len(pages_data), "data": pages_data}

    async def deep_crawl(
        self,
        start_urls: Sequence[str] | str,
        query: Optional[str] = None,
        max_pages: int = 25,
        max_depth: int = 3,
        concurrency: int = 4,
        exporter: Optional[StreamingCorpusExporter] = None,
    ) -> Dict[str, Any]:
        async with DeepSiteCrawler() as deep:
            return await deep.crawl_site(
                start_urls=start_urls,
                query=query,
                max_pages=max_pages,
                max_depth=max_depth,
                concurrency=concurrency,
                exporter=exporter,
            )


__all__ = ["FirecrawlReplacementBlueprint"]
'''


def install_package(pkg_dir: Path, repo_root: Path) -> None:
    # If full repo exists on target PC, also upgrade checkpoint.py and blueprints/firecrawl.py
    if (repo_root / "src" / "veil" / "crawling" / "models.py").exists():
        ckpt_dst = repo_root / "src" / "veil" / "crawling" / "checkpoint.py"
        ckpt_dst.write_text(CHECKPOINT_PY_CODE, encoding="utf-8")
        print("[INSTALLED] src/veil/crawling/checkpoint.py")

    if (repo_root / "src" / "veil" / "blueprints").exists():
        fc_dst = repo_root / "src" / "veil" / "blueprints" / "firecrawl.py"
        fc_dst.write_text(FIRECRAWL_PY_CODE, encoding="utf-8")
        print("[INSTALLED] src/veil/blueprints/firecrawl.py")

    src_veil = pkg_dir / "src" / "veil"
    if src_veil.exists():
        for file_path in sorted(src_veil.rglob("*.py")):
            rel = file_path.relative_to(pkg_dir)
            dst = repo_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if file_path.resolve() != dst.resolve():
                shutil.copy2(file_path, dst)
            print(f"[INSTALLED] {rel.as_posix()}")

            sub_rel = file_path.relative_to(src_veil)
            bp_dst = repo_root / "src" / "behavioral_playwright" / sub_rel
            bp_dst.parent.mkdir(parents=True, exist_ok=True)
            if sub_rel.name == "__init__.py":
                parent_parts = sub_rel.parent.parts
                mod_target = "veil" if not parent_parts else "veil." + ".".join(parent_parts)
                bp_dst.write_text(PKG_SHIM_TEMPLATE.format(mod_target=mod_target), encoding="utf-8")
            else:
                mod_target = "veil." + sub_rel.with_suffix("").as_posix().replace("/", ".")
                bp_dst.write_text(LEAF_SHIM_TEMPLATE.format(mod_target=mod_target), encoding="utf-8")

    # Also ensure behavioral_playwright shims exist for all existing veil submodules
    target_veil = repo_root / "src" / "veil"
    if target_veil.exists():
        for file_path in sorted(target_veil.rglob("*.py")):
            if "__pycache__" in file_path.parts:
                continue
            sub_rel = file_path.relative_to(target_veil)
            bp_dst = repo_root / "src" / "behavioral_playwright" / sub_rel
            if not bp_dst.exists():
                bp_dst.parent.mkdir(parents=True, exist_ok=True)
                if sub_rel.name == "__init__.py":
                    parent_parts = sub_rel.parent.parts
                    mod_target = "veil" if not parent_parts else "veil." + ".".join(parent_parts)
                    bp_dst.write_text(PKG_SHIM_TEMPLATE.format(mod_target=mod_target), encoding="utf-8")
                else:
                    mod_target = "veil." + sub_rel.with_suffix("").as_posix().replace("/", ".")
                    bp_dst.write_text(LEAF_SHIM_TEMPLATE.format(mod_target=mod_target), encoding="utf-8")

    tests_dir = pkg_dir / "tests"
    if tests_dir.exists():
        for f_path in sorted(tests_dir.rglob("*.py")):
            rel = f_path.relative_to(pkg_dir)
            dst = repo_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if f_path.resolve() != dst.resolve():
                shutil.copy2(f_path, dst)
            print(f"[INSTALLED] {rel.as_posix()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Wave 1 + Wave 2 Deep Crawling & Extraction Upgrade")
    parser.add_argument("--repo-root", type=str, default=".", help="Target repository root")
    args = parser.parse_args()

    pkg_dir = Path(__file__).resolve().parent
    repo_root = Path(args.repo_root).resolve()
    install_package(pkg_dir, repo_root)

    for suite in (
        "tests/integration/test_top_01_pillars_real.py",
        "tests/integration/test_wave2_deep_crawling_real.py",
    ):
        suite_path = repo_root / suite
        if suite_path.exists():
            print(f"\n[VERIFYING] Running {suite} ...")
            res = subprocess.run([sys.executable, str(suite_path)], cwd=str(repo_root))
            if res.returncode != 0:
                return res.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
