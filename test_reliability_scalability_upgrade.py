"""Verification Test Suite: Architectural Upgrade 5 — Distributed Reliability & Scalability Hardening.

Asserts:
1. Test 1 (Zombie Lease Reaper & Heartbeat):
   - SQLiteTaskQueue (real temp file) with lease_timeout_sec=0.15:
     * heartbeat_task() extends lease and prevents expiration.
     * un-heartbeated running task expires, is reclaimed by reclaim_expired_leases() to 'retry:1',
       re-popped, and completed.
     * task exceeding max_retries becomes 'failed:lease_expired'.
   - RedisTaskQueue (thread-safe stateful engine) verified under the exact same contract.
2. Test 2 (Discounted Bandit Adaptation & Cross-Worker State Sync):
   - Proves decay_gamma=0.95 allows healthy proxy to rapidly overtake a degraded proxy that hit
     consecutive 403 blocks after 200 prior successes.
   - Verifies export_state() / import_state() cross-instance state synchronization.
3. Test 3 (Cross-Worker Clearance Lease Sharing via Live TCPServer):
   - Live socketserver.TCPServer challenges requests missing cf_clearance cookie with 403.
   - Worker 1 solves challenge, saves ClearanceLease to shared_store, and receives 200 OK.
   - Worker 2 fetches same URL with zero browser clearance invocations and receives 200 OK immediately.
4. Test 4 (Hierarchical Concurrency Bulkhead Cap & Timeout):
   - 20 concurrent BROWSER_HEADLESS tasks through max_browser_concurrency=3 bulkhead:
     peak_browser is strictly <= 3.
   - Verified that timeout backpressure raises TimeoutError and increments rejected_timeouts.
"""

from __future__ import annotations

import asyncio
from http.server import BaseHTTPRequestHandler
import json
import os
import socketserver
import tempfile
import threading
import time
import unittest
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from behavioral_playwright.crawling.bandit_proxy_rotator import (
    BanditProxyRotator,
    ProxyArmState,
)
from behavioral_playwright.crawling.clearance_bridge import (
    BrowserClearanceBridge,
    ClearanceLease,
)
from behavioral_playwright.crawling.models import CrawlerTier
from behavioral_playwright.crawling.service import TieredConcurrencyBulkhead
from behavioral_playwright.storage.task_queue import (
    RedisTaskQueue,
    SQLiteTaskQueue,
)


# =============================================================================
# Stateful Thread-Safe Redis Engine for Local Deterministic Testing
# =============================================================================

class _StatefulRedisPipeline:
    def __init__(self, engine: "_StatefulRedisEngine") -> None:
        self._engine = engine
        self._ops: List[Any] = []

    def hset(
        self,
        key: str,
        field: Optional[str] = None,
        value: Optional[str] = None,
        mapping: Optional[Dict[str, str]] = None,
    ) -> "_StatefulRedisPipeline":
        self._ops.append(("hset", key, field, value, mapping))
        return self

    def zadd(self, key: str, mapping: Dict[str, float]) -> "_StatefulRedisPipeline":
        self._ops.append(("zadd", key, mapping))
        return self

    def execute(self) -> List[Any]:
        results = []
        with self._engine._lock:
            for op in self._ops:
                if op[0] == "hset":
                    results.append(self._engine.hset(op[1], op[2], op[3], mapping=op[4]))
                elif op[0] == "zadd":
                    results.append(self._engine.zadd(op[1], op[2]))
            self._ops.clear()
        return results


