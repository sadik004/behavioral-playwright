# 🕷️ Advanced Web Crawling & Deep Site Exploration Guide

> **Framework Version**: `10.0.2 Quantum Architecture`  
> **Status**: [VERIFIED & PASSING 742 GATES]

---

## 1. Overview

The framework provides an enterprise-grade, paper-grounded web crawling engine designed for large-scale web scraping, anti-bot evasion, and LLM corpus preparation. It supports both high-level facade crawling via `BP` and standalone deep exploration pipelines.

---

## 2. 4-Tier Adaptive Crawling Escalation

When facing modern anti-bot protection (Cloudflare Turnstile, DataDome, Akamai, PerimeterX), the crawler uses a 4-tier automated escalation hierarchy:

| Tier | Engine Type | Transport | Best Suited For |
| :--- | :--- | :--- | :--- |
| **Tier 1: `HTTP_FAST`** | Async Python HTTP | In-memory cached connection pool | Static HTML, blogs, public APIs, RSS feeds |
| **Tier 2: `TLS_IMPERSONATE`** | `curl_cffi` | JA3/JA4 fingerprint spoofing | Basic Cloudflare / TLS-fingerprinted domains |
| **Tier 3: `BROWSER_HEADLESS`** | Headless Chromium | Patchright with CDP WeakMap shields | Client-Side Rendered (CSR) SPAs, dynamic tables |
| **Tier 4: `BROWSER_STEALTH_KINEMATICS`**| Full Stealth Browser | Saccadic Costello curves + micro-tremor | High-security enterprise portals, Turnstile challenges |

### 4-Tier Escalation Example:

```python
import asyncio
from veil import BP
from veil.crawling.models import CrawlerTier

async def main():
    async with BP() as bp:
        # Automatically escalates up to Tier 4 if challenges are detected
        results = await bp.crawl(
            "https://target-portal.com",
            max_pages=25,
            initial_tier=CrawlerTier.HTTP_FAST,
            max_tier=CrawlerTier.BROWSER_STEALTH_KINEMATICS,
        )
        print(f"Successfully scraped {len(results)} pages across tiers.")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 3. Crash-Resilient Deep Site Crawler (`DeepSiteCrawler`)

For multi-day or massive website crawls, `DeepSiteCrawler` coupled with `PersistentFrontierQueue` uses SQLite in WAL (Write-Ahead Logging) mode to ensure zero data loss during power outages or process crashes:

```python
import asyncio
from pathlib import Path
from veil.crawling.deep_crawler import DeepSiteCrawler, PersistentFrontierQueue

async def main():
    db_path = Path("crawl_state.db")
    
    # 1. Initialize persistent WAL frontier
    frontier = PersistentFrontierQueue(db_path=str(db_path))
    
    # 2. Instantiate multi-worker deep crawler
    crawler = DeepSiteCrawler(
        frontier=frontier,
        max_concurrency=5,
        max_depth=3,
        enable_simhash_dedup=True,
    )
    
    # 3. Execute deep crawl (resumes automatically if previously interrupted)
    await crawler.crawl_site(start_url="https://docs.example.com")
    
    print("Crawl completed successfully. Frontier sealed.")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 4. Multi-Armed Bandit (MAB) Proxy Selection (`BanditProxyRotator`)

The crawling engine implements Beta-Bernoulli Thompson Sampling and Upper Confidence Bound (UCB1) algorithms to route traffic through the most reliable proxies while avoiding burned IPs:

```python
from veil.crawling.bandit_proxy_rotator import BanditProxyRotator, ProxyRecord

# Initialize rotator with proxy list
rotator = BanditProxyRotator(
    proxies=[
        ProxyRecord(url="http://proxy1.internal:8080"),
        ProxyRecord(url="http://proxy2.internal:8080"),
        ProxyRecord(url="http://proxy3.internal:8080"),
    ],
    cooldown_seconds=120.0,
)

# Select best performing proxy based on historical rewards
proxy = rotator.select_proxy()

# Update telemetry after request
try:
    # ... execute request ...
    rotator.record_result(proxy, success=True, latency_ms=145.2)
except Exception:
    rotator.record_result(proxy, success=False, status_code=429)
```

---

## 5. Bounded BFS Recursive Crawling & Sitemap Generation

For standard website mapping and sitemap creation:

```python
import asyncio
from veil import BP

async def main():
    async with BP() as bp:
        visited_urls = await bp.web.crawl_recursive(
            url="https://example.com",
            max_depth=2,
            max_pages=20,
            db_path="crawl_session.db"
        )
        print(f"Crawled {len(visited_urls)} unique pages.")

        # Generate XML Sitemap from discovered URLs
        sitemap_xml = bp.web.generate_sitemap(visited_urls)
        with open("sitemap.xml", "w", encoding="utf-8") as f:
            f.write(sitemap_xml)

if __name__ == "__main__":
    asyncio.run(main())
```
