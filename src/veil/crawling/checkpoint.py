"""SQLite WAL Crash-Resilient Crawl Checkpoint Store (`veil.crawling.checkpoint`)."""

from __future__ import annotations

import contextlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Iterator, Optional

from .models import CrawlerTier, CrawlResponse


class CheckpointStore:
    """Persists completed crawl responses in SQLite WAL mode with Windows NTFS handle hygiene."""

    def __init__(self, db_path: str | Path = "crawl_checkpoint.db") -> None:
        self.db_path = str(db_path)
        self._is_memory = self.db_path == ":memory:" or self.db_path.startswith("file::memory:")
        self._mem_conn: Optional[sqlite3.Connection] = None
        if self._is_memory:
            self._mem_conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_schema()

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

    def _init_schema(self) -> None:
        with self._session() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS crawl_checkpoints (
                    crawl_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    body TEXT NOT NULL,
                    headers_json TEXT NOT NULL,
                    resolved_tier TEXT NOT NULL,
                    is_success INTEGER NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (crawl_id, url)
                )
                """
            )

    def save_response(self, crawl_id: str, resp: CrawlResponse) -> None:
        tier_val = resp.resolved_tier.value if hasattr(resp.resolved_tier, "value") else str(resp.resolved_tier)
        with self._session() as conn:
            conn.execute(
                """
                INSERT INTO crawl_checkpoints
                    (crawl_id, url, status_code, body, headers_json, resolved_tier, is_success, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(crawl_id, url) DO UPDATE SET
                    status_code = excluded.status_code,
                    body = excluded.body,
                    headers_json = excluded.headers_json,
                    resolved_tier = excluded.resolved_tier,
                    is_success = excluded.is_success,
                    updated_at = excluded.updated_at
                """,
                (
                    crawl_id,
                    resp.url,
                    int(resp.status_code),
                    resp.body,
                    json.dumps(resp.headers or {}),
                    tier_val,
                    1 if resp.is_success else 0,
                    time.time(),
                ),
            )

    def get_response(self, crawl_id: str, url: str) -> Optional[CrawlResponse]:
        with self._session() as conn:
            row = conn.execute(
                """
                SELECT status_code, body, headers_json, resolved_tier, is_success
                FROM crawl_checkpoints
                WHERE crawl_id = ? AND url = ?
                """,
                (crawl_id, url),
            ).fetchone()
            if row is None:
                return None
            try:
                tier = CrawlerTier(row[3])
            except Exception:
                tier = CrawlerTier.HTTP_FAST
            return CrawlResponse(
                url=url,
                status_code=int(row[0]),
                body=str(row[1]),
                headers=json.loads(row[2] or "{}"),
                resolved_tier=tier,
                escalation_history=[],
                is_success=bool(row[4]),
            )

    def is_completed(self, crawl_id: str, url: str) -> bool:
        resp = self.get_response(crawl_id, url)
        return resp is not None and resp.is_success

    def close(self) -> None:
        if self._mem_conn is not None:
            self._mem_conn.close()
            self._mem_conn = None
        elif not self._is_memory and Path(self.db_path).exists():
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                conn.execute("PRAGMA journal_mode=DELETE;")
            except Exception:
                _ = "checkpoint_cleanup"
            finally:
                conn.close()


__all__ = ["CheckpointStore"]
