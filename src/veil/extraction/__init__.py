"""DOM & Semantic Extraction Subsystem."""

from veil.extraction.auto_schema import (
    AdaptiveSchemaSynthesizer,
    AutoSchemaExtractor,
    FieldExtractionRule,
    SynthesizedTemplateSchema,
)
from veil.extraction.hydration import extract_hydration_state
from veil.extraction.markdown import (
    DistilledMarkdown,
    MarkdownConverter,
    html_to_fit_markdown,
)
from veil.extraction.quarantine import (
    DataQuarantineGate,
    QuarantineVerdict,
)
from veil.extraction.block_tree_pruner import (
    BlockTreePruneResult,
    BlockTreePruner,
    DOMBlockNode,
    flatten_shadow_dom_and_iframes,
    lossless_structural_compress,
)
from veil.extraction.rag_chunker_exporter import (
    HierarchicalRAGChunker,
    SemanticRAGChunk,
    StreamingCorpusExporter,
    dataman_sampling_probabilities,
    lexical_jaccard_cohesion,
)

try:
    from behavioral_playwright.extraction.dom import (
        DOMExtractor,
        extract_json_ld,
        extract_next_data,
        extract_nuxt_data,
        extract_open_graph,
    )
    from behavioral_playwright.extraction.normalizer import (
        clean_text,
        normalize_unicode,
        normalize_whitespace,
        parse_numeric,
        parse_price,
        remove_zero_width,
        resolve_url,
    )
except ImportError as _optional_ext_exc:
    _ = _optional_ext_exc

__all__ = [
    "DOMExtractor",
    "extract_json_ld",
    "extract_next_data",
    "extract_nuxt_data",
    "extract_open_graph",
    "clean_text",
    "normalize_unicode",
    "normalize_whitespace",
    "parse_numeric",
    "parse_price",
    "remove_zero_width",
    "resolve_url",
    "AdaptiveSchemaSynthesizer",
    "AutoSchemaExtractor",
    "FieldExtractionRule",
    "SynthesizedTemplateSchema",
    "extract_hydration_state",
    "DistilledMarkdown",
    "html_to_fit_markdown",
    "MarkdownConverter",
    "DataQuarantineGate",
    "QuarantineVerdict",
    "BlockTreePruneResult",
    "BlockTreePruner",
    "DOMBlockNode",
    "flatten_shadow_dom_and_iframes",
    "lossless_structural_compress",
    "HierarchicalRAGChunker",
    "SemanticRAGChunk",
    "StreamingCorpusExporter",
    "dataman_sampling_probabilities",
    "lexical_jaccard_cohesion",
]
