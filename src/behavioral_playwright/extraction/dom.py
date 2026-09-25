import json
import re
from typing import Any, Dict, List, Optional

from behavioral_playwright.exceptions import ExtractionError
from behavioral_playwright.models.results import ExtractionRecord


class DOMExtractor:
    """Provides structured data extraction from web pages."""

    async def extract_links(
        self,
        page: Any,
        container_selector: Optional[str] = None
    ) -> List[ExtractionRecord]:
        """Extracts structured hyperlink records from page."""
        try:
            script = f"""
            () => {{
                const root = {f"document.querySelector('{container_selector}')" if container_selector else "document"};
                if (!root) return [];
                const anchors = Array.from(root.querySelectorAll('a[href]'));
                return anchors.map(a => {{
                    return {{
                        text: (a.innerText || a.textContent || '').trim(),
                        href: a.href || a.getAttribute('href') || '',
                        attributes: {{
                            title: a.getAttribute('title') || '',
                            target: a.getAttribute('target') || '',
                            rel: a.getAttribute('rel') || '',
                            class: a.className || ''
                        }},
                        metadata: {{
                            id: a.id || ''
                        }}
                    }};
                }}).filter(item => item.text.length > 0 && item.href.length > 0);
            }}
            """
            raw_data = await page.evaluate(script)
            if not isinstance(raw_data, list):
                return []

            records = []
            for item in raw_data:
                records.append(ExtractionRecord(
                    text=item.get("text", ""),
                    href=item.get("href"),
                    attributes=item.get("attributes", {}),
                    metadata=item.get("metadata", {})
                ))
            return records
        except Exception as e:
            raise ExtractionError(f"Failed to extract links: {e}") from e

    async def extract_table(
        self,
        page: Any,
        table_selector: str
    ) -> List[Dict[str, str]]:
        """Extracts HTML table rows as a list of dictionaries keyed by header text."""
        try:
            script = f"""
            () => {{
                const table = document.querySelector('{table_selector}');
                if (!table) return [];
                const headers = Array.from(table.querySelectorAll('th')).map(th => th.innerText.trim());
                const rows = Array.from(table.querySelectorAll('tbody tr, tr')).filter(r => r.querySelectorAll('td').length > 0);
                
                return rows.map(r => {{
                    const cells = Array.from(r.querySelectorAll('td')).map(td => td.innerText.trim());
                    const rowObj = {{}};
                    cells.forEach((cell, idx) => {{
                        const key = headers[idx] || 'col_' + idx;
                        rowObj[key] = cell;
                    }});
                    return rowObj;
                }});
            }}
            """
            result = await page.evaluate(script)
            return result if isinstance(result, list) else []
        except Exception as e:
            raise ExtractionError(f"Failed to extract table '{table_selector}': {e}") from e

    async def extract_articles(
        self,
        page: Any,
        container_selector: Optional[str] = None
    ) -> List[ExtractionRecord]:
        """Extracts structured article blocks (headings, summaries, and links)."""
        try:
            script = f"""
            () => {{
                const root = {f"document.querySelector('{container_selector}')" if container_selector else "document"};
                if (!root) return [];
                const cards = Array.from(root.querySelectorAll('article, div.card, div[class*="article"], div[class*="story"], div[class*="post"]'));
                
                return cards.map(c => {{
                    const hEl = c.querySelector('h1, h2, h3, h4, .title, a');
                    const aEl = c.querySelector('a[href]') || (c.tagName.toLowerCase() === 'a' ? c : null);
                    const descEl = c.querySelector('p, .summary, .description');
                    
                    const title = hEl ? (hEl.innerText || '').trim() : '';
                    const href = aEl ? (aEl.href || aEl.getAttribute('href') || '') : '';
                    const summary = descEl ? (descEl.innerText || '').trim() : '';
                    
                    return {{
                        text: title,
                        href: href,
                        attributes: {{
                            summary: summary
                        }},
                        metadata: {{
                            tag: c.tagName.toLowerCase()
                        }}
                    }};
                }}).filter(item => item.text.length > 5);
            }}
            """
            raw_data = await page.evaluate(script)
            if not isinstance(raw_data, list):
                return []

            records = []
            for item in raw_data:
                records.append(ExtractionRecord(
                    text=item.get("text", ""),
                    href=item.get("href"),
                    attributes=item.get("attributes", {}),
                    metadata=item.get("metadata", {})
                ))
            return records
        except Exception as e:
            raise ExtractionError(f"Failed to extract articles: {e}") from e

    async def extract_next_data(self, page: Any) -> Optional[Dict[str, Any]]:
        """Extracts Next.js __NEXT_DATA__ state dictionary."""
        return await extract_next_data(page)

    async def extract_nuxt_data(self, page: Any) -> Optional[Dict[str, Any]]:
        """Extracts Nuxt.js __NUXT__ or __NUXT_DATA__ state dictionary."""
        return await extract_nuxt_data(page)

    async def extract_json_ld(self, page: Any) -> List[Dict[str, Any]]:
        """Extracts and unpacks JSON-LD schema objects (@graph unnested)."""
        return await extract_json_ld(page)

    async def extract_open_graph(self, page: Any) -> Dict[str, str]:
        """Extracts OpenGraph and Twitter card metadata tags."""
        return await extract_open_graph(page)


