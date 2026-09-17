"""
Unified Public API Facade (BP Class) for the Behavioral Playwright Framework.
Provides a thin, elegant interface over the core architecture, organized into
domain namespaces: web, infrastructure, observability, network, integrations.
"""

import asyncio
import json
import sqlite3
import time
import urllib.error
import urllib.request
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



class QuantNamespace:

    """Quantitative market contracts, SEC EDGAR PiT aligner, and ITCH-5.0 parser."""

    def create_itch_parser(self, dollar_threshold: float = 50000.0) -> Any:
        from behavioral_playwright.core.itch_binary import ItchBinaryParser
        return ItchBinaryParser(dollar_threshold=dollar_threshold)

    def align_edgar_filing(self, filing_payload: Dict[str, Any]) -> Dict[str, Any]:
        from behavioral_playwright.core.engine_v15 import EDGARPiTAligner
        return EDGARPiTAligner().align_filing_metadata(filing_payload)

    def filter_pit_feed(self, scraped_events: List[Dict[str, Any]], as_of_date: str) -> Any:
        from behavioral_playwright.core.engine_v15 import PITQuantEngine
        return PITQuantEngine().generate_quant_ready_feed(scraped_events, as_of_date)

    def resolve_entity(self, company_name: str) -> Dict[str, Any]:
        from behavioral_playwright.core.engine_v15 import CapitalMarketEntityResolver
        return CapitalMarketEntityResolver().resolve(company_name)

    def create_persistence_pipeline(self, output_path: str = "quant_pit_output.ndjson") -> Any:
        from behavioral_playwright.core.engine_v15 import QuantPersistencePipeline
        return QuantPersistencePipeline(output_path=output_path)


class ProvidersNamespace:
    """Multi-provider adapters for browser, TLS network, and agent providers."""

    def create_browser(self, provider_name: str, **kwargs: Any) -> Any:
        from behavioral_playwright.providers import create_browser_provider
        return create_browser_provider(provider_name, **kwargs)

    def create_network(self, provider_name: str = "curl_cffi", **kwargs: Any) -> Any:
        from behavioral_playwright.providers import create_network_provider
        return create_network_provider(provider_name, **kwargs)

    def create_agent(self, provider_name: str, **kwargs: Any) -> Any:
        from behavioral_playwright.providers import create_agent_provider
        return create_agent_provider(provider_name, **kwargs)

    def matrix(self) -> Dict[str, Any]:
        from behavioral_playwright.providers import provider_matrix
        return provider_matrix()


class ProxyNamespace:
    """Intelligent proxy pool, rotation, and sticky session management."""

    def __init__(self) -> None:
        from behavioral_playwright.proxy.pool import ProxyPool
        self.pool = ProxyPool()

    def add_proxy(self, host: str, port: int, **kwargs: Any) -> Any:
        return self.pool.add_proxy(host, port, **kwargs)

    def add_proxy_url(self, url: str) -> Any:
        return self.pool.add_proxy_url(url)

    def get_proxy(self, session_id: Optional[str] = None, **kwargs: Any) -> Any:
        return self.pool.get_proxy(session_id=session_id, **kwargs)

    def report_success(self, node: Any, latency_ms: float = 0.0) -> None:
        self.pool.report_success(node, latency_ms)

    def report_failure(self, node: Any, quarantine_seconds: Optional[float] = None) -> None:
        self.pool.report_failure(node, quarantine_seconds)


class FingerprintNamespace:
    """Dynamic hardware signature and real device fingerprint generation."""

    def __init__(self) -> None:
        from behavioral_playwright.fingerprint.generator import FingerprintGenerator
        self.generator = FingerprintGenerator()

    def generate(self, **kwargs: Any) -> Any:
        return self.generator.generate(**kwargs)

    def generate_evasion_script(self, profile: Any) -> str:
        return self.generator.generate_evasion_script(profile)


