"""SQLite Crash-Resilient Crawl Checkpoint Store (`src/veil/crawling/checkpoint.py`).

Provides WAL-mode SQLite state checkpointing for distributed and multi-page crawls,
allowing interrupted crawls to resume immediately without re-fetching completed URLs.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

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
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            self._conn.executescript(_CHECKPOINT_SCHEMA)
            self._conn.commit()

    def save_response(self, crawl_id: str, response: CrawlResponse) -> None:
        """Atomically saves or updates a crawl checkpoint."""
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

        with self._lock:
            self._conn.execute(
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
            self._conn.commit()

    def get_response(self, crawl_id: str, url: str) -> Optional[CrawlResponse]:
        """Retrieves a cached checkpoint response if completed."""
        with self._lock:
            cursor = self._conn.execute(
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

        # Reconstruct escalation records
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
        """Returns True if the given URL has already been completed in this crawl."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT 1 FROM crawl_checkpoints WHERE crawl_id = ? AND url = ? AND is_success = 1",
                (crawl_id, url),
            )
            return cursor.fetchone() is not None

    def get_completed_urls(self, crawl_id: str) -> Set[str]:
        """Returns the set of all completed URLs for the crawl."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT url FROM crawl_checkpoints WHERE crawl_id = ? AND is_success = 1",
                (crawl_id,),
            )
            return {row[0] for row in cursor.fetchall()}

    def clear(self, crawl_id: Optional[str] = None) -> None:
        """Clears checkpoints for a specific crawl_id or all checkpoints."""
        with self._lock:
            if crawl_id:
                self._conn.execute("DELETE FROM crawl_checkpoints WHERE crawl_id = ?", (crawl_id,))
            else:
                self._conn.execute("DELETE FROM crawl_checkpoints")
            self._conn.commit()

    def close(self) -> None:
        """Closes the underlying SQLite connection."""
        with self._lock:
            self._conn.close()

    def __enter__(self) -> "CheckpointStore":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


__all__ = ["CheckpointStore"]
