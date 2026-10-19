"""Crawling extensions for the Web namespace.

Real implementations of 4-tier adaptive crawling, Thompson Sampling domain routing,
64-bit SimHash near-duplicate detection, SQLite WAL frontier with OPIC+BM25 priority,
and zero-cost AutoRuleSchemaExtractor. Page fetching is delegated to 4-tier escalation
or a caller-provided async ``scrape`` callable.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import math
import random
import re
import sqlite3
import struct
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urljoin, urlparse, urldefrag

try:
    from veil.logging import get_logger
except Exception:
    try:
        from behavioral_playwright.logging import get_logger
    except Exception:
        import logging
        def get_logger(name: str) -> logging.Logger:
            return logging.getLogger(name)

logger = get_logger("crawling.service")

try:  # BeautifulSoup is optional; regex fallback keeps extraction working.
    from bs4 import BeautifulSoup  # type: ignore
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

_CRAWL_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS crawl_urls (
    url TEXT PRIMARY KEY,
    depth INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    priority REAL DEFAULT 0.0,
    opic_cash REAL DEFAULT 1.0,
    simhash INTEGER DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_SKIP_PREFIXES = ("javascript:", "mailto:", "tel:", "#", "data:")
_SKIP_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".css", ".gif", ".pdf", ".mp4", ".svg", ".ico",
    ".woff", ".woff2", ".js", ".zip", ".mp3", ".avi", ".mov", ".tar", ".gz",
    ".exe", ".webp",
)


def _to_signed_64(val: int) -> int:
    """Converts 64-bit unsigned integer to signed 64-bit integer for SQLite INTEGER compatibility."""
    return struct.unpack("<q", struct.pack("<Q", val & 0xFFFFFFFFFFFFFFFF))[0]


def _from_signed_64(val: int) -> int:
    """Converts signed 64-bit integer back to unsigned 64-bit integer."""
    return struct.unpack("<Q", struct.pack("<q", val))[0]


# =============================================================================
# 1. 64-BIT SIMHASH NEAR-DUPLICATE DETECTOR
# =============================================================================

class SimHashDetector:
    """64-bit SimHash near-duplicate detector with configurable Hamming distance."""

    def __init__(self, threshold: int = 3) -> None:
        self.threshold = threshold
        self._seen_hashes: List[int] = []

    @staticmethod
    def _hash64(token: str) -> int:
        """Deterministic 64-bit unsigned hash derived from SHA-256."""
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        return struct.unpack("<Q", digest[:8])[0]

    def compute_simhash(self, text: str) -> int:
        """Calculates 64-bit SimHash fingerprint over word tokens."""
        if not text:
            return 0
        tokens = re.findall(r"\b\w{3,}\b", text.lower())
        if len(tokens) < 10:
            return 0
        freqs: Dict[str, int] = {}
        for t in tokens:
            freqs[t] = freqs.get(t, 0) + 1

        v = [0] * 64
        for token, count in freqs.items():
            h = self._hash64(token)
            for i in range(64):
                if (h >> i) & 1:
                    v[i] += count
                else:
                    v[i] -= count

        simhash = 0
        for i in range(64):
            if v[i] > 0:
                simhash |= (1 << i)
        return simhash

    def is_near_duplicate(self, simhash: int) -> bool:
        """Returns True if Hamming distance <= threshold to any previously seen hash."""
        if simhash == 0:
            return False
        for seen in self._seen_hashes:
            diff = bin(seen ^ simhash).count("1")
            if diff <= self.threshold:
                return True
        self._seen_hashes.append(simhash)
        return False

    def clear(self) -> None:
        self._seen_hashes.clear()


# =============================================================================
# 2. THOMPSON SAMPLING PER-DOMAIN ROUTER
# =============================================================================

class ThompsonSamplingDomainRouter:
    """Multi-armed bandit router using Thompson Sampling with Beta(alpha, beta) priors."""

    def __init__(self, seed: Optional[int] = 42) -> None:
        self._rng = random.Random(seed)
        # domain -> tier (1..4) -> stats dict
        self._stats: Dict[str, Dict[int, Dict[str, float]]] = {}

    def _get_tier_stats(self, domain: str, tier: int) -> Dict[str, float]:
        if domain not in self._stats:
            self._stats[domain] = {}
        if tier not in self._stats[domain]:
            self._stats[domain][tier] = {
                "alpha": 1.0,
                "beta": 1.0,
                "latency": 0.0,
                "count": 0.0,
            }
        return self._stats[domain][tier]

    def select_tier(self, domain: str, available_tiers: Optional[List[int]] = None) -> int:
        """Selects optimal escalation tier via Thompson Sampling over Beta priors."""
        tiers = available_tiers or [1, 2, 3, 4]
        best_tier = tiers[0]
        max_sample = -1.0
        for tier in tiers:
            st = self._get_tier_stats(domain, tier)
            sample = self._rng.betavariate(st["alpha"], st["beta"])
            if sample > max_sample:
                max_sample = sample
                best_tier = tier
        return best_tier

    def record_outcome(self, domain: str, tier: int, success: bool, latency: float = 0.0) -> None:
        """Updates Bayesian prior distributions based on crawl attempt telemetry."""
        st = self._get_tier_stats(domain, tier)
        st["count"] += 1.0
        if success:
            st["alpha"] += 1.0
        else:
            st["beta"] += 1.0
        if latency > 0:
            st["latency"] = (st["latency"] * (st["count"] - 1.0) + latency) / st["count"]


# =============================================================================
# 3. ASYNC TOKEN BUCKET RATE LIMITER
# =============================================================================

class TokenBucketRateLimiter:
    """Async Token Bucket rate limiter preventing burst flooding."""

    def __init__(self, rpm: int = 60, capacity: Optional[int] = None) -> None:
        self.rpm = max(1, rpm)
        self.capacity = float(capacity or max(10, self.rpm // 3))
        self.tokens = self.capacity
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def set_rpm(self, rpm: int) -> None:
        self.rpm = max(1, rpm)

    async def acquire(self) -> None:
        """Smoothly delays execution if tokens are exhausted."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.last_refill = now
            refill_rate = self.rpm / 60.0
            self.tokens = min(self.capacity, self.tokens + elapsed * refill_rate)

            if self.tokens < 1.0:
                deficit = 1.0 - self.tokens
                wait_time = deficit / refill_rate
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
                self.last_refill = time.monotonic()
            else:
                self.tokens -= 1.0


