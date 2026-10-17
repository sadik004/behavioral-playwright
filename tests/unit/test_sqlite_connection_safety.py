"""Unit tests verifying zero SQLite connection leaks across all facade and service methods.

Ensures that even upon sqlite3.OperationalError or schema corruption, all SQLite
connections are closed deterministically and file handles released without
PermissionError on Windows.
"""

import os
import sqlite3
import tempfile
import pytest
from unittest.mock import patch

from veil.facade import BP, VeilClient, WebNamespace, ObservabilityNamespace
from veil.crawling.service import CrawlingService
from veil.crawling.delta_store import DeltaCrawlStore
from veil.crawling.deep_crawler import PersistentFrontierQueue, DeepSiteCrawler
from veil.integrations.extensions import IntegrationExtensions


class TrackedConnection:
    """Wrapper around sqlite3.Connection to track close() invocations and simulate errors."""

    def __init__(self, real_conn: sqlite3.Connection, should_fail: bool = False):
        self._real = real_conn
        self.should_fail = should_fail
        self.is_closed = False

    def execute(self, *args, **kwargs):
        if self.should_fail:
            raise sqlite3.OperationalError("Simulated query execution failure")
        return self._real.execute(*args, **kwargs)

    def executescript(self, *args, **kwargs):
        if self.should_fail:
            raise sqlite3.OperationalError("Simulated script execution failure")
        return self._real.executescript(*args, **kwargs)

    def commit(self):
        return self._real.commit()

    def close(self):
        self.is_closed = True
        return self._real.close()


def test_veil_client_alias():
    """Verify VeilClient is an alias of BP facade."""
    assert VeilClient is BP
    client = VeilClient()
    assert isinstance(client, BP)


def test_web_namespace_sqlite_closing_on_error():
    """Verify WebNamespace methods close connections even if sqlite execute fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_web.db")
        web = WebNamespace()

        # Normal init
        web.init_crawl_session(db_path)
        web.save_crawl_state(db_path, "https://example.com/1", status="pending")
        recovered = web.recover_crawl_session(db_path)
        assert "https://example.com/1" in recovered

        # Mocking connection to raise error during execute
        real_connect = sqlite3.connect
        tracked_instances = []

        def tracked_connect(*args, **kwargs):
            real = real_connect(*args, **kwargs)
            inst = TrackedConnection(real, should_fail=True)
            tracked_instances.append(inst)
            return inst

        with patch("sqlite3.connect", side_effect=tracked_connect):
            with pytest.raises(sqlite3.OperationalError):
                web.save_crawl_state(db_path, "https://example.com/2")
            assert len(tracked_instances) == 1
            assert tracked_instances[0].is_closed

            with pytest.raises(sqlite3.OperationalError):
                web.recover_crawl_session(db_path)
            assert len(tracked_instances) == 2
            assert tracked_instances[1].is_closed

        # Verify file is not locked on disk and can be removed
        os.unlink(db_path)


def test_observability_namespace_sqlite_closing_on_error():
    """Verify ObservabilityNamespace methods close connections even if execute fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_obs.db")
        obs = ObservabilityNamespace()

        # Normal initialization
        obs._ensure_legacy_db(db_path)
        obs.start_trace("trace-1", target="https://example.com", db_path=db_path)
        obs.log_execution(db_path, "trace-1", "https://example.com", "scrape", 150, "success")
        obs.end_trace("trace-1", target="https://example.com", db_path=db_path)

        # Mock connection to raise OperationalError
        real_connect = sqlite3.connect
        tracked_instances = []

        def tracked_connect(*args, **kwargs):
            real = real_connect(*args, **kwargs)
            inst = TrackedConnection(real, should_fail=True)
            tracked_instances.append(inst)
            return inst

        with patch("sqlite3.connect", side_effect=tracked_connect):
            # _ensure_legacy_db catches OperationalError internally
            obs._ensure_legacy_db(db_path)
            assert len(tracked_instances) >= 1
            assert all(inst.is_closed for inst in tracked_instances)

            # start_trace calls _ensure_legacy_db then connects itself
            obs.start_trace("trace-fail", db_path=db_path)
            assert all(inst.is_closed for inst in tracked_instances)

            # end_trace calls _metrics.end_trace -> log_execution, raising OperationalError
            with pytest.raises(sqlite3.OperationalError):
                obs.end_trace("trace-fail", db_path=db_path)
            assert all(inst.is_closed for inst in tracked_instances)

            # log_execution calls _metrics.log_execution, raising OperationalError
            with pytest.raises(sqlite3.OperationalError):
                obs.log_execution(db_path, "trace-fail", "target", "action", 10, "success")
            assert all(inst.is_closed for inst in tracked_instances)

            # generate_qa_report falls back safely when OperationalError occurs
            report = obs.generate_qa_report(db_path=db_path)
            assert report is not None
            assert all(inst.is_closed for inst in tracked_instances)

        # Verify file is released and can be deleted immediately
        os.unlink(db_path)


