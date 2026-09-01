# Recursive Web Crawling Guide

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Bounded BFS Recursive Crawling

The recursive crawler systematically explores websites, respecting depth bounds, page maximums, domain barriers, and cycle traps:

```python
import asyncio
from bp_facade12 import BP

async def crawl_site():
    async with BP() as bp:
        visited_urls = await bp.web.crawl_recursive(
            url="https://example.com",
            max_depth=2,
            max_pages=20,
            db_path="crawl_session.db"
        )
        print(f"Crawled {len(visited_urls)} unique pages:")
        for u in visited_urls:
            print(" -", u)

        # Generate XML Sitemap from crawled URLs
        sitemap_xml = bp.web.generate_sitemap(visited_urls)
        with open("sitemap.xml", "w", encoding="utf-8") as f:
            f.write(sitemap_xml)

if __name__ == "__main__":
    asyncio.run(crawl_site())
```