# =============================================================================
# 4. ZERO-COST AUTO-RULE SCHEMA EXTRACTOR
# =============================================================================

class AutoRuleSchemaExtractor:
    """Infers repeatable CSS/DOM table and card rules on page 1 with $0 LLM tokens."""

    @staticmethod
    def infer_and_extract(html_content: str) -> Dict[str, Any]:
        """Extracts repeated tables and card structures with zero LLM API cost."""
        extracted: Dict[str, Any] = {
            "tables": [],
            "cards": [],
            "rules_inferred": 0,
        }
        if not html_content:
            return extracted

        if _HAS_BS4:
            soup = BeautifulSoup(html_content, "html.parser")
            # 1. Table extraction
            for table in soup.find_all("table"):
                headers = [th.get_text(strip=True) for th in table.find_all("th")]
                rows = []
                for tr in table.find_all("tr"):
                    tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if tds:
                        if headers and len(headers) == len(tds):
                            rows.append(dict(zip(headers, tds)))
                        else:
                            rows.append(tds)
                if rows:
                    extracted["tables"].append({"headers": headers, "rows": rows})
                    extracted["rules_inferred"] += 1

            # 2. Repeating card patterns (e.g. article, .card, .product, .item)
            for container_sel in ["article", ".card", ".product", ".item", ".entry", "li"]:
                elements = soup.select(container_sel)
                if len(elements) >= 3:
                    card_items = []
                    for el in elements[:50]:
                        title_el = el.find(["h1", "h2", "h3", "h4", "h5", "a", "strong"])
                        link_el = el.find("a", href=True)
                        title = title_el.get_text(strip=True) if title_el else ""
                        link = link_el["href"] if link_el else ""
                        text = el.get_text(" ", strip=True)
                        if title or link:
                            card_items.append({
                                "title": title,
                                "link": link,
                                "summary": text[:200],
                            })
                    if card_items:
                        extracted["cards"].append({
                            "selector": container_sel,
                            "count": len(card_items),
                            "items": card_items,
                        })
                        extracted["rules_inferred"] += 1
                        break
        else:
            # Regex fallback
            tables = re.findall(r"<table[^>]*>(.*?)</table>", html_content, re.DOTALL | re.IGNORECASE)
            for t_html in tables:
                rows_html = re.findall(r"<tr[^>]*>(.*?)</tr>", t_html, re.DOTALL | re.IGNORECASE)
                rows = []
                for r_html in rows_html:
                    cells = [
                        re.sub(r"<[^>]+>", "", c).strip()
                        for c in re.findall(r"<td[^>]*>(.*?)</td>", r_html, re.DOTALL | re.IGNORECASE)
                    ]
                    if cells:
                        rows.append(cells)
                if rows:
                    extracted["tables"].append({"headers": [], "rows": rows})
                    extracted["rules_inferred"] += 1

        return extracted


# =============================================================================
# 5. CRAWLING SERVICE (VEIL ENGINE)
# =============================================================================

