"""
Multi-Worker Concurrent Crawler
===============================
Demonstrates the SQLite priority task queue (`bp.infrastructure`) driving
multiple concurrent crawl workers through the unified `BP` facade.

    pip install -e .
    python examples/multi_worker_crawler.py
"""

import asyncio
from typing import List

from behavioral_playwright import BP


async def worker(bp: BP, db_path: str, worker_id: int) -> int:
    """Pops tasks from the queue until empty; returns pages crawled."""
    crawled = 0
    while True:
        task = bp.infrastructure.pop_task(db_path)
        if task is None:
            return crawled
        url = task["url"]
        print(f"[worker-{worker_id}] crawling {url}")
        try:
            async with bp as facade:
                await facade.open(url)
                await asyncio.sleep(1.0)  # polite delay
            bp.infrastructure.complete_task(db_path, task["id"])
            bp.web.save_crawl_state("crawl_state.db", url, "completed")
            crawled += 1
        except Exception as exc:
            print(f"[worker-{worker_id}] failed {url}: {exc!r}")
            bp.infrastructure.fail_task(db_path, task["id"])


async def main() -> None:
    db_path = "crawler_tasks.db"
    bp = BP()
    bp.infrastructure.init_queue(db_path)
    bp.web.init_crawl_session("crawl_state.db")

    seeds: List[str] = [
        "https://quotes.toscrape.com",
        "https://quotes.toscrape.com/login",
        "https://quotes.toscrape.com/scroll",
    ]
    for i, url in enumerate(seeds):
        bp.infrastructure.push_task(db_path, url=url,
                                    operation="crawl_page", priority=i)

    results = await asyncio.gather(
        *(worker(bp, db_path, w) for w in range(3))
    )
    print(f"\nTotal pages crawled: {sum(results)}")


if __name__ == "__main__":
    asyncio.run(main())
