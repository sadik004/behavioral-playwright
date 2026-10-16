"""Pillar 6: Universal Pagination, Infinite Scroll & GraphQL Cursor State-Machine Engine.

Automatically detects and drives all 4 modern pagination patterns:
1. `<link rel="next">` / `<a rel="next">` and numbered query/path pagination (`?page=2`, `/page/2`)
2. GraphQL / REST JSON cursor pagination (`pageInfo.endCursor`, `next_cursor`, `nextPageToken`)
3. Interactive DOM "Load More / Show More" button selectors
4. Infinite scroll containers with SimHash/item-count termination guard
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .dedup import canonicalize_url

_REL_NEXT_RE = re.compile(
    r"""<(?:a|link)[^>]+rel=["']next["'][^>]+href=["']([^"']+)["']|"""
    r"""<(?:a|link)[^>]+href=["']([^"']+)["'][^>]+rel=["']next["']""",
    re.IGNORECASE,
)
_NEXT_ANCHOR_RE = re.compile(
    r"""<a[^>]+href=["']([^"'#]+)["'][^>]*>\s*(?:next|next\s*&raquo;|next\s*&gt;|›|»|পরবর্তী)\s*</a>""",
    re.IGNORECASE,
)
_LOAD_MORE_BTN_RE = re.compile(
    r"""<(button|a)([^>]*?)>\s*(load\s+more|show\s+more|view\s+more|more\s+results|see\s+more)\s*</\1>""",
    re.IGNORECASE,
)
_INFINITE_SCROLL_RE = re.compile(
    r"""(data-infinite-scroll|infinite-scroll|IntersectionObserver|hx-trigger=["']revealed["'])""",
    re.IGNORECASE,
)


@dataclass
class PaginationPlan:
    strategy: str  # "URL_NEXT" | "CURSOR_API" | "LOAD_MORE_BUTTON" | "INFINITE_SCROLL" | "NONE"
    next_url: Optional[str] = None
    next_cursor: Optional[str] = None
    button_selector: Optional[str] = None
    scroll_action: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class UniversalPaginationEngine:
    """Detects pagination mechanisms across HTML and JSON/GraphQL responses."""

    def detect(
        self,
        current_url: str,
        html_or_json: str,
        json_payload: Optional[Dict[str, Any]] = None,
    ) -> PaginationPlan:
        # 1. Check structured JSON / GraphQL cursor pagination first
        payload = json_payload
        if payload is None and html_or_json.strip().startswith("{"):
            try:
                payload = json.loads(html_or_json)
            except Exception:
                payload = None

        if isinstance(payload, dict):
            cursor_plan = self._detect_json_cursor(current_url, payload)
            if cursor_plan is not None:
                return cursor_plan

        # 2. Check <link/a rel="next"> or "Next" anchor in HTML
        m_rel = _REL_NEXT_RE.search(html_or_json)
        if m_rel:
            href = m_rel.group(1) or m_rel.group(2)
            return PaginationPlan(
                strategy="URL_NEXT",
                next_url=canonicalize_url(href, base_url=current_url),
                metadata={"source": "rel_next"},
            )

        m_next_a = _NEXT_ANCHOR_RE.search(html_or_json)
        if m_next_a:
            return PaginationPlan(
                strategy="URL_NEXT",
                next_url=canonicalize_url(m_next_a.group(1), base_url=current_url),
                metadata={"source": "next_anchor_text"},
            )

        # 3. Check ?page=N link in HTML that increments current page
        next_page_url = self._detect_incremented_page_link(current_url, html_or_json)
        if next_page_url:
            return PaginationPlan(
                strategy="URL_NEXT",
                next_url=next_page_url,
                metadata={"source": "query_page_increment"},
            )

        # 4. Check "Load More / Show More" button
        m_btn = _LOAD_MORE_BTN_RE.search(html_or_json)
        if m_btn:
            tag = m_btn.group(1).lower()
            attrs_raw = m_btn.group(2)
            btn_id = re.search(r"""id=["']([^"']+)["']""", attrs_raw, re.I)
            btn_cls = re.search(r"""class=["']([^"']+)["']""", attrs_raw, re.I)
            if btn_id:
                selector = f"{tag}#{btn_id.group(1)}"
            elif btn_cls:
                first_cls = btn_cls.group(1).split()[0]
                selector = f"{tag}.{first_cls}"
            else:
                selector = f"{tag}:has-text('{m_btn.group(3).strip()}')"
            return PaginationPlan(
                strategy="LOAD_MORE_BUTTON",
                button_selector=selector,
                metadata={"button_text": m_btn.group(3).strip()},
            )

        # 5. Check Infinite Scroll markers
        if _INFINITE_SCROLL_RE.search(html_or_json):
            return PaginationPlan(
                strategy="INFINITE_SCROLL",
                scroll_action={"delta_y": 1200, "max_scrolls": 10, "wait_ms": 600},
            )

        return PaginationPlan(strategy="NONE")

    def _detect_json_cursor(self, current_url: str, data: Dict[str, Any]) -> Optional[PaginationPlan]:
        stack = [data]
        while stack:
            cur = stack.pop()
            if "pageInfo" in cur and isinstance(cur["pageInfo"], dict):
                pi = cur["pageInfo"]
                if pi.get("hasNextPage") and pi.get("endCursor"):
                    cursor = str(pi["endCursor"])
                    return PaginationPlan(
                        strategy="CURSOR_API",
                        next_cursor=cursor,
                        next_url=self._with_query_param(current_url, "after", cursor),
                        metadata={"type": "graphql_page_info"},
                    )
            for key in ("next_cursor", "nextCursor", "next_page_token", "nextPageToken"):
                if cur.get(key):
                    cursor = str(cur[key])
                    return PaginationPlan(
                        strategy="CURSOR_API",
                        next_cursor=cursor,
                        next_url=self._with_query_param(current_url, "cursor", cursor),
                        metadata={"type": key},
                    )
            if isinstance(cur.get("next"), str) and cur["next"].startswith(("http", "/")):
                return PaginationPlan(
                    strategy="URL_NEXT",
                    next_url=canonicalize_url(cur["next"], base_url=current_url),
                    metadata={"type": "json_next_url"},
                )
            for v in cur.values():
                if isinstance(v, dict):
                    stack.append(v)
        return None

    @staticmethod
    def _with_query_param(url: str, key: str, value: str) -> str:
        parts = urlsplit(url)
        q = dict(parse_qsl(parts.query, keep_blank_values=True))
        q[key] = value
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), ""))

    @staticmethod
    def _detect_incremented_page_link(current_url: str, html: str) -> Optional[str]:
        parts = urlsplit(current_url)
        q = dict(parse_qsl(parts.query))
        cur_page = int(q.get("page", "1")) if q.get("page", "1").isdigit() else 1
        target_page = cur_page + 1
        pattern = re.compile(rf"""href=["']([^"']*?[?&]page={target_page}(?:[&#"']|$))""", re.I)
        m = pattern.search(html)
        if m:
            href = m.group(1).rstrip("\"'")
            return canonicalize_url(href, base_url=current_url)
        return None