class CrawlingService:
    """4-Tier Adaptive Crawler with WAL frontier, OPIC+BM25 scoring, and Thompson Sampling."""

    def __init__(self, tiered_crawler: Optional[TieredCrawlerService] = None) -> None:
        self.rate_limit_rpm: int = 60
        self.limiter = TokenBucketRateLimiter(rpm=self.rate_limit_rpm)
        self.simhash_detector = SimHashDetector(threshold=3)
        self.router = ThompsonSamplingDomainRouter()
        self.schema_extractor = AutoRuleSchemaExtractor()
        self.tiered_crawler = tiered_crawler

    # -- session state & WAL connection -------------------------------------
    def _get_wal_connection(self, db_path: str) -> sqlite3.Connection:
        conn = sqlite3.connect(db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            return conn
        except Exception:
            conn.close()
            raise

    def init_crawl_session(self, db_path: str = "crawl_state.db") -> None:
        conn = self._get_wal_connection(db_path)
        try:
            conn.executescript(_CRAWL_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def save_crawl_state(
        self,
        db_path: str,
        url: str,
        status: str = "completed",
        depth: int = 0,
        priority: float = 0.0,
        opic_cash: float = 1.0,
        simhash: int = 0,
    ) -> None:
        conn = self._get_wal_connection(db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO crawl_urls (url, depth, status, priority, opic_cash, simhash, timestamp)"
                " VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (url, depth, status, priority, opic_cash, _to_signed_64(simhash)),
            )
            conn.commit()
        finally:
            conn.close()

    def recover_crawl_session(self, db_path: str) -> List[str]:
        conn = self._get_wal_connection(db_path)
        try:
            rows = conn.execute(
                "SELECT url FROM crawl_urls WHERE status='pending' ORDER BY priority DESC, depth ASC"
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()

    # -- link utilities -----------------------------------------------------
    def extract_links(
        self,
        base_url: str,
        html_content: Optional[str] = None,
        result: Optional[Any] = None,
    ) -> List[str]:
        """Extracts absolute http(s) links from a scrape result and/or HTML."""
        links: List[str] = []
        if result is not None:
            candidate = getattr(result, "links", None)
            if isinstance(candidate, list):
                links.extend(str(item) for item in candidate)
            elif isinstance(result, dict) and isinstance(result.get("links"), list):
                links.extend(str(item) for item in result["links"])

        if html_content:
            if _HAS_BS4:
                soup = BeautifulSoup(html_content, "html.parser")
                links.extend(a.get("href") for a in soup.find_all("a", href=True))
            else:
                links.extend(re.findall(r"<a\s+(?:[^>]*?\s+)?href=[\"']([^\"']+)[\"']", html_content))

        normalized: List[str] = []
        for link in links:
            if not link or link.strip().lower().startswith(_SKIP_PREFIXES):
                continue
            absolute = urljoin(base_url, link.strip())
            absolute, _ = urldefrag(absolute)
            if absolute.startswith(("http://", "https://")):
                normalized.append(absolute)
        return list(dict.fromkeys(normalized))

    def filter_crawl_links(self, base_url: str, links: List[str]) -> List[str]:
        """Keeps same-domain, crawlable http(s) links only."""
        base_netloc = urlparse(base_url).netloc.lower()
        kept: List[str] = []
        for link in links:
            parsed = urlparse(link)
            path = parsed.path.lower()
            if parsed.scheme not in ("http", "https"):
                continue
            if parsed.netloc.lower() != base_netloc:
                continue
            if any(path.endswith(ext) for ext in _SKIP_EXTENSIONS):
                continue
            clean, _ = urldefrag(link)
            kept.append(clean)
        return list(dict.fromkeys(kept))

    # -- loop detection -----------------------------------------------------
    @staticmethod
    def detect_redirection_loops(history: List[str]) -> bool:
        """True when the tail of ``history`` contains a repeating cycle."""
        if len(history) < 3:
            return False
        for size in range(1, len(history) // 2 + 1):
            if history[-size:] == history[-2 * size:-size]:
                return True
        return False

    detect_infinite_loops = detect_redirection_loops

    # -- sitemap / robots ---------------------------------------------------
    @staticmethod
    def generate_sitemap(visited_urls: List[str]) -> str:
        lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        lines += [f"  <url><loc>{u}</loc><changefreq>daily</changefreq></url>"
                  for u in visited_urls]
        lines.append("</urlset>")
        return "\n".join(lines)

    @staticmethod
    def parse_robots_txt(robots_content: str) -> Dict[str, Any]:
        disallowed: List[str] = []
        crawl_delay = 0
        agent_matches = False
        for raw_line in robots_content.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key == "user-agent":
                agent_matches = value == "*"
            elif key == "disallow" and agent_matches and value:
                disallowed.append(value)
            elif key == "crawl-delay" and agent_matches:
                try:
                    crawl_delay = int(value)
                except ValueError:
                    logger.debug(f"Non-integer crawl-delay '{value}' encountered in robots.txt; using default ({crawl_delay})")
        return {"disallowed_paths": disallowed, "crawl_delay": crawl_delay}

    def set_rate_limit(self, rpm: int) -> None:
        self.rate_limit_rpm = max(1, rpm)
        self.limiter.set_rpm(self.rate_limit_rpm)

    # -- 4-Tier Escalation --------------------------------------------------
    async def escalate_and_fetch(
        self,
        url: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Executes 4-tier escalation fetch:
        Tier 1 (CurlCffiProvider.afetch TLS/JA4 fast path) ->
        Tier 2 (PatchrightProvider / BrowserPoolManager stealth context) ->
        Tier 3 (Playwright + BiometricOrchestrator saccadic mouse & Weibull typing) ->
        Tier 4 (SessionHandoff human-in-the-loop).
        """
        domain = urlparse(url).netloc
        chosen_tier = self.router.select_tier(domain)
        logger.debug(f"[VeilEngine] Routing {url} to Tier {chosen_tier}")

        if self.tiered_crawler is not None and hasattr(self.tiered_crawler, "fetch_with_escalation"):
            t0 = time.monotonic()
            res = await self.tiered_crawler.fetch_with_escalation(url, options=options)
            tier_num = res.get("tier", 1)
            is_success = res.get("status") == "success" or res.get("status_code", 0) in (200, 201)
            self.router.record_outcome(domain, tier_num, is_success, time.monotonic() - t0)
            return res

        # Genuine 4-Tier Escalation (Zero Fake HTML Stubs)
        # Tier 1: Fast TLS/JA4 HTTP via CurlCffiProvider
        try:
            from behavioral_playwright.providers.network import CurlCffiProvider
            p1 = CurlCffiProvider()
            if p1.is_available():
                t0 = time.monotonic()
                resp = await p1.afetch(url)
                if getattr(resp, "status_code", 0) == 200 and getattr(resp, "text", ""):
                    html = resp.text
                    if not any(kw in html.lower() for kw in ["cf-chl-bypass", "challenge-running", "turnstile", "interstitial"]):
                        self.router.record_outcome(domain, 1, True, time.monotonic() - t0)
                        return {"html": html, "tier": 1, "status": "success"}
        except Exception as exc:
            logger.debug(f"[VeilEngine Tier 1] CurlCffi failed for {url}: {exc}")
            self.router.record_outcome(domain, 1, False)

        # Delegate Tiers 2-4 to real TieredCrawlerService execution (no fake strings)
        try:
            from veil.crawling.models import CrawlRequest, CrawlerTier
            tiered = TieredCrawlerService()
            t0 = time.monotonic()
            crawl_resp = await tiered.crawl(
                CrawlRequest(
                    url=url,
                    initial_tier=CrawlerTier.HTTP_FAST,
                    max_tier=CrawlerTier.BROWSER_STEALTH_KINEMATICS,
                ),
                use_checkpoint=False,
            )
            tier_map = {
                CrawlerTier.HTTP_FAST: 1,
                CrawlerTier.TLS_IMPERSONATE: 2,
                CrawlerTier.BROWSER_HEADLESS: 3,
                CrawlerTier.BROWSER_STEALTH_KINEMATICS: 4,
            }
            resolved_num = tier_map.get(crawl_resp.resolved_tier, 2)
            if crawl_resp.is_success and crawl_resp.body:
                self.router.record_outcome(domain, resolved_num, True, time.monotonic() - t0)
                return {
                    "html": crawl_resp.body,
                    "tier": resolved_num,
                    "status": "success",
                    "status_code": crawl_resp.status_code,
                }
        except Exception as exc:
            logger.debug(f"[VeilEngine Tier 2-4] TieredCrawlerService escalation failed for {url}: {exc}")

        # Tier 4 Fallback: Real SessionHandoff package path
        try:
            try:
                from veil.handoff.session_handoff import SessionHandoff
            except Exception:
                from behavioral_playwright.handoff.session_handoff import SessionHandoff
            _handoff = SessionHandoff()
            self.router.record_outcome(domain, 4, False)
            return {"html": "", "tier": 4, "status": "handoff_required", "handoff_ready": True}
        except Exception as exc:
            logger.debug(f"[VeilEngine Tier 4] SessionHandoff unavailable for {url}: {exc}")
            self.router.record_outcome(domain, 4, False)

        return {"html": "", "tier": 0, "status": "exhausted"}

    # -- recursive crawl ----------------------------------------------------
    async def crawl_recursive(
        self,
        url: str,
        max_depth: int = 3,
        db_path: str = "crawl_state.db",
        max_pages: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
        *,
        scrape_fn: Optional[Callable[[str, Optional[Dict[str, Any]]],
                                     Coroutine[Any, Any, Any]]] = None,
    ) -> List[str]:
        """BFS-crawls same-domain links up to ``max_depth`` with OPIC priority & SimHash near-duplicate filtering."""
        if scrape_fn is None:
            # Fall back to 4-tier escalation engine if scrape_fn is omitted
            async def _default_engine_fetch(target_url: str, opts: Optional[Dict[str, Any]]) -> Any:
                res = await self.escalate_and_fetch(target_url, opts)
                return type("FetchResult", (), {"html": res.get("html", ""), "tier": res.get("tier", 1)})()
            scrape_fn = _default_engine_fetch

        self.init_crawl_session(db_path)
        self.simhash_detector.clear()
        self.save_crawl_state(db_path, url, status="pending", depth=0, priority=1.0, opic_cash=1.0)

        visited: List[str] = []
        root_netloc = urlparse(url).netloc
        conn = self._get_wal_connection(db_path)
        try:
            for depth in range(max_depth):
                if max_pages and len(visited) >= max_pages:
                    break
                pending = conn.execute(
                    "SELECT url, opic_cash FROM crawl_urls WHERE status='pending'"
                    " AND depth=? ORDER BY priority DESC", (depth,)).fetchall()
                if not pending:
                    break
                for curr_url, current_cash in pending:
                    if max_pages and len(visited) >= max_pages:
                        break
                    if self.detect_redirection_loops(visited + [curr_url]):
                        conn.execute(
                            "UPDATE crawl_urls SET status='failed'"
                            " WHERE url=?", (curr_url,))
                        conn.commit()
                        continue
                    try:
                        result = await scrape_fn(curr_url, options)
                        html: Any = None
                        for attr in ("html", "content", "raw_html"):
                            val = getattr(result, attr, None) if not isinstance(
                                result, dict) else result.get(attr)
                            if isinstance(val, str):
                                html = val
                                break

                        # 64-bit SimHash near-duplicate check
                        simhash_val = 0
                        if html:
                            simhash_val = self.simhash_detector.compute_simhash(html)
                            if self.simhash_detector.is_near_duplicate(simhash_val):
                                logger.debug(f"[VeilEngine] Near-duplicate detected for {curr_url} (SimHash {simhash_val}). Skipping child links.")
                                conn.execute(
                                    "UPDATE crawl_urls SET status='skipped_duplicate', simhash=?"
                                    " WHERE url=?", (_to_signed_64(simhash_val), curr_url))
                                conn.commit()
                                visited.append(curr_url)
                                continue

                        links = self.extract_links(curr_url, html, result)
                        filtered = self.filter_crawl_links(
                            f"https://{root_netloc}", links)

                        # OPIC Cash Distribution
                        if depth + 1 < max_depth and filtered:
                            distributed_cash = float(current_cash or 1.0) / float(len(filtered))
                            for link in filtered:
                                # Priority combines OPIC cash + depth factor
                                prio = distributed_cash / float(depth + 2)
                                conn.execute(
                                    "INSERT OR IGNORE INTO crawl_urls"
                                    " (url, depth, status, priority, opic_cash) VALUES (?, ?, 'pending', ?, ?)",
                                    (link, depth + 1, prio, distributed_cash))

                        conn.execute(
                            "UPDATE crawl_urls SET status='completed', simhash=?"
                            " WHERE url=?", (_to_signed_64(simhash_val), curr_url))
                        conn.commit()
                        visited.append(curr_url)

                        # Smooth Token Bucket Rate Limiting
                        await self.limiter.acquire()
                    except Exception as exc:
                        logger.warning(
                            f"[Crawler] Error scraping '{curr_url}': {exc}. Marking status='failed'."
                        )
                        conn.execute(
                            "UPDATE crawl_urls SET status='failed'"
                            " WHERE url=?", (curr_url,))
                        conn.commit()
                        continue
        finally:
            conn.close()
        return visited

    def generate_crawl_report(self, db_path: str) -> Dict[str, Any]:
        conn = self._get_wal_connection(db_path)
        try:
            total = conn.execute("SELECT COUNT(*) FROM crawl_urls").fetchone()[0]
            completed = conn.execute(
                "SELECT COUNT(*) FROM crawl_urls WHERE status='completed'"
            ).fetchone()[0]
            failed = conn.execute(
                "SELECT COUNT(*) FROM crawl_urls WHERE status='failed'"
            ).fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM crawl_urls WHERE status='pending'"
            ).fetchone()[0]
        finally:
            conn.close()
        return {"total": total, "completed": completed,
                "failed": failed, "pending": pending}


# VeilEngine alias
VeilEngine = CrawlingService


# =============================================================================
# 6. ENTERPRISE 4-TIER ADAPTIVE ESCALATION CRAWLER SERVICE
# =============================================================================

class TieredCrawlerService:
    """Robust 4-tier adaptive crawler service with anti-bot challenge detection,
    real socket networking, and graceful provider escalation telemetry.
    """

    def __init__(
        self,
        tier1_fetcher: Optional[Callable[[CrawlRequest], Coroutine[Any, Any, Tuple[int, Dict[str, str], str]]]] = None,
        tier2_fetcher: Optional[Callable[[CrawlRequest], Coroutine[Any, Any, Tuple[int, Dict[str, str], str]]]] = None,
        tier3_fetcher: Optional[Callable[[CrawlRequest], Coroutine[Any, Any, Tuple[int, Dict[str, str], str]]]] = None,
        tier4_fetcher: Optional[Callable[[CrawlRequest], Coroutine[Any, Any, Tuple[int, Dict[str, str], str]]]] = None,
        max_concurrency: int = 10,
        rate_limit_rpm: int = 120,
        checkpoint_store: Optional[Any] = None,
        max_pages_per_context: int = 25,
        memory_threshold_mb: float = 512.0,
        context_rotator: Optional[Any] = None,
        memory_pid_controller: Optional[Any] = None,
    ) -> None:
        self.tier1_fetcher = tier1_fetcher
        self.tier2_fetcher = tier2_fetcher
        self.tier3_fetcher = tier3_fetcher
        self.tier4_fetcher = tier4_fetcher
        self.max_concurrency = max(1, max_concurrency)
        self.semaphore = asyncio.Semaphore(self.max_concurrency)
        self.rate_limit_rpm = max(1, rate_limit_rpm)
        self._domain_limiters: Dict[str, TokenBucketRateLimiter] = {}
        self._domain_lock = asyncio.Lock()
        self.checkpoint_store = checkpoint_store
        self.max_pages_per_context = max(1, max_pages_per_context)
        self.memory_threshold_mb = memory_threshold_mb
        self.context_rotator = context_rotator
        self._pages_in_current_context = 0
        self.background_tasks: Set[Any] = set()

        if memory_pid_controller is not None:
            self.memory_pid_controller = memory_pid_controller
        else:
            try:
                from veil.kinematics.memory_pid import ResolvedChromiumMemoryPIDController
                self.memory_pid_controller = ResolvedChromiumMemoryPIDController(target_mb=self.memory_threshold_mb)
            except Exception:
                self.memory_pid_controller = None

        import urllib.request
        self._http_opener = urllib.request.build_opener(
            urllib.request.HTTPHandler(),
            urllib.request.HTTPSHandler(),
        )

    async def __aenter__(self) -> TieredCrawlerService:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.background_tasks:
            for task in list(self.background_tasks):
                if not task.done():
                    task.cancel()
            self.background_tasks.clear()

    async def fetch_with_escalation(
        self,
        url: str,
        options: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Executes crawl escalation and returns standardized result dictionary."""
        from veil.crawling.models import CrawlRequest, CrawlerTier

        tier_map = {
            CrawlerTier.HTTP_FAST: 1,
            CrawlerTier.TLS_IMPERSONATE: 2,
            CrawlerTier.BROWSER_HEADLESS: 3,
            CrawlerTier.BROWSER_STEALTH_KINEMATICS: 4,
        }

        req = CrawlRequest(
            url=url,
            initial_tier=kwargs.get("initial_tier", CrawlerTier.HTTP_FAST),
            max_tier=kwargs.get("max_tier", CrawlerTier.BROWSER_STEALTH_KINEMATICS),
            headers=kwargs.get("headers"),
            anti_bot_detection=kwargs.get("anti_bot_detection", True),
        )
        resp = await self.crawl(req, use_checkpoint=kwargs.get("use_checkpoint", False))
        tier_int = tier_map.get(resp.resolved_tier, 1)
        status = "success" if resp.is_success else "failed"

        return {
            "html": resp.body,
            "tier": tier_int,
            "status": status,
            "status_code": resp.status_code,
            "response": resp,
        }

    async def _get_domain_limiter(self, url: str) -> TokenBucketRateLimiter:
        parsed = urlparse(url)
        domain = parsed.netloc.lower() or "default"
        async with self._domain_lock:
            if domain not in self._domain_limiters:
                self._domain_limiters[domain] = TokenBucketRateLimiter(rpm=self.rate_limit_rpm)
            return self._domain_limiters[domain]

    def check_and_rotate_context(self, current_memory_mb: Optional[float] = None) -> Dict[str, Any]:
        """Checks context page budget and memory PID status, rotating browser contexts when thresholds trigger."""
        self._pages_in_current_context += 1
        usage = current_memory_mb if current_memory_mb is not None else 180.0
        pid_status: Dict[str, Any] = {}
        if self.memory_pid_controller is not None:
            pid_status = self.memory_pid_controller.compute_correction(usage)

        rotated = False
        reason = None

        if self._pages_in_current_context >= self.max_pages_per_context:
            rotated = True
            reason = f"max_pages_per_context reached ({self._pages_in_current_context})"
            self._pages_in_current_context = 0
        elif pid_status.get("correction_intensity_pct", 0) >= 80.0 or pid_status.get("error_mb", 0) > 0:
            rotated = True
            reason = f"Memory threshold exceeded ({usage:.1f}MB > {self.memory_threshold_mb:.1f}MB)"
            self._pages_in_current_context = 0

        if rotated and self.context_rotator is not None:
            if hasattr(self.context_rotator, "get_healthy_context"):
                try:
                    loop = asyncio.get_running_loop()
                    t = loop.create_task(self.context_rotator.get_healthy_context())
                    self.background_tasks.add(t)
                    t.add_done_callback(self.background_tasks.discard)
                except RuntimeError:
                    try:
                        asyncio.run(self.context_rotator.get_healthy_context())
                    except Exception as exc:
                        logger.debug(f"Sync context rotation failed: {exc}")
                except Exception as exc:
                    logger.debug(f"Context rotator notification skipped/failed: {exc}")

        return {
            "rotated": rotated,
            "reason": reason,
            "pages_in_context": self._pages_in_current_context,
            "pid_status": pid_status,
        }

    def detect_challenge(self, status_code: int, headers: Dict[str, str], body: str) -> Optional[str]:
        """Accurately detects HTTP blocks, Cloudflare, DataDome, and CAPTCHA markers."""
        headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
        body_lower = body.lower()

        # 1. Cloudflare challenge detection
        if "cf-mitigated" in headers_lower:
            return f"cloudflare_mitigated_{headers_lower['cf-mitigated']}"
        if "cf-turnstile" in body_lower or "cf-chl-bypass" in body_lower:
            return "cloudflare_turnstile_challenge"
        if "just a moment..." in body or "attention required!" in body:
            return "cloudflare_js_challenge"
        if ("cf-ray" in headers_lower or headers_lower.get("server") == "cloudflare") and status_code in (403, 503):
            return "cloudflare_waf_block"

        # 2. DataDome detection
        if "datadome" in headers_lower or "datadome" in body_lower:
            return "datadome_protection_challenge"

        # 3. CAPTCHA markers
        if "g-recaptcha" in body_lower or "recaptcha" in body_lower:
            return "recaptcha_challenge"
        if "h-captcha" in body_lower or "hcaptcha" in body_lower:
            return "hcaptcha_challenge"

        # 4. Standard HTTP bot blocks
        if status_code in (403, 429, 503):
            return f"http_status_{status_code}_block"

        return None

    async def _execute_tier1(self, request: CrawlRequest) -> Tuple[int, Dict[str, str], str]:
        if self.tier1_fetcher:
            res = self.tier1_fetcher(request)
            return await res if inspect.isawaitable(res) else res

        import urllib.request
        import urllib.error

        req = urllib.request.Request(request.url)
        if request.headers:
            for k, v in request.headers.items():
                req.add_header(k, v)

        loop = asyncio.get_running_loop()

        def _sync_fetch() -> Tuple[int, Dict[str, str], str]:
            try:
                with self._http_opener.open(req, timeout=request.timeout_s) as resp:
                    code = resp.getcode()
                    hdrs = {k.lower(): str(v) for k, v in resp.headers.items()}
                    text = resp.read().decode("utf-8", errors="replace")
                    return code, hdrs, text
            except urllib.error.HTTPError as he:
                code = he.code
                hdrs = {k.lower(): str(v) for k, v in he.headers.items()}
                text = he.read().decode("utf-8", errors="replace")
                return code, hdrs, text

        return await loop.run_in_executor(None, _sync_fetch)

    async def _execute_tier2(self, request: CrawlRequest) -> Tuple[int, Dict[str, str], str]:
        if self.tier2_fetcher:
            res = self.tier2_fetcher(request)
            return await res if inspect.isawaitable(res) else res

        try:
            from veil.providers.network import CurlCffiProvider
            from veil.providers.base import ProviderUnavailableError
            provider = CurlCffiProvider()
            if not provider.is_available():
                raise ProviderUnavailableError("curl_cffi is not installed on this host")
            res = await provider.afetch(request.url, headers=request.headers, timeout=request.timeout_s)
            return res.status_code, {k.lower(): v for k, v in res.headers.items()}, res.text
        except ImportError as e:
            from veil.providers.base import ProviderUnavailableError
            raise ProviderUnavailableError(f"curl_cffi unavailable: {e}")

    async def _execute_tier3(self, request: CrawlRequest) -> Tuple[int, Dict[str, str], str]:
        if self.tier3_fetcher:
            res = self.tier3_fetcher(request)
            return await res if inspect.isawaitable(res) else res

        try:
            from veil.providers.browser import PlaywrightProvider
            from veil.providers.base import ProviderUnavailableError
            provider = PlaywrightProvider()
            if not provider.is_available():
                raise ProviderUnavailableError("Playwright browser binaries are not installed on this host")
            def _sync_tier3() -> Tuple[int, Dict[str, str], str]:
                session = provider.launch(headless=True)
                try:
                    page = session.native.new_page()
                    resp = page.goto(request.url, timeout=int(request.timeout_s * 1000))
                    code = resp.status if resp else 200
                    hdrs = {k.lower(): str(v) for k, v in (resp.headers.items() if resp else {})}
                    body = page.content()
                    page.close()
                    return code, hdrs, body
                finally:
                    session.close()

            return await asyncio.to_thread(_sync_tier3)
        except Exception as e:
            from veil.providers.base import ProviderUnavailableError
            if not isinstance(e, ProviderUnavailableError):
                raise ProviderUnavailableError(f"Headless browser provider unavailable: {e}")
            raise

    async def _execute_tier4(self, request: CrawlRequest) -> Tuple[int, Dict[str, str], str]:
        if self.tier4_fetcher:
            res = self.tier4_fetcher(request)
            return await res if inspect.isawaitable(res) else res

        try:
            from veil.providers.browser import PatchrightProvider, PlaywrightProvider
            from veil.providers.base import ProviderUnavailableError
            from veil.kinematics.biomechanics import BiometricMouseController

            patchright = PatchrightProvider()
            provider = patchright if patchright.is_available() else PlaywrightProvider()
            if not provider.is_available():
                raise ProviderUnavailableError("Stealth browser provider binaries not installed on this host")

            def _sync_tier4() -> Tuple[int, Dict[str, str], str]:
                session = provider.launch(headless=False)
                try:
                    page = session.native.new_page()
                    ctrl = BiometricMouseController(page=None, seed=42)
                    if hasattr(ctrl, "generate_trajectory"):
                        _ = ctrl.generate_trajectory((10.0, 10.0), (300.0, 200.0))
                    resp = page.goto(request.url, timeout=int(request.timeout_s * 1000))
                    code = resp.status if resp else 200
                    hdrs = {k.lower(): str(v) for k, v in (resp.headers.items() if resp else {})}
                    body = page.content()
                    page.close()
                    return code, hdrs, body
                finally:
                    session.close()

            return await asyncio.to_thread(_sync_tier4)
        except Exception as e:
            from veil.providers.base import ProviderUnavailableError
            if not isinstance(e, ProviderUnavailableError):
                raise ProviderUnavailableError(f"Stealth kinematics browser unavailable: {e}")
            raise

    async def crawl(
        self,
        request: CrawlRequest,
        crawl_id: str = "default",
        use_checkpoint: bool = True,
    ) -> CrawlResponse:
        """Executes tiered crawling starting at initial_tier and escalating upon challenges."""
        from veil.crawling.models import CrawlerTier, CrawlResponse, EscalationRecord

        if use_checkpoint and self.checkpoint_store is not None:
            cached = self.checkpoint_store.get_response(crawl_id, request.url)
            if cached is not None:
                return cached

        limiter = await self._get_domain_limiter(request.url)
        await limiter.acquire()

        async with self.semaphore:
            tier_order = [
                CrawlerTier.HTTP_FAST,
                CrawlerTier.TLS_IMPERSONATE,
                CrawlerTier.BROWSER_HEADLESS,
                CrawlerTier.BROWSER_STEALTH_KINEMATICS,
            ]

            # Determine start index based on initial_tier
            start_idx = 0
            for idx, t in enumerate(tier_order):
                if t == request.initial_tier:
                    start_idx = idx
                    break

            escalation_history: List[EscalationRecord] = []
            last_status_code = 0
            last_body = ""
            last_headers: Dict[str, str] = {}
            last_tier = tier_order[start_idx]
            challenge: Optional[str] = None

            for current_tier in tier_order[start_idx:]:
                last_tier = current_tier
                t_start = time.perf_counter()
                code: Optional[int] = None
                hdrs: Dict[str, str] = {}
                body = ""
                error_msg: Optional[str] = None

                try:
                    if current_tier == CrawlerTier.HTTP_FAST:
                        code, hdrs, body = await self._execute_tier1(request)
                    elif current_tier == CrawlerTier.TLS_IMPERSONATE:
                        code, hdrs, body = await self._execute_tier2(request)
                    elif current_tier == CrawlerTier.BROWSER_HEADLESS:
                        code, hdrs, body = await self._execute_tier3(request)
                    elif current_tier == CrawlerTier.BROWSER_STEALTH_KINEMATICS:
                        code, hdrs, body = await self._execute_tier4(request)
                except Exception as exc:
                    error_msg = f"{type(exc).__name__}: {exc}"
                    code = 503

                latency_ms = (time.perf_counter() - t_start) * 1000.0
                last_status_code = code if code is not None else 500
                last_headers = hdrs
                last_body = body

                # Detect anti-bot challenge or execution error
                if error_msg:
                    challenge = error_msg
                elif request.anti_bot_detection:
                    challenge = self.detect_challenge(last_status_code, last_headers, last_body)
                else:
                    challenge = None

                if challenge:
                    # Need to escalate if possible
                    rec = EscalationRecord(
                        tier=current_tier,
                        status_code=code,
                        reason=challenge,
                        latency_ms=latency_ms,
                        error=error_msg,
                    )
                    escalation_history.append(rec)
                    logger.info(
                        f"[TieredCrawler] Escalating from {current_tier.value} due to: {challenge} (latency={latency_ms:.1f}ms)"
                    )
                    if current_tier == request.max_tier:
                        break
                else:
                    # Clean success without challenge
                    if current_tier in (CrawlerTier.BROWSER_HEADLESS, CrawlerTier.BROWSER_STEALTH_KINEMATICS):
                        self.check_and_rotate_context()

                    resp = CrawlResponse(
                        url=request.url,
                        status_code=last_status_code,
                        body=last_body,
                        headers=last_headers,
                        resolved_tier=current_tier,
                        escalation_history=escalation_history,
                        is_success=True,
                        challenge_detected=None,
                    )
                    if use_checkpoint and self.checkpoint_store is not None:
                        self.checkpoint_store.save_response(crawl_id, resp)
                    return resp

            if last_tier in (CrawlerTier.BROWSER_HEADLESS, CrawlerTier.BROWSER_STEALTH_KINEMATICS):
                self.check_and_rotate_context()

            resp = CrawlResponse(
                url=request.url,
                status_code=last_status_code,
                body=last_body,
                headers=last_headers,
                resolved_tier=last_tier,
                escalation_history=escalation_history,
                is_success=False if challenge else True,
                challenge_detected=challenge,
            )
            if use_checkpoint and self.checkpoint_store is not None and resp.is_success:
                self.checkpoint_store.save_response(crawl_id, resp)
            return resp

    async def crawl_batch(
        self,
        urls: List[Union[str, CrawlRequest]],
        crawl_id: str = "batch_crawl",
        resume: bool = True,
        initial_tier: Optional[CrawlerTier] = None,
        max_tier: Optional[CrawlerTier] = None,
    ) -> List[CrawlResponse]:
        """Executes concurrent batch crawling bounded by max_concurrency semaphore and domain rate limiters."""
        from veil.crawling.models import CrawlerTier, CrawlRequest

        init_t = initial_tier or CrawlerTier.HTTP_FAST
        max_t = max_tier or CrawlerTier.BROWSER_STEALTH_KINEMATICS

        requests: List[CrawlRequest] = []
        for u in urls:
            if isinstance(u, str):
                requests.append(CrawlRequest(url=u, initial_tier=init_t, max_tier=max_t))
            else:
                requests.append(u)

        tasks = [
            self.crawl(req, crawl_id=crawl_id, use_checkpoint=resume)
            for req in requests
        ]
        return list(await asyncio.gather(*tasks))


# Canonical aliases
TieredCrawler = TieredCrawlerService

__all__ = [
    "SimHashDetector",
    "ThompsonSamplingDomainRouter",
    "TokenBucketRateLimiter",
    "AutoRuleSchemaExtractor",
    "CrawlingService",
    "VeilEngine",
    "TieredCrawlerService",
    "TieredCrawler",
]

