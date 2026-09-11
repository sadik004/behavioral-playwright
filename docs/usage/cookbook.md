# Automation & Scraping Cookbook (Real-World Recipes)

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## Recipe 1: End-to-End Stealth Login & Screenshot
```python
import asyncio
from bp_facade12 import BP

async def recipe_login():
    async with BP() as bp:
        await bp.browser.goto("https://example.com/login")
        await bp.browser.type("input#email", "user@example.com")
        await bp.browser.type("input#password", "Secret1234!")
        await bp.browser.check("input#remember")
        await bp.browser.click("button[type='submit']")
        await bp.browser.scroll(300.0)
        await bp.browser.screenshot("logged_in_dashboard.png")
        print("Recipe 1: Logged in and captured snapshot.")

if __name__ == "__main__":
    asyncio.run(recipe_login())
```

---

## Recipe 2: Recursive Crawling, Offline Caching & Sitemap Generation
```python
import asyncio
from bp_facade12 import BP

async def recipe_crawl():
    async with BP() as bp:
        urls = await bp.web.crawl_recursive("https://example.com", max_depth=2, max_pages=10)
        sitemap = bp.web.generate_sitemap(urls)
        print("Recipe 2: Generated Sitemap:\n", sitemap)

if __name__ == "__main__":
    asyncio.run(recipe_crawl())
```

---

## Recipe 3: Image OCR to Slack Notification
```python
import asyncio
from bp_facade12 import BP

async def recipe_ocr_slack():
    async with BP() as bp:
        ocr_data = await bp.document.ocr_image_with_autocorrect("receipt.png")
        message = f"*Receipt Processed*: {ocr_data['text'][:100]}... (Checksum: {ocr_data['checksum']})"
        await bp.integrations.slack_webhook_notify_async(
            "https://hooks.slack.com/services/...",
            message
        )
        print("Recipe 3: OCR text dispatched to Slack.")

if __name__ == "__main__":
    asyncio.run(recipe_ocr_slack())
```

---

## Recipe 4: Performance Profiling with Monotonic Traces & QA Audit
```python
import asyncio
from bp_facade12 import BP

async def recipe_observability():
    async with BP() as bp:
        db = "qa_audit.db"
        bp.observability.init_metrics_db(db)

        bp.observability.start_trace("search_flow")
        await bp.browser.goto("https://httpbin.org/html")
        await bp.browser.click("h1")
        elapsed = bp.observability.end_trace("search_flow", url="https://httpbin.org/html", db_path=db)

        qa_rep = bp.observability.generate_qa_report(db)
        print(f"Recipe 4: Flow elapsed: {elapsed:.2f} ms | QA Status: {qa_rep['status']}")

if __name__ == "__main__":
    asyncio.run(recipe_observability())
```
