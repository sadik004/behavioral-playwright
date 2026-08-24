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
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar
from types import SimpleNamespace

from behavioral_playwright.config.settings import AutomationConfig
from behavioral_playwright.page.session import BrowserSession, PageSession
from behavioral_playwright.models.results import ExtractionRecord
from behavioral_playwright.exceptions import ProviderUnavailableError

# Domain services (kept out of the facade to avoid a god object)
from behavioral_playwright.crawling.service import CrawlingService
from behavioral_playwright.document.ocr import DocumentNamespace
from behavioral_playwright.browser.actions import BrowserActionNamespace
from behavioral_playwright.observability.metrics import ObservabilityMetrics
from behavioral_playwright.integrations.extensions import IntegrationExtensions

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

    def __init__(self, bp: Any = None) -> None:
        self._bp = bp
        self.rate_limit_rpm: int = 60
        # Real crawling engine (extract/filter/sitemap/robots/crawl_recursive)
        self._crawler = CrawlingService()

    def __getattr__(self, name: str) -> Any:
        # Delegate crawling-domain calls to the service (crawl_recursive,
        # extract_links, filter_crawl_links, generate_sitemap, robots...).
        if name.startswith("__"):
            raise AttributeError(name)
        crawler = self.__dict__.get("_crawler")
        if crawler is None:
            raise AttributeError(name)

        # crawl_recursive needs a scrape_fn; bind the booted-facade scraper
        # automatically so callers can invoke it directly on bp.web.
        if name == "crawl_recursive":
            async def _crawl_recursive(url: str, max_depth: int = 3,
                                       db_path: str = "crawl_state.db",
                                       max_pages: Optional[int] = None,
                                       options: Optional[Dict[str, Any]] = None,
                                       **kwargs: Any) -> List[str]:
                if kwargs.get("scrape_fn") is None:
                    kwargs["scrape_fn"] = self._default_scrape_fn()
                return await crawler.crawl_recursive(
                    url, max_depth=max_depth, db_path=db_path,
                    max_pages=max_pages, options=options, **kwargs)
            return _crawl_recursive

        try:
            return getattr(crawler, name)
        except AttributeError:
            raise AttributeError(
                f"{type(self).__name__!s} has no attribute {name!r}") from None

    def _default_scrape_fn(self) -> Callable[[str, Optional[Dict[str, Any]]],
                                             Coroutine[Any, Any, Any]]:
        async def _scrape(target_url: str,
                          opts: Optional[Dict[str, Any]]) -> Any:
            # Late-bound: tests may replace bp.web.scrape with a mock after
            # construction, so resolve the attribute at call time.
            scrape = getattr(self, "scrape")
            return await scrape(target_url, options=opts)
        return _scrape

    async def scrape(self, url_or_html: str, schema: Any = None,
                     options: Optional[Dict[str, Any]] = None) -> Any:
        """Fetches a URL via the booted browser session and returns the page.

        The returned object exposes ``html``/``content`` for downstream
        extraction, matching the legacy AcquisitionResult contract.
        """
        bp = self._bp_ref()
        if bp is None or bp.page is None:
            raise ProviderUnavailableError(
                "Facade is not booted. Call bp.boot() first.")
        await bp.page.goto(url_or_html)
        html = await bp.page.evaluate("() => document.documentElement.outerHTML")
        return type("ScrapedPage", (), {"url": url_or_html, "html": html,
                                        "content": None})()

    def _bp_ref(self) -> Any:
        return getattr(self, "_bp", None)

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

    def __init__(self) -> None:
        # Legacy-compatible fine-grained metrics engine (metrics_log /
        # compliance_audit / session_replays tables, traces, QA report).
        self._metrics = ObservabilityMetrics()

    def __getattr__(self, name: str) -> Any:
        # Delegate metric APIs (init_metrics_db, log_execution, start_trace,
        # end_trace, get_average_duration, get_error_rate, audit_compliance_log,
        # save_session_replay_state, get_session_replays, _initialized_dbs...)
        return getattr(self._metrics, name)

    # Legacy-compatible signatures (url, operation, duration_ms, status,
    # db_path) — the refactored examples/autonomous_agent.py used a different
    # positional order, so both are supported via keyword-friendly design.
    def start_trace(self, trace_id: str, target: str = "",
                    db_path: str = "bp_metrics.db") -> None:
        self._metrics.start_trace(trace_id)
        self._ensure_legacy_db(db_path)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO traces VALUES (?, ?, ?, NULL)",
                (trace_id, target, time.strftime("%Y-%m-%dT%H:%M:%S")),
            )
            conn.commit()
        except sqlite3.OperationalError:
            pass  # traces table only exists in queue-schema DBs
        finally:
            conn.close()

    def end_trace(self, trace_id: str, target: str = "",
                  db_path: str = "bp_metrics.db", url: str = "",
                  ) -> float:
        target = url or target
        duration = self._metrics.end_trace(trace_id, url=target or "trace_log",
                                           db_path=db_path)
        self._ensure_legacy_db(db_path)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("UPDATE traces SET ended_at=?, target=? WHERE trace_id=?",
                         (time.strftime("%Y-%m-%dT%H:%M:%S"), target, trace_id))
            conn.commit()
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()
        return duration

    def log_execution(self, url_or_db: str, operation_or_trace: str,
                      duration_or_target: Any = None, status: Any = "success",
                      db_path: Any = None, action: str = "",
                      ) -> Any:
        """Dual-signature logger.

        Legacy form:  log_execution(url, operation, duration_ms, status, db_path)
        Facade form:  log_execution(db_path, trace_id, target, action, duration_ms, status)
        """
        if isinstance(status, int) and not isinstance(status, bool):
            # Facade form detected (status is an int here)
            db_path = url_or_db
            trace_id = operation_or_trace
            target = duration_or_target
            duration_ms = status
            status_str = str(db_path) if isinstance(db_path, str) else "success"
            real_status = action or "success"
            self._metrics.log_execution(target, f"{trace_id}:{action}",
                                        duration_ms, real_status,
                                        db_path=db_path)
            self._ensure_legacy_db(db_path)
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    "INSERT INTO executions VALUES (NULL, ?, ?, ?, ?, ?, ?)",
                    (trace_id, target, action, duration_ms, status_str,
                     time.strftime("%Y-%m-%dT%H:%M:%S")))
                conn.commit()
            except sqlite3.OperationalError:
                pass
            finally:
                conn.close()
            return None
        # Legacy form
        real_db = db_path if isinstance(db_path, str) else "bp_metrics.db"
        return self._metrics.log_execution(url_or_db, operation_or_trace,
                                           duration_or_target, status,
                                           db_path=real_db)

    def _ensure_legacy_db(self, db_path: str) -> None:
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS traces ("
                " trace_id TEXT PRIMARY KEY, target TEXT, "
                " started_at TEXT NOT NULL, ended_at TEXT)")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS executions ("
                " id INTEGER PRIMARY KEY AUTOINCREMENT, "
                " trace_id TEXT NOT NULL, target TEXT NOT NULL, "
                " action TEXT NOT NULL, duration_ms INTEGER NOT NULL, "
                " status TEXT NOT NULL, logged_at TEXT NOT NULL)")
            conn.commit()
            conn.close()
        except sqlite3.OperationalError:
            pass

    def generate_qa_report(self, db_path: str = "") -> Any:
        # Legacy dict contract takes precedence when a metrics DB is given.
        if isinstance(db_path, str) and db_path:
            try:
                dict_report = self._metrics.generate_qa_report(db_path=db_path)
                if dict_report.get("total_executed_ops", 0) > 0 or (
                        dict_report["compliance_violations_count"] > 0):
                    return dict_report
            except sqlite3.OperationalError:
                pass
            conn = sqlite3.connect(db_path)
            try:
                total, ok = conn.execute(
                    "SELECT COUNT(*), SUM(status='success') FROM executions"
                ).fetchone()
                avg_ms = conn.execute(
                    "SELECT AVG(duration_ms) FROM executions").fetchone()[0]
            except sqlite3.OperationalError:
                return self._metrics.generate_qa_report(db_path=db_path)
            finally:
                conn.close()
            rate = (ok / total * 100.0) if total else 0.0
            return (f"Executions: {total} | Success rate: {rate:.1f}% | "
                    f"Avg latency: {(avg_ms or 0):.1f} ms")
        return self._metrics.generate_qa_report()


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

    def __init__(self, bp: Any = None) -> None:
        self._bp = bp
        # n8n/MCP/health extensions (real HTTP + facade delegation)
        self._ext = IntegrationExtensions(bp)

    def notify_webhook(self, webhook_url: str, payload: Dict[str, Any],
                       timeout: float = 10.0) -> bool:
        if not str(webhook_url).lower().startswith(("http://", "https://")):
            raise ValueError(f"Invalid webhook URL schema: {webhook_url!r}")
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url, data=data,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp.read()
            return True
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Webhook rejected ({exc.code})") from exc

    def __getattr__(self, name: str) -> Any:
        # Delegate legacy APIs: n8n_webhook_trigger(_async), mcp_call_tool_async,
        # generate_mcp_manifest, integrations_health_check...
        return getattr(self._ext, name)


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
        # Internal state required by humanized browser actions
        self._humanizer: Any = None
        self._page: Any = None
        self._navigation_manager: Any = None
        # Domain namespaces (lazy DB paths are caller-managed)
        self.web = WebNamespace(bp=self)
        self.web._bp = self
        self.infrastructure = InfrastructureNamespace()
        self.observability = ObservabilityNamespace()
        self.network = NetworkNamespace()
        self.integrations = IntegrationsNamespace(bp=self)
        # Restored legacy-capability namespaces
        self.document = DocumentNamespace()
        self.browser = BrowserActionNamespace(self)
        self.metrics = ObservabilityMetrics()
        self.integrations_ext = IntegrationExtensions(self)

    async def boot(self) -> "BP":
        """Starts the browser session and initializes the first page."""
        if not self.session:
            self.session = BrowserSession(config=self.config,
                                          provider=self._provider)
            await self.session.start()

        if not self.page:
            self.page = await self.session.new_page()
        # Install internal refs consumed by the humanized browser namespace
        self._page = self.page
        self._humanizer = self._humanizer or SimpleNamespace(
            execute_safe_hover=None, execute_safe_click=None)
        # A plain booted marker: browser namespace falls back to page methods
        self._humanizer = object()  # truthy sentinel; methods looked up dynamically

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

    # -- restored legacy delegations ----------------------------------------
    async def crawl_recursive(self, url: str, max_depth: int = 3,
                              db_path: str = "crawl_state.db",
                              max_pages: Optional[int] = None,
                              options: Optional[Dict[str, Any]] = None
                              ) -> List[str]:
        """Delegates to the crawling service using the booted page scraper."""
        async def _scrape(target_url: str, opts: Optional[Dict[str, Any]]) -> Any:
            return await self.web.scrape(target_url, options=opts)
        return await self.web._crawler.crawl_recursive(
            url, max_depth=max_depth, db_path=db_path,
            max_pages=max_pages, options=options, scrape_fn=_scrape)

    async def ocr_image(self, file_path: str) -> Dict[str, Any]:
        return await self.document.ocr_image(file_path)

    async def ocr_image_with_autocorrect(self, file_path: str) -> Dict[str, Any]:
        return await self.document.ocr_image_with_autocorrect(file_path)

    async def mcp_call_tool(self, tool_name: str,
                            arguments: Dict[str, Any]) -> Any:
        return await self.integrations_ext.mcp_call_tool_async(
            tool_name, arguments)

    async def n8n_webhook_trigger(self, webhook_url: str,
                                  payload: Dict[str, Any],
                                  timeout: float = 10.0) -> bool:
        return await self.integrations_ext.n8n_webhook_trigger_async(
            webhook_url, payload, timeout)

    # Humanized browser action passthroughs
    async def hover(self, selector: str) -> bool:
        return await self.browser.hover(selector)

    async def drag_and_drop(self, source_selector: str,
                            target_selector: str) -> bool:
        return await self.browser.drag_and_drop(source_selector,
                                                target_selector)

    async def check_checkbox(self, selector: str, checked: bool = True) -> bool:
        return await self.browser.check_checkbox(selector, checked)

    async def check(self, selector: str) -> bool:
        return await self.browser.check(selector)

    async def uncheck(self, selector: str) -> bool:
        return await self.browser.uncheck(selector)

    async def select_option(self, selector: str, value: str) -> bool:
        return await self.browser.select_option(selector, value)

    async def keyboard_press(self, selector: str, key: str) -> bool:
        return await self.browser.keyboard_press(selector, key)

    async def press(self, selector: str, key: str) -> bool:
        return await self.browser.press(selector, key)
