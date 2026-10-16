"""
Isolated Worker Context Swarm Orchestrator
Orchestrates parallel browser worker contexts with isolated socket contexts.
"""
import asyncio
import logging
from typing import Dict, List, Any

logger = logging.getLogger("BehavioralEvasion.SwarmOrchestrator")


class MultiTabSwarmOrchestrator:
    """Orchestrates parallel browser worker contexts with isolated socket contexts."""
    def __init__(self, max_tabs: int = 5):
        self.max_tabs = max_tabs

    async def execute_swarm_task(self, browser_instance: Any, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info(f"⚡ Dispatching Swarm Task across {len(tasks)} items with isolated context sockets...")
        results = []

        async def worker_tab(task_info: Dict[str, Any]):
            url = task_info.get("url")
            try:
                ctx = await browser_instance.new_context()
                page = await ctx.new_page()
                await page.goto(url, wait_until="domcontentloaded")
                await asyncio.sleep(0.5)
                title = await page.title()
                res = {"url": url, "status": "success", "title": title}
                await ctx.close()
            except Exception as e:
                res = {"url": url, "status": "error", "error": str(e)}
            return res

        for i in range(0, len(tasks), self.max_tabs):
            chunk = tasks[i:i + self.max_tabs]
            chunk_results = await asyncio.gather(*[worker_tab(t) for t in chunk])
            results.extend(chunk_results)
        return results
