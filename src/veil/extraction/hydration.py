"""Pillar 3: Zero-DOM Hydration & Passive API Harvester.

Extracts structured database records directly from SSR/CSR hydration payloads
before touching fragile DOM selectors:
1. Next.js Pages Router (`<script id="__NEXT_DATA__">`)
2. Next.js App Router React Server Components (`self.__next_f.push([1, "..."])`)
3. Nuxt / Remix / Redux / Apollo (`window.__NUXT__`, `window.__INITIAL_STATE__`, `window.__APOLLO_STATE__`)
4. Structured Schema.org (`<script type="application/ld+json">`) & OpenGraph (`og:*`)
5. Passive inline API / GraphQL endpoint discovery (`/api/...`, `/graphql`)
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

_NEXT_DATA_RE = re.compile(
    r"""<script[^>]+id=["']__NEXT_DATA__["'][^>]*>(.*?)</script>""",
    re.IGNORECASE | re.DOTALL,
)
_NEXT_RSC_RE = re.compile(
    r"""self\.__next_f\.push\(\s*\[\s*\d+\s*,\s*("(?:\\.|[^"\\])*")\s*\]\s*\)""",
    re.DOTALL,
)
_WINDOW_STATE_RE = re.compile(
    r"""window\.(?:__INITIAL_STATE__|__NUXT__|__APOLLO_STATE__|__remixContext|__PRELOADED_STATE__)\s*=\s*(\{.*?\})\s*;?\s*</script>""",
    re.DOTALL,
)
_JSON_LD_RE = re.compile(
    r"""<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>""",
    re.IGNORECASE | re.DOTALL,
)
_OG_META_RE = re.compile(
    r"""<meta[^>]+property=["'](og:[a-zA-Z0-9_:-]+)["'][^>]+content=["']([^"']*)["']""",
    re.IGNORECASE,
)
_API_ENDPOINT_RE = re.compile(
    r"""["']((?:https?://[^"']+)?/(?:api|graphql|v1|v2|v3)/[a-zA-Z0-9_./?-]+)["']"""
)


def extract_hydration_state(html: str) -> Dict[str, Any]:
    """Extracts all structured SSR/CSR hydration states and passive API endpoints from raw HTML."""
    result: Dict[str, Any] = {
        "next_data": None,
        "next_rsc_chunks": [],
        "window_state": None,
        "json_ld": [],
        "open_graph": {},
        "discovered_api_endpoints": [],
        "has_structured_payload": False,
    }

    if not html:
        return result

    # 1. Next.js __NEXT_DATA__
    m_next = _NEXT_DATA_RE.search(html)
    if m_next:
        try:
            result["next_data"] = json.loads(m_next.group(1).strip())
            result["has_structured_payload"] = True
        except Exception:
            _ = "malformed_next_data"

    # 2. Next.js App Router RSC chunks: self.__next_f.push([1, "..."])
    for m_rsc in _NEXT_RSC_RE.finditer(html):
        try:
            decoded_str = json.loads(m_rsc.group(1))
            if isinstance(decoded_str, str):
                for line in decoded_str.splitlines():
                    if ":" in line:
                        _, payload = line.split(":", 1)
                        payload = payload.strip()
                        if payload.startswith(("{", "[")):
                            try:
                                parsed_obj = json.loads(payload)
                                result["next_rsc_chunks"].append(parsed_obj)
                                result["has_structured_payload"] = True
                            except Exception:
                                continue
        except Exception:
            continue

    # 3. Window state (__INITIAL_STATE__, __NUXT__, __APOLLO_STATE__)
    m_win = _WINDOW_STATE_RE.search(html)
    if m_win:
        try:
            result["window_state"] = json.loads(m_win.group(1).strip())
            result["has_structured_payload"] = True
        except Exception:
            _ = "malformed_window_state"

    # 4. JSON-LD blocks
    for m_ld in _JSON_LD_RE.finditer(html):
        raw_ld = m_ld.group(1).strip()
        if not raw_ld:
            continue
        try:
            parsed_ld = json.loads(raw_ld)
            if isinstance(parsed_ld, list):
                result["json_ld"].extend(parsed_ld)
            else:
                result["json_ld"].append(parsed_ld)
            result["has_structured_payload"] = True
        except Exception:
            continue

    # 5. OpenGraph tags
    for m_og in _OG_META_RE.finditer(html):
        result["open_graph"][m_og.group(1).lower()] = m_og.group(2)
    if result["open_graph"]:
        result["has_structured_payload"] = True

    # 6. Passive API / GraphQL endpoint discovery
    seen_eps: set[str] = set()
    eps: List[str] = []
    for m_ep in _API_ENDPOINT_RE.finditer(html):
        ep = m_ep.group(1)
        if ep not in seen_eps:
            seen_eps.add(ep)
            eps.append(ep)
    result["discovered_api_endpoints"] = eps

    return result