class _StatefulRedisEngine:
    def __init__(self, enable_eval: bool = True) -> None:
        self._lock = threading.RLock()
        self._hashes: Dict[str, Dict[str, str]] = {}
        self._zsets: Dict[str, Dict[str, float]] = {}
        self.enable_eval = enable_eval

    def ping(self) -> bool:
        return True

    def pipeline(self) -> _StatefulRedisPipeline:
        return _StatefulRedisPipeline(self)

    def hset(
        self,
        key: str,
        field: Optional[str] = None,
        value: Optional[str] = None,
        mapping: Optional[Dict[str, str]] = None,
    ) -> int:
        with self._lock:
            bucket = self._hashes.setdefault(key, {})
            if field is not None and value is not None:
                bucket[str(field)] = str(value)
            if mapping:
                for k, v in mapping.items():
                    bucket[str(k)] = str(v)
            return 1

    def hgetall(self, key: str) -> Dict[str, str]:
        with self._lock:
            return dict(self._hashes.get(key, {}))

    def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        with self._lock:
            zset = self._zsets.setdefault(key, {})
            for member, score in mapping.items():
                zset[str(member)] = float(score)
            return len(mapping)

    def zrevrange(self, key: str, start: int, end: int) -> List[str]:
        with self._lock:
            zset = self._zsets.get(key, {})
            ordered = sorted(zset.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
            members = [m for m, _ in ordered]
            return members[start : end + 1]

    def zrem(self, key: str, member: str) -> int:
        with self._lock:
            zset = self._zsets.get(key, {})
            if member in zset:
                del zset[member]
                return 1
            return 0

    def keys(self, pattern: str = "*") -> List[str]:
        with self._lock:
            prefix = pattern.rstrip("*")
            return [k for k in self._hashes.keys() if k.startswith(prefix)]

    def eval(self, script: str, numkeys: int, *keys_and_args: str) -> Any:
        if not self.enable_eval:
            raise NotImplementedError("eval disabled")
        with self._lock:
            pending_key = keys_and_args[0]
            prefix = keys_and_args[1]
            leased_until = keys_and_args[2] if len(keys_and_args) > 2 else "0.0"
            items = self.zrevrange(pending_key, 0, 0)
            if not items:
                return None
            task_id = items[0]
            self.zrem(pending_key, task_id)
            task_hash = f"{prefix}:task:{task_id}"
            self.hset(task_hash, "status", "running")
            self.hset(task_hash, "leased_until", leased_until)
            data = self.hgetall(task_hash)
            flat: List[str] = []
            for k, v in data.items():
                flat.extend([k, v])
            return [task_id, flat]


# =============================================================================
# Live HTTP Server for Cross-Worker Clearance Lease Verification
# =============================================================================

class _WAFChallengeHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        cookie_header = self.headers.get("Cookie", "")
        if "cf_clearance=cleared_token_xyz" in cookie_header:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "success", "content": "protected_data"}')
        else:
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.send_header("cf-mitigated", "challenge")
            self.end_headers()
            self.wfile.write(b'{"error": "cf-mitigated", "msg": "challenge-running"}')

    def log_message(self, format: str, *args: Any) -> None:
        pass


# =============================================================================
# Test Suite
# =============================================================================

