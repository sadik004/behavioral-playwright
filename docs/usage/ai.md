# AI & Statistical NLP Usage Guide

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Multilingual TF-IDF Document Re-Ranking

Rank raw documents against a natural language search query without external API costs or model weights:

```python
from bp_facade12 import BP

bp = BP()
documents = [
    "Playwright automation with stealth CDP shims",
    "Deep learning transformer models in PyTorch",
    "High-speed recursive web crawler in Python",
    "Statistical NLP vector space algorithms"
]

ranked = bp.ai.re_rank("python crawler", documents)
for item in ranked:
    print(f"Score: {item['score']:.4f} | Document: {item['document']}")
```

---

## 2. JIT Schema Coercion & Entity Extraction

```python
# Coerce messy string dictionary to typed primitives
schema = {"id": int, "price": float, "in_stock": bool}
raw_record = {"id": "1001", "price": "49.95", "in_stock": "true"}
clean_record = bp.ai.coerce_data_to_schema(raw_record, schema)
print("Coerced:", clean_record)

# Extract contact entities
entities = bp.ai.extract_entities("Support: help@example.com, Phone: +1-800-555-0199")
print("Emails:", entities["emails"], "Phones:", entities["phone_numbers"])
```
