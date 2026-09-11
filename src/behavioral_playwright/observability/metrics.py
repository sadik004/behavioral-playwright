"""Metrics-grade observability namespace.

Legacy-compatible metric APIs backed by SQLite with lazy, idempotent DDL
initialization (tracked via ``_initialized_dbs``).
"""

from __future__ import annotations

import sqlite3
import time
from typing import Any, Dict, List

_METRICS_SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT,
    operation TEXT,
    duration_ms REAL,
    status TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS compliance_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT,
    compliant INTEGER,
    violations TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS session_replays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_state TEXT,
    screenshots_count INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


class ObservabilityMetrics:
    """Fine-grained execution metrics exposed as ``bp.observability``."""

    def __init__(self) -> None:
        self._active_traces: Dict[str, float] = {}
        self._initialized_dbs: set = set()

    def init_metrics_db(self, db_path: str = "bp_metrics.db",
                        force: bool = False) -> None:
        """Creates the metrics schema; idempotent unless ``force=True``."""
        if not force and db_path in self._initialized_dbs:
            return
        conn = sqlite3.connect(db_path)
        try:
            conn.executescript(_METRICS_SCHEMA)
            conn.commit()
        finally:
            conn.close()
        self._initialized_dbs.add(db_path)

    def _ensure_db_initialized(self, db_path: str) -> None:
        if db_path not in self._initialized_dbs:
            self.init_metrics_db(db_path)

    # -- execution metrics --------------------------------------------------
    def log_execution(self, url: str, operation: str, duration_ms: float,
                      status: str = "success",
                      db_path: str = "bp_metrics.db") -> None:
        self._ensure_db_initialized(db_path)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT INTO metrics_log (url, operation, duration_ms, status)"
                " VALUES (?, ?, ?, ?)", (url, operation, duration_ms, status))
            conn.commit()
        finally:
            conn.close()

    def get_average_duration(self, operation: str,
                             db_path: str = "bp_metrics.db") -> float:
        self._ensure_db_initialized(db_path)
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                "SELECT AVG(duration_ms) FROM metrics_log WHERE operation=?",
                (operation,)).fetchone()
            return float(row[0]) if row and row[0] is not None else 0.0
        finally:
            conn.close()

    def get_error_rate(self, operation: str,
                       db_path: str = "bp_metrics.db") -> float:
        self._ensure_db_initialized(db_path)
        conn = sqlite3.connect(db_path)
        try:
            total = conn.execute(
                "SELECT COUNT(*) FROM metrics_log WHERE operation=?",
                (operation,)).fetchone()[0]
            if total == 0:
                return 0.0
            failures = conn.execute(
                "SELECT COUNT(*) FROM metrics_log WHERE operation=?"
                " AND status != 'success'", (operation,)).fetchone()[0]
            return failures / total
        finally:
            conn.close()

    # -- tracing ------------------------------------------------------------
    def start_trace(self, trace_id: str) -> None:
        self._active_traces[trace_id] = time.perf_counter()

    def end_trace(self, trace_id: str, url: str = "trace_log",
                  db_path: str = "bp_metrics.db") -> float:
        start = self._active_traces.pop(trace_id, None)
        if start is None:
            return 0.0
        duration_ms = (time.perf_counter() - start) * 1000.0
        self.log_execution(url, f"trace:{trace_id}", duration_ms,
                           status="success", db_path=db_path)
        return duration_ms

    # -- replays & compliance -----------------------------------------------
    def save_session_replay_state(self, page_state: str, screenshots_count: int,
                                  db_path: str = "bp_metrics.db") -> None:
        self._ensure_db_initialized(db_path)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT INTO session_replays (page_state, screenshots_count)"
                " VALUES (?, ?)", (page_state, screenshots_count))
            conn.commit()
        finally:
            conn.close()

    def get_session_replays(self, db_path: str = "bp_metrics.db"
                            ) -> List[Dict[str, Any]]:
        self._ensure_db_initialized(db_path)
        conn = sqlite3.connect(db_path)
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, page_state, screenshots_count, timestamp"
                " FROM session_replays").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def audit_compliance_log(self, url: str, compliant: bool,
                             violations: List[str],
                             db_path: str = "bp_metrics.db") -> None:
        import json
        self._ensure_db_initialized(db_path)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT INTO compliance_audit (url, compliant, violations)"
                " VALUES (?, ?, ?)",
                (url, 1 if compliant else 0, json.dumps(violations)))
            conn.commit()
        finally:
            conn.close()

    # -- reporting ----------------------------------------------------------
    def generate_qa_report(self, db_path: str = "bp_metrics.db"
                           ) -> Dict[str, Any]:
        self._ensure_db_initialized(db_path)
        conn = sqlite3.connect(db_path)
        try:
            total = conn.execute(
                "SELECT COUNT(*) FROM metrics_log").fetchone()[0]
            violations = conn.execute(
                "SELECT COUNT(*) FROM compliance_audit"
                " WHERE compliant = 0").fetchone()[0]
        finally:
            conn.close()
        return {
            "total_executed_ops": total,
            "compliance_violations_count": violations,
            "status": "compliant" if violations == 0 else "risk",
        }


__all__ = ["ObservabilityMetrics"]
