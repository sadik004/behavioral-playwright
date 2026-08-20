"""
LLM Reasoning engine formulating healing prompts and parsing structured JSON actions.
"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger("BehavioralAutomation.AI.Reasoning")


class LLMReasoning:
    """Formulates reasoning prompts and parses JSON healing proposals."""

    def __init__(self, provider: Any) -> None:
        self.provider = provider
        self.logger = logger

    async def propose_healing_action(
        self,
        failed_selector: str,
        dom_snippet: str,
        visual_elements: List[Any],
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are a web agent healing broken selectors. Return JSON of action, selector, confidence, reason."
        )
        visual_str_list = [
            {"text": getattr(ve, "text", ""), "box": getattr(ve, "bounding_box", {})} for ve in visual_elements
        ]
        prompt = f"Broken Selector: '{failed_selector}'\nDOM: {dom_snippet}\nVisuals: {json.dumps(visual_str_list)}"
        raw = await self.provider.generate_response(prompt, system_prompt)

        try:
            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            parsed = json.loads(cleaned.strip())
            return {
                "action": parsed.get("action", "click"),
                "selector": parsed.get("selector", failed_selector),
                "confidence": float(parsed.get("confidence", 0.0)),
                "reason": parsed.get("reason", "Parsed."),
            }
        except Exception as e:
            return {
                "action": "click",
                "selector": failed_selector,
                "confidence": 0.0,
                "reason": f"Parsing failed: {e}",
            }
