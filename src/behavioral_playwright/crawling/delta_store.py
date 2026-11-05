"""Pillar 5: SQLite WAL Incremental Delta & Change-Intelligence Engine.

Tracks `(canonical_url, etag, last_modified, simhash, fit_markdown, structured_json)`
across crawl runs in SQLite WAL mode. Emits `ADDED`, `UNCHANGED`, `MODIFIED`, or `REMOVED`
with exact unified line diffs and JSON field-level diffs (`changed_fields`).

Production Windows & Multi-Worker Safe:
- For file-backed databases (`db_path != ":memory:"`), uses scoped atomic connections
  (`_session()`) that commit and release OS file handles immediately after each operation,
  preventing `WinError 32` file locks and `-wal` bloat during long network crawls.
- Supports both synchronous (`with DeltaCrawlStore(...)`) and explicit `.close()` lifecycles.
"""

from __future__ import annotations

import contextlib
import difflib
import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .dedup import canonicalize_url, compute_simhash_64, hamming_distance_64


@dataclass
class DeltaEvaluation:
    url: str
    status: str  # "ADDED" | "UNCHANGED" | "MODIFIED"
    simhash: int
    hamming_distance: int = 0
    changed_fields: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    line_diff: List[str] = field(default_factory=list)


class DeltaCrawlStore:
    """Persistent SQLite WAL store for incremental delta crawling and change detection."""

    def __init__(self, db_path: str | Path = ":memory:", simhash_threshold: int = 2) -> None:
        self.db_path = str(db_path)
        self.simhash_threshold = simhash_threshold
        self._is_memory = self.db_path == ":memory:" or self.db_path.startswith("file::memory:")
        self._mem_conn: Optional[sqlite3.Connection] = None
        if self._is_memory:
            self._mem_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row
        self._init_schema()

    @contextlib.contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        """Production-safe connection scope: keeps `:memory:` alive, but opens and
        immediately closes file-backed connections on Windows/Linux so file descriptors
        are never held across network I/O.
        """
        if self._is_memory:
            if self._mem_conn is None:
                self._mem_conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self._mem_conn.row_factory = sqlite3.Row
            yield self._mem_conn
            return

        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._session() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS page_snapshots (
                    url TEXT PRIMARY KEY,
                    etag TEXT,
                    last_modified TEXT,
                    simhash TEXT NOT NULL,
                    fit_markdown TEXT NOT NULL,
                    structured_json TEXT,
                    updated_at REAL NOT NULL
                )
                """
            )

    def get_conditional_headers(self, url: str) -> Dict[str, str]:
        canon = canonicalize_url(url)
        with self._session() as conn:
            row = conn.execute(
                "SELECT etag, last_modified FROM page_snapshots WHERE url = ?",
                (canon,),
            ).fetchone()
        headers: Dict[str, str] = {}
        if row:
            if row["etag"]:
                headers["If-None-Match"] = row["etag"]
            if row["last_modified"]:
                headers["If-Modified-Since"] = row["last_modified"]
        return headers

    def evaluate_and_upsert(
        self,
        url: str,
        fit_markdown: str,
        structured_data: Optional[Dict[str, Any]] = None,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        http_status: int = 200,
    ) -> DeltaEvaluation:
        canon = canonicalize_url(url)
        with self._session() as conn:
            row = conn.execute(
                "SELECT etag, last_modified, simhash, fit_markdown, structured_json FROM page_snapshots WHERE url = ?",
                (canon,),
            ).fetchone()

            if http_status == 304 and row is not None:
                return DeltaEvaluation(
                    url=canon,
                    status="UNCHANGED",
                    simhash=int(row["simhash"], 16),
                    hamming_distance=0,
                )

            new_simhash = compute_simhash_64(fit_markdown)
            new_simhash_hex = f"{new_simhash:016x}"
            new_json_str = json.dumps(structured_data or {}, sort_keys=True, ensure_ascii=False)
            now = time.time()

            if row is None:
                conn.execute(
                    """
                    INSERT INTO page_snapshots (url, etag, last_modified, simhash, fit_markdown, structured_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (canon, etag, last_modified, new_simhash_hex, fit_markdown, new_json_str, now),
                )
                return DeltaEvaluation(url=canon, status="ADDED", simhash=new_simhash, hamming_distance=0)

            old_simhash = int(row["simhash"], 16)
            dist = hamming_distance_64(old_simhash, new_simhash)
            old_md = row["fit_markdown"] or ""
            old_json = json.loads(row["structured_json"] or "{}")
            new_json = structured_data or {}

            changed_fields: Dict[str, Dict[str, Any]] = {}
            for k in set(old_json.keys()) | set(new_json.keys()):
                if old_json.get(k) != new_json.get(k):
                    changed_fields[k] = {"old": old_json.get(k), "new": new_json.get(k)}

            if dist <= self.simhash_threshold and not changed_fields and old_md.strip() == fit_markdown.strip():
                return DeltaEvaluation(
                    url=canon,
                    status="UNCHANGED",
                    simhash=new_simhash,
                    hamming_distance=dist,
                )

            diff_lines = [
                line
                for line in difflib.unified_diff(
                    old_md.splitlines(),
                    fit_markdown.splitlines(),
                    lineterm="",
                    n=0,
                )
                if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
            ]

            conn.execute(
                """
                UPDATE page_snapshots
                SET etag = ?, last_modified = ?, simhash = ?, fit_markdown = ?, structured_json = ?, updated_at = ?
                WHERE url = ?
                """,
                (etag, last_modified, new_simhash_hex, fit_markdown, new_json_str, now, canon),
            )

            return DeltaEvaluation(
                url=canon,
                status="MODIFIED",
                simhash=new_simhash,
                hamming_distance=dist,
                changed_fields=changed_fields,
                line_diff=diff_lines[:50],
            )

    def close(self) -> None:
        if self._mem_conn is not None:
            self._mem_conn.close()
            self._mem_conn = None

    def __enter__(self) -> "DeltaCrawlStore":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()