async def extract_next_data(page: Any) -> Optional[Dict[str, Any]]:
    """
    Locates <script id="__NEXT_DATA__" type="application/json"> or evaluates window.__NEXT_DATA__.
    Parses with json.loads and returns the complete dictionary (especially pageProps) with zero DOM traversal.
    Supports Playwright Page, PageSession, or static HTML string.
    """
    try:
        if isinstance(page, str):
            match = re.search(r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', page, re.DOTALL | re.IGNORECASE)
            if match:
                return json.loads(match.group(1).strip())
            return None

        if hasattr(page, "evaluate") and callable(page.evaluate):
            raw_page = page
        else:
            raw_page = getattr(page, "raw_page", None) or page

        script = """
        () => {
            if (window.__NEXT_DATA__) {
                return JSON.stringify(window.__NEXT_DATA__);
            }
            const el = document.getElementById('__NEXT_DATA__') || document.querySelector('script#__NEXT_DATA__');
            return el ? (el.textContent || el.innerText || null) : null;
        }
        """
        raw_val = await raw_page.evaluate(script)
        if not raw_val:
            return None
        if isinstance(raw_val, dict):
            return raw_val
        return json.loads(raw_val)
    except Exception as exc:
        raise ExtractionError(f"Failed to extract __NEXT_DATA__: {exc}") from exc


async def extract_nuxt_data(page: Any) -> Optional[Dict[str, Any]]:
    """
    Evaluates window.__NUXT__ or parses <script id="__NUXT_DATA__">.
    Supports Playwright Page, PageSession, or static HTML string.
    """
    try:
        if isinstance(page, str):
            match_script = re.search(r'<script[^>]*id=["\']__NUXT_DATA__["\'][^>]*>(.*?)</script>', page, re.DOTALL | re.IGNORECASE)
            if match_script:
                try:
                    return json.loads(match_script.group(1).strip())
                except Exception:
                    pass
            match_var = re.search(r'window\.__NUXT__\s*=\s*(\{.*?\});', page, re.DOTALL)
            if match_var:
                try:
                    return json.loads(match_var.group(1).strip())
                except Exception:
                    pass
            return None

        if hasattr(page, "evaluate") and callable(page.evaluate):
            raw_page = page
        else:
            raw_page = getattr(page, "raw_page", None) or page

        script = """
        () => {
            if (window.__NUXT__) {
                return JSON.stringify(window.__NUXT__);
            }
            const el = document.getElementById('__NUXT_DATA__') || document.querySelector('script#__NUXT_DATA__');
            return el ? (el.textContent || el.innerText || null) : null;
        }
        """
        raw_val = await raw_page.evaluate(script)
        if not raw_val:
            return None
        if isinstance(raw_val, dict):
            return raw_val
        return json.loads(raw_val)
    except Exception as exc:
        raise ExtractionError(f"Failed to extract Nuxt data: {exc}") from exc


async def extract_json_ld(page: Any) -> List[Dict[str, Any]]:
    """
    Locates all <script type="application/ld+json"> elements.
    If the root object contains @graph, unpacks all nested items into individual schema dictionaries
    (Product, FAQPage, Article, Organization, etc.).
    Supports Playwright Page, PageSession, or static HTML string.
    """
    try:
        raw_scripts: List[str] = []
        if isinstance(page, str):
            matches = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page, re.DOTALL | re.IGNORECASE)
            raw_scripts = [m.strip() for m in matches if m.strip()]
        else:
            if hasattr(page, "evaluate") and callable(page.evaluate):
                raw_page = page
            else:
                raw_page = getattr(page, "raw_page", None) or page
            script = """
            () => {
                const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
                return scripts.map(s => (s.textContent || s.innerText || '').trim()).filter(Boolean);
            }
            """
            eval_res = await raw_page.evaluate(script)
            if isinstance(eval_res, list):
                raw_scripts = [s for s in eval_res if isinstance(s, str) and s]

        schemas: List[Dict[str, Any]] = []
        for raw_text in raw_scripts:
            try:
                parsed = json.loads(raw_text)
            except Exception:
                continue

            def _unpack_item(item: Any) -> None:
                if not isinstance(item, dict):
                    return
                if "@graph" in item and isinstance(item["@graph"], list):
                    for sub_item in item["@graph"]:
                        _unpack_item(sub_item)
                else:
                    schemas.append(item)

            if isinstance(parsed, list):
                for item in parsed:
                    _unpack_item(item)
            elif isinstance(parsed, dict):
                _unpack_item(parsed)

        return schemas
    except Exception as exc:
        raise ExtractionError(f"Failed to extract JSON-LD: {exc}") from exc


