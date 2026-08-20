"""Generic structured DOM extraction utilities."""

from typing import Any, Dict, List, Optional

from behavioral_playwright.exceptions import ExtractionError
from behavioral_playwright.models.elements import DOMElement
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
