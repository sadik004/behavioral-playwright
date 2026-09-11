# Feature Specification: AI Namespace (`bp.ai`)

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Overview & Capabilities
The `AINamespace` ([`bp_facade12.py:1004`](file:///c:/Users/User/SAA/bp_facade12.py#L1004)) provides zero-cost, offline statistical NLP, multilingual document re-ranking, and structured schema coercion.

---

## 2. API Method Reference

### `re_rank(query, documents)`
- **Signature**: `def re_rank(self, query: str, documents: List[str]) -> List[Dict[str, Any]]`
- **Description**: Tokenizes UTF-8 strings, constructs TF-IDF matrices, and computes Cosine Similarity scores.

### `coerce_data_to_schema(data, schema)`
- **Signature**: `def coerce_data_to_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]`
- **Description**: Gracefully casts extracted string values to matching target Python primitive types (e.g. `int`, `float`, `bool`).

### `analyze_sentiment(text)`
- **Signature**: `def analyze_sentiment(self, text: str) -> Dict[str, Any]`
- **Description**: Evaluates text sentiment against a domain-specific 100+ keyword lexicon.
