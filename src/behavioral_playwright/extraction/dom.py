"""DOM Extraction module providing structured, live-DOM authoritative data extraction."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from behavioral_playwright.exceptions import ExtractionError
from behavioral_playwright.extraction.normalizer import (
    clean_text,
    normalize_whitespace,
    parse_numeric,
    parse_price,
    resolve_url,
)
from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.results import ExtractionRecord

logger = get_logger("extraction.dom")


def _get_raw_page(page: Any) -> Any:
    """Unwraps PageSession or custom wrappers to obtain the underlying evaluatable page."""
    if hasattr(page, "__class__") and "Mock" in page.__class__.__name__:
        return page
    if hasattr(page, "raw_page") and getattr(page, "raw_page", None) is not None:
        return getattr(page, "raw_page")
    return page



def _current_timestamp() -> Tuple[str, float]:
    """Returns (iso_utc_string, unix_timestamp_float)."""
    now = datetime.now(timezone.utc)
    return now.isoformat(), now.timestamp()


class DOMExtractor:
    """Provides structured, live-DOM authoritative data extraction from web pages."""

    async def extract_links(
        self,
        page: Any,
        container_selector: Optional[str] = None
    ) -> List[ExtractionRecord]:
        """
        Extracts structured hyperlink records from page.
        Resolves relative URLs to absolute against document.baseURI.
        Attaches provenance (page URL, container selector, timestamp).
        Raises ExtractionError if a specified container_selector does not exist.
        """
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
                const baseURI = document.baseURI || window.location.href;
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

            # Determine provenance page URL
            page_url = ""
            if hasattr(raw_page, "url"):
                u = raw_page.url
                page_url = u() if callable(u) else str(u or "")

            ts_iso, ts_epoch = _current_timestamp()

            records: List[ExtractionRecord] = []
            for item in raw_data:
                records.append(ExtractionRecord(
                    text=item.get("text", ""),
                    href=item.get("href"),
                    attributes=item.get("attributes", {}),
                    metadata=item.get("metadata", {}),
                    page_url=page_url,
                    selector=container_selector,
                    timestamp=ts_iso,
                    extracted_at=ts_epoch,
                ))
            return records
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract links: {e}") from e

    async def extract_table(
        self,
        page: Any,
        table_selector: str,
        has_headers: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Extracts HTML table rows as a list of dictionaries keyed by header text.
        Preserves column alignment, supports colspan expansion, deduplicates duplicate headers,
        and distinguishes empty cells ('') from missing cells (None).
        Raises ExtractionError if table_selector does not exist.
        """
        if not table_selector or not table_selector.strip():
            raise ExtractionError("table_selector must not be empty.")

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

                // 1. Detect and normalize headers
                let headerEls = Array.from(table.querySelectorAll('thead th, th'));
                let headerTexts = [];
                let skipFirstRow = false;

                if (headerEls.length > 0) {
                    for (const th of headerEls) {
                        const colspan = parseInt(th.getAttribute('colspan') || '1', 10);
                        const hText = (th.innerText || th.textContent || '').trim();
                        headerTexts.push(hText);
                        for (let c = 1; c < colspan; c++) {
                            headerTexts.push(hText);
                        }
                    }
                } else if (hasH) {
                    // Fallback to first row
                    const firstTr = table.querySelector('tr');
                    if (firstTr) {
                        const firstRowCells = Array.from(firstTr.querySelectorAll('th, td'));
                        if (firstRowCells.length > 0) {
                            for (const c of firstRowCells) {
                                const colspan = parseInt(c.getAttribute('colspan') || '1', 10);
                                const cText = (c.innerText || c.textContent || '').trim();
                                headerTexts.push(cText);
                                for (let k = 1; k < colspan; k++) {
                                    headerTexts.push(cText);
                                }
                            }
                            skipFirstRow = true;
                        }
                    }
                }

                // Deduplicate header names to prevent silent overwriting
                const headerCounts = {};
                const deduplicatedHeaders = headerTexts.map((h, idx) => {
                    const baseKey = h || ('col_' + idx);
                    if (headerCounts[baseKey] === undefined) {
                        headerCounts[baseKey] = 1;
                        return baseKey;
                    } else {
                        headerCounts[baseKey] += 1;
                        return `${baseKey}_${headerCounts[baseKey]}`;
                    }
                });

                // 2. Extract rows
                let allRows = Array.from(table.querySelectorAll('tbody tr, tr')).filter(r => r.querySelectorAll('td').length > 0);
                if (skipFirstRow && allRows.length > 0) {
                    allRows = allRows.slice(1);
                }

                const result = [];
                for (const row of allRows) {
                    const cells = Array.from(row.querySelectorAll('td, th'));
                    // Expand cells respecting colspan
                    const expandedCells = [];
                    for (const cell of cells) {
                        const colspan = parseInt(cell.getAttribute('colspan') || '1', 10);
                        const cellText = (cell.innerText || cell.textContent || '').trim();
                        expandedCells.push(cellText);
                        for (let c = 1; c < colspan; c++) {
                            expandedCells.push(cellText);
                        }
                    }

                    const rowObj = {};
                    const colLimit = Math.max(deduplicatedHeaders.length, expandedCells.length);
                    for (let idx = 0; idx < colLimit; idx++) {
                        const key = deduplicatedHeaders[idx] || ('col_' + idx);
                        if (idx < expandedCells.length) {
                            rowObj[key] = expandedCells[idx];
                        } else {
                            rowObj[key] = null; // Cell missing in row
                        }
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
        container_selector: Optional[str] = None
    ) -> List[ExtractionRecord]:
        """
        Extracts structured article blocks (headings, summaries, and links).
        Attaches provenance and respects live DOM.
        Raises ExtractionError if container_selector does not exist.
        """
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
                    
                    const title = hEl ? (hEl.innerText || hEl.textContent || '').trim() : '';
                    const href = aEl ? (aEl.href || aEl.getAttribute('href') || '') : '';
                    const summary = descEl ? (descEl.innerText || descEl.textContent || '').trim() : '';
                    
                    return {
                        text: title,
                        href: href,
                        attributes: {
                            summary: summary
                        },
                        metadata: {
                            tag: c.tagName.toLowerCase()
                        }
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

            records: List[ExtractionRecord] = []
            for item in raw_data:
                records.append(ExtractionRecord(
                    text=item.get("text", ""),
                    href=item.get("href"),
                    attributes=item.get("attributes", {}),
                    metadata=item.get("metadata", {}),
                    page_url=page_url,
                    selector=container_selector,
                    timestamp=ts_iso,
                    extracted_at=ts_epoch,
                ))
            return records
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract articles: {e}") from e

    async def extract_text(
        self,
        page: Any,
        selector: str,
        normalize: bool = True,
        visible_only: bool = True
    ) -> str:
        """
        Extracts text content from a target DOM selector.
        Distinguishes missing element (raises ExtractionError) from element with empty text ('').
        """
        if not selector or not selector.strip():
            raise ExtractionError("selector must not be empty.")

        try:
            raw_page = _get_raw_page(page)
            script = """
            (args) => {
                const el = document.querySelector(args.sel);
                if (!el) {
                    return { __bp_error: "ELEMENT_NOT_FOUND", selector: args.sel };
                }
                if (args.vis) {
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                        return { text: "" };
                    }
                    if (el.offsetParent === null && style.position !== 'fixed') {
                        return { text: "" };
                    }
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
        attributes: Optional[List[str]] = None
    ) -> Dict[str, Optional[str]]:
        """
        Extracts specified attributes from target DOM selector.
        Distinguishes missing attribute (None) from empty attribute ('').
        Raises ExtractionError if selector does not exist.
        """
        if not selector or not selector.strip():
            raise ExtractionError("selector must not be empty.")

        try:
            raw_page = _get_raw_page(page)
            script = """
            (args) => {
                const el = document.querySelector(args.sel);
                if (!el) {
                    return { __bp_error: "ELEMENT_NOT_FOUND", selector: args.sel };
                }
                const res = {};
                const requested = args.attrs;
                if (requested && requested.length > 0) {
                    for (const attr of requested) {
                        if (el.hasAttribute(attr)) {
                            res[attr] = el.getAttribute(attr);
                        } else {
                            res[attr] = null;
                        }
                    }
                } else {
                    for (const attr of el.attributes) {
                        res[attr.name] = attr.value;
                    }
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
        outer: bool = True
    ) -> str:
        """Extracts inner or outer HTML of the target selector. Raises ExtractionError if not found."""
        if not selector or not selector.strip():
            raise ExtractionError("selector must not be empty.")

        try:
            raw_page = _get_raw_page(page)
            script = """
            (args) => {
                const el = document.querySelector(args.sel);
                if (!el) {
                    return { __bp_error: "ELEMENT_NOT_FOUND", selector: args.sel };
                }
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
        container_selector: Optional[str] = None
    ) -> List[ExtractionRecord]:
        """
        Extracts image elements with resolved absolute URLs, alt tags, dimensions, and lazy attributes.
        Raises ExtractionError if container_selector is specified and does not exist.
        """
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
                        metadata: {
                            id: img.id || '',
                            raw_src: srcAttr
                        }
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

            records: List[ExtractionRecord] = []
            for item in raw_data:
                records.append(ExtractionRecord(
                    text=item.get("alt", ""),
                    href=item.get("src"),
                    url=item.get("src"),
                    attributes=item.get("attributes", {}),
                    metadata=item.get("metadata", {}),
                    page_url=page_url,
                    selector=container_selector,
                    timestamp=ts_iso,
                    extracted_at=ts_epoch,
                ))
            return records
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract images: {e}") from e

    async def extract_list(
        self,
        page: Any,
        list_selector: str,
        normalize: bool = True
    ) -> List[str]:
        """
        Extracts list items (li) from an ordered/unordered list container, preserving document order.
        Raises ExtractionError if list_selector does not exist.
        """
        if not list_selector or not list_selector.strip():
            raise ExtractionError("list_selector must not be empty.")

        try:
            raw_page = _get_raw_page(page)
            script = """
            (sel) => {
                const root = document.querySelector(sel);
                if (!root) {
                    return { __bp_error: "CONTAINER_NOT_FOUND", selector: sel };
                }
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
        container_selector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extracts structured repeated cards.
        schema maps output field names to scoped relative sub-selectors.
        Example schema: {"title": "h3", "price": ".price", "link": "a@href", "img": "img@src"}
        """
        if not item_selector or not item_selector.strip():
            raise ExtractionError("item_selector must not be empty.")

        try:
            raw_page = _get_raw_page(page)
            script = """
            (args) => {
                let root = document;
                if (args.container) {
                    root = document.querySelector(args.container);
                    if (!root) {
                        return { __bp_error: "CONTAINER_NOT_FOUND", selector: args.container };
                    }
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
            raw_data = await raw_page.evaluate(script, {
                "container": container_selector,
                "itemSel": item_selector,
                "schema": schema,
            })
            if isinstance(raw_data, dict) and raw_data.get("__bp_error") == "CONTAINER_NOT_FOUND":
                raise ExtractionError(f"Container element not found for selector: '{container_selector}'")

            return raw_data if isinstance(raw_data, list) else []
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract cards for '{item_selector}': {e}") from e

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

        raw_page = _get_raw_page(page)

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
                except (json.JSONDecodeError, ValueError) as exc:
                    logger.debug(f"Failed decoding __NUXT_DATA__ JSON script: {exc}")
            match_var = re.search(r'window\.__NUXT__\s*=\s*(\{.*?\});', page, re.DOTALL)
            if match_var:
                try:
                    return json.loads(match_var.group(1).strip())
                except (json.JSONDecodeError, ValueError) as exc:
                    logger.debug(f"Failed decoding window.__NUXT__ JSON variable: {exc}")
            return None

        raw_page = _get_raw_page(page)

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

        raw_page = _get_raw_page(page)
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
