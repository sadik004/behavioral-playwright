"""Wave 2 Module 4: DataMan Quality-Weighted Corpus Sampler, Hierarchical RAG Chunker & Streaming Exporter.

Grounded in:
- DataMan: "Data Manager for Pre-Training Large Language Models" (arXiv:2502.19363):
  * Equation (1): Pointwise L2R quality regression loss L(f; t, L) = sum_i (f(t_i) - l_i)^2.
  * Equation (5): Quality- and domain-diversity-aware softmax temperature sampling:
      P(d_i | l_j, tau) = exp(l_{ji} / tau) / sum_k exp(l_{ki} / tau)
- Firecrawl RAG Chunking & Crawl4AI Markdown Chunking:
  * Preserves hierarchical Markdown heading breadcrumbs (`H1 > H2 > H3`) at the top of every
    emitted chunk so vector embeddings never lose parent section context.
  * Uses lexical cohesion (Jaccard similarity between adjacent paragraphs) to place chunk
    boundaries at natural topic shifts while enforcing `max_tokens` and `overlap_tokens`.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class SemanticRAGChunk:
    chunk_id: str
    url: str
    heading_breadcrumb: str
    content: str
    token_count: int
    lexical_cohesion_with_prev: float
    quality_score: float = 1.0


def dataman_sampling_probabilities(
    quality_scores: Sequence[float],
    domains: Optional[Sequence[str]] = None,
    temperature: float = 0.5,
) -> List[float]:
    """Implements Equation (5) of DataMan (arXiv:2502.19363):
    Computes temperature-scaled quality sampling probabilities combined with
    inverse-frequency domain diversity prior P(q) so a single domain cannot monopolize
    the training/RAG corpus.
    """
    if not quality_scores:
        return []
    tau = max(1e-4, float(temperature))
    max_s = max(quality_scores)

    # Domain diversity prior: inverse square-root of domain frequency
    domain_weights = [1.0] * len(quality_scores)
    if domains and len(domains) == len(quality_scores):
        counts: Dict[str, int] = {}
        for d in domains:
            counts[d] = counts.get(d, 0) + 1
        domain_weights = [1.0 / math.sqrt(counts[d]) for d in domains]

    raw_weights = [
        math.exp((float(s) - max_s) / tau) * dw
        for s, dw in zip(quality_scores, domain_weights)
    ]
    total = sum(raw_weights)
    if total <= 1e-12:
        return [round(1.0 / len(quality_scores), 6)] * len(quality_scores)
    return [round(w / total, 6) for w in raw_weights]


def lexical_jaccard_cohesion(text_a: str, text_b: str) -> float:
    """Computes lexical Jaccard cohesion |W_a intersect W_b| / |W_a union W_b| between two blocks."""
    words_a = set(re.findall(r"[a-z0-9\u0980-\u09ff]{2,}", (text_a or "").lower()))
    words_b = set(re.findall(r"[a-z0-9\u0980-\u09ff]{2,}", (text_b or "").lower()))
    if not words_a or not words_b:
        return 0.0
    return round(len(words_a & words_b) / len(words_a | words_b), 4)


class HierarchicalRAGChunker:
    """Splits Markdown into token-budgeted chunks while preserving `H1 > H2 > H3`
    heading breadcrumbs and detecting semantic topic boundaries via lexical cohesion.
    """

    def __init__(
        self,
        max_tokens: int = 120,
        overlap_tokens: int = 20,
        cohesion_split_threshold: float = 0.08,
    ) -> None:
        self.max_tokens = max(20, max_tokens)
        self.overlap_tokens = max(0, min(overlap_tokens, self.max_tokens // 2))
        self.cohesion_split_threshold = cohesion_split_threshold

    def chunk_markdown(
        self,
        url: str,
        markdown: str,
        quality_score: float = 1.0,
    ) -> List[SemanticRAGChunk]:
        if not markdown or not markdown.strip():
            return []

        blocks = [b.strip() for b in re.split(r"\n\s*\n", markdown.strip()) if b.strip()]
        headings: Dict[int, str] = {}
        chunks: List[SemanticRAGChunk] = []

        cur_paragraphs: List[str] = []
        cur_tokens = 0
        active_breadcrumb = "Document"
        prev_para_text = ""

        def _current_breadcrumb() -> str:
            parts = [headings[lvl] for lvl in sorted(headings.keys())]
            return " > ".join(parts) if parts else "Document"

        def _emit_chunk(cohesion_val: float) -> None:
            nonlocal cur_paragraphs, cur_tokens
            if not cur_paragraphs:
                return
            body = "\n\n".join(cur_paragraphs).strip()
            full_text = f"[{active_breadcrumb}]\n{body}" if active_breadcrumb else body
            toks = len(re.findall(r"\S+", full_text))
            cid = hashlib.sha256(f"{url}::{len(chunks)}::{full_text}".encode("utf-8")).hexdigest()[:16]
            chunks.append(
                SemanticRAGChunk(
                    chunk_id=cid,
                    url=url,
                    heading_breadcrumb=active_breadcrumb,
                    content=full_text,
                    token_count=toks,
                    lexical_cohesion_with_prev=cohesion_val,
                    quality_score=quality_score,
                )
            )
            # Retain overlap words from the end of the last paragraph if configured
            if self.overlap_tokens > 0 and cur_paragraphs:
                tail_words = re.findall(r"\S+", cur_paragraphs[-1])[-self.overlap_tokens :]
                overlap_str = " ".join(tail_words)
                cur_paragraphs = [overlap_str] if overlap_str else []
                cur_tokens = len(tail_words)
            else:
                cur_paragraphs = []
                cur_tokens = 0

        for blk in blocks:
            m_hdr = re.match(r"^(#{1,6})\s+(.*)$", blk)
            if m_hdr:
                # Flush current chunk before entering a new major section heading (H1/H2)
                lvl = len(m_hdr.group(1))
                hdr_title = m_hdr.group(2).strip()
                if lvl <= 2 and cur_paragraphs:
                    _emit_chunk(cohesion_val=1.0)
                headings[lvl] = hdr_title
                for deeper in [k for k in headings if k > lvl]:
                    del headings[deeper]
                active_breadcrumb = _current_breadcrumb()
                continue

            blk_tokens = len(re.findall(r"\S+", blk))
            cohesion = lexical_jaccard_cohesion(prev_para_text, blk) if prev_para_text else 1.0

            # Split if token budget would be exceeded OR if chunk is >60% full and topic shifts sharply
            topic_shift = (
                cur_tokens >= int(self.max_tokens * 0.6)
                and prev_para_text != ""
                and cohesion < self.cohesion_split_threshold
            )
            if cur_paragraphs and (cur_tokens + blk_tokens > self.max_tokens or topic_shift):
                _emit_chunk(cohesion_val=cohesion)

            cur_paragraphs.append(blk)
            cur_tokens += blk_tokens
            prev_para_text = blk

        if cur_paragraphs:
            _emit_chunk(cohesion_val=1.0)

        return chunks


class StreamingCorpusExporter:
    """Streams crawled records and RAG chunks to `.jsonl` and `.csv` in O(1) memory."""

    def __init__(self, jsonl_path: str | Path, csv_path: Optional[str | Path] = None) -> None:
        self.jsonl_path = Path(jsonl_path)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self.csv_path = Path(csv_path) if csv_path else None
        if self.csv_path:
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._csv_header_written = False
        self.records_written = 0

    def append_record(self, record: Dict[str, Any]) -> None:
        with self.jsonl_path.open("a", encoding="utf-8") as jf:
            jf.write(json.dumps(record, ensure_ascii=False) + "\n")

        if self.csv_path:
            flat = {
                "url": record.get("url", ""),
                "status": record.get("status", 200),
                "quality_score": record.get("quality_score", 0.0),
                "delta_status": record.get("delta_status", ""),
                "token_reduction_pct": record.get("token_reduction_pct", 0.0),
                "chunk_count": len(record.get("rag_chunks", [])),
            }
            with self.csv_path.open("a", encoding="utf-8", newline="") as cf:
                writer = csv.DictWriter(cf, fieldnames=list(flat.keys()))
                if not self._csv_header_written:
                    writer.writeheader()
                    self._csv_header_written = True
                writer.writerow(flat)

        self.records_written += 1
