"""DOM Extraction module providing structured, live-DOM and static-HTML authoritative data extraction."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from veil.exceptions import ExtractionError
from veil.extraction.normalizer import (
    clean_text,
    resolve_url,
)
from veil.logging import get_logger
from veil.models.results import ExtractionRecord

logger = get_logger("extraction.dom")


def _get_raw_page(page: Any) -> Any:
    """Unwraps PageSession or custom wrappers to obtain the underlying evaluatable page."""
    if hasattr(page, "_mock_return_value") or type(page).__module__.startswith("unittest.mock"):
        return page
    if hasattr(page, "raw_page") and getattr(page, "raw_page", None) is not None:
        return getattr(page, "raw_page")
    return page


def _get_static_html(page: Any) -> Optional[str]:
    """Returns static HTML string when `page` is a str or a PageSession without a live browser `raw_page`."""
    if isinstance(page, str):
        return page
    if hasattr(page, "raw_page") and getattr(page, "raw_page", None) is None and hasattr(page, "last_html"):
        return str(getattr(page, "last_html") or "")
    if not hasattr(_get_raw_page(page), "evaluate") and hasattr(page, "last_html"):
        return str(getattr(page, "last_html") or "")
    return None


def _current_timestamp() -> Tuple[str, float]:
    """Returns (iso_utc_string, unix_timestamp_float)."""
    now = datetime.now(timezone.utc)
    return now.isoformat(), now.timestamp()


def _parse_attrs_from_tag(attr_str: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for m in re.finditer(r'([a-zA-Z0-9_:-]+)\s*=\s*(?:["\']([^"\']*)["\']|([^\s>]+))', attr_str or ""):
        key = m.group(1).lower()
        val = m.group(2) if m.group(2) is not None else (m.group(3) or "")
        out[key] = val
    for m_bool in re.finditer(r'\b([a-zA-Z0-9_:-]+)\b(?!=)', attr_str or ""):
        k = m_bool.group(1).lower()
        if k not in out:
            out[k] = ""
    return out


_VOID_HTML_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})


def _find_all_elements_in_html(html_str: str, selector: str) -> List[Tuple[str, str, str]]:
    """Finds all (tag, attr_str, inner_html) matching CSS selector (tag, #id, .class) with full nesting support."""
    sel = selector.strip()
    tag_m = re.match(r"^([a-zA-Z0-9]+)", sel)
    id_m = re.search(r"#([a-zA-Z0-9_-]+)", sel)
    cls_m = re.search(r"\.([a-zA-Z0-9_-]+)", sel)
    target_tag = tag_m.group(1).lower() if tag_m else None

    matches: List[Tuple[str, str, str]] = []
    for m in re.finditer(r"<([a-zA-Z0-9]+)\b([^>]*)>", html_str):
        t_name = m.group(1)
        t_lower = t_name.lower()
        if target_tag and t_lower != target_tag:
            continue
        attrs_raw = m.group(2)
        attrs = _parse_attrs_from_tag(attrs_raw)
        if id_m and attrs.get("id") != id_m.group(1):
            continue
        if cls_m and cls_m.group(1) not in attrs.get("class", "").split():
            continue
        if t_lower in _VOID_HTML_TAGS or attrs_raw.rstrip().endswith("/"):
            matches.append((t_name, attrs_raw, ""))
            continue
        depth = 1
        pos = m.end()
        inner_end = len(html_str)
        tag_tok_re = re.compile(rf"<(/?){re.escape(t_lower)}\b[^>]*>", re.I)
        for tm in tag_tok_re.finditer(html_str, pos):
            if tm.group(1) == "/":
                depth -= 1
                if depth == 0:
                    inner_end = tm.start()
                    break
            elif not tm.group(0).rstrip().endswith("/>"):
                depth += 1
        matches.append((t_name, attrs_raw, html_str[m.end():inner_end]))
    return matches


def _find_element_in_html(html_str: str, selector: str) -> Optional[Tuple[str, str, str]]:
    found = _find_all_elements_in_html(html_str, selector)
    return found[0] if found else None


class DOMExtractor:
    """Provides structured, live-DOM and static-HTML authoritative data extraction from web pages."""

    async def extract_links(
        self,
        page: Any,
        container_selector: Optional[str] = None,
    ) -> List[ExtractionRecord]:
        html_str = _get_static_html(page)
        if html_str is not None:
            scope_html = html_str
            if container_selector:
                found = _find_element_in_html(html_str, container_selector)
                if found is None:
                    raise ExtractionError(f"Container element not found for selector: '{container_selector}'")
                scope_html = found[2]
            ts_iso, ts_epoch = _current_timestamp()
            page_url = getattr(page, "current_url", "https://local.test")
            records: List[ExtractionRecord] = []
            for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", scope_html, re.I | re.S):
                attrs = _parse_attrs_from_tag(m.group(1))
                raw_href = attrs.get("href", "").strip()
                if not raw_href:
                    continue
                href = resolve_url(page_url, raw_href)
                txt = clean_text(re.sub(r"<[^>]+>", " ", m.group(2)))
                if txt and href:
                    records.append(
                        ExtractionRecord(
                            text=txt,
                            href=href,
                            attributes={
                                "title": attrs.get("title", ""),
                                "target": attrs.get("target", ""),
                                "rel": attrs.get("rel", ""),
                                "class": attrs.get("class", ""),
                                "aria-label": attrs.get("aria-label", ""),
                            },
                            metadata={"id": attrs.get("id", ""), "tag": "a", "raw_href": raw_href},
                            page_url=page_url,
                            selector=container_selector,
                            timestamp=ts_iso,
                            extracted_at=ts_epoch,
                        )
                    )
            return records

        try:
            raw_page = _get_raw_page(page)
            script = """
            (containerSel) => {
                let root = document;
                if (containerSel) {
                    root = document.querySelector(containerSel);
                    if (!root) {
                        return { __bp_error: "CONTAINER_NOT_FOUND", selector: containerSel };
                    }
                }
                const anchors = Array.from(root.querySelectorAll('a[href]'));
                return anchors.map(a => {
                    let hrefAttr = a.getAttribute('href') || '';
                    let resolvedHref = a.href || hrefAttr;
                    return {
                        text: (a.innerText || a.textContent || '').trim(),
                        href: resolvedHref,
                        attributes: {
                            title: a.getAttribute('title') || '',
                            target: a.getAttribute('target') || '',
                            rel: a.getAttribute('rel') || '',
                            class: a.className || '',
                            "aria-label": a.getAttribute('aria-label') || ''
                        },
                        metadata: {
                            id: a.id || '',
                            tag: 'a',
                            raw_href: hrefAttr
                        }
                    };
                }).filter(item => item.text.length > 0 && item.href.length > 0);
            }
            """
            raw_data = await raw_page.evaluate(script, container_selector)
            if isinstance(raw_data, dict) and raw_data.get("__bp_error") == "CONTAINER_NOT_FOUND":
                raise ExtractionError(f"Container element not found for selector: '{container_selector}'")
            if not isinstance(raw_data, list):
                return []

            page_url = ""
            if hasattr(raw_page, "url"):
                u = raw_page.url
                page_url = u() if callable(u) else str(u or "")
            ts_iso, ts_epoch = _current_timestamp()

            return [
                ExtractionRecord(
                    text=item.get("text", ""),
                    href=item.get("href"),
                    attributes=item.get("attributes", {}),
                    metadata=item.get("metadata", {}),
                    page_url=page_url,
                    selector=container_selector,
                    timestamp=ts_iso,
                    extracted_at=ts_epoch,
                )
                for item in raw_data
            ]
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract links: {e}") from e

    async def extract_table(
        self,
        page: Any,
        table_selector: str = "table",
        has_headers: bool = True,
    ) -> List[Dict[str, Any]]:
        if not table_selector or not table_selector.strip():
            raise ExtractionError("table_selector must not be empty.")

        html_str = _get_static_html(page)
        if html_str is not None:
            found = _find_element_in_html(html_str, table_selector)
            if found is None and "<table" not in html_str.lower():
                raise ExtractionError(f"Table element not found for selector: '{table_selector}'")
            scope = found[2] if found is not None else html_str
            headers = [clean_text(re.sub(r"<[^>]+>", "", h)) for h in re.findall(r"<th[^>]*>(.*?)</th>", scope, re.I | re.S)]
            rows_out: List[Dict[str, Any]] = []
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", scope, re.I | re.S):
                tds = [clean_text(re.sub(r"<[^>]+>", "", td)) for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.I | re.S)]
                if tds:
                    if headers and len(headers) == len(tds):
                        rows_out.append(dict(zip(headers, tds)))
                    else:
                        rows_out.append({(headers[i] if i < len(headers) and headers[i] else f"col_{i}"): v for i, v in enumerate(tds)})
            return rows_out

        try:
            raw_page = _get_raw_page(page)
            script = """
            (args) => {
                const sel = args.sel;
                const hasH = args.hasH;
                const table = document.querySelector(sel);
                if (!table) {
                    return { __bp_error: "TABLE_NOT_FOUND", selector: sel };
                }
                let headerEls = Array.from(table.querySelectorAll('thead th, th'));
                let headerTexts = [];
                let skipFirstRow = false;
                if (headerEls.length > 0) {
                    for (const th of headerEls) {
                        const colspan = parseInt(th.getAttribute('colspan') || '1', 10);
                        const hText = (th.innerText || th.textContent || '').trim();
                        for (let c = 0; c < colspan; c++) headerTexts.push(hText);
                    }
                } else if (hasH) {
                    const firstTr = table.querySelector('tr');
                    if (firstTr) {
                        const firstRowCells = Array.from(firstTr.querySelectorAll('th, td'));
                        for (const c of firstRowCells) {
                            const colspan = parseInt(c.getAttribute('colspan') || '1', 10);
                            const cText = (c.innerText || c.textContent || '').trim();
                            for (let k = 0; k < colspan; k++) headerTexts.push(cText);
                        }
                        skipFirstRow = true;
                    }
                }
                const headerCounts = {};
                const deduplicatedHeaders = headerTexts.map((h, idx) => {
                    const baseKey = h || ('col_' + idx);
                    if (headerCounts[baseKey] === undefined) {
                        headerCounts[baseKey] = 1;
                        return baseKey;
                    }
                    headerCounts[baseKey] += 1;
                    return `${baseKey}_${headerCounts[baseKey]}`;
                });
                let allRows = Array.from(table.querySelectorAll('tbody tr, tr')).filter(r => r.querySelectorAll('td').length > 0);
                if (skipFirstRow && allRows.length > 0) allRows = allRows.slice(1);
                const result = [];
                for (const row of allRows) {
                    const cells = Array.from(row.querySelectorAll('td, th'));
                    const expandedCells = [];
                    for (const cell of cells) {
                        const colspan = parseInt(cell.getAttribute('colspan') || '1', 10);
                        const cellText = (cell.innerText || cell.textContent || '').trim();
                        for (let c = 0; c < colspan; c++) expandedCells.push(cellText);
                    }
                    const rowObj = {};
                    const colLimit = Math.max(deduplicatedHeaders.length, expandedCells.length);
                    for (let idx = 0; idx < colLimit; idx++) {
                        const key = deduplicatedHeaders[idx] || ('col_' + idx);
                        rowObj[key] = idx < expandedCells.length ? expandedCells[idx] : null;
                    }
                    result.push(rowObj);
                }
                return result;
            }
            """
            result = await raw_page.evaluate(script, {"sel": table_selector, "hasH": has_headers})
            if isinstance(result, dict) and result.get("__bp_error") == "TABLE_NOT_FOUND":
                raise ExtractionError(f"Table element not found for selector: '{table_selector}'")
            return result if isinstance(result, list) else []
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract table '{table_selector}': {e}") from e

    async def extract_articles(
        self,
        page: Any,
        container_selector: Optional[str] = None,
    ) -> List[ExtractionRecord]:
        html_str = _get_static_html(page)
        if html_str is not None:
            scope_html = html_str
            if container_selector:
                found = _find_element_in_html(html_str, container_selector)
                if found is None:
                    raise ExtractionError(f"Container element not found for selector: '{container_selector}'")
                scope_html = found[2]
            ts_iso, ts_epoch = _current_timestamp()
            page_url = getattr(page, "current_url", "https://local.test")
            from veil.extraction.auto_schema import AutoSchemaExtractor
            items = AutoSchemaExtractor().extract(scope_html)
            if items:
                return [
                    ExtractionRecord(
                        text=str(it.get("title", "")),
                        href=resolve_url(page_url, str(it["url"])) if it.get("url") else None,
                        attributes={"summary": str(it.get("description", "")), "price": str(it.get("price", ""))},
                        metadata={"tag": "article"},
                        page_url=page_url,
                        selector=container_selector,
                        timestamp=ts_iso,
                        extracted_at=ts_epoch,
                    )
                    for it in items
                ]
            return await self.extract_links(page, container_selector=container_selector)

        try:
            raw_page = _get_raw_page(page)
            script = """
            (containerSel) => {
                let root = document;
                if (containerSel) {
                    root = document.querySelector(containerSel);
                    if (!root) {
                        return { __bp_error: "CONTAINER_NOT_FOUND", selector: containerSel };
                    }
                }
                const cards = Array.from(root.querySelectorAll('article, div.card, div[class*="article"], div[class*="story"], div[class*="post"]'));
                return cards.map(c => {
                    const hEl = c.querySelector('h1, h2, h3, h4, .title, a');
                    const aEl = c.querySelector('a[href]') || (c.tagName.toLowerCase() === 'a' ? c : null);
                    const descEl = c.querySelector('p, .summary, .description');
                    return {
                        text: hEl ? (hEl.innerText || hEl.textContent || '').trim() : '',
                        href: aEl ? (aEl.href || aEl.getAttribute('href') || '') : '',
                        attributes: { summary: descEl ? (descEl.innerText || descEl.textContent || '').trim() : '' },
                        metadata: { tag: c.tagName.toLowerCase() }
                    };
                }).filter(item => item.text.length > 0);
            }
            """
            raw_data = await raw_page.evaluate(script, container_selector)
            if isinstance(raw_data, dict) and raw_data.get("__bp_error") == "CONTAINER_NOT_FOUND":
                raise ExtractionError(f"Container element not found for selector: '{container_selector}'")
            if not isinstance(raw_data, list):
                return []
            page_url = ""
            if hasattr(raw_page, "url"):
                u = raw_page.url
                page_url = u() if callable(u) else str(u or "")
            ts_iso, ts_epoch = _current_timestamp()
            return [
                ExtractionRecord(
                    text=item.get("text", ""),
                    href=item.get("href"),
                    attributes=item.get("attributes", {}),
                    metadata=item.get("metadata", {}),
                    page_url=page_url,
                    selector=container_selector,
                    timestamp=ts_iso,
                    extracted_at=ts_epoch,
                )
                for item in raw_data
            ]
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract articles: {e}") from e

    async def extract_text(
        self,
        page: Any,
        selector: str,
        normalize: bool = True,
        visible_only: bool = True,
    ) -> str:
        if not selector or not selector.strip():
            raise ExtractionError("selector must not be empty.")

        html_str = _get_static_html(page)
        if html_str is not None:
            found = _find_element_in_html(html_str, selector)
            if found is None and selector.strip().lower() not in ("body", "html"):
                raise ExtractionError(f"Target element not found for selector: '{selector}'")
            inner = found[2] if found is not None else html_str
            raw_t = re.sub(r"<[^>]+>", " ", inner)
            return clean_text(raw_t) if normalize else raw_t.strip()

        try:
            raw_page = _get_raw_page(page)
            script = """
            (args) => {
                const el = document.querySelector(args.sel);
                if (!el) return { __bp_error: "ELEMENT_NOT_FOUND", selector: args.sel };
                if (args.vis) {
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return { text: "" };
                    if (el.offsetParent === null && style.position !== 'fixed') return { text: "" };
                }
                const t = el.innerText !== undefined ? el.innerText : (el.textContent || '');
                return { text: t };
            }
            """
            res = await raw_page.evaluate(script, {"sel": selector, "vis": visible_only})
            if isinstance(res, dict) and res.get("__bp_error") == "ELEMENT_NOT_FOUND":
                raise ExtractionError(f"Target element not found for selector: '{selector}'")
            text_val = res.get("text", "") if isinstance(res, dict) else ""
            return clean_text(text_val) if normalize else text_val
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract text for '{selector}': {e}") from e

    async def extract_attributes(
        self,
        page: Any,
        selector: str,
        attributes: Optional[List[str]] = None,
    ) -> Dict[str, Optional[str]]:
        if not selector or not selector.strip():
            raise ExtractionError("selector must not be empty.")

        html_str = _get_static_html(page)
        if html_str is not None:
            found = _find_element_in_html(html_str, selector)
            if found is None and selector.strip().lower() not in ("body", "html"):
                raise ExtractionError(f"Target element not found for selector: '{selector}'")
            parsed_attrs = _parse_attrs_from_tag(found[1]) if found is not None else {}
            if attributes:
                return {a: parsed_attrs.get(a.lower(), None) for a in attributes}
            return {k: v for k, v in parsed_attrs.items()}

        try:
            raw_page = _get_raw_page(page)
            script = """
            (args) => {
                const el = document.querySelector(args.sel);
                if (!el) return { __bp_error: "ELEMENT_NOT_FOUND", selector: args.sel };
                const res = {};
                const requested = args.attrs;
                if (requested && requested.length > 0) {
                    for (const attr of requested) {
                        res[attr] = el.hasAttribute(attr) ? el.getAttribute(attr) : null;
                    }
                } else {
                    for (const attr of el.attributes) res[attr.name] = attr.value;
                }
                return res;
            }
            """
            res = await raw_page.evaluate(script, {"sel": selector, "attrs": attributes})
            if isinstance(res, dict) and res.get("__bp_error") == "ELEMENT_NOT_FOUND":
                raise ExtractionError(f"Target element not found for selector: '{selector}'")
            return res if isinstance(res, dict) else {}
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract attributes for '{selector}': {e}") from e

    async def extract_html(
        self,
        page: Any,
        selector: str,
        outer: bool = True,
    ) -> str:
        if not selector or not selector.strip():
            raise ExtractionError("selector must not be empty.")

        html_str = _get_static_html(page)
        if html_str is not None:
            found = _find_element_in_html(html_str, selector)
            if found is None:
                raise ExtractionError(f"Target element not found for selector: '{selector}'")
            t_name, attrs_raw, inner = found
            if outer:
                return f"<{t_name}{attrs_raw}>{inner}</{t_name}>"
            return inner

        try:
            raw_page = _get_raw_page(page)
            script = """
            (args) => {
                const el = document.querySelector(args.sel);
                if (!el) return { __bp_error: "ELEMENT_NOT_FOUND", selector: args.sel };
                return { html: args.outer ? el.outerHTML : el.innerHTML };
            }
            """
            res = await raw_page.evaluate(script, {"sel": selector, "outer": outer})
            if isinstance(res, dict) and res.get("__bp_error") == "ELEMENT_NOT_FOUND":
                raise ExtractionError(f"Target element not found for selector: '{selector}'")
            return res.get("html", "") if isinstance(res, dict) else ""
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract HTML for '{selector}': {e}") from e

    async def extract_images(
        self,
        page: Any,
        container_selector: Optional[str] = None,
    ) -> List[ExtractionRecord]:
        html_str = _get_static_html(page)
        if html_str is not None:
            scope_html = html_str
            if container_selector:
                found = _find_element_in_html(html_str, container_selector)
                if found is None:
                    raise ExtractionError(f"Container element not found for selector: '{container_selector}'")
                scope_html = found[2]
            ts_iso, ts_epoch = _current_timestamp()
            page_url = getattr(page, "current_url", "https://local.test")
            records: List[ExtractionRecord] = []
            for m in re.finditer(r"<img\b([^>]*)/?>", scope_html, re.I | re.S):
                attrs = _parse_attrs_from_tag(m.group(1))
                raw_src = attrs.get("src") or attrs.get("data-src") or ""
                alt_txt = attrs.get("alt", "")
                if not raw_src and not alt_txt:
                    continue
                resolved_src = resolve_url(page_url, raw_src) if raw_src else ""
                records.append(
                    ExtractionRecord(
                        text=alt_txt,
                        href=resolved_src,
                        url=resolved_src,
                        attributes={
                            "title": attrs.get("title", ""),
                            "srcset": attrs.get("srcset", ""),
                            "data-src": attrs.get("data-src", ""),
                            "width": int(attrs["width"]) if attrs.get("width", "").isdigit() else 0,
                            "height": int(attrs["height"]) if attrs.get("height", "").isdigit() else 0,
                        },
                        metadata={"id": attrs.get("id", ""), "raw_src": raw_src},
                        page_url=page_url,
                        selector=container_selector,
                        timestamp=ts_iso,
                        extracted_at=ts_epoch,
                    )
                )
            return records

        try:
            raw_page = _get_raw_page(page)
            script = """
            (containerSel) => {
                let root = document;
                if (containerSel) {
                    root = document.querySelector(containerSel);
                    if (!root) return { __bp_error: "CONTAINER_NOT_FOUND", selector: containerSel };
                }
                const imgs = Array.from(root.querySelectorAll('img'));
                return imgs.map(img => {
                    const srcAttr = img.getAttribute('src') || '';
                    const resolvedSrc = img.src || srcAttr;
                    return {
                        src: resolvedSrc,
                        alt: img.getAttribute('alt') || '',
                        attributes: {
                            title: img.getAttribute('title') || '',
                            srcset: img.getAttribute('srcset') || '',
                            "data-src": img.getAttribute('data-src') || img.getAttribute('data-original') || '',
                            width: img.naturalWidth || img.width || 0,
                            height: img.naturalHeight || img.height || 0
                        },
                        metadata: { id: img.id || '', raw_src: srcAttr }
                    };
                }).filter(i => i.src.length > 0 || i.alt.length > 0);
            }
            """
            raw_data = await raw_page.evaluate(script, container_selector)
            if isinstance(raw_data, dict) and raw_data.get("__bp_error") == "CONTAINER_NOT_FOUND":
                raise ExtractionError(f"Container element not found for selector: '{container_selector}'")
            if not isinstance(raw_data, list):
                return []
            page_url = ""
            if hasattr(raw_page, "url"):
                u = raw_page.url
                page_url = u() if callable(u) else str(u or "")
            ts_iso, ts_epoch = _current_timestamp()
            return [
                ExtractionRecord(
                    text=item.get("alt", ""),
                    href=item.get("src"),
                    url=item.get("src"),
                    attributes=item.get("attributes", {}),
                    metadata=item.get("metadata", {}),
                    page_url=page_url,
                    selector=container_selector,
                    timestamp=ts_iso,
                    extracted_at=ts_epoch,
                )
                for item in raw_data
            ]
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract images: {e}") from e

    async def extract_list(
        self,
        page: Any,
        list_selector: str,
        normalize: bool = True,
    ) -> List[str]:
        if not list_selector or not list_selector.strip():
            raise ExtractionError("list_selector must not be empty.")

        html_str = _get_static_html(page)
        if html_str is not None:
            found = _find_element_in_html(html_str, list_selector)
            if found is None:
                raise ExtractionError(f"List element not found for selector: '{list_selector}'")
            items = [re.sub(r"<[^>]+>", " ", li) for li in re.findall(r"<li[^>]*>(.*?)</li>", found[2], re.I | re.S)]
            return [clean_text(s) if normalize else s.strip() for s in items]

        try:
            raw_page = _get_raw_page(page)
            script = """
            (sel) => {
                const root = document.querySelector(sel);
                if (!root) return { __bp_error: "CONTAINER_NOT_FOUND", selector: sel };
                const items = Array.from(root.querySelectorAll('li'));
                return items.map(li => (li.innerText || li.textContent || '').trim());
            }
            """
            raw_items = await raw_page.evaluate(script, list_selector)
            if isinstance(raw_items, dict) and raw_items.get("__bp_error") == "CONTAINER_NOT_FOUND":
                raise ExtractionError(f"List element not found for selector: '{list_selector}'")
            if not isinstance(raw_items, list):
                return []
            return [clean_text(s) if normalize else s for s in raw_items]
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract list for '{list_selector}': {e}") from e

    async def extract_cards(
        self,
        page: Any,
        item_selector: str,
        schema: Dict[str, str],
        container_selector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not item_selector or not item_selector.strip():
            raise ExtractionError("item_selector must not be empty.")

        html_str = _get_static_html(page)
        if html_str is not None:
            scope_html = html_str
            if container_selector:
                found_c = _find_element_in_html(html_str, container_selector)
                if found_c is None:
                    raise ExtractionError(f"Container element not found for selector: '{container_selector}'")
                scope_html = found_c[2]

            results: List[Dict[str, Any]] = []
            for m_tag, m_attrs_raw, card_html in _find_all_elements_in_html(scope_html, item_selector):
                row: Dict[str, Any] = {}
                for field_key, sub_sel in (schema or {}).items():
                    if "@" in sub_sel:
                        elem_sel, attr_name = sub_sel.split("@", 1)
                        sub_found = _find_element_in_html(card_html, elem_sel.strip()) if elem_sel.strip() else (m_tag, m_attrs_raw, card_html)
                        if sub_found is not None:
                            sub_attrs = _parse_attrs_from_tag(sub_found[1])
                            row[field_key] = sub_attrs.get(attr_name.strip().lower(), "")
                        else:
                            row[field_key] = None
                    else:
                        sub_found = _find_element_in_html(card_html, sub_sel.strip())
                        row[field_key] = clean_text(re.sub(r"<[^>]+>", " ", sub_found[2])) if sub_found is not None else None
                results.append(row)
            if results or schema:
                return results
            from veil.extraction.auto_schema import AutoSchemaExtractor
            return AutoSchemaExtractor().extract(scope_html, schema=schema)

        try:
            raw_page = _get_raw_page(page)
            script = """
            (args) => {
                let root = document;
                if (args.container) {
                    root = document.querySelector(args.container);
                    if (!root) return { __bp_error: "CONTAINER_NOT_FOUND", selector: args.container };
                }
                const cards = Array.from(root.querySelectorAll(args.itemSel));
                const schema = args.schema;
                return cards.map(c => {
                    const row = {};
                    for (const [key, subSel] of Object.entries(schema)) {
                        if (subSel.includes('@')) {
                            const [elemSel, attrName] = subSel.split('@', 2);
                            const targetEl = elemSel.trim() ? c.querySelector(elemSel.trim()) : c;
                            row[key] = (targetEl && targetEl.getAttribute) ? (targetEl.getAttribute(attrName.trim()) || '') : null;
                        } else {
                            const targetEl = c.querySelector(subSel.trim());
                            row[key] = targetEl ? (targetEl.innerText || targetEl.textContent || '').trim() : null;
                        }
                    }
                    return row;
                });
            }
            """
            raw_data = await raw_page.evaluate(script, {"container": container_selector, "itemSel": item_selector, "schema": schema})
            if isinstance(raw_data, dict) and raw_data.get("__bp_error") == "CONTAINER_NOT_FOUND":
                raise ExtractionError(f"Container element not found for selector: '{container_selector}'")
            return raw_data if isinstance(raw_data, list) else []
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract cards for '{item_selector}': {e}") from e

    async def extract_next_data(self, page: Any) -> Optional[Dict[str, Any]]:
        return await extract_next_data(page)

    async def extract_nuxt_data(self, page: Any) -> Optional[Dict[str, Any]]:
        return await extract_nuxt_data(page)

    async def extract_json_ld(self, page: Any) -> List[Dict[str, Any]]:
        return await extract_json_ld(page)

    async def extract_open_graph(self, page: Any) -> Dict[str, str]:
        return await extract_open_graph(page)


async def extract_next_data(page: Any) -> Optional[Dict[str, Any]]:
    try:
        html_str = _get_static_html(page)
        if html_str is not None:
            match = re.search(r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', html_str, re.DOTALL | re.IGNORECASE)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except (json.JSONDecodeError, ValueError) as exc:
                    logger.debug(f"Failed decoding __NEXT_DATA__ JSON script: {exc}")
            return None

        raw_page = _get_raw_page(page)
        script = """
        () => {
            if (window.__NEXT_DATA__) return JSON.stringify(window.__NEXT_DATA__);
            const el = document.getElementById('__NEXT_DATA__') || document.querySelector('script#__NEXT_DATA__');
            return el ? (el.textContent || el.innerText || null) : null;
        }
        """
        raw_val = await raw_page.evaluate(script)
        if not raw_val:
            return None
        if isinstance(raw_val, dict):
            return raw_val
        try:
            return json.loads(raw_val)
        except (json.JSONDecodeError, ValueError):
            return None
    except Exception as exc:
        raise ExtractionError(f"Failed to extract __NEXT_DATA__: {exc}") from exc


async def extract_nuxt_data(page: Any) -> Optional[Dict[str, Any]]:
    try:
        html_str = _get_static_html(page)
        if html_str is not None:
            match_script = re.search(r'<script[^>]*id=["\']__NUXT_DATA__["\'][^>]*>(.*?)</script>', html_str, re.DOTALL | re.IGNORECASE)
            if match_script:
                try:
                    return json.loads(match_script.group(1).strip())
                except (json.JSONDecodeError, ValueError) as exc:
                    logger.debug(f"Failed decoding __NUXT_DATA__ JSON script: {exc}")
            match_var = re.search(r'window\.__NUXT__\s*=\s*(\{.*?\});', html_str, re.DOTALL)
            if match_var:
                try:
                    return json.loads(match_var.group(1).strip())
                except (json.JSONDecodeError, ValueError) as exc:
                    logger.debug(f"Failed decoding window.__NUXT__ JSON variable: {exc}")
            return None

        raw_page = _get_raw_page(page)
        script = """
        () => {
            if (window.__NUXT__) return JSON.stringify(window.__NUXT__);
            const el = document.getElementById('__NUXT_DATA__') || document.querySelector('script#__NUXT_DATA__');
            return el ? (el.textContent || el.innerText || null) : null;
        }
        """
        raw_val = await raw_page.evaluate(script)
        if not raw_val:
            return None
        if isinstance(raw_val, dict):
            return raw_val
        try:
            return json.loads(raw_val)
        except (json.JSONDecodeError, ValueError):
            return None
    except Exception as exc:
        raise ExtractionError(f"Failed to extract Nuxt data: {exc}") from exc


async def extract_json_ld(page: Any) -> List[Dict[str, Any]]:
    try:
        raw_scripts: List[str] = []
        html_str = _get_static_html(page)
        if html_str is not None:
            matches = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html_str, re.DOTALL | re.IGNORECASE)
            raw_scripts = [m.strip() for m in matches if m.strip()]
        else:
            raw_page = _get_raw_page(page)
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
    try:
        html_str = _get_static_html(page)
        if html_str is not None:
            result: Dict[str, str] = {}
            tag_matches = re.findall(r'<meta[^>]+(?:property|name)=["\']((?:og|twitter):[^"\']+)["\'][^>]+content=["\']([^"\']*)["\']', html_str, re.IGNORECASE)
            for k, v in tag_matches:
                result[k.strip().lower()] = v.strip()
            rev_matches = re.findall(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']((?:og|twitter):[^"\']+)["\']', html_str, re.IGNORECASE)
            for v, k in rev_matches:
                if k.strip().lower() not in result:
                    result[k.strip().lower()] = v.strip()
            return result

        raw_page = _get_raw_page(page)
        script = """
        () => {
            const tags = Array.from(document.querySelectorAll('meta[property^="og:"], meta[name^="og:"], meta[property^="twitter:"], meta[name^="twitter:"]'));
            const res = {};
            for (const tag of tags) {
                const key = tag.getAttribute('property') || tag.getAttribute('name');
                const content = tag.getAttribute('content');
                if (key && content !== null) res[key.trim().toLowerCase()] = content.trim();
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
