# Feature Specification: Mining & Verification Subsystem (`bp.mining`)

> **Version**: `v6.0.0`
> **Status**: [VERIFIED]
> **Subsystem**: `src/behavioral_playwright/mining/` & `src/behavioral_playwright/verification/`

---

## 1. Overview & Capabilities
The `MiningNamespace` ([`facade.py`](file:///e:/Bug/src/behavioral_playwright/facade.py)) provides automated search intelligence, keyword prediction expansion, Answer Engine Optimization (AEO), Generative Engine Optimization (GEO), and Client-Side Rendering (CSR) drift auditing.

---

## 2. Component Specifications

### 2.1 Google Suggest Wildcard & Alphabet Miner ([`suggest_miner.py`](file:///e:/Bug/src/behavioral_playwright/mining/suggest_miner.py))
- **Class**: `GoogleSuggestMiner` (alias: `SuggestMiner`)
- **Capabilities**:
  - Connects to Google Suggest endpoints using `curl_cffi` with Chrome 120 browser impersonation and an async `urllib` fallback.
  - Supports wildcard (`*`, `_`) replacement and automatic query normalization.
  - Concurrent A–Z alphabet drilldown (`alphabet_tree`) with bounded semaphore concurrency (`asyncio.Semaphore`).
  - Output mapped to typed Pydantic v2 [`SuggestResult`](file:///e:/Bug/src/behavioral_playwright/models/seo_dtos.py).

### 2.2 CSR Rendering Drift Auditor ([`rendering_auditor.py`](file:///e:/Bug/src/behavioral_playwright/verification/rendering_auditor.py))
- **Class**: `CSRRenderingDriftAuditor` (alias: `RenderingDriftAuditor`)
- **Capabilities**:
  - Compares initial static SSR/HTML against hydrated client-side rendered DOM.
  - Computes word-level Jaccard token drift ratio ($1 - \text{Jaccard}(T_{\text{raw}}, T_{\text{csr}})$).
  - Flags critical missing signals:
    - Missing H1 headings in initial HTML.
    - Missing page `<title>` tag.
    - Client-injected internal/external links (`<a>`).
    - Client-injected Schema.org JSON-LD scripts.
    - Empty SPA root containers (e.g. `<div id="root">`, `<div id="__next">`).
  - Evaluates indexation risk: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` via [`CSRDriftReport`](file:///e:/Bug/src/behavioral_playwright/models/seo_dtos.py).

### 2.3 People Also Ask (PAA) Semantic Miner ([`paa_miner.py`](file:///e:/Bug/src/behavioral_playwright/mining/paa_miner.py))
- **Class**: `PAAMiner`
- **Capabilities**:
  - Interactive multi-depth accordion expansion on live Playwright pages with dynamic DOM mutation tracking.
  - Static SERP HTML parsing via BeautifulSoup4 or fallback regex.
  - Extracts question hierarchies, answer snippet text, and citation URLs into [`PAANode`](file:///e:/Bug/src/behavioral_playwright/models/seo_dtos.py).

### 2.4 SERP Cannibalization & GEO Overlap Engine ([`cannibalization.py`](file:///e:/Bug/src/behavioral_playwright/mining/cannibalization.py))
- **Class**: `SERPCannibalizationEngine`
- **Capabilities**:
  - Normalizes URLs by stripping tracking parameters (`utm_*`, `gclid`, `fbclid`, `ref`, etc.).
  - Calculates Jaccard similarity coefficient:
    $$J(A, B) = \frac{|A \cap B|}{|A \cup B|}$$
  - Returns canonical guidance: `MERGE_INTO_SINGLE_CANONICAL` or `SPLIT_INTO_SEPARATE_PAGES` via [`CannibalizationReport`](file:///e:/Bug/src/behavioral_playwright/models/seo_dtos.py).

### 2.5 Hydration & Structured Data Extractor ([`extraction/dom.py`](file:///e:/Bug/src/behavioral_playwright/extraction/dom.py))
- **Functions**:
  - `extract_next_data(page_or_html)`: Extracts Next.js `__NEXT_DATA__` state JSON.
  - `extract_nuxt_data(page_or_html)`: Extracts Nuxt 2/3 `__NUXT__` or `__NUXT_DATA__`.
  - `extract_json_ld(page_or_html)`: Flattens all Schema.org structured scripts (`@graph` unpacked).
  - `extract_open_graph(page_or_html)`: Extracts OpenGraph and Twitter card metadata.

### 2.6 Background API Response Sniffer ([`network/sniffer.py`](file:///e:/Bug/src/behavioral_playwright/network/sniffer.py))
- **Class**: `JSONResponseSniffer`
- **Capabilities**:
  - Attaches to Playwright page `response` events.
  - Filters XHR/Fetch responses matching URL patterns.
  - Safely extracts and buffers parsed JSON payloads asynchronously with automatic detachment.

---

## 3. Public Method Signatures on `bp.mining`

```python
async def mine_suggest(query: str, alphabet: bool = False, lang: str = "en", country: str = "us") -> SuggestResult
async def audit_csr_drift(url: Optional[str] = None, raw_html: Optional[str] = None, rendered_html: Optional[str] = None) -> CSRDriftReport
async def check_overlap(query_a: str, query_b: str, urls_a: Optional[List[str]] = None, urls_b: Optional[List[str]] = None, threshold: float = 0.40) -> CannibalizationReport
async def mine_paa(page_or_html: Any = None, query: Optional[str] = None, max_depth: int = 3) -> List[PAANode]
async def audit_aio(query: str, page_or_html: Any = None, brand: Optional[str] = None, competitors: Optional[List[str]] = None) -> AIOAuditResult
async def extract_next_data(page_or_html: Any = None) -> Optional[Dict[str, Any]]
async def extract_nuxt_data(page_or_html: Any = None) -> Optional[Dict[str, Any]]
async def extract_json_ld(page_or_html: Any = None) -> List[Dict[str, Any]]
async def extract_open_graph(page_or_html: Any = None) -> Dict[str, str]
def create_sniffer(page: Any = None) -> JSONResponseSniffer
```