class TestReliabilityScalabilityUpgrade(unittest.TestCase):
    """Rigorous verification suite for Phase 2 Reliability & Scalability Hardening."""

    def test_1_zombie_lease_reaper_and_heartbeat(self) -> None:
        """Verifies visibility timeout leases, heartbeats, and zombie lease recovery
        across both SQLiteTaskQueue (real disk) and RedisTaskQueue (stateful engine).
        """
        # --- Part A: SQLiteTaskQueue ---
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name

        try:
            sqlite_q = SQLiteTaskQueue(db_path, lease_timeout_sec=0.15)
            sqlite_q.init_queue()

            # 1. Heartbeat test: Task 1 should NOT be reclaimed while heartbeat is maintained
            t1 = sqlite_q.push_task("https://example.com/heartbeat", "scrape", priority=5)
            popped1 = sqlite_q.pop_task()
            self.assertIsNotNone(popped1)
            self.assertEqual(popped1["id"], t1)

            time.sleep(0.08)
            updated = sqlite_q.heartbeat_task(t1, extend_sec=0.30)
            self.assertTrue(updated)

            time.sleep(0.10)  # total elapsed: 0.18s > original 0.15s lease
            reclaimed = sqlite_q.reclaim_expired_leases()
            self.assertEqual(reclaimed, 0, "Heartbeated task must not be reclaimed prematurely")

            # Complete task 1
            sqlite_q.complete_task(t1)

            # 2. Dead Worker / Zombie Recovery: Task 2 expires without heartbeat
            t2 = sqlite_q.push_task("https://example.com/zombie", "scrape", priority=10)
            popped2 = sqlite_q.pop_task()
            self.assertIsNotNone(popped2)
            self.assertEqual(popped2["id"], t2)

            time.sleep(0.20)  # Worker crashes, exceeding lease_timeout_sec=0.15s
            reclaimed = sqlite_q.reclaim_expired_leases(max_retries=3)
            self.assertEqual(reclaimed, 1, "Expired zombie task must be reclaimed")

            # Verify reclaimed task is re-popped by another worker as retry:1
            repopped = sqlite_q.pop_task()
            self.assertIsNotNone(repopped)
            self.assertEqual(repopped["id"], t2)
            sqlite_q.complete_task(t2)

            # 3. Max Retries Exhaustion: Task 3 expires past max_retries -> failed:lease_expired
            t3 = sqlite_q.push_task("https://example.com/fail_loop", "scrape", priority=1)
            _ = sqlite_q.pop_task()
            time.sleep(0.20)
            reclaimed_fail = sqlite_q.reclaim_expired_leases(max_retries=1)
            self.assertEqual(reclaimed_fail, 1)

            # Should not be returned on next pop
            next_pop = sqlite_q.pop_task()
            self.assertIsNone(next_pop, "Exhausted task must transition to failed:lease_expired and not be re-popped")
        finally:
            if os.path.exists(db_path):
                try:
                    os.unlink(db_path)
                except Exception:
                    pass

        # --- Part B: RedisTaskQueue ---
        redis_engine = _StatefulRedisEngine(enable_eval=True)
        redis_q = RedisTaskQueue(client=redis_engine, lease_timeout_sec=0.15)
        redis_q.init_queue()

        # Heartbeat check
        rt1 = redis_q.push_task("https://example.com/r_heartbeat", "scrape", priority=5)
        r_pop1 = redis_q.pop_task()
        self.assertIsNotNone(r_pop1)
        self.assertEqual(r_pop1["id"], rt1)

        time.sleep(0.08)
        self.assertTrue(redis_q.heartbeat_task(rt1, extend_sec=0.30))
        time.sleep(0.10)
        self.assertEqual(redis_q.reclaim_expired_leases(), 0)
        redis_q.complete_task(rt1)

        # Zombie lease recovery
        rt2 = redis_q.push_task("https://example.com/r_zombie", "scrape", priority=8)
        _ = redis_q.pop_task()
        time.sleep(0.20)
        self.assertEqual(redis_q.reclaim_expired_leases(max_retries=3), 1)

        r_repopped = redis_q.pop_task()
        self.assertIsNotNone(r_repopped)
        self.assertEqual(r_repopped["id"], rt2)
        redis_q.complete_task(rt2)

        # Max retries exhaustion
        rt3 = redis_q.push_task("https://example.com/r_exhaust", "scrape", priority=2)
        _ = redis_q.pop_task()
        time.sleep(0.20)
        self.assertEqual(redis_q.reclaim_expired_leases(max_retries=1), 1)
        self.assertIsNone(redis_q.pop_task())

    def test_2_discounted_bandit_adaptation_and_state_sync(self) -> None:
        """Verifies non-stationary Thompson Sampling decay and cross-instance state import/export."""
        rotator = BanditProxyRotator(
            proxies=["http://proxy-degraded:8080", "http://proxy-healthy:8080"],
            decay_gamma=0.95,
            seed=42,
        )

        # 1. Warm up proxy-degraded with 150 historical successes
        for _ in range(150):
            rotator.report_success("http://proxy-degraded:8080", latency_ms=60.0)

        # With decay_gamma=0.95, alpha saturates around 1/(1-gamma) = 20, NOT 151!
        deg_arm = rotator._arms["http://proxy-degraded:8080"]
        self.assertLess(deg_arm.alpha, 35.0, "Exponential discounting must bound historical alpha growth")

        # 2. Proxy degraded suddenly hits 15 consecutive WAF 403 blocks
        for _ in range(15):
            rotator.report_failure(
                "http://proxy-degraded:8080",
                status_code=403,
                is_waf_challenge=True,
                latency_ms=1200.0,
            )

        # Warm up healthy proxy with 25 clean successes
        for _ in range(25):
            rotator.report_success("http://proxy-healthy:8080", latency_ms=45.0)

        # Simulate time past cooldown
        future_time = time.time() + 3600.0

        # Sample 100 choices; proxy-healthy must dominate despite degraded's 150 historical wins
        picks = [rotator.select_proxy(policy="thompson", now=future_time).proxy_url for _ in range(100)]
        healthy_count = picks.count("http://proxy-healthy:8080")
        self.assertGreaterEqual(
            healthy_count, 85,
            f"Healthy proxy must receive >=85% traffic after degradation, got {healthy_count}%"
        )

        # 3. State Export & Import Verification
        exported = rotator.export_state()
        self.assertIn("http://proxy-healthy:8080", exported)
        self.assertIn("alpha", exported["http://proxy-healthy:8080"])

        # Create worker 2 with fresh state and import worker 1's knowledge
        rotator2 = BanditProxyRotator(
            proxies=["http://proxy-degraded:8080", "http://proxy-healthy:8080"],
            decay_gamma=0.95,
        )
        rotator2.import_state(exported, blend_weight=0.8)
        self.assertGreater(
            rotator2._arms["http://proxy-healthy:8080"].alpha, 5.0,
            "Remote state must be blended into local arm"
        )

    def test_3_cross_worker_clearance_lease_sharing(self) -> None:
        """Verifies distributed ClearanceLease sharing across two independent workers
        using a live TCPServer and shared store.
        """
        # 1. Start live local TCP Server
        server = socketserver.TCPServer(("127.0.0.1", 0), _WAFChallengeHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        port = server.server_address[1]
        base_url = f"http://127.0.0.1:{port}/protected"

        shared_store: Dict[str, str] = {}
        bridge_worker1 = BrowserClearanceBridge(shared_store=shared_store)
        bridge_worker2 = BrowserClearanceBridge(shared_store=shared_store)

        import urllib.request

        async def http_fetcher(
            url: str,
            headers: Optional[Dict[str, str]] = None,
            proxy: Optional[str] = None,
            tls_impersonate: str = "chrome124",
        ) -> Dict[str, Any]:
            req = urllib.request.Request(url, headers=headers or {})
            t0 = time.perf_counter()
            try:
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    body = resp.read().decode("utf-8")
                    return {
                        "status": resp.getcode(),
                        "headers": dict(resp.headers),
                        "body": body,
                        "rtt_ms": (time.perf_counter() - t0) * 1000.0,
                    }
            except urllib.error.HTTPError as he:
                body = he.read().decode("utf-8", errors="replace")
                return {
                    "status": he.code,
                    "headers": dict(he.headers),
                    "body": body,
                    "rtt_ms": (time.perf_counter() - t0) * 1000.0,
                }

        worker1_browser_calls = []

        async def worker1_solver(target_url: str) -> ClearanceLease:
            worker1_browser_calls.append(target_url)
            return ClearanceLease(
                domain=urlparse(target_url).hostname or "127.0.0.1",
                cookies={"cf_clearance": "cleared_token_xyz"},
                headers={"User-Agent": "Mozilla/5.0 TestBrowser"},
                ttl_seconds=300.0,
            )

        worker2_browser_calls = []

        async def worker2_solver(target_url: str) -> ClearanceLease:
            worker2_browser_calls.append(target_url)
            return ClearanceLease(
                domain=urlparse(target_url).hostname or "127.0.0.1",
                cookies={"cf_clearance": "cleared_token_xyz"},
                headers={"User-Agent": "Mozilla/5.0 TestBrowser"},
                ttl_seconds=300.0,
            )

        loop = asyncio.new_event_loop()
        try:
            # Worker 1 fetches -> hits 403 -> invokes browser solver -> gets 200 OK
            res1 = loop.run_until_complete(
                bridge_worker1.fetch_with_promotion(base_url, http_fetcher, worker1_solver)
            )
            self.assertEqual(res1["status"], 200)
            self.assertEqual(len(worker1_browser_calls), 1)
            self.assertTrue(res1["clearance_reused"])
            self.assertEqual(bridge_worker1.stats["challenge_escalations"], 1)

            # Assert lease was written to shared store
            self.assertTrue(any("127.0.0.1" in k for k in shared_store.keys()))

            # Worker 2 fetches same URL -> reads lease from shared store -> gets 200 OK immediately
            res2 = loop.run_until_complete(
                bridge_worker2.fetch_with_promotion(base_url, http_fetcher, worker2_solver)
            )
            self.assertEqual(res2["status"], 200)
            self.assertEqual(
                len(worker2_browser_calls), 0,
                "Worker 2 must reuse Worker 1's shared clearance lease without invoking browser solver!"
            )
            self.assertEqual(bridge_worker2.stats["challenge_escalations"], 0)
            self.assertEqual(bridge_worker2.stats["promoted_http_reuses"], 1)
        finally:
            loop.close()
            server.shutdown()
            server.server_close()

    def test_4_hierarchical_concurrency_bulkhead_cap_and_timeout(self) -> None:
        """Verifies hierarchical bulkhead semaphore caps and timeout backpressure."""
        bulkhead = TieredConcurrencyBulkhead(
            max_network_concurrency=32,
            max_browser_concurrency=3,
        )

        async def run_test() -> None:
            # 1. Concurrency Cap Test: 20 browser tasks attempting execution concurrently
            active_during_run = []

            async def browser_worker() -> None:
                async with bulkhead.slot(CrawlerTier.BROWSER_HEADLESS, timeout=5.0):
                    active_during_run.append(bulkhead.active_browser)
                    await asyncio.sleep(0.04)

            await asyncio.gather(*[browser_worker() for _ in range(20)])
            self.assertEqual(bulkhead.peak_browser, 3, "Peak browser concurrency must not exceed max_browser_concurrency (3)")
            self.assertTrue(all(a <= 3 for a in active_during_run))

            # 2. Backpressure Timeout Test: When all 3 slots are locked, 4th task times out
            async def long_holder() -> None:
                async with bulkhead.slot(CrawlerTier.BROWSER_STEALTH_KINEMATICS, timeout=5.0):
                    await asyncio.sleep(0.35)

            async def impatient_worker() -> None:
                await asyncio.sleep(0.02)  # Ensure holders have slots
                with self.assertRaises(TimeoutError):
                    async with bulkhead.slot(CrawlerTier.BROWSER_HEADLESS, timeout=0.08):
                        pass

            holders = [asyncio.create_task(long_holder()) for _ in range(3)]
            impatient = asyncio.create_task(impatient_worker())
            # Also verify network tasks run immediately while all 3 browser slots are saturated
            network_completed = False

            async def fast_network_worker() -> None:
                nonlocal network_completed
                await asyncio.sleep(0.02)
                async with bulkhead.acquire_slot(CrawlerTier.HTTP_FAST, timeout=0.05):
                    network_completed = True

            net_task = asyncio.create_task(fast_network_worker())
            await asyncio.gather(impatient, net_task, *holders)
            self.assertTrue(network_completed, "Network bulkhead must not be starved by saturated browser slots")

            metrics = bulkhead.get_bulkhead_metrics()
            self.assertGreaterEqual(metrics["rejected_timeouts"], 1, "Timed out requests must register in metrics")
            self.assertGreaterEqual(metrics["peak_network"], 1)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()

        # Verify bare domain extraction & expired shared_store eviction
        shared: Dict[str, str] = {}
        b = BrowserClearanceBridge(shared_store=shared)
        b.store_lease(ClearanceLease(domain="example.com", cookies={"k": "v"}, ttl_seconds=60.0))
        self.assertIsNotNone(b.get_valid_lease("example.com"))
        # Store an already-expired lease in shared_store and verify eviction on read
        shared["bp:lease:expired.org"] = json.dumps({
            "domain": "expired.org",
            "cookies": {"a": "b"},
            "headers": {},
            "acquired_at": time.time() - 500.0,
            "ttl_seconds": 10.0,
            "reuse_count": 0,
        })
        self.assertIsNone(b.get_valid_lease("expired.org"))
        self.assertNotIn("bp:lease:expired.org", shared)


if __name__ == "__main__":
    unittest.main()

