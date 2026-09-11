# Acquisition Subsystem Usage Guide

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. The Acquisition Request & Result Pattern

The `AcquisitionRouter` allows standardized data extraction from both online URLs and local HTML strings:

```python
import asyncio
from bp_facade12 import BP

async def main():
    async with BP() as bp:
        # 1. Acquire offline HTML
        html_doc = "<html><body><h1>Product</h1><p class='price'>$29.99</p></body></html>"
        result = await bp.web.scrape(html_doc)
        print("Scraped:", result.content)

if __name__ == "__main__":
    asyncio.run(main())
```
