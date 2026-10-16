# Feature Specification: Web Namespace (`bp.web`)

> **Last Verified Against Commit**: `v10.0.2`
> **Status**: [VERIFIED]

---

## 1. Overview & Capabilities
The `WebNamespace` ([`veil/facade.py`](src/veil/facade.py)) provides high-speed, stateless HTML data acquisition, link filtering, and bounded recursive crawling.

---

## 2. API Method Reference

### `scrape(url_or_html, schema=None, options=None)`
- **Signature**: `async def scrape(self, url_or_html: str, schema: Optional[Dict[str, Any]] = None, options: Optional[Dict[str, Any]] = None) -> AcquisitionResult`
- **Description**: Parses and cleans DOM content based on `includeTags` and `excludeTags`.
- **Throws**: `ValueError` if input is empty or invalid.

### `crawl_recursive(url, max_depth=3, db_path="crawl_state.db", max_pages=None, options=None)`
- **Signature**: `async def crawl_recursive(self, url: str, max_depth: int = 3, db_path: str = "crawl_state.db", max_pages: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> List[str]`
- **Description**: Executes BFS web crawling, discovering links, tracking visited states in SQLite, and enforcing domain limits.

### `extract_links(base_url, html_content=None, result=None)`
- **Signature**: `def extract_links(self, base_url: str, html_content: Optional[str] = None, result: Optional[Any] = None) -> List[str]`
- **Description**: Extracts and resolves all valid HTTP/HTTPS URLs from HTML content.

### `generate_sitemap(visited_urls)`
- **Signature**: `def generate_sitemap(self, visited_urls: List[str]) -> str`
- **Description**: Converts a list of URLs into valid XML sitemap markup.
