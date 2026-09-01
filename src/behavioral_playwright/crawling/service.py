"""Crawling extensions for the Web namespace.

Real implementations of recursive crawling, link extraction/filtering,
sitemap generation and robots.txt parsing — backed by SQLite crawl-state
persistence. Page fetching is delegated to a caller-provided async
``scrape`` callable so the crawler stays transport-agnostic.
"""

from __future__ import annotations

import asyncio
import re
import sqlite3
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional
from urllib.parse import urljoin, urlparse, urldefrag

try:  # BeautifulSoup is optional; regex fallback keeps extraction working.
    from bs4 import BeautifulSoup  # type: ignore
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

_CRAWL_SCHEMA = """
CREATE TABLE IF NOT EXISTS crawl_urls (
    url TEXT PRIMARY KEY,
    depth INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_SKIP_PREFIXES = ("javascript:", "mailto:", "tel:", "#", "data:")
_SKIP_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".css", ".gif", ".pdf", ".mp4", ".svg", ".ico",
    ".woff", ".woff2", ".js", ".zip", ".mp3", ".avi", ".mov", ".tar", ".gz",
    ".exe", ".webp",
)


class CrawlingService:
    """Stateful crawling engine used by ``bp.web``."""

    def __init__(self) -> None:
        self.rate_limit_rpm: int = 60

    # -- session state ------------------------------------------------------
    def init_crawl_session(self, db_path: str = "crawl_state.db") -> None:
        conn = sqlite3.connect(db_path)
        try:
            conn.executescript(_CRAWL_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def save_crawl_state(self, db_path: str, url: str,
                         status: str = "completed", depth: int = 0) -> None:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO crawl_urls (url, depth, status, timestamp)"
                " VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (url, depth, status))
            conn.commit()
        finally:
            conn.close()

    def recover_crawl_session(self, db_path: str) -> List[str]:
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                "SELECT url FROM crawl_urls WHERE status='pending'").fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()

    # -- link utilities -----------------------------------------------------
    def extract_links(self, base_url: str, html_content: Optional[str] = None,
                      result: Optional[Any] = None) -> List[str]:
        """Extracts absolute http(s) links from a scrape result and/or HTML."""
        links: List[str] = []
        if result is not None:
            candidate = getattr(result, "links", None)
            if isinstance(candidate, list):
                links.extend(str(l) for l in candidate)
            elif isinstance(result, dict) and isinstance(
                    result.get("links"), list):
                links.extend(str(l) for l in result["links"])

        if html_content:
            if _HAS_BS4:
                soup = BeautifulSoup(html_content, "html.parser")
                links.extend(
                    a.get("href") for a in soup.find_all("a", href=True))
            else:
                links.extend(re.findall(
                    r"<a\s+(?:[^>]*?\s+)?href=[\"']([^\"']+)[\"']",
                    html_content))

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
                    pass
        return {"disallowed_paths": disallowed, "crawl_delay": crawl_delay}

    def set_rate_limit(self, rpm: int) -> None:
        self.rate_limit_rpm = max(1, rpm)

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
        """BFS-crawls same-domain links up to ``max_depth``.

        ``scrape_fn(url, options)`` must return an object exposing the page
        HTML via an ``html``/``content``/``raw_html`` attribute (or dict key).
        Failures on individual pages are logged-and-skipped (resilience).
        """
        if scrape_fn is None:
            raise ValueError(
                "crawl_recursive requires a scrape_fn coroutine factory")

        self.init_crawl_session(db_path)
        self.save_crawl_state(db_path, url, status="pending", depth=0)

        visited: List[str] = []
        root_netloc = urlparse(url).netloc
        conn = sqlite3.connect(db_path)
        try:
            for depth in range(max_depth):
                if max_pages and len(visited) >= max_pages:
                    break
                pending = conn.execute(
                    "SELECT url FROM crawl_urls WHERE status='pending'"
                    " AND depth=?", (depth,)).fetchall()
                if not pending:
                    break
                for (curr_url,) in pending:
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
                            # Only accept real string content; skip None/MagicMock
                            if isinstance(val, str):
                                html = val
                                break
                        links = self.extract_links(curr_url, html, result)
                        filtered = self.filter_crawl_links(
                            f"https://{root_netloc}", links)
                        if depth + 1 < max_depth:
                            for link in filtered:
                                conn.execute(
                                    "INSERT OR IGNORE INTO crawl_urls"
                                    " (url, depth, status) VALUES (?, ?, 'pending')",
                                    (link, depth + 1))
                        conn.execute(
                            "UPDATE crawl_urls SET status='completed'"
                            " WHERE url=?", (curr_url,))
                        conn.commit()
                        visited.append(curr_url)
                        await asyncio.sleep(60.0 / self.rate_limit_rpm)
                    except Exception:  # resilience: skip failed pages
                        conn.execute(
                            "UPDATE crawl_urls SET status='failed'"
                            " WHERE url=?", (curr_url,))
                        conn.commit()
                        continue
        finally:
            conn.close()
        return visited

    def generate_crawl_report(self, db_path: str) -> Dict[str, Any]:
        conn = sqlite3.connect(db_path)
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


__all__ = ["CrawlingService"]