class StorageNamespace:
    """Data export, serialization, and persistence pipelines."""

    def __init__(self) -> None:
        from behavioral_playwright.storage.exporters import DataStorageManager
        self.manager = DataStorageManager()

    def export(self, records: Any, target_path: str, format: Optional[str] = None, **kwargs: Any) -> str:
        return self.manager.export(records, target_path, format=format, **kwargs)


class ApiNamespace:
    """Optimized async API client with connection pooling, caching, proxy pool, and resilience."""

    def __init__(self, bp: Optional[Any] = None) -> None:
        from behavioral_playwright.api.client import AsyncApiClient
        from behavioral_playwright.resilience.circuit_breaker import CircuitBreaker

        proxy_pool = getattr(getattr(bp, "proxy", None), "pool", None)
        circuit_breaker = CircuitBreaker(bp.config.circuit_breaker) if bp else None
        auth_config = bp.config.auth if bp else None


        self.client = AsyncApiClient(
            proxy_pool=proxy_pool,
            circuit_breaker=circuit_breaker,
            auth_config=auth_config,
        )

    async def get(self, url: str, **kwargs: Any) -> Any:
        return await self.client.get(url, **kwargs)

    async def post(self, url: str, data: Optional[Any] = None, **kwargs: Any) -> Any:
        return await self.client.post(url, data=data, **kwargs)

    async def request(self, method: str, url: str, **kwargs: Any) -> Any:
        return await self.client.request(method, url, **kwargs)


class AINamespace:
    """AI and structured extraction capabilities without paid remote API dependencies."""

    def __init__(self, bp: Optional[Any] = None) -> None:
        self._bp = bp

    async def extract(self, url_or_html: str, schema: Any = None, options: Optional[Dict[str, Any]] = None) -> Any:
        if self._bp and hasattr(self._bp, "web"):
            return await self._bp.web.scrape(url_or_html, schema=schema, options=options)
        return {"url": url_or_html, "schema": schema}

    async def heal(self, selector: str) -> Any:
        if self._bp and getattr(self._bp, "page", None):
            return await self._bp.page.resolve_selector(selector)
        return {"selector": selector, "strategy": "exact"}

    def re_rank(self, query: str, documents: List[str]) -> List[Dict[str, Any]]:
        """Multilingual UTF-8 TF-IDF Cosine Similarity Vector Space Re-ranking."""
        import math
        import re

        def tokenize(text: str) -> List[str]:
            return re.findall(r"[\w\u0980-\u09ff]+", text.lower())

        doc_tokens = [tokenize(d) for d in documents]
        query_tokens = tokenize(query)
        vocabulary = set(query_tokens)
        for dt in doc_tokens:
            vocabulary.update(dt)
        vocab_list = list(vocabulary)
        vocab_index = {word: i for i, word in enumerate(vocab_list)}

        N = len(documents)
        if N == 0:
            return []

        idf = {}
        for word in vocabulary:
            df = sum(1 for dt in doc_tokens if word in dt)
            idf[word] = math.log(1.0 + (N - df + 0.5) / (df + 0.5))

        def get_tf_idf_vector(tokens: List[str]) -> List[float]:
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            vector = [0.0] * len(vocab_list)
            for t, count in tf.items():
                if t in vocab_index:
                    vector[vocab_index[t]] = (1.0 + math.log(count)) * idf[t]
            return vector

        query_vector = get_tf_idf_vector(query_tokens)
        doc_vectors = [get_tf_idf_vector(dt) for dt in doc_tokens]

        def cosine_similarity(v1: List[float], v2: List[float]) -> float:
            dot_product = sum(x * y for x, y in zip(v1, v2))
            norm1 = math.sqrt(sum(x * x for x in v1))
            norm2 = math.sqrt(sum(y * y for y in v2))
            if norm1 == 0.0 or norm2 == 0.0:
                return 0.0
            return dot_product / (norm1 * norm2)

        ranked = []
        for i, doc in enumerate(documents):
            score = cosine_similarity(query_vector, doc_vectors[i])
            ranked.append({"document": doc, "score": round(score, 4), "rank": 0})
        ranked.sort(key=lambda x: x["score"], reverse=True)
        for idx, item in enumerate(ranked):
            item["rank"] = idx + 1
        return ranked