def test_integrations_health_check_closing_on_error():
    """Verify integrations_health_check closes connection on sqlite3.Error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_health.db")

        # Success case
        res = IntegrationExtensions.integrations_health_check(db_path)
        assert res["sqlite_connections"] == "healthy"

        # Failure case with mock
        real_connect = sqlite3.connect
        tracked_instances = []

        def tracked_connect(*args, **kwargs):
            real = real_connect(*args, **kwargs)
            inst = TrackedConnection(real, should_fail=True)
            tracked_instances.append(inst)
            return inst

        with patch("sqlite3.connect", side_effect=tracked_connect):
            res_fail = IntegrationExtensions.integrations_health_check(db_path)
            assert res_fail["sqlite_connections"] == "unreachable"
            assert len(tracked_instances) == 1
            assert tracked_instances[0].is_closed

        # Confirm Windows file handle is released
        os.unlink(db_path)


def test_crawling_service_wal_connection_closing_on_pragma_failure():
    """Verify CrawlingService._get_wal_connection closes connection if PRAGMA raises."""
    crawler = CrawlingService()
    real_connect = sqlite3.connect
    tracked_instances = []

    def tracked_connect(*args, **kwargs):
        real = real_connect(*args, **kwargs)
        inst = TrackedConnection(real, should_fail=True)
        tracked_instances.append(inst)
        return inst

    with patch("sqlite3.connect", side_effect=tracked_connect):
        with pytest.raises(sqlite3.OperationalError):
            crawler._get_wal_connection(":memory:")
        assert len(tracked_instances) == 1
        assert tracked_instances[0].is_closed


def test_context_managers_cleanup_file_locks():
    """Verify context managers for stores cleanly close file handles on Windows."""
    with tempfile.TemporaryDirectory() as tmpdir:
        delta_path = os.path.join(tmpdir, "delta.db")
        frontier_path = os.path.join(tmpdir, "frontier.db")

        # DeltaCrawlStore context manager
        with DeltaCrawlStore(delta_path) as ds:
            ds.evaluate_and_upsert("https://example.com", "Sample markdown content")

        # Should be able to remove without PermissionError (Windows file lock released)
        os.unlink(delta_path)

        # PersistentFrontierQueue context manager
        with PersistentFrontierQueue(frontier_path) as pfq:
            pfq.enqueue_if_new("https://example.com/2", depth=1, priority_score=0.9)

        os.unlink(frontier_path)

        # DeepSiteCrawler context manager
        c_path = os.path.join(tmpdir, "chk.db")
        d_path = os.path.join(tmpdir, "dlt.db")
        with DeepSiteCrawler(checkpoint_db_path=c_path, delta_db_path=d_path) as dsc:
            assert dsc.checkpoint is not None

        os.unlink(c_path)
        os.unlink(d_path)
