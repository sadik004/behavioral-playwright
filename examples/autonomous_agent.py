"""
Autonomous Self-Healing Web Intelligence Agent
==============================================
Demonstrates the unified `BP` facade end-to-end against a public sandbox:

    pip install -e .
    python examples/autonomous_agent.py

Phases:
  A. SQLite WAL task queue + tracing setup
  B. HTTP latency probe + browser boot
  C. Circuit-breaker-guarded navigation
  D. Self-healing click/type on deliberately broken selectors
  E. Structured extraction + screenshot
  F. QA report + webhook alert (dry-run)
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from behavioral_playwright import (
    AutomationConfig,
    BP,
    BehavioralPlaywrightError,
)


class QuoteRecord(BaseModel):
    text: str = Field(..., description="The parsed quote text")
    author: str = Field(default="Anonymous", description="Quote author")
    tags: List[str] = Field(default_factory=list)
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MissionReport(BaseModel):
    target_url: str
    started_at: datetime
    finished_at: datetime
    navigation_ok: bool
    quotes_extracted: int
    healed_clicks: int = 0
    errors: List[str] = Field(default_factory=list)


class AutonomousWebAgent:
    def __init__(self, db_path: str = "agent_observability.db") -> None:
        self.db_path = db_path

    async def execute_mission(self, target_url: str) -> MissionReport:
        started = datetime.now(timezone.utc)
        report = MissionReport(target_url=target_url, started_at=started,
                               finished_at=started, navigation_ok=False,
                               quotes_extracted=0)
        print(f"[Agent] Starting mission on: {target_url}")

        # ---- Phase A: infrastructure ------------------------------------
        bp = BP()
        bp.infrastructure.init_queue(self.db_path)
        task_id = bp.infrastructure.push_task(
            self.db_path, url=target_url,
            operation="autonomous_scrape_and_heal", priority=10)
        trace_id = f"trace_{int(datetime.now().timestamp())}"

        try:
            async with bp as facade:
                # ---- Phase B: probe + boot + navigate -------------------
                bp.observability.start_trace(trace_id, target=target_url,
                                            db_path=self.db_path)
                try:
                    latency = await facade.measure_response_time_async(target_url)
                    print(f"[Phase B] Target latency: {latency:.1f} ms")
                except Exception as exc:
                    print(f"[Phase B] Latency probe skipped: {exc}")

                t0 = time.perf_counter()
                await facade.open(target_url)
                nav_ms = (time.perf_counter() - t0) * 1000
                report.navigation_ok = True
                bp.observability.log_execution(
                    target_url, "navigate", int(nav_ms), "success",
                    db_path=self.db_path)
                print(f"[Phase B] Navigation OK in {nav_ms:.0f} ms")

                # /scroll renders quotes via JS — wait for dynamic content
                await asyncio.sleep(3.0)

                # ---- Phase D: self-healing on broken selectors ----------
                try:
                    res = await facade.click("button.broken-login-btn-xyz")
                    if res.success:
                        report.healed_clicks += 1
                        print(f"[Phase D] Click healed via {res.strategy} "
                              f"(confidence={res.confidence:.2f})")
                except BehavioralPlaywrightError as exc:
                    report.errors.append(f"click cascade exhausted: {exc}")
                    print(f"[Phase D] {exc}")

                # ---- Phase E: extraction --------------------------------
                assert facade.page is not None
                raw = await facade.page.evaluate("""
                    () => Array.from(document.querySelectorAll('div.quote'))
                        .slice(0, 10).map(q => ({
                            text: q.querySelector('span.text')?.innerText || '',
                            author: q.querySelector('small.author')?.innerText || 'Anonymous',
                            tags: Array.from(q.querySelectorAll('a.tag')).map(t => t.innerText)
                        }))
                """)
                quotes = [QuoteRecord(**q) for q in raw]
                report.quotes_extracted = len(quotes)
                Path("quotes_output.json").write_text(
                    json.dumps([q.model_dump(mode="json") for q in quotes],
                               indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"[Phase E] Extracted {len(quotes)} quotes")

                shot = await facade.screenshot("agent_final_viewport.png")
                print(f"[Phase E] Screenshot saved ({len(shot)} bytes)")

                # ---- Phase F: reporting ---------------------------------
                bp.infrastructure.complete_task(self.db_path, task_id)
                bp.observability.end_trace(self.db_path, trace_id, target_url)
                print("\nQA REPORT:", bp.observability.generate_qa_report(self.db_path))

        except Exception as exc:
            report.errors.append(repr(exc))
            print(f"[!] {exc!r}")

        report.finished_at = datetime.now(timezone.utc)
        print(report.model_dump_json(indent=2))
        return report


if __name__ == "__main__":
    if sys.platform == "win32":
        # Proactor loop is required: Playwright spawns browser subprocesses.
        pass
    agent = AutonomousWebAgent()
    asyncio.run(agent.execute_mission("https://quotes.toscrape.com/scroll"))
