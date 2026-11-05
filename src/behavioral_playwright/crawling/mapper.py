"""Pillar 4B: Instant `/map` Site Topology & Sitemap Discovery Engine.

Discovers a site's URL structure in sub-second time without full page rendering by combining:
1. `/robots.txt` (`Sitemap:` directives and `Disallow:` rules)
2. `/sitemap.xml`, `/sitemap_index.xml`, and gzipped `.xml.gz` sitemaps
3. Homepage `<a href>` links and Next.js `_buildManifest.js` route paths
"""

from __future__ import annotations

import gzip
import re
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

from .dedup import canonicalize_url

_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.IGNORECASE)
_HREF_RE = re.compile(r"""<a[^>]+href=["']([^"'#]+)["']""", re.IGNORECASE)
_NEXT_ROUTES_RE = re.compile(r"sortedPages\s*:\s*\[(.*?)\]", re.DOTALL)


@dataclass
class MappedUrl:
    url: str
    source: str  # "sitemap" | "robots_sitemap" | "html_link" | "js_manifest"
    priority_score: float = 1.0


class SiteMapper:
    """Fast `/map` site topology discovery engine."""

    def __init__(
        self,
        fetcher: Optional[Callable[[str], Awaitable[Tuple[int, bytes, Dict[str, str]]]]] = None,
    ) -> None:
        self._fetcher = fetcher or self._default_fetcher

    @staticmethod
    async def _default_fetcher(url: str) -> Tuple[int, bytes, Dict[str, str]]:
        import asyncio
        import urllib.error
        import urllib.request

        def _sync_get() -> Tuple[int, bytes, Dict[str, str]]:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VeilMapper/10.0"},
            )
            try:
                with urllib.request.urlopen(req, timeout=8.0) as resp:
                    return resp.status, resp.read(), {k: v for k, v in resp.headers.items()}
            except urllib.error.HTTPError as exc:
                return exc.code, (exc.read() if exc.fp else b""), (dict(exc.headers.items()) if exc.headers else {})
            except Exception:
                return 0, b"", {}

        return await asyncio.to_thread(_sync_get)

    async def map_site(
        self,
        base_url: str,
        search_query: Optional[str] = None,
        max_urls: int = 5000,
    ) -> List[MappedUrl]:
        parsed_base = urlparse(base_url)
        root_origin = f"{parsed_base.scheme or 'https'}://{parsed_base.netloc}"
        target_host = (parsed_base.hostname or "").lower()

        discovered: Dict[str, MappedUrl] = {}
        disallowed_prefixes: List[str] = []
        sitemap_urls: List[str] = [urljoin(root_origin, "/sitemap.xml")]

        # 1. Fetch /robots.txt
        robots_url = urljoin(root_origin, "/robots.txt")
        status, raw_bytes, _ = await self._fetcher(robots_url)
        if status == 200 and raw_bytes:
            robots_txt = raw_bytes.decode("utf-8", errors="ignore")
            for line in robots_txt.splitlines():
                line_s = line.strip()
                if line_s.lower().startswith("sitemap:"):
                    sm = line_s.split(":", 1)[1].strip()
                    if sm and sm not in sitemap_urls:
                        sitemap_urls.insert(0, sm)
                elif line_s.lower().startswith("disallow:"):
                    dis = line_s.split(":", 1)[1].strip()
                    if dis and dis != "/":
                        disallowed_prefixes.append(dis)

        # 2. Parse Sitemaps (including nested sitemap_index and .xml.gz)
        visited_sitemaps: Set[str] = set()
        queue = list(sitemap_urls)
        while queue and len(discovered) < max_urls:
            sm_url = queue.pop(0)
            if sm_url in visited_sitemaps:
                continue
            visited_sitemaps.add(sm_url)

            st, body_bytes, _ = await self._fetcher(sm_url)
            if st != 200 or not body_bytes:
                continue
            if sm_url.endswith(".gz") or body_bytes[:2] == b"\x1f\x8b":
                try:
                    body_bytes = gzip.decompress(body_bytes)
                except Exception:
                    continue
            xml_text = body_bytes.decode("utf-8", errors="ignore")
            for m_loc in _LOC_RE.finditer(xml_text):
                loc = m_loc.group(1).strip()
                if loc.endswith((".xml", ".xml.gz")) and "sitemap" in loc.lower():
                    if loc not in visited_sitemaps:
                        queue.append(loc)
                else:
                    self._add_candidate(
                        discovered,
                        loc,
                        base_url=root_origin,
                        target_host=target_host,
                        source="sitemap",
                        disallowed=disallowed_prefixes,
                        query=search_query,
                    )

        # 3. Fetch Homepage HTML for `<a href>` and Next.js buildManifest routes
        st_home, home_bytes, _ = await self._fetcher(base_url)
        if st_home == 200 and home_bytes:
            home_html = home_bytes.decode("utf-8", errors="ignore")
            for m_href in _HREF_RE.finditer(home_html):
                self._add_candidate(
                    discovered,
                    m_href.group(1),
                    base_url=base_url,
                    target_host=target_host,
                    source="html_link",
                    disallowed=disallowed_prefixes,
                    query=search_query,
                )
            for m_routes in _NEXT_ROUTES_RE.finditer(home_html):
                for route in re.findall(r"""["'](/[^"']*?)["']""", m_routes.group(1)):
                    if not route.startswith("/_") and "[" not in route:
                        self._add_candidate(
                            discovered,
                            urljoin(root_origin, route),
                            base_url=root_origin,
                            target_host=target_host,
                            source="js_manifest",
                            disallowed=disallowed_prefixes,
                            query=search_query,
                        )

        results = sorted(
            discovered.values(),
            key=lambda item: (-item.priority_score, item.url),
        )
        return results[:max_urls]

    @staticmethod
    def _add_candidate(
        discovered: Dict[str, MappedUrl],
        raw_url: str,
        base_url: str,
        target_host: str,
        source: str,
        disallowed: List[str],
        query: Optional[str],
    ) -> None:
        if raw_url.startswith(("javascript:", "mailto:", "tel:")):
            return
        canon = canonicalize_url(raw_url, base_url=base_url)
        parsed = urlparse(canon)
        if (parsed.hostname or "").lower() != target_host:
            return
        if any(parsed.path.startswith(prefix) for prefix in disallowed):
            return
        if canon in discovered:
            return

        score = 1.0
        if source == "sitemap":
            score += 0.3
        elif source == "js_manifest":
            score += 0.2
        if query:
            q_tokens = re.findall(r"[a-z0-9]+", query.lower())
            url_l = canon.lower()
            matches = sum(1 for tok in q_tokens if tok in url_l)
            score += matches * 1.5

        discovered[canon] = MappedUrl(url=canon, source=source, priority_score=round(score, 3))
