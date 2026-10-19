"""Wave 2 Module 2: Block-Tree DOM Pruner, Lossless Structural Compressor & Shadow/Iframe Flattener.

Grounded in:
- HtmlRAG: "HTML is Better Than Plain Text for RAG Modeling" (arXiv:2411.02959v2):
  * Section 3.2.2: Lossless Structural Compression (merging single-child nested tag chains
    and removing empty leaf tags).
  * Section 3.3 & 3.4 (Algorithm 1 & Algorithm 2): Granularity-adjustable Block Tree construction
    and Greedy Block Pruning under a context token budget B_tokens.
  * Equation (3): Block log-probability / information salience score:
      Score(b) = sum_{i=1}^N log P(t_i | q)
- Dripper: "Token-Efficient Main HTML Extraction with a Lightweight LM" (arXiv:2511.23119):
  * Equation (2) & Section 3.2: Dual-branch Simplified HTML + Mapping HTML subset selection
    C = {m_i in M | y_hat_i = 1} and Total FLOPs reduction (Equation 6).
- D2Snap: "Beyond Pixels: Exploring DOM Downsampling for LLM-Based Web Agents" (arXiv:2508.04412v4)
  & Prune4Web (arXiv:2511.21398, AAAI 2026):
  * Programmatic DOM tree scoring and actionability-preserving attribute downsampling.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple


_SHADOW_TEMPLATE_RE = re.compile(
    r"""<template[^>]+shadowroot(?:mode)?=["']?(?:open|closed)["']?[^>]*>(.*?)</template>""",
    re.IGNORECASE | re.DOTALL,
)
_IFRAME_SRCDOC_RE = re.compile(
    r"""<iframe[^>]+srcdoc=["'](.*?)["'][^>]*>\s*</iframe>""",
    re.IGNORECASE | re.DOTALL,
)
_EMPTY_TAG_RE = re.compile(
    r"<(div|span|p|section|article|aside|nav|header|footer)\b[^>]*>\s*</\1>",
    re.IGNORECASE,
)
_SINGLE_NESTED_RE = re.compile(
    r"<(div|span|section)\b[^>]*>\s*(<\1\b[^>]*>.*?</\1>)\s*</\1>",
    re.IGNORECASE | re.DOTALL,
)


