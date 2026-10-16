# Developer Guide & Cookbook: Data Mining Subsystem (`bp.mining`)

> **Version**: `v6.0.0`
> **Status**: [VERIFIED]

This guide demonstrates practical usage of the Search Intelligence, Autocomplete Mining, Hydration Extraction, and CSR Drift Verification engine via the Python API and CLI.

---

## 1. Python API Examples

### 1.1 Autocomplete Prediction & A–Z Alphabet Drilldown

```python
import asyncio
from behavioral_playwright import BP

async def main():
    async with BP() as bp:
        # Full A-Z alphabet drilldown
        result = await bp.mining.mine_suggest("fastapi vs", alphabet=True)
        print(f"Total Unique Suggestions: {result.total_unique}")
        for letter, suggestions in list(result.alphabet_tree.items())[:5]:
            print(f"[{letter.upper()}]:", suggestions[:2])

if __name__ == "__main__":
    asyncio.run(main())
```

### 1.2 CSR Rendering Drift Audit

```python
import asyncio
from behavioral_playwright import BP

async def main():
    async with BP() as bp:
        report = await bp.mining.audit_csr_drift(url="https://example.com")
        print(f"Drift Score: {report.drift_ratio}")
        print(f"Indexation Risk: {report.seo_indexation_risk}")
        if report.missing_in_raw:
            print("Missing in initial SSR:", report.missing_in_raw)

if __name__ == "__main__":
    asyncio.run(main())
```

### 1.3 Search Intent Cannibalization Check

```python
import asyncio
from behavioral_playwright import BP

async def main():
    async with BP() as bp:
        report = await bp.mining.check_overlap(
            query_a="python web scraping",
            query_b="python web automation",
            threshold=0.40,
        )
        print(f"Jaccard Score: {report.jaccard_score}")
        print(f"Recommendation: {report.recommendation}")
        print(f"Common URLs: {report.common_urls}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 1.4 Zero-Latency Hydration State Extraction

```python
import asyncio
from behavioral_playwright import BP

async def main():
    async with BP() as bp:
        await bp.goto("https://target-nextjs-site.com")
        
        # Zero DOM traversal state extractions
        next_data = await bp.mining.extract_next_data()
        json_ld = await bp.mining.extract_json_ld()
        open_graph = await bp.mining.extract_open_graph()

        print("Next.js Build ID:", next_data.get("buildId") if next_data else "None")
        print("Structured Data Schemas:", len(json_ld))
        print("OG Title:", open_graph.get("og:title"))

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 2. CLI Production Interface Cookbook

All mining commands can be invoked using `bp` or `python -m behavioral_playwright`:

```bash
# 1. Zero-latency Next.js / Nuxt hydration & JSON-LD metadata extraction
python -m behavioral_playwright extract-meta "https://example.com" -o meta.json

# 2. Recursively mine Google People Also Ask tree
python -m behavioral_playwright mine-paa "best mechanical keyboard for coding" --depth 2 -o paa.json

# 3. Check search intent cannibalization (Jaccard Overlap)
python -m behavioral_playwright check-overlap "python web scraping" "python web automation" --threshold 0.40

# 4. Run Google wildcard & alphabet suggest drilldown
python -m behavioral_playwright mine-suggest "fastapi vs" --alphabet -o suggestions.json

# 5. Audit CSR vs SSR rendering drift & SEO indexation risk
python -m behavioral_playwright audit-drift "https://example.com" -o drift.json
```

---

## 3. Model Context Protocol (MCP) Usage

The mining engine is exposed as native MCP tools for AI coding assistants (Claude Desktop, Cursor):

| Tool Name | Arguments | Output |
| :--- | :--- | :--- |
| `mine_google_suggest` | `query`, `alphabet`, `lang`, `country` | Typed `SuggestResult` JSON |
| `audit_csr_drift` | `url`, `raw_html`, `rendered_html` | Typed `CSRDriftReport` JSON |
| `mine_paa` | `query`, `depth`, `html` | Array of `PAANode` items |
| `check_cannibalization` | `query_a`, `query_b`, `urls_a`, `urls_b`, `threshold` | Typed `CannibalizationReport` JSON |
| `extract_metadata` | `url` | Hydration states, JSON-LD, OpenGraph |
| `sniff_api_responses` | `url`, `url_patterns`, `timeout` | Intercepted JSON payloads |