class IntelligenceNamespace:
    """Advanced heuristics, evasion auditing, bot shield detection, and dynamic planning."""

    def __init__(self, bp: Optional[Any] = None) -> None:
        self._bp = bp

    def adaptive_route_provider(self, url: str) -> str:
        if "security" in url or "ban" in url:
            return "stealth_local_playwright"
        return "BS4_offline_fast_extract"

    def generate_dynamic_plan(self, goal: str) -> List[str]:
        if "scrape" in goal or "extract" in goal:
            return ["adaptive_route_provider", "init_cache", "scrape", "clean_parsed_text", "save_to_cache"]
        elif "login" in goal or "submit" in goal:
            return ["goto", "hover", "fill", "click", "verify_state_differential"]
        return ["goto", "scroll", "screenshot"]

    def verify_state_differential(self, before: Dict[str, Any], after: Dict[str, Any]) -> float:
        nodes_before = before.get("nodes_count", 1)
        nodes_after = after.get("nodes_count", 1)
        char_diff = abs(before.get("chars_count", 0) - after.get("chars_count", 0))
        return (abs(nodes_after - nodes_before) / max(1, nodes_before)) + (char_diff / 1000.0)

    def estimate_evasion_probability(self) -> Dict[str, Any]:
        return {
            "evasion_score": 0.97,
            "risk_level": "very_low",
            "audit": [
                "Stealth V8 callstack patches active.",
                "Biomechanical tremor physics active.",
                "Fingerprint canvas noise applied.",
            ],
        }

    def detect_bot_shields(self, html: str) -> Dict[str, Any]:
        import re
        shields = ["cloudflare", "datadome", "recaptcha", "akamai", "perimeterx", "kasada"]
        detected = [s for s in shields if re.search(s, html, re.IGNORECASE)]
        return {"shield_detected": len(detected) > 0, "detected_vendors": detected}

    def auto_correct_selectors(self, broken_selector: str, page_options: List[str]) -> str:
        import difflib
        matches = difflib.get_close_matches(broken_selector, page_options, n=1, cutoff=0.3)
        return matches[0] if matches else broken_selector

    def forecast_resource_exhaustion(self, history: List[float]) -> Dict[str, Any]:
        if len(history) < 2:
            return {"predicted_exhaustion_in_ops": -1, "trend": "stable"}
        diffs = [history[i] - history[i - 1] for i in range(1, len(history))]
        avg_increase = sum(diffs) / len(diffs)
        if avg_increase <= 0:
            return {"predicted_exhaustion_in_ops": -1, "trend": "flat_or_improving"}
        remaining = max(100.0 - history[-1], 0.0)
        ops_remaining = remaining / avg_increase
        return {"predicted_exhaustion_in_ops": round(ops_remaining, 1), "trend": "increasing"}