def flatten_shadow_dom_and_iframes(html: str) -> Tuple[str, int]:
    """Flattens declarative Shadow DOM (`<template shadowrootmode="open">`) and
    inline `<iframe srcdoc="...">` documents into standard traversable HTML blocks.

    Returns `(flattened_html, flattened_root_count)`.
    """
    if not html:
        return "", 0
    count = 0

    def _replace_shadow(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return f'<div data-shadow-root="flattened">{m.group(1)}</div>'

    def _replace_srcdoc(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        unescaped = (
            m.group(1)
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("&amp;", "&")
        )
        return f'<div data-iframe-srcdoc="flattened">{unescaped}</div>'

    out = _SHADOW_TEMPLATE_RE.sub(_replace_shadow, html)
    out = _IFRAME_SRCDOC_RE.sub(_replace_srcdoc, out)
    return out, count


def lossless_structural_compress(html: str) -> str:
    """Implements HtmlRAG (arXiv:2411.02959v2 §3.2.2) Lossless Structural Compression:
    1. Removes empty leaf container tags (`<div></div>`, `<span></span>`).
    2. Merges redundant single-nested wrapper tags (`<div><div>...</div></div>` -> `<div>...</div>`).
    """
    compressed = html or ""
    for _ in range(4):
        prev = compressed
        compressed = _EMPTY_TAG_RE.sub("", compressed)
        compressed = _SINGLE_NESTED_RE.sub(r"\2", compressed)
        if compressed == prev:
            break
    return compressed.strip()


@dataclass
class DOMBlockNode:
    block_id: int
    tag_path: str
    tag: str
    text: str
    raw_html_len: int
    token_estimate: int
    is_interactive: bool = False
    score: float = 0.0
    keep: bool = True


@dataclass
class BlockTreePruneResult:
    simplified_html: str
    pruned_markdown: str
    kept_blocks: List[DOMBlockNode] = field(default_factory=list)
    total_blocks_before: int = 0
    total_blocks_after: int = 0
    shadow_or_iframes_flattened: int = 0
    original_tokens: int = 0
    pruned_tokens: int = 0
    compression_ratio: float = 0.0
    saved_flops_ratio: float = 0.0


class _BlockTreeBuilder(HTMLParser):
    _VOID_TAGS = frozenset(
        {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    )
    _SKIP_TAGS = frozenset({"script", "style", "noscript", "svg", "canvas", "head"})
    _BLOCK_BOUNDARY_TAGS = frozenset(
        {
            "p", "h1", "h2", "h3", "h4", "h5", "h6",
            "li", "tr", "article", "section", "div", "blockquote", "pre",
            "nav", "footer", "header", "aside", "main",
        }
    )
    _INTERACTIVE_TAGS = frozenset({"a", "button", "input", "select", "textarea", "details", "summary"})
    _SEMANTIC_ATTRS = frozenset({"id", "class", "href", "src", "alt", "role", "aria-label", "data-testid", "data-shadow-root", "data-iframe-srcdoc"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._tag_stack: List[str] = []
        self._cur_text: List[str] = []
        self._cur_attrs: Dict[str, str] = {}
        self._cur_interactive = False
        self.blocks: List[DOMBlockNode] = []
        self._seq = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        t = tag.lower()
        is_void = t in self._VOID_TAGS
        if self._skip_depth > 0 or t in self._SKIP_TAGS:
            if not is_void:
                self._skip_depth += 1
            return

        attr_d = {k.lower(): (v or "") for k, v in attrs if k and k.lower() in self._SEMANTIC_ATTRS}
        if attr_d.get("style") and "display:none" in attr_d["style"].replace(" ", "").lower():
            if not is_void:
                self._skip_depth += 1
            return

        if t in self._BLOCK_BOUNDARY_TAGS:
            self._flush()
            self._cur_attrs = attr_d

        if t in self._INTERACTIVE_TAGS:
            self._cur_interactive = True
            label = attr_d.get("aria-label") or attr_d.get("alt") or ""
            if label:
                self._cur_text.append(label)

        if not is_void:
            self._tag_stack.append(t)

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        cleaned = " ".join(data.split())
        if cleaned:
            self._cur_text.append(cleaned)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if self._skip_depth > 0:
            if t not in self._VOID_TAGS:
                self._skip_depth -= 1
            return

        if t in self._BLOCK_BOUNDARY_TAGS:
            self._flush(closing_tag=t)

        if self._tag_stack and self._tag_stack[-1] == t:
            self._tag_stack.pop()

    def _flush(self, closing_tag: Optional[str] = None) -> None:
        txt = " ".join(self._cur_text).strip()
        if txt:
            self._seq += 1
            active_tag = closing_tag or (self._tag_stack[-1] if self._tag_stack else "div")
            path = "/".join(self._tag_stack[-4:]) if self._tag_stack else active_tag
            tok_est = max(1, len(re.findall(r"\S+", txt)))
            raw_len = len(txt) + len(path) * 4 + 16
            self.blocks.append(
                DOMBlockNode(
                    block_id=self._seq,
                    tag_path=path,
                    tag=active_tag,
                    text=txt,
                    raw_html_len=raw_len,
                    token_estimate=tok_est,
                    is_interactive=self._cur_interactive,
                )
            )
        self._cur_text = []
        self._cur_interactive = False


class BlockTreePruner:
    """Implements HtmlRAG Algorithm 2 (Greedy Block Tree Pruning, arXiv:2411.02959v2)
    combined with Dripper Dual-Branch Reconstruction (arXiv:2511.23119) and D2Snap
    actionability preservation (arXiv:2508.04412v4).
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b

    def score_blocks_bm25_and_salience(
        self,
        blocks: List[DOMBlockNode],
        query: Optional[str] = None,
    ) -> None:
        """Scores each block using HtmlRAG Eq. (3) log-salience + Okapi BM25 query similarity
        + D2Snap interactive/heading boost.
        """
        if not blocks:
            return

        q_tokens = re.findall(r"[a-z0-9\u0980-\u09ff]+", (query or "").lower())
        avg_dl = sum(b.token_estimate for b in blocks) / max(1, len(blocks))
        n_docs = len(blocks)

        df: Dict[str, int] = {}
        block_tokens_list: List[List[str]] = []
        for blk in blocks:
            toks = re.findall(r"[a-z0-9\u0980-\u09ff]+", blk.text.lower())
            block_tokens_list.append(toks)
            seen = set(toks)
            for qt in q_tokens:
                if qt in seen:
                    df[qt] = df.get(qt, 0) + 1

        for blk, toks in zip(blocks, block_tokens_list):
            text_density = len(blk.text) / max(1, blk.raw_html_len)
            log_salience = math.log1p(len(blk.text)) * text_density

            role_boost = 0.0
            if blk.tag in ("h1", "h2", "h3"):
                role_boost += 2.5
            if blk.is_interactive:
                role_boost += 0.8
            if blk.tag in ("nav", "footer", "aside") or any(bp in blk.tag_path.split("/") for bp in ("nav", "footer", "aside")):
                role_boost -= 4.0

            bm25 = 0.0
            if q_tokens and toks:
                dl = len(toks)
                for qt in q_tokens:
                    tf = toks.count(qt)
                    if tf > 0:
                        n_q = df.get(qt, 0)
                        idf = math.log(1.0 + (n_docs - n_q + 0.5) / (n_q + 0.5))
                        denom = tf + self.k1 * (1.0 - self.b + self.b * (dl / max(1.0, avg_dl)))
                        bm25 += idf * ((tf * (self.k1 + 1.0)) / denom)

            blk.score = round(log_salience + role_boost + (3.0 * bm25), 4)

    def prune(
        self,
        html: str,
        query: Optional[str] = None,
        max_tokens: int = 250,
    ) -> BlockTreePruneResult:
        """Executes:
        1. Shadow DOM & `<iframe srcdoc>` flattening.
        2. HtmlRAG §3.2.2 lossless structural compression.
        3. Block tree construction & BM25 + log-salience scoring.
        4. HtmlRAG Algorithm 2 greedy lowest-score block deletion until total tokens <= `max_tokens`
           (and always pruning negative-score boilerplate blocks).
        5. Dripper Eq. (2) & Eq. (6) FLOPs reduction computation.
        """
        flattened_html, flattened_count = flatten_shadow_dom_and_iframes(html or "")
        compressed_html = lossless_structural_compress(flattened_html)

        builder = _BlockTreeBuilder()
        builder.feed(compressed_html)
        builder._flush()
        blocks = builder.blocks

        orig_tokens = max(1, sum(b.token_estimate for b in blocks), len(re.findall(r"<[^>]+>|[^\s<>]+", html or "")))
        if not blocks:
            return BlockTreePruneResult(
                simplified_html="",
                pruned_markdown="",
                total_blocks_before=0,
                total_blocks_after=0,
                shadow_or_iframes_flattened=flattened_count,
                original_tokens=orig_tokens,
                pruned_tokens=0,
            )

        self.score_blocks_bm25_and_salience(blocks, query=query)

        current_tokens = sum(b.token_estimate for b in blocks)
        by_ascending_score = sorted(blocks, key=lambda b: (b.score, -b.block_id))
        for blk in by_ascending_score:
            if current_tokens <= max_tokens and blk.score >= 0.0:
                break
            if blk.tag == "h1" and blk.token_estimate <= max_tokens and blk.score >= 0.0:
                continue
            blk.keep = False
            current_tokens -= blk.token_estimate

        kept = [b for b in blocks if b.keep]
        if not kept and blocks:
            best = max(blocks, key=lambda b: b.score)
            best.keep = True
            kept = [best]

        pruned_toks = sum(b.token_estimate for b in kept)
        simplified_html = "\n".join(f"<{b.tag}>{b.text}</{b.tag}>" for b in kept)
        pruned_md = "\n\n".join(
            f"# {b.text}" if b.tag == "h1" else (f"## {b.text}" if b.tag in ("h2", "h3") else b.text)
            for b in kept
        )

        comp_ratio = round(1.0 - (pruned_toks / max(1, orig_tokens)), 4)
        saved_flops = round(max(0.0, 1.0 - ((pruned_toks / max(1, orig_tokens)) ** 2)), 4)

        return BlockTreePruneResult(
            simplified_html=simplified_html,
            pruned_markdown=pruned_md,
            kept_blocks=kept,
            total_blocks_before=len(blocks),
            total_blocks_after=len(kept),
            shadow_or_iframes_flattened=flattened_count,
            original_tokens=orig_tokens,
            pruned_tokens=pruned_toks,
            compression_ratio=comp_ratio,
            saved_flops_ratio=saved_flops,
        )
