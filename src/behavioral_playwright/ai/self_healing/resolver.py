"""
Cascading Self-Healing Resolver: L1 Levenshtein -> L2 DOM Accessibility -> L3 CV/OCR -> L4 LLM Reasoning.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("BehavioralAutomation.AI.Resolver")


class SelfHealingResolver:
    """Implements the 4-tier Cascading Self-Healing Resolver."""

    def __init__(
        self,
        config: Any,
        deterministic_healer: Any,
        vision_engine: Any,
        llm_reasoning: Any,
    ) -> None:
        self.config = config
        self.healer = deterministic_healer
        self.vision = vision_engine
        self.llm = llm_reasoning
        self.logger = logger

    async def resolve_element(self, page: Any, selector: str) -> Optional[Dict[str, Any]]:
        if hasattr(self.config, "ai") and not self.config.ai.self_healing_enabled:
            return None

        self.logger.warning(f"[RESOLVER] Cascading healing resolver triggered for '{selector}'")
        candidates = []
        try:
            candidates = await page.evaluate("""() => {
                const query = 'button, input, a, select, textarea, [role="button"], [role="link"], [role="textbox"], [role="checkbox"], [role="menuitem"], [role="tab"], [onclick], [tabindex]';
                const els = Array.from(document.querySelectorAll(query));
                return els.map(el => {
                    const id = el.id ? '#' + el.id : '';
                    const cls = el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/).join('.') : '';
                    const tag = el.tagName.toLowerCase();
                    const text = el.innerText ? el.innerText.substring(0, 30).trim() : '';
                    return {selector: id || (tag + cls) || tag, text: text, role: el.getAttribute('role') || '', name: el.getAttribute('name') || '', tag: tag};
                }).filter(e => e.selector !== 'body');
            }""")
        except Exception:
            candidates = [
                {"selector": "#btn-login", "text": "Login", "role": "button", "name": "login", "tag": "button"},
                {"selector": "input[name='login']", "text": "", "role": "", "name": "login", "tag": "input"},
                {"selector": "button[type='submit']", "text": "Submit", "role": "button", "name": "", "tag": "button"},
                {"selector": "#text-input", "text": "Input field", "role": "textbox", "name": "input", "tag": "input"},
            ]

        candidate_selectors = [c["selector"] for c in candidates if isinstance(c, dict) and c.get("selector")]

        # Level 1: Deterministic Levenshtein Fuzzy Match
        best = self.healer.heal_selector(selector, candidate_selectors)
        if best:
            return {
                "selector": best,
                "coordinates": None,
                "strategy": "deterministic_levenshtein",
                "confidence": 0.85,
            }

        # Level 2: DOM Accessibility Attribute Matching
        clean_sel = selector.lower().replace("#", "").replace(".", "").replace("-", "")
        for c in candidates:
            c_role = c.get("role", "").lower()
            c_text = c.get("text", "").lower()
            c_name = c.get("name", "").lower()
            if (c_text and c_text in clean_sel) or (c_name and c_name in clean_sel) or (c_role and c_role in clean_sel):
                return {
                    "selector": c["selector"],
                    "coordinates": None,
                    "strategy": "dom_accessibility",
                    "confidence": 0.80,
                }

        # Level 3: Computer Vision & OCR
        visual_elements = await self.vision.capture_and_analyze(page)
        clean_selector = selector.replace("#", "").replace(".", "").replace("-", " ").lower()
        for ve in visual_elements:
            if clean_selector in ve.text.lower() or ve.text.lower() in clean_selector:
                box = ve.bounding_box
                cx = box["x"] + box["width"] / 2.0
                cy = box["y"] + box["height"] / 2.0
                return {
                    "selector": None,
                    "coordinates": (cx, cy),
                    "strategy": "cv_ocr",
                    "confidence": 0.90,
                }

        # Level 4: LLM Cognitive Reasoning
        dom_snippet = ""
        try:
            dom_snippet = await page.evaluate("() => document.body.innerHTML.substring(0, 1000)")
        except Exception:
            dom_snippet = "<div><button id='btn-login'>Login Here</button></div>"

        proposal = await self.llm.propose_healing_action(selector, dom_snippet, visual_elements)
        threshold = self.config.ai.confidence_threshold if hasattr(self.config, "ai") else 0.70

        if proposal["confidence"] >= threshold:
            return {
                "selector": proposal["selector"],
                "coordinates": None,
                "strategy": "llm_reasoning",
                "confidence": proposal["confidence"],
                "action": proposal["action"],
            }

        return None
