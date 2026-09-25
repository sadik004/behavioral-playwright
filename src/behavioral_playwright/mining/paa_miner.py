"""
People Also Ask (PAA) Semantic Tree Mining Engine.
Extracts recursive PAA accordion queries, response snippets, and citation sources.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, Set

from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.seo_dtos import PAANode

logger = get_logger("mining.paa")

try:
    from bs4 import BeautifulSoup  # type: ignore
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


class PAAMiner:
    """
    Mines People Also Ask (PAA) question hierarchies from Google SERP pages.
    Supports both live Playwright Page interaction and static HTML parsing.
    """

    def __init__(self, max_depth: int = 3, max_questions_per_depth: int = 4) -> None:
        self.max_depth = min(max(1, max_depth), 5)
        self.max_questions_per_depth = max(1, max_questions_per_depth)

    def parse_from_html(
        self,
        html_content: str,
        initial_parent: Optional[str] = None,
        depth: int = 1,
        base_depth: Optional[int] = None,
    ) -> List[PAANode]:
        """Parses PAA questions and answer snippets from static SERP HTML content."""
        effective_depth = base_depth if base_depth is not None else depth
        nodes: List[PAANode] = []
        if not html_content:
            return nodes

        if _HAS_BS4:
            soup = BeautifulSoup(html_content, "html.parser")
            # Multiple Google PAA question accordion wrapper patterns
            question_containers = soup.select(
                "div.related-question-pair, div[jsname='yEVEwb'], div[data-q], div.cbphWd, div.M6764"
            )

            for container in question_containers[:self.max_questions_per_depth]:
                # Extract question
                q_elem = container.select_one("div[role='button'], div.match-mod-horizontal-padding, div.JlqpRe, span")
                question_text = q_elem.get_text(strip=True) if q_elem else container.get("data-q", "")
                if not question_text:
                    continue

                # Extract answer snippet
                snippet_elem = container.select_one("div.LGOjhe, div.hgKElc, div.kno-rdesc, div[data-attrid='wa:/description'], div.X5LH0c")
                snippet_text = snippet_elem.get_text(strip=True) if snippet_elem else ""

                # Extract citation link & title
                link_elem = container.select_one("a[href^='http'], a[ping]")
                source_url = link_elem.get("href", "") if link_elem else ""
                title_elem = container.select_one("h3, div.LC20lb, span.VuuXrf, a span")
                source_title = title_elem.get_text(strip=True) if title_elem else ""

                node = PAANode(
                    question=question_text,
                    snippet_text=snippet_text,
                    source_title=source_title,
                    source_url=source_url,
                    depth=effective_depth,
                    parent_question=initial_parent
                )
                nodes.append(node)
        else:
            # Fallback regex extraction
            matches = re.findall(
                r"<div[^>]*?(?:related-question-pair|jsname=[\"']yEVEwb[\"'])[^>]*?>(.*?)</div></div>",
                html_content,
                re.DOTALL
            )
            for raw_chunk in matches[:self.max_questions_per_depth]:
                q_match = re.search(r"<(?:span|div)[^>]*?>([^<]{10,120}\?)</(?:span|div)>", raw_chunk)
                if q_match:
                    q_text = q_match.group(1).strip()
                    url_match = re.search(r"href=[\"'](https?://[^\"']+)[\"']", raw_chunk)
                    src_url = url_match.group(1) if url_match else ""
                    nodes.append(PAANode(
                        question=q_text,
                        snippet_text="",
                        source_title="",
                        source_url=src_url,
                        depth=depth,
                        parent_question=initial_parent
                    ))

        return nodes

    async def extract_from_page(
        self,
        page: Any,
        target_query: Optional[str] = None
    ) -> List[PAANode]:
        """
        Dynamically drives an active Playwright page to expand and mine PAA accordions.
        """
        if target_query and hasattr(page, "goto"):
            from urllib.parse import quote_plus
            search_url = f"https://www.google.com/search?q={quote_plus(target_query)}&hl=en"
            await page.goto(search_url, wait_until="domcontentloaded")

        collected_nodes: List[PAANode] = []
        visited_questions: Set[str] = set()

        try:
            # Query top-level PAA accordions
            paa_selectors = [
                "div.related-question-pair",
                "div[jsname='yEVEwb']",
                "div.cbphWd",
                "div[role='button'][aria-expanded]"
            ]
            paa_items = []
            for sel in paa_selectors:
                items = await page.query_selector_all(sel)
                if items:
                    paa_items = items
                    break

            for i, item in enumerate(paa_items[:self.max_questions_per_depth]):
                try:
                    q_text = await item.inner_text()
                    q_first_line = q_text.split("\n")[0].strip() if q_text else ""
                    if not q_first_line or q_first_line in visited_questions:
                        continue

                    visited_questions.add(q_first_line)

                    # Dynamic actionability click to expand accordion
                    try:
                        await item.click(timeout=3000)
                    except Exception:
                        pass

                    # Extract details
                    content_html = await item.inner_html()
                    parsed_subnodes = self.parse_from_html(
                        content_html,
                        initial_parent=None,
                        depth=1
                    )
                    if parsed_subnodes:
                        collected_nodes.extend(parsed_subnodes)
                    else:
                        collected_nodes.append(PAANode(
                            question=q_first_line,
                            snippet_text="",
                            source_title="",
                            source_url="",
                            depth=1,
                            parent_question=None
                        ))
                except Exception as exc:
                    logger.debug(f"[PAAMiner] Error processing accordion {i}: {exc}")

        except Exception as e:
            logger.warning(f"[PAAMiner] Failed during interactive extraction: {e}")

        # If interactive extraction yielded 0 items, fallback to full page HTML parsing
        if not collected_nodes and hasattr(page, "content"):
            full_html = await page.content()
            collected_nodes = self.parse_from_html(full_html, depth=1)

        return collected_nodes


__all__ = ["PAAMiner"]