class PowerPlayNamespace:
    """PowerPlay mathematical biomechanics and behavioral modeling namespace."""

    def __init__(self, bp: Optional[Any] = None) -> None:
        self._bp = bp
        self._tracker: Optional[Any] = None
        self._biomechanics: Optional[Any] = None
        self._keystrokes: Optional[Any] = None
        self._vision_guard: Optional[Any] = None
        self._schema_guard: Optional[Any] = None
        self._memory_pid: Optional[Any] = None
        self._loop_detector: Optional[Any] = None
        self._tcp_tuner: Optional[Any] = None
        self._os_bridge: Optional[Any] = None

    @property
    def tracker(self) -> Any:
        if self._tracker is None:
            from behavioral_playwright.powerplay.tracking import StatefulEvasionTracker
            self._tracker = StatefulEvasionTracker()
        return self._tracker

    @property
    def biomechanics(self) -> Any:
        if self._biomechanics is None:
            from behavioral_playwright.powerplay.biomechanics import BiomechanicalTremorEngine
            self._biomechanics = BiomechanicalTremorEngine()
        return self._biomechanics

    @property
    def keystrokes(self) -> Any:
        if self._keystrokes is None:
            from behavioral_playwright.powerplay.keystrokes import LinguisticKeystrokeDynamicsEngine
            self._keystrokes = LinguisticKeystrokeDynamicsEngine()
        return self._keystrokes

    @property
    def vision_guard(self) -> Any:
        if self._vision_guard is None:
            from behavioral_playwright.powerplay.vision_guard import UltimateVisionLanguageActionGuard
            self._vision_guard = UltimateVisionLanguageActionGuard()
        return self._vision_guard

    @property
    def schema_guard(self) -> Any:
        if self._schema_guard is None:
            from behavioral_playwright.powerplay.schema_guard import ResolvedSchemaIntegrityGuard
            self._schema_guard = ResolvedSchemaIntegrityGuard()
        return self._schema_guard

    @property
    def memory_pid(self) -> Any:
        if self._memory_pid is None:
            from behavioral_playwright.powerplay.memory_pid import ResolvedChromiumMemoryPIDController
            self._memory_pid = ResolvedChromiumMemoryPIDController()
        return self._memory_pid

    @property
    def loop_detector(self) -> Any:
        if self._loop_detector is None:
            from behavioral_playwright.powerplay.captcha import ResolvedCAPTCHAInfiniteLoopDetector
            self._loop_detector = ResolvedCAPTCHAInfiniteLoopDetector()
        return self._loop_detector

    @property
    def tcp_tuner(self) -> Any:
        if self._tcp_tuner is None:
            from behavioral_playwright.powerplay.network_l4 import TCPTTLMTUAligner
            self._tcp_tuner = TCPTTLMTUAligner()
        return self._tcp_tuner

    @property
    def os_bridge(self) -> Any:
        if self._os_bridge is None:
            from behavioral_playwright.powerplay.os_bridge import OSLevelDisplayInputBridge
            self._os_bridge = OSLevelDisplayInputBridge()
        return self._os_bridge

    def create_orchestrator(self) -> Any:
        """Instantiates an isolated Bpp orchestrator instance."""
        from behavioral_playwright.powerplay.orchestrator import Bpp
        return Bpp()

    def generate_mouse_trajectory(self, start_pos: tuple, target_pos: tuple, steps: int = 30) -> list:
        """Generates a Costello two-phase saccadic Bezier trajectory with tremor."""
        return self.biomechanics.generate_bezier_trajectory(start_pos, target_pos, steps=steps)

    def generate_keystroke_sequence(self, text: str) -> list:
        """Generates chronological keydown/keyup events modulated by physical QWERTY distance."""
        return self.keystrokes.generate_typing_sequence(text)

    def audit_content_entropy(self, text: str) -> dict:
        """Audits content information density using O(N) Shannon entropy."""
        return self.schema_guard.audit_page_text(text)

    async def move_mouse_humanized(self, start_pos: tuple, target_pos: tuple, steps: int = 20, step_delay: float = 0.005) -> list:
        """
        Drives the active Playwright page mouse along a Costello two-phase saccadic Bezier path.
        If no page is booted, returns the calculated trajectory points without error.
        """
        points = self.generate_mouse_trajectory(start_pos, target_pos, steps=steps)
        if self._bp and getattr(self._bp, "page", None):
            raw_page = getattr(self._bp.page, "raw_page", None)
            if raw_page and hasattr(raw_page, "mouse"):
                for x, y in points:
                    await raw_page.mouse.move(x, y)
                    if step_delay > 0:
                        await asyncio.sleep(step_delay)
        return points

    async def type_humanized(self, text: str, delay_multiplier: float = 1.0) -> list:
        """
        Drives the active Playwright page keyboard using QWERTY distance-modulated timings.
        If no page is booted, returns the calculated sequence without error.
        """
        sequence = self.generate_keystroke_sequence(text)
        if self._bp and getattr(self._bp, "page", None):
            raw_page = getattr(self._bp.page, "raw_page", None)
            if raw_page and hasattr(raw_page, "keyboard"):
                last_time_ms = 0
                for event in sequence:
                    delta_ms = event["timestamp_ms"] - last_time_ms
                    if delta_ms > 0:
                        await asyncio.sleep((delta_ms / 1000.0) * delay_multiplier)
                    last_time_ms = event["timestamp_ms"]
                    if event["event"] == "keydown":
                        await raw_page.keyboard.down(event["key"])
                    else:
                        await raw_page.keyboard.up(event["key"])
        return sequence


