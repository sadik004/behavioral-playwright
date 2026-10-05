"""Workflow executor routing actions strictly through existing framework abstractions."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Optional, Tuple

from behavioral_playwright.exceptions import BehavioralPlaywrightError
from behavioral_playwright.orchestration.exceptions import ExecutionError
from behavioral_playwright.orchestration.models import WorkflowStep
from behavioral_playwright.orchestration.state import WorkflowState


class WorkflowExecutor:
    """Executes validated workflow steps using the existing Behavioral Playwright architecture."""

    def __init__(self, clock_fn: Optional[Any] = None) -> None:
        self._clock_fn = clock_fn or time.monotonic

    async def execute_step(
        self,
        step: WorkflowStep,
        session: Any,
        state: WorkflowState,
    ) -> Tuple[Any, Dict[str, Any]]:
        """Executes a single step and captures live runtime evidence.
        
        Returns:
            Tuple of (step_result, runtime_evidence_dict)
        """
        start_time = self._clock_fn()
        action = step.action.lower()
        inp = step.input_data

        if session is None:
            raise ExecutionError(f"Cannot execute step '{step.step_id}': Session is None or invalid.")

        try:
            result = None
            evidence: Dict[str, Any] = {
                "step_id": step.step_id,
                "action": step.action,
                "timestamp": start_time,
            }

            # 1. Navigation
            if action in ("navigate", "goto"):
                url = inp.get("url", "")
                await session.goto(url)
                page = getattr(session, "raw_page", None)
                curr_url = page.url if page and hasattr(page, "url") else url
                title = await session.get_title() if hasattr(session, "get_title") else ""
                dom_html = await page.content() if page and hasattr(page, "content") else ""
                dom_hash = hashlib.sha256(dom_html.encode("utf-8")).hexdigest()

                result = {"url": curr_url, "title": title}
                evidence.update({
                    "url": curr_url,
                    "title": title,
                    "dom_hash": dom_hash,
                })

            # 2. Selector Resolution
            elif action in ("resolve", "find"):
                selector = inp.get("selector", "")
                res = await session.resolve(selector)
                result = res
                found = res is not None and getattr(res, "element", None) is not None
                evidence.update({
                    "selector": selector,
                    "element_found": found,
                    "strategy": getattr(res, "strategy", None).value if getattr(res, "strategy", None) else "UNKNOWN",
                    "confidence": getattr(res, "confidence", 0.0),
                    "is_healed": getattr(res, "is_healed", False),
                })

            # 3. Behavioral Mouse Click
            elif action in ("click", "stealth_click"):
                selector = inp.get("selector", "")
                if hasattr(session, "click_healed"):
                    res = await session.click_healed(selector)
                elif hasattr(session, "click"):
                    res = await session.click(selector)
                elif hasattr(session, "mouse") and hasattr(session.mouse, "click_selector"):
                    res = await session.mouse.click_selector(selector)
                elif hasattr(session, "raw_page") and hasattr(session.raw_page, "click"):
                    res = await session.raw_page.click(selector)
                else:
                    raise ExecutionError(f"Session does not support click action: {type(session)}")

                result = res
                page = getattr(session, "raw_page", None)
                dom_html = await page.content() if page and hasattr(page, "content") else ""
                dom_hash = hashlib.sha256(dom_html.encode("utf-8")).hexdigest()
                evidence.update({
                    "selector": selector,
                    "clicked": True,
                    "dom_hash": dom_hash,
                })

            # 4. Keystroke Typing
            elif action in ("type", "type_text", "fill"):
                selector = inp.get("selector", "")
                text = inp.get("text", "")
                if hasattr(session, "type_healed"):
                    res = await session.type_healed(selector, text)
                elif hasattr(session, "type"):
                    res = await session.type(selector, text)
                elif hasattr(session, "keyboard") and hasattr(session.keyboard, "fill"):
                    res = await session.keyboard.fill(selector, text)
                elif hasattr(session, "raw_page") and hasattr(session.raw_page, "fill"):
                    res = await session.raw_page.fill(selector, text)
                else:
                    raise ExecutionError(f"Session does not support type action: {type(session)}")

                result = res
                page = getattr(session, "raw_page", None)
                dom_html = await page.content() if page and hasattr(page, "content") else ""
                dom_hash = hashlib.sha256(dom_html.encode("utf-8")).hexdigest()
                evidence.update({
                    "selector": selector,
                    "text_length": len(text),
                    "dom_hash": dom_hash,
                })

            # 5. DOM Extraction
            elif action in ("extract", "scrape"):
                selector = inp.get("selector")
                target = inp.get("target", "text")
                if hasattr(session, "extract"):
                    res = await session.extract(selector=selector, target=target)
                elif target == "text" and selector and hasattr(session, "extract_text"):
                    res = await session.extract_text(selector)
                elif target == "links" and hasattr(session, "extract_links"):
                    res = await session.extract_links(selector)
                elif hasattr(session, "extractor") and hasattr(session, "raw_page") and selector:
                    res = await session.extractor.extract_text(session.raw_page, selector)
                elif hasattr(session, "raw_page") and hasattr(session.raw_page, "inner_text") and selector:
                    res = await session.raw_page.inner_text(selector)
                else:
                    res = {}
                result = res
                evidence.update({
                    "selector": selector,
                    "target": target,
                    "extracted_count": len(res) if isinstance(res, (list, dict, str)) else 1,
                    "data_sample": str(res)[:200],
                })

            # 6. Structured Schema Mapping
            elif action in ("map_schema", "schema_map"):
                schema_cls = inp.get("schema")
                res = await session.map_schema(schema_cls=schema_cls)
                result = res
                evidence.update({
                    "schema": getattr(schema_cls, "__name__", str(schema_cls)),
                    "confidence": getattr(res, "confidence", 1.0),
                    "conflicts": getattr(res, "conflicts", []),
                })

            # 7. Search
            elif action == "search":
                query = inp.get("query", "")
                res = await session.search(query=query)
                result = res
                evidence.update({
                    "query": query,
                    "result_count": len(res) if isinstance(res, list) else 0,
                })

            # 8. Recovery Trigger
            elif action == "recover":
                category = inp.get("category")
                res = await session.recover(category=category)
                result = res
                evidence.update({
                    "recovered": bool(res),
                    "recovery_record": getattr(res, "to_dict", lambda: str(res))(),
                })

            # 9. Custom / Forwarder
            else:
                if hasattr(session, action):
                    fn = getattr(session, action)
                    res = fn(**inp)
                    if hasattr(res, "__await__"):
                        res = await res
                    result = res
                    evidence.update({"custom_action": action, "output": str(res)[:200]})
                else:
                    raise ExecutionError(f"Unsupported workflow action: '{action}' on session {type(session)}")

            return result, evidence

        except Exception as exc:
            if isinstance(exc, ExecutionError):
                raise
            raise ExecutionError(f"Step '{step.step_id}' failed executing action '{action}': {exc}") from exc