async def extract_open_graph(page: Any) -> Dict[str, str]:
    """
    Extracts og:* and twitter:* meta tags into a normalized dictionary.
    Supports Playwright Page, PageSession, or static HTML string.
    """
    try:
        if isinstance(page, str):
            result: Dict[str, str] = {}
            tag_matches = re.findall(r'<meta[^>]+(?:property|name)=["\']((?:og|twitter):[^"\']+)["\'][^>]+content=["\']([^"\']*)["\']', page, re.IGNORECASE)
            for k, v in tag_matches:
                result[k.strip().lower()] = v.strip()
            rev_matches = re.findall(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']((?:og|twitter):[^"\']+)["\']', page, re.IGNORECASE)
            for v, k in rev_matches:
                if k.strip().lower() not in result:
                    result[k.strip().lower()] = v.strip()
            return result

        if hasattr(page, "evaluate") and callable(page.evaluate):
            raw_page = page
        else:
            raw_page = getattr(page, "raw_page", None) or page
        script = """
        () => {
            const tags = Array.from(document.querySelectorAll('meta[property^="og:"], meta[name^="og:"], meta[property^="twitter:"], meta[name^="twitter:"]'));
            const res = {};
            for (const tag of tags) {
                const key = tag.getAttribute('property') || tag.getAttribute('name');
                const content = tag.getAttribute('content');
                if (key && content !== null) {
                    res[key.trim().toLowerCase()] = content.trim();
                }
            }
            return res;
        }
        """
        eval_res = await raw_page.evaluate(script)
        if isinstance(eval_res, dict):
            return {str(k): str(v) for k, v in eval_res.items()}
        return {}
    except Exception as exc:
        raise ExtractionError(f"Failed to extract Open Graph metadata: {exc}") from exc


__all__ = [
    "DOMExtractor",
    "extract_next_data",
    "extract_nuxt_data",
    "extract_json_ld",
    "extract_open_graph",
]
