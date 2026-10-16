"""SQLite WAL-mode priority task queue repository and persistence layer."""
from __future__ import annotations

import sqlite3
import time
from typing import Any, Dict, Optional

TASK_QUEUE_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    operation TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL,
    target TEXT NOT NULL,
    action TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    status TEXT NOT NULL,
    logged_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS traces (
    trace_id TEXT PRIMARY KEY,
    target TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT
);
"""


class TaskQueueRepository:
    """Thread-safe, WAL-enabled priority task repository."""

    def __init__(self, default_db: str = "bp_tasks.db") -> None:
        self.default_db = default_db

    def init_queue(self, db_path: Optional[str] = None) -> None:
        target = db_path or self.default_db
        conn = sqlite3.connect(target)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(TASK_QUEUE_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def push_task(
        self,
        db_path: str,
        url: str,
        operation: str,
        priority: int = 0,
    ) -> int:
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.execute(
                "INSERT INTO tasks (url, operation, priority, created_at)"
                " VALUES (?, ?, ?, ?)",
                (url, operation, priority, time.strftime("%Y-%m-%dT%H:%M:%S")),
            )
            conn.commit()
            return int(cur.lastrowid or 0)
        finally:
            conn.close()

    def pop_task(self, db_path: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                "SELECT id, url, operation FROM tasks WHERE status='pending'"
                " ORDER BY priority DESC LIMIT 1"
            ).fetchone()
            if row:
                conn.execute("UPDATE tasks SET status='running' WHERE id=?", (row[0],))
                conn.commit()
            return {"id": row[0], "url": row[1], "operation": row[2]} if row else None
        finally:
            conn.close()

    def complete_task(self, db_path: str, task_id: int) -> None:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "UPDATE tasks SET status='completed', completed_at=? WHERE id=?",
                (time.strftime("%Y-%m-%dT%H:%M:%S"), task_id),
            )
            conn.commit()
        finally:
            conn.close()

    def fail_task(self, db_path: str, task_id: int, max_retries: int = 3) -> None:
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                "SELECT COALESCE(SUBSTR(status, 8), '') FROM tasks WHERE id=?",
                (task_id,),
            ).fetchone()
            retries = row[0] if row else ""
            attempt = len(retries) + 1
            if attempt >= max_retries:
                conn.execute("UPDATE tasks SET status='failed' WHERE id=?", (task_id,))
            else:
                conn.execute(
                    "UPDATE tasks SET status=? WHERE id=?",
                    (f"retry:{attempt}", task_id),
                )
            conn.commit()
        finally:
            conn.close()
