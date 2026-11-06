"""Verification Test Suite: Architectural Upgrade 4 — Pluggable Distributed Storage & Task Queue.

Asserts:
1. SQLite Backend: create_task_queue("bp_tasks.db") or in-memory pushes and pops tasks with priority ordering cleanly.
2. Redis Lazy Import & Fallback:
   - When redis is absent, create_task_queue("redis://...") raises ProviderUnavailableError without breaking root imports.
   - When mocked redis client is provided, RedisTaskQueue pushes and pops tasks atomically.
3. Postgres Backend Contract:
   - When postgresql:// URI is passed without psycopg2, raises ProviderUnavailableError.
4. Backward Compatibility:
   - TaskQueueRepository and bp.infrastructure methods execute seamlessly.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from behavioral_playwright.exceptions import ProviderUnavailableError
from behavioral_playwright.facade import BP
from behavioral_playwright.storage.task_queue import (
    BaseTaskQueue,
    PostgresTaskQueue,
    RedisTaskQueue,
    SQLiteTaskQueue,
    TaskQueueRepository,
    create_task_queue,
)


class TestPluggableStorageUpgrade(unittest.TestCase):
    """Rigorous verification suite for Pluggable Task Queue Backends."""

    def test_1_sqlite_backend_lifecycle_and_priority(self) -> None:
        """Asserts that SQLiteTaskQueue initializes, pushes with priority, and pops in descending order."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name

        try:
            queue = create_task_queue(db_path)
            self.assertIsInstance(queue, SQLiteTaskQueue)
            queue.init_queue()

            # Push low and high priority tasks
            id_low = queue.push_task("https://example.com/low", "scrape", priority=1)
            id_high = queue.push_task("https://example.com/high", "scrape", priority=10)

            self.assertGreater(id_low, 0)
            self.assertGreater(id_high, 0)

            # Pop highest priority first
            popped1 = queue.pop_task()
            self.assertIsNotNone(popped1)
            self.assertEqual(popped1["url"], "https://example.com/high")
            queue.complete_task(popped1["id"])

            # Pop lower priority second
            popped2 = queue.pop_task()
            self.assertIsNotNone(popped2)
            self.assertEqual(popped2["url"], "https://example.com/low")
            queue.fail_task(popped2["id"], max_retries=2)

            # Assert empty
            self.assertIsNone(queue.pop_task())
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_2_redis_lazy_import_and_mock_atomicity(self) -> None:
        """Asserts Redis lazy import raises ProviderUnavailableError when missing, and operates atomically with mock client."""
        # 1. Test uninstalled/absent redis provider gating
        with patch("behavioral_playwright.storage.task_queue.REDIS_AVAILABLE", False):
            with self.assertRaises(ProviderUnavailableError) as ctx:
                create_task_queue("redis://localhost:6379/0")
            self.assertIn("pip install redis", str(ctx.exception))

        # 2. Test RedisTaskQueue with mock Redis client
        mock_client = MagicMock()
        mock_client._is_mock = True
        mock_pipe = MagicMock()
        mock_client.pipeline.return_value = mock_pipe

        # Mock zrevrange returning task ID 't123'
        mock_client.zrevrange.return_value = ["t123"]
        mock_client.hgetall.return_value = {
            "id": "t123",
            "url": "https://distributed.example/job",
            "operation": "extract",
            "status": "running",
            "priority": "5",
        }

        redis_q = RedisTaskQueue(uri="redis://mock:6379/0", client=mock_client)
        self.assertIsInstance(redis_q, BaseTaskQueue)

        # Push task
        task_id = redis_q.push_task("https://distributed.example/job", "extract", priority=5)
        self.assertTrue(len(task_id) > 0)
        mock_pipe.execute.assert_called()

        # Pop task
        task = redis_q.pop_task()
        self.assertIsNotNone(task)
        self.assertEqual(task["id"], "t123")
        self.assertEqual(task["url"], "https://distributed.example/job")

        # Complete & Fail
        redis_q.complete_task("t123")
        mock_client.hset.assert_called()

    def test_3_postgres_lazy_gating(self) -> None:
        """Asserts Postgres queue raises ProviderUnavailableError if psycopg2 is absent."""
        with patch("behavioral_playwright.storage.task_queue.POSTGRES_AVAILABLE", False):
            with self.assertRaises(ProviderUnavailableError) as ctx:
                create_task_queue("postgresql://user:pass@localhost:5432/db")
            self.assertIn("psycopg2", str(ctx.exception))

    def test_4_facade_and_legacy_repository_compatibility(self) -> None:
        """Asserts that bp.infrastructure and TaskQueueRepository backward-compat methods work with exit code 0."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name

        try:
            # 1. TaskQueueRepository legacy contract
            repo = TaskQueueRepository(default_db=db_path)
            repo.init_queue(db_path)
            tid = repo.push_task(db_path, "https://legacy.example", "parse", priority=2)
            self.assertTrue(tid)
            popped = repo.pop_task(db_path)
            self.assertEqual(popped["id"], tid)
            repo.complete_task(db_path, tid)

            # 2. BP.infrastructure facade delegation
            bp = BP()
            bp.infrastructure.init_queue(db_path)
            fid = bp.infrastructure.push_task(db_path, "https://facade.example", "crawl", priority=7)
            f_popped = bp.infrastructure.pop_task(db_path)
            self.assertEqual(f_popped["id"], fid)
            bp.infrastructure.complete_task(db_path, fid)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
