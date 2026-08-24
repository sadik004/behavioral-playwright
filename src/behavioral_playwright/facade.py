"""
Unified Public API Facade (BP Class) for the Behavioral Playwright Framework.
Provides a thin, elegant interface over the core architecture, organized into
domain namespaces: web, infrastructure, observability, network, integrations.
"""

import asyncio
import json
import re
import sqlite3
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, TypeVar

from behavioral_playwright.config.settings import AutomationConfig
from behavioral_playwright.page.session import BrowserSession, PageSession
from behavioral_playwright.models.results import ExtractionRecord

T = TypeVar("T")

_SCHEMA = """
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


class WebNamespace:
    """Crawl session state and link utilities backed by SQLite."""

    def __init__(self) -> None:
        self.rate_limit_rpm: int = 60

    def init_crawl_session(self, db_path: str = "crawl_state.db") -> None:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS crawl_state ("
                " url TEXT PRIMARY KEY, status TEXT, depth INTEGER, "
                " updated_at TEXT)"
            )
            conn.commit()
        finally:
            conn.close()

    def save_crawl_state(self, db_path: str, url: str,
                         status: str = "completed", depth: int = 0) -> None:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO crawl_state VALUES (?, ?, ?, ?)",
                (url, status, depth, time.strftime("%Y-%m-%dT%H:%M:%S")),
            )
            conn.commit()
        finally:
            conn.close()

    def recover_crawl_session(self, db_path: str) -> List[str]:
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                "SELECT url FROM crawl_state WHERE status='pending'"
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()

    def set_rate_limit(self, rpm: int) -> None:
        self.rate_limit_rpm = max(1, rpm)


class InfrastructureNamespace:
    """SQLite WAL-mode priority task queue with retry accounting."""

    def init_queue(self, db_path: str = "bp_tasks.db") -> None:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def push_task(self, db_path: str, url: str, operation: str,
                  priority: int = 0) -> int:
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.execute(
                "INSERT INTO tasks (url, operation, priority, created_at)"
                " VALUES (?, ?, ?, ?)",
                (url, operation, priority, time.strftime("%Y-%m-%dT%H:%M:%S")),
            )
            conn.commit()
            return int(cur.lastrowid)
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
                conn.execute("UPDATE tasks SET status='running' WHERE id=?",
                             (row[0],))
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
            retries = conn.execute(
                "SELECT COALESCE(SUBSTR(status, 8), '') FROM tasks WHERE id=?",
                (task_id,)).fetchone()[0]
            attempt = len(retries) + 1
            if attempt >= max_retries:
                conn.execute("UPDATE tasks SET status='failed' WHERE id=?",
                             (task_id,))
            else:
                conn.execute("UPDATE tasks SET status=? WHERE id=?",
                             (f"retry:{attempt}", task_id))
            conn.commit()
        finally:
            conn.close()


class ObservabilityNamespace:
    """Execution tracing and QA reporting backed by SQLite."""

    def start_trace(self, db_path: str, trace_id: str, target: str) -> None:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO traces VALUES (?, ?, ?, NULL)",
                (trace_id, target, time.strftime("%Y-%m-%dT%H:%M:%S")),
            )
            conn.commit()
        finally:
            conn.close()

    def end_trace(self, db_path: str, trace_id: str, target: str) -> None:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("UPDATE traces SET ended_at=?, target=? WHERE trace_id=?",
                         (time.strftime("%Y-%m-%dT%H:%M:%S"), target, trace_id))
            conn.commit()
        finally:
            conn.close()

    def log_execution(self, db_path: str, trace_id: str, target: str,
                      action: str, duration_ms: int, status: str) -> None:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT INTO executions VALUES (NULL, ?, ?, ?, ?, ?, ?)",
                (trace_id, target, action, duration_ms, status,
                 time.strftime("%Y-%m-%dT%H:%M:%S")),
            )
            conn.commit()
        finally:
            conn.close()

    def generate_qa_report(self, db_path: str) -> str:
        conn = sqlite3.connect(db_path)
        try:
            total, ok = conn.execute(
                "SELECT COUNT(*), SUM(status='success') FROM executions"
            ).fetchone()
            avg_ms = conn.execute(
                "SELECT AVG(duration_ms) FROM executions").fetchone()[0]
        finally:
            conn.close()
        rate = (ok / total * 100.0) if total else 0.0
        return (f"Executions: {total} | Success rate: {rate:.1f}% | "
                f"Avg latency: {(avg_ms or 0):.1f} ms")


class NetworkNamespace:
    """Real HTTP latency measurement via HEAD requests."""

    def __init__(self) -> None:
        self._timeout_ms: int = 30000
        self._custom_headers: Dict[str, str] = {}

    def set_timeout(self, timeout_ms: int) -> None:
        self._timeout_ms = timeout_ms

    def set_custom_headers(self, headers: Dict[str, str]) -> None:
        self._custom_headers = dict(headers)

    def measure_response_time(self, url: str, timeout: Optional[float] = None) -> float:
        """Measures HTTP HEAD roundtrip latency in ms.

        HTTP error statuses (4xx/5xx) still count as a completed roundtrip.
        """
        if not url.lower().startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL schema: {url!r}")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                   **self._custom_headers}
        req = urllib.request.Request(url, method="HEAD", headers=headers)
        effective_timeout = (timeout if timeout is not None
                             else self._timeout_ms / 1000.0)
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
                resp.read(0)
        except urllib.error.HTTPError:
            pass  # 4xx/5xx still prove the roundtrip completed
        return (time.perf_counter() - start) * 1000.0

    async def measure_response_time_async(self, url: str,
                                          timeout: Optional[float] = None) -> float:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self.measure_response_time(url, timeout))


class IntegrationsNamespace:
    """JSON webhook notifications (Slack/Discord/n8n compatible)."""

    def notify_webhook(self, webhook_url: str, payload: Dict[str, Any],
                       timeout: float = 10.0) -> bool:
        if not str(webhook_url).lower().startswith(("http://", "https://")):
            raise ValueError(f"Invalid webhook URL schema: {webhook_url!r}")
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp.read()
            return True
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Webhook rejected ({exc.code})") from exc


class BP:
    """
    Unified high-level facade orchestrating the Behavioral Playwright framework.
    Provides a simplified public API while maintaining structural integrity.
    """

    def __init__(self, config: Optional[AutomationConfig] = None,
                 provider: Optional[Any] = None) -> None:
        self.config = config or AutomationConfig()
        self._provider = provider
        self.session: Optional[BrowserSession] = None
        self.page: Optional[PageSession] = None
        # Domain namespaces (lazy DB paths are caller-managed)
        self.web = WebNamespace()
        self.infrastructure = InfrastructureNamespace()
        self.observability = ObservabilityNamespace()
        self.network = NetworkNamespace()
        self.integrations = IntegrationsNamespace()

    async def boot(self) -> "BP":
        """Starts the browser session and initializes the first page."""
        if not self.session:
            self.session = BrowserSession(config=self.config,
                                          provider=self._provider)
            await self.session.start()
        
        if not self.page:
            self.page = await self.session.new_page()
            
        return self

    async def open(self, url: str) -> None:
        """Navigates to the specified URL."""
        if not self.page:
            await self.boot()
        await self.page.goto(url)

    async def goto(self, url: str) -> None:
        """Alias for open()."""
        await self.open(url)

    async def click(self, selector: str) -> Any:
        """Executes a self-healing click on the target selector."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        return await self.page.click_healed(selector)

    async def type(self, selector: str, text: str) -> Any:
        """Executes a self-healing type into the target selector."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        return await self.page.type_healed(selector, text)

    async def fill(self, selector: str, text: str) -> Any:
        """Alias for type()."""
        return await self.type(selector, text)

    async def scroll(self, distance_y: float = 500) -> None:
        """Scrolls the page down by the specified distance."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        await self.page.scroll.down(distance=int(distance_y))

    async def screenshot(self, path: Optional[str] = None) -> bytes:
        """Captures a screenshot of the current page."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        return await self.page.screenshot(path=path)

    async def extract(self, target: str = "links", container_selector: Optional[str] = None) -> List[ExtractionRecord]:
        """Extracts structured data from the DOM."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        
        if target == "links":
            return await self.page.extract_links(container_selector)
        elif target == "articles":
            return await self.page.extract_articles(container_selector)
        else:
            raise ValueError(f"Extraction target '{target}' is not supported by DOMExtractor.")

    async def crawl(self, start_url: str, max_pages: int = 5) -> List[ExtractionRecord]:
        """Crawls starting from a URL and extracts data."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        from behavioral_playwright.crawling.crawler import Crawler
        crawler = Crawler(self.page)
        return await crawler.crawl(start_url, max_pages)

    async def search(self, query: str, search_input_selector: str = "input[type='search'], input[name='q']", submit_selector: str = "button[type='submit']") -> List[ExtractionRecord]:
        """Submits a search query and extracts the results."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        from behavioral_playwright.search.engine import SearchEngine
        engine = SearchEngine(self.page)
        return await engine.search(query, search_input_selector, submit_selector)

    async def map(self, url: str) -> Dict[str, Any]:
        """Maps out the structural links and articles of a page."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        from behavioral_playwright.mapping.mapper import SiteMapper
        mapper = SiteMapper(self.page)
        return await mapper.map(url)

    async def handoff(self, context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Exports or injects the current context state for handoff."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        from behavioral_playwright.handoff.session_handoff import SessionHandoff
        handoff_manager = SessionHandoff(self.page)
        return await handoff_manager.handoff(context_data)

    async def verify(self, 
                     state_before: Optional[Dict[str, Any]] = None, 
                     expected_title: Optional[str] = None,
                     expected_url: Optional[str] = None,
                     expected_element_selector: Optional[str] = None,
                     expected_text: Optional[str] = None) -> Dict[str, Any]:
        """Validates the current DOM/page state against expectations."""
        if not self.page:
            raise RuntimeError("BP is not booted. Call bp.boot() first.")
        from behavioral_playwright.verification.verifier import StateVerifier
        verifier = StateVerifier(self.page)
        return await verifier.verify(state_before, expected_title, expected_url, expected_element_selector, expected_text)

    async def close(self) -> None:
        """Gracefully closes the page and browser session."""
        if self.page:
            await self.page.close()
            self.page = None
        if self.session:
            await self.session.close()
            self.session = None

    async def __aenter__(self) -> "BP":
        await self.boot()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def measure_response_time_async(self, url: str) -> float:
        """Runs the blocking HTTP probe on a worker thread."""
        return await self.network.measure_response_time_async(url)

    def measure_response_time(self, url: str, timeout: Optional[float] = None) -> float:
        """Blocking HTTP HEAD latency probe (delegates to network namespace)."""
        return self.network.measure_response_time(url)

    async def slack_webhook_notify(self, webhook_url: str, message: str,
                                   timeout: float = 10.0) -> bool:
        """Posts a Slack-formatted webhook message off the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self.integrations.notify_webhook(
                webhook_url, {"text": message}, timeout))

    async def discord_webhook_notify(self, webhook_url: str, message: str,
                                     timeout: float = 10.0) -> bool:
        """Posts a Discord-formatted webhook message off the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self.integrations.notify_webhook(
                webhook_url, {"content": message}, timeout))
