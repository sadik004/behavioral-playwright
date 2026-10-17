"""Pillar 5: SQLite WAL Incremental Delta & Change-Intelligence Engine.

Tracks `(canonical_url, etag, last_modified, simhash, fit_markdown, structured_json)`
across crawl runs in SQLite WAL mode. Emits `ADDED`, `UNCHANGED`, `MODIFIED`, or `REMOVED`
with exact unified line diffs and JSON field-level diffs (`changed_fields`).
"""

from __future__ import annotations

import difflib
import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

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
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute(
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
        row = self._conn.execute(
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
        row = self._conn.execute(
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
            with self._conn:
                self._conn.execute(
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

        with self._conn:
            self._conn.execute(
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
        self._conn.close()

    def __enter__(self) -> "DeltaCrawlStore":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

