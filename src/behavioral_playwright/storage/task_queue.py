"""Pluggable Distributed Storage & Task Queue Backend (SQLite WAL, Redis, PostgreSQL).

Provides a decoupled BaseTaskQueue interface with:
1. SQLiteTaskQueue: Local thread-safe WAL-mode queue with exponential backoff retries.
2. RedisTaskQueue: Distributed high-throughput in-memory queue using Redis Hashes and Sorted Sets (ZSET)
   with atomic Lua-scripted priority pop (guaranteeing exactly-one worker delivery).
3. PostgresTaskQueue: Enterprise relational distributed queue using SELECT ... FOR UPDATE SKIP LOCKED.
4. create_task_queue(uri_or_path, **kwargs): Dynamic factory routing based on URI scheme.
5. TaskQueueRepository: Backward-compatible wrapper maintaining legacy 2-arg method contracts.
"""

from __future__ import annotations

import logging
import random
import sqlite3
import threading
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from behavioral_playwright.exceptions import ProviderUnavailableError

logger = logging.getLogger(__name__)

# Check lazy optional dependencies
try:
    import redis
    REDIS_AVAILABLE = True
except (ImportError, Exception):
    REDIS_AVAILABLE = False

try:
    import psycopg2
    from psycopg2 import pool as psycopg2_pool
    POSTGRES_AVAILABLE = True
except (ImportError, Exception):
    POSTGRES_AVAILABLE = False


TASK_QUEUE_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    operation TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    leased_until REAL DEFAULT 0.0,
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

