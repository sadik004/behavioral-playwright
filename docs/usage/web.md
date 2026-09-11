# Web Scraping & HTML Processing Guide

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Local DOM Scraping & Tag Filtering

Scrape web pages without spawning a full browser, removing non-content tags (such as headers, footers, and scripts):

```python
import asyncio
from bp_facade12 import BP

async def main():
    async with BP() as bp:
        result = await bp.web.scrape(
            "https://example.com/article",
            options={
                "includeTags": ["article", "main", "h1", "p"],
                "excludeTags": ["nav", "footer", "script", "style"]
            }
        )
        print("Cleaned Content:\n", result.content)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 2. Link Extraction & Filtering

Extract and resolve relative URLs from raw HTML:

```python
links = bp.web.extract_links("https://example.com", html_content="<a href='/news'>News</a>")
clean_links = bp.web.filter_crawl_links("https://example.com", links)
print("Resolved Links:", clean_links)
```
