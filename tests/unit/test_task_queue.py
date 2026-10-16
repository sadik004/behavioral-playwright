"""Unit test suite for TaskQueueRepository and InfrastructureNamespace."""
from __future__ import annotations

import tempfile
import os
import pytest
from veil.storage.task_queue import TaskQueueRepository
from veil.facade import BP


def test_task_queue_repository_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_tasks.db")
        repo = TaskQueueRepository(default_db=db_path)
        repo.init_queue()

        # Push 2 tasks with different priorities
        t1 = repo.push_task(db_path, "http://example.com/1", "scrape", priority=5)
        t2 = repo.push_task(db_path, "http://example.com/2", "crawl", priority=10)
        assert t1 > 0
        assert t2 > 0

        # High priority popped first
        popped = repo.pop_task(db_path)
        assert popped is not None
        assert popped["id"] == t2
        assert popped["priority"] == 10 if "priority" in popped else popped["url"] == "http://example.com/2"

        # Complete task
        repo.complete_task(db_path, t2)

        # Pop next task
        popped2 = repo.pop_task(db_path)
        assert popped2 is not None
        assert popped2["id"] == t1

        # Fail and retry task
        repo.fail_task(db_path, t1, max_retries=2)
        repo.fail_task(db_path, t1, max_retries=2)

        # No more pending tasks
        assert repo.pop_task(db_path) is None


def test_bp_infrastructure_facade_delegation():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "facade_tasks.db")
        bp = BP()
        bp.infrastructure.init_queue(db_path)

        tid = bp.infrastructure.push_task(db_path, "http://example.org", "parse", priority=1)
        assert tid > 0

        task = bp.infrastructure.pop_task(db_path)
        assert task is not None
        assert task["url"] == "http://example.org"

        bp.infrastructure.complete_task(db_path, tid)