POSTGRES_TASK_QUEUE_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    operation TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    leased_until DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks (status, priority DESC);
"""


def _extract_retry_count(status: str) -> int:
    """Extracts the numeric retry count from status strings like 'retry:2' or 'running:2'."""
    for prefix in ("retry:", "running:"):
        if status.startswith(prefix):
            sub = status.split(prefix, 1)[1]
            if sub.isdigit():
                return int(sub)
    return 0


class BaseTaskQueue(ABC):
    """Abstract interface defining standard lifecycle operations for all task queue backends."""

    def __init__(self, lease_timeout_sec: float = 60.0) -> None:
        self.lease_timeout_sec = float(lease_timeout_sec)

    @abstractmethod
    def init_queue(self) -> None:
        """Initializes tables, indices, or data structures."""
        pass

    @abstractmethod
    def push_task(
        self, url: str, operation: str, priority: int = 0
    ) -> Union[int, str]:
        """Pushes a task into the queue and returns its unique task identifier."""
        pass

    @abstractmethod
    def pop_task(self) -> Optional[Dict[str, Any]]:
        """Atomically leases the highest-priority pending task and transitions status to 'running'."""
        pass

    @abstractmethod
    def complete_task(self, task_id: Union[int, str]) -> None:
        """Marks a task as completed."""
        pass

    @abstractmethod
    def fail_task(
        self, task_id: Union[int, str], max_retries: int = 3
    ) -> None:
        """Increments task retry counter or marks it as failed once max_retries is reached."""
        pass

    @abstractmethod
    def heartbeat_task(
        self, task_id: Union[int, str], extend_sec: Optional[float] = None
    ) -> bool:
        """Extends task lease if currently running. Returns True if updated, False otherwise."""
        pass

    @abstractmethod
    def reclaim_expired_leases(self, max_retries: int = 3) -> int:
        """Reclaims expired running task leases and increments retries or marks as failed."""
        pass


class SQLiteTaskQueue(BaseTaskQueue):
    """Local SQLite WAL-mode priority queue with exponential jittered backoff."""

    def __init__(
        self,
        db_path: str = "bp_tasks.db",
        timeout: float = 30.0,
        lease_timeout_sec: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(lease_timeout_sec=lease_timeout_sec)
        if db_path.startswith("sqlite:///"):
            db_path = db_path[len("sqlite:///"):]
        self.db_path = db_path
        self.timeout = timeout
        self._lock = threading.Lock()

    def init_queue(self) -> None:
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=self.timeout, check_same_thread=False)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.executescript(TASK_QUEUE_SCHEMA)
                # Safe migration check for existing tables without leased_until column
                cols = [r[1] for r in conn.execute("PRAGMA table_info(tasks);").fetchall()]
                if "leased_until" not in cols:
                    conn.execute("ALTER TABLE tasks ADD COLUMN leased_until REAL DEFAULT 0.0;")
                conn.commit()
            finally:
                conn.close()

    def push_task(
        self, url: str, operation: str, priority: int = 0, max_attempts: int = 8
    ) -> int:
        for attempt in range(max_attempts):
            conn = None
            try:
                with self._lock:
                    conn = sqlite3.connect(self.db_path, timeout=self.timeout, check_same_thread=False)
                    cur = conn.execute(
                        "INSERT INTO tasks (url, operation, priority, created_at, leased_until)"
                        " VALUES (?, ?, ?, ?, 0.0)",
                        (url, operation, priority, time.strftime("%Y-%m-%dT%H:%M:%S")),
                    )
                    conn.commit()
                    return int(cur.lastrowid or 0)
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc).lower() and attempt < max_attempts - 1:
                    time.sleep(random.uniform(0.01, 0.08) * (2 ** attempt))
                    continue
                raise
            finally:
                if conn is not None:
                    conn.close()
        return 0

    def pop_task(self, max_attempts: int = 8) -> Optional[Dict[str, Any]]:
        for attempt in range(max_attempts):
            conn = None
            try:
                with self._lock:
                    conn = sqlite3.connect(
                        self.db_path,
                        timeout=self.timeout,
                        isolation_level=None,
                        check_same_thread=False,
                    )
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("PRAGMA busy_timeout=30000;")
                    conn.execute("BEGIN IMMEDIATE;")
                    row = conn.execute(
                        "SELECT id, url, operation, status FROM tasks "
                        "WHERE status='pending' OR status LIKE 'retry:%' "
                        "ORDER BY priority DESC, id ASC LIMIT 1"
                    ).fetchone()
                    if row:
                        now = time.time()
                        leased_until = now + self.lease_timeout_sec
                        prev_retries = _extract_retry_count(str(row[3] or ""))
                        running_status = f"running:{prev_retries}" if prev_retries > 0 else "running"
                        conn.execute(
                            "UPDATE tasks SET status=?, leased_until=? WHERE id=?",
                            (running_status, leased_until, row[0]),
                        )
                        conn.execute("COMMIT;")
                        return {"id": row[0], "url": row[1], "operation": row[2]}
                    else:
                        conn.execute("COMMIT;")
                        return None
            except sqlite3.OperationalError as exc:
                if conn is not None:
                    try:
                        conn.execute("ROLLBACK;")
                    except Exception:
                        pass
                if "locked" in str(exc).lower() and attempt < max_attempts - 1:
                    time.sleep(random.uniform(0.01, 0.08) * (2 ** attempt))
                    continue
                raise
            except Exception:
                if conn is not None:
                    try:
                        conn.execute("ROLLBACK;")
                    except Exception:
                        _ = "handled_expected_exception"
                raise
            finally:
                if conn is not None:
                    conn.close()
        return None

    def complete_task(self, task_id: Union[int, str]) -> None:
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=self.timeout, check_same_thread=False)
            try:
                conn.execute(
                    "UPDATE tasks SET status='completed', completed_at=?, leased_until=0.0 WHERE id=?",
                    (time.strftime("%Y-%m-%dT%H:%M:%S"), int(task_id)),
                )
                conn.commit()
            finally:
                conn.close()

    def fail_task(self, task_id: Union[int, str], max_retries: int = 3) -> None:
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=self.timeout, check_same_thread=False)
            try:
                row = conn.execute("SELECT status FROM tasks WHERE id=?", (int(task_id),)).fetchone()
                if not row:
                    return
                status = str(row[0] or "")
                attempt = _extract_retry_count(status) + 1

                if attempt >= max_retries:
                    conn.execute("UPDATE tasks SET status='failed', leased_until=0.0 WHERE id=?", (int(task_id),))
                else:
                    conn.execute("UPDATE tasks SET status=?, leased_until=0.0 WHERE id=?", (f"retry:{attempt}", int(task_id)))
                conn.commit()
            finally:
                conn.close()

    def heartbeat_task(self, task_id: Union[int, str], extend_sec: Optional[float] = None) -> bool:
        duration = self.lease_timeout_sec if extend_sec is None else float(extend_sec)
        now = time.time()
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=self.timeout, check_same_thread=False)
            try:
                row = conn.execute("SELECT status FROM tasks WHERE id=?", (int(task_id),)).fetchone()
                if not row:
                    return False
                status = str(row[0] or "")
                if not (status == "running" or status.startswith("running:")):
                    return False
                conn.execute("UPDATE tasks SET leased_until=? WHERE id=?", (now + duration, int(task_id)))
                conn.commit()
                return True
            finally:
                conn.close()

    def reclaim_expired_leases(self, max_retries: int = 3) -> int:
        now = time.time()
        with self._lock:
            conn = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                isolation_level=None,
                check_same_thread=False,
            )
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA busy_timeout=30000;")
                conn.execute("BEGIN IMMEDIATE;")
                rows = conn.execute(
                    "SELECT id, status FROM tasks "
                    "WHERE (status='running' OR status LIKE 'running:%') "
                    "AND leased_until > 0.0 AND leased_until < ?",
                    (now,),
                ).fetchall()
                reclaimed = 0
                for row in rows:
                    tid = row[0]
                    curr_status = str(row[1] or "")
                    retries = _extract_retry_count(curr_status)
                    new_retries = retries + 1
                    if new_retries < max_retries:
                        conn.execute(
                            "UPDATE tasks SET status=?, leased_until=0.0 WHERE id=?",
                            (f"retry:{new_retries}", tid),
                        )
                    else:
                        conn.execute(
                            "UPDATE tasks SET status='failed:lease_expired', leased_until=0.0 WHERE id=?",
                            (tid,),
                        )
                    reclaimed += 1
                conn.execute("COMMIT;")
                return reclaimed
            except Exception:
                if conn is not None:
                    try:
                        conn.execute("ROLLBACK;")
                    except Exception:
                        pass
                raise
            finally:
                if conn is not None:
                    conn.close()


class RedisTaskQueue(BaseTaskQueue):
    """Distributed in-memory task queue backed by Redis / Valkey.

    Uses Redis Hash `tasks:{id}` to store metadata and Sorted Set (ZSET) `tasks:pending`
    ordered by priority. Atomic pop is executed via a Lua script or verified atomic ZREM
    claim loop to guarantee zero duplicate delivery across concurrent workers.
    """

    POP_LUA_SCRIPT = """
    local pending_key = KEYS[1]
    local prefix = ARGV[1]
    local leased_until = ARGV[2] or "0"
    local items = redis.call('ZREVRANGE', pending_key, 0, 0)
    if #items == 0 then
        return nil
    end
    local task_id = items[1]
    redis.call('ZREM', pending_key, task_id)
    local task_hash = prefix .. ':task:' .. task_id
    redis.call('HSET', task_hash, 'status', 'running', 'leased_until', leased_until)
    local task_data = redis.call('HGETALL', task_hash)
    return {task_id, task_data}
    """

    def __init__(
        self,
        uri: str = "redis://localhost:6379/0",
        prefix: str = "bp",
        client: Optional[Any] = None,
        lease_timeout_sec: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(lease_timeout_sec=lease_timeout_sec)
        self.uri = uri
        self.prefix = prefix
        self._pending_zset = f"{prefix}:tasks:pending"

        if client is not None:
            self._client = client
        else:
            if not REDIS_AVAILABLE:
                raise ProviderUnavailableError("redis", "redis", "pip install redis")
            self._client = redis.Redis.from_url(uri, decode_responses=True, **kwargs)

    def init_queue(self) -> None:
        """Verifies connectivity to the Redis server."""
        self._client.ping()

    def push_task(self, url: str, operation: str, priority: int = 0) -> str:
        task_id = str(uuid.uuid4().hex[:12])
        task_key = f"{self.prefix}:task:{task_id}"

        mapping = {
            "id": task_id,
            "url": url,
            "operation": operation,
            "priority": str(priority),
            "status": "pending",
            "leased_until": "0.0",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "completed_at": "",
            "retries": "0",
        }
        pipe = self._client.pipeline()
        pipe.hset(task_key, mapping=mapping)
        pipe.zadd(self._pending_zset, {task_id: float(priority)})
        pipe.execute()
        return task_id

    def pop_task(self) -> Optional[Dict[str, Any]]:
        now = time.time()
        leased_until_str = str(now + self.lease_timeout_sec)

        # 1. Primary path: server-side atomic Lua script via EVAL
        if hasattr(self._client, "eval"):
            try:
                res = self._client.eval(self.POP_LUA_SCRIPT, 1, self._pending_zset, self.prefix, leased_until_str)
                if not res:
                    return None
                task_id, raw_fields = res[0], res[1]
                if isinstance(raw_fields, dict):
                    data = dict(raw_fields)
                    data["id"] = str(task_id)
                else:
                    data = {"id": str(task_id)}
                    for i in range(0, len(raw_fields), 2):
                        data[str(raw_fields[i])] = raw_fields[i + 1]

                # Guarantee leased_until is populated in case external engine didn't evaluate ARGV[2]
                task_key = f"{self.prefix}:task:{task_id}"
                self._client.hset(task_key, "leased_until", leased_until_str)

                return {
                    "id": data["id"],
                    "url": data.get("url", ""),
                    "operation": data.get("operation", ""),
                }
            except NotImplementedError:
                pass

        # 2. Optimistic atomic ZREM claim loop (only the worker whose ZREM returns 1 wins the lease)
        for _ in range(16):
            items = self._client.zrevrange(self._pending_zset, 0, 0)
            if not items:
                return None
            task_id = items[0]
            removed = self._client.zrem(self._pending_zset, task_id)
            if int(removed or 0) == 1:
                task_key = f"{self.prefix}:task:{task_id}"
                self._client.hset(task_key, mapping={"status": "running", "leased_until": leased_until_str})
                data = self._client.hgetall(task_key)
                return {
                    "id": task_id,
                    "url": data.get("url", ""),
                    "operation": data.get("operation", ""),
                }
        return None

    def complete_task(self, task_id: Union[int, str]) -> None:
        task_key = f"{self.prefix}:task:{task_id}"
        self._client.hset(task_key, mapping={
            "status": "completed",
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "leased_until": "0.0",
        })

    def fail_task(self, task_id: Union[int, str], max_retries: int = 3) -> None:
        task_key = f"{self.prefix}:task:{task_id}"
        data = self._client.hgetall(task_key)
        retries = int(data.get("retries", 0)) + 1
        priority = float(data.get("priority", 0))

        if retries >= max_retries:
            self._client.hset(task_key, mapping={"status": "failed", "retries": str(retries), "leased_until": "0.0"})
        else:
            self._client.hset(task_key, mapping={"status": f"retry:{retries}", "retries": str(retries), "leased_until": "0.0"})
            self._client.zadd(self._pending_zset, {str(task_id): priority})

    def heartbeat_task(self, task_id: Union[int, str], extend_sec: Optional[float] = None) -> bool:
        task_key = f"{self.prefix}:task:{task_id}"
        data = self._client.hgetall(task_key)
        if not data:
            return False
        status = str(data.get("status", ""))
        if not (status == "running" or status.startswith("running:")):
            return False
        duration = self.lease_timeout_sec if extend_sec is None else float(extend_sec)
        new_leased_until = str(time.time() + duration)
        self._client.hset(task_key, "leased_until", new_leased_until)
        return True

    def reclaim_expired_leases(self, max_retries: int = 3) -> int:
        now = time.time()
        if hasattr(self._client, "scan_iter"):
            task_keys = list(self._client.scan_iter(f"{self.prefix}:task:*"))
        elif hasattr(self._client, "keys"):
            task_keys = list(self._client.keys(f"{self.prefix}:task:*"))
        elif hasattr(self._client, "_hashes"):
            task_keys = [k for k in self._client._hashes.keys() if k.startswith(f"{self.prefix}:task:")]
        else:
            task_keys = []

        reclaimed = 0
        for task_key in task_keys:
            data = self._client.hgetall(task_key)
            if not data:
                continue
            status = str(data.get("status", ""))
            if not (status == "running" or status.startswith("running:")):
                continue
            try:
                leased_until = float(data.get("leased_until", 0.0) or 0.0)
            except (ValueError, TypeError):
                leased_until = 0.0

            if 0.0 < leased_until < now:
                tid = data.get("id") or task_key.split(":")[-1]
                retries = int(data.get("retries", 0)) + 1
                priority = float(data.get("priority", 0))
                if retries < max_retries:
                    self._client.hset(
                        task_key,
                        mapping={
                            "status": f"retry:{retries}",
                            "retries": str(retries),
                            "leased_until": "0.0",
                        },
                    )
                    self._client.zadd(self._pending_zset, {str(tid): priority})
                else:
                    self._client.hset(
                        task_key,
                        mapping={
                            "status": "failed:lease_expired",
                            "retries": str(retries),
                            "leased_until": "0.0",
                        },
                    )
                reclaimed += 1
        return reclaimed


class PostgresTaskQueue(BaseTaskQueue):
    """Enterprise relational distributed task queue backed by PostgreSQL.

    Uses `SELECT ... FOR UPDATE SKIP LOCKED` for non-blocking, lock-free concurrency
    across multiple distributed worker nodes.
    """

    def __init__(
        self,
        uri: str = "postgresql://postgres:postgres@localhost:5432/bp",
        pool: Optional[Any] = None,
        lease_timeout_sec: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(lease_timeout_sec=lease_timeout_sec)
        self.uri = uri
        self.kwargs = kwargs
        if pool is not None:
            self._pool = pool
        else:
            if not POSTGRES_AVAILABLE:
                raise ProviderUnavailableError("postgresql", "psycopg2", "pip install psycopg2-binary")
            self._pool = None

    def _get_connection(self) -> Any:
        if self._pool is None:
            self._pool = psycopg2_pool.ThreadedConnectionPool(1, 10, self.uri, **self.kwargs)
        return self._pool.getconn()

    def _release_connection(self, conn: Any) -> None:
        if self._pool is not None and conn is not None:
            self._pool.putconn(conn)

    def init_queue(self) -> None:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(POSTGRES_TASK_QUEUE_SCHEMA)
            conn.commit()
        finally:
            self._release_connection(conn)

    def push_task(self, url: str, operation: str, priority: int = 0) -> int:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO tasks (url, operation, priority, leased_until) VALUES (%s, %s, %s, 0.0) RETURNING id;",
                    (url, operation, priority),
                )
                task_id = cur.fetchone()[0]
            conn.commit()
            return int(task_id)
        finally:
            self._release_connection(conn)

    def pop_task(self) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, url, operation, status
                    FROM tasks
                    WHERE status = 'pending' OR status LIKE 'retry:%%'
                    ORDER BY priority DESC, id ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1;
                    """
                )
                row = cur.fetchone()
                if not row:
                    conn.commit()
                    return None
                task_id, url, operation, status = row[0], row[1], row[2], str(row[3] or "")
                now = time.time()
                leased_until = now + self.lease_timeout_sec
                prev_retries = _extract_retry_count(status)
                running_status = f"running:{prev_retries}" if prev_retries > 0 else "running"
                cur.execute(
                    "UPDATE tasks SET status = %s, leased_until = %s WHERE id = %s;",
                    (running_status, leased_until, task_id),
                )
            conn.commit()
            return {"id": task_id, "url": url, "operation": operation}
        finally:
            self._release_connection(conn)

    def complete_task(self, task_id: Union[int, str]) -> None:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tasks SET status = 'completed', completed_at = NOW(), leased_until = 0.0 WHERE id = %s;",
                    (int(task_id),),
                )
            conn.commit()
        finally:
            self._release_connection(conn)

    def fail_task(self, task_id: Union[int, str], max_retries: int = 3) -> None:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT status FROM tasks WHERE id = %s;", (int(task_id),))
                row = cur.fetchone()
                if not row:
                    return
                status = str(row[0] or "")
                attempt = _extract_retry_count(status) + 1

                if attempt >= max_retries:
                    cur.execute("UPDATE tasks SET status = 'failed', leased_until = 0.0 WHERE id = %s;", (int(task_id),))
                else:
                    cur.execute("UPDATE tasks SET status = %s, leased_until = 0.0 WHERE id = %s;", (f"retry:{attempt}", int(task_id)))
            conn.commit()
        finally:
            self._release_connection(conn)

    def heartbeat_task(self, task_id: Union[int, str], extend_sec: Optional[float] = None) -> bool:
        duration = self.lease_timeout_sec if extend_sec is None else float(extend_sec)
        new_leased_until = time.time() + duration
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tasks SET leased_until = %s WHERE id = %s AND (status = 'running' OR status LIKE 'running:%%') RETURNING id;",
                    (new_leased_until, int(task_id)),
                )
                row = cur.fetchone()
            conn.commit()
            return row is not None
        finally:
            self._release_connection(conn)

    def reclaim_expired_leases(self, max_retries: int = 3) -> int:
        now = time.time()
        conn = self._get_connection()
        try:
            reclaimed = 0
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, status FROM tasks
                    WHERE (status = 'running' OR status LIKE 'running:%%')
                    AND leased_until > 0.0 AND leased_until < %s
                    FOR UPDATE SKIP LOCKED;
                    """,
                    (now,),
                )
                rows = cur.fetchall()
                for row in rows:
                    tid, st = row[0], str(row[1] or "")
                    retries = _extract_retry_count(st) + 1
                    if retries < max_retries:
                        cur.execute(
                            "UPDATE tasks SET status = %s, leased_until = 0.0 WHERE id = %s;",
                            (f"retry:{retries}", tid),
                        )
                    else:
                        cur.execute(
                            "UPDATE tasks SET status = 'failed:lease_expired', leased_until = 0.0 WHERE id = %s;",
                            (tid,),
                        )
                    reclaimed += 1
            conn.commit()
            return reclaimed
        finally:
            self._release_connection(conn)


def create_task_queue(
    uri_or_path: str = "bp_tasks.db",
    lease_timeout_sec: float = 60.0,
    **kwargs: Any,
) -> BaseTaskQueue:
    """Factory creating SQLite, Redis, or Postgres task queue based on URI precedence."""
    clean_uri = (uri_or_path or "").strip()
    if clean_uri.startswith(("redis://", "rediss://")):
        return RedisTaskQueue(clean_uri, lease_timeout_sec=lease_timeout_sec, **kwargs)
    if clean_uri.startswith(("postgres://", "postgresql://")):
        return PostgresTaskQueue(clean_uri, lease_timeout_sec=lease_timeout_sec, **kwargs)
    return SQLiteTaskQueue(clean_uri or "bp_tasks.db", lease_timeout_sec=lease_timeout_sec, **kwargs)


class TaskQueueRepository:
    """Thread-safe, WAL-enabled priority task repository maintaining backward-compatible contracts."""

    def __init__(self, default_db: str = "bp_tasks.db", lease_timeout_sec: float = 60.0) -> None:
        self.default_db = default_db
        self.lease_timeout_sec = float(lease_timeout_sec)
        self._queues: Dict[str, BaseTaskQueue] = {}
        self._lock = threading.Lock()

    def _get_queue(self, uri_or_path: Optional[str] = None) -> BaseTaskQueue:
        target = uri_or_path or self.default_db
        with self._lock:
            if target not in self._queues:
                self._queues[target] = create_task_queue(target, lease_timeout_sec=self.lease_timeout_sec)
            return self._queues[target]

    def init_queue(self, db_path: Optional[str] = None) -> None:
        queue = self._get_queue(db_path)
        queue.init_queue()

    def push_task(
        self,
        db_path: str,
        url: str,
        operation: str,
        priority: int = 0,
        max_attempts: int = 5,
    ) -> Union[int, str]:
        queue = self._get_queue(db_path)
        return queue.push_task(url=url, operation=operation, priority=priority)

    def pop_task(self, db_path: str, max_attempts: int = 5) -> Optional[Dict[str, Any]]:
        queue = self._get_queue(db_path)
        return queue.pop_task()

    def complete_task(self, db_path: str, task_id: Union[int, str]) -> None:
        queue = self._get_queue(db_path)
        queue.complete_task(task_id)

    def fail_task(self, db_path: str, task_id: Union[int, str], max_retries: int = 3) -> None:
        queue = self._get_queue(db_path)
        queue.fail_task(task_id, max_retries=max_retries)

    def heartbeat_task(self, db_path: str, task_id: Union[int, str], extend_sec: Optional[float] = None) -> bool:
        queue = self._get_queue(db_path)
        return queue.heartbeat_task(task_id, extend_sec=extend_sec)

    def reclaim_expired_leases(self, db_path: Optional[str] = None, max_retries: int = 3) -> int:
        queue = self._get_queue(db_path)
        return queue.reclaim_expired_leases(max_retries=max_retries)