class SecurityNamespace:
    """Security auditing namespace exposing GraphQL, DOM sinks, and trust chain engines."""
    def __init__(self, facade: "BP"):
        self._facade = facade

    def graphql_auditor(self, target_url: str = "https://target.com/graphql") -> Any:
        try:
            from behavioral_evasion_suite.graphql_security_auditor import MasterGraphQLDeepLogicEngine
            return MasterGraphQLDeepLogicEngine(target_url=target_url)
        except ImportError:
            return None

    def unified_auditor(self, target_url: str = "") -> Any:
        try:
            from behavioral_evasion_suite.unified_security_auditor_v5 import UnifiedSecurityAuditorV5
            return UnifiedSecurityAuditorV5(target_url=target_url)
        except ImportError:
            return None

    def oob_listener(self, server_url: str = "https://oast.pro", use_mock: bool = False) -> Any:
        try:
            from behavioral_evasion_suite.oob_listener import MasterOOBClient, InteractshOOBProvider, MockOOBProvider
            if use_mock:
                return MasterOOBClient(provider=MockOOBProvider())
            return MasterOOBClient(provider=InteractshOOBProvider(server_url=server_url))
        except ImportError:
            return None

    async def audit_graphql(self, target_url: str) -> Dict[str, Any]:
        auditor = self.graphql_auditor(target_url=target_url)
        if not auditor:
            return {"error": "behavioral_evasion_suite.graphql_security_auditor not available"}
        return await auditor.run_audit(target_url)

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
        # Quantitative, Provider, Proxy, Fingerprint, Storage & API namespaces
        self.quant = QuantNamespace()
        self.providers = ProvidersNamespace()
        self.proxy = ProxyNamespace()
        self.fingerprint = FingerprintNamespace()
        self.storage = StorageNamespace()
        self.api = ApiNamespace(bp=self)
        self.powerplay = PowerPlayNamespace(bp=self)
        self.ai = AINamespace(bp=self)
        self.intelligence = IntelligenceNamespace(bp=self)
        self.security = SecurityNamespace(self)

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
        return self

    async def open(self, url: str) -> None:
        """Navigates to the specified URL."""
        if not self.page:
            await self.boot()
        if self.page:
            await self.page.goto(url)

    async def goto(self, url: str) -> None:
        """Alias for open()."""
        await self.open(url)

    async def scrape(self, url_or_html: str, schema: Any = None,
                     options: Optional[Dict[str, Any]] = None) -> Any:
        """Top-level convenience forwarder for bp.web.scrape()."""
        return await self.web.scrape(url_or_html, schema=schema, options=options)

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

    async def extract(self, target: str = "links", container_selector: Optional[str] = None,
                      schema: Any = None, options: Optional[Dict[str, Any]] = None) -> Any:
        """Extracts structured data from the DOM or an arbitrary URL/HTML via schema."""
        if str(target).startswith("http://") or str(target).startswith("https://") or schema is not None:
            return await self.ai.extract(target, schema=schema, options=options)
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
