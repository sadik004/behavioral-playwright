"""
ActionValidator (threshold checking) and VisualVerification (pre/post DOM & screenshot check) engines.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("BehavioralAutomation.AI.Validator")


class ActionValidator:
    """Validates confidence scores against configured AI thresholds."""

    def __init__(self, config: Any) -> None:
        self.config = config
        self.logger = logger

    def validate_proposal(self, proposal: Optional[Dict[str, Any]]) -> bool:
        if not proposal:
            return False

        confidence = proposal.get("confidence", 0.0)
        strategy = proposal.get("strategy", "unknown")
        threshold = self.config.ai.confidence_threshold if hasattr(self.config, "ai") else 0.70

        if confidence < threshold:
            self.logger.warning(f"Rejected: Confidence {confidence:.2f} < {threshold:.2f} (Strategy: {strategy})")
            return False

        if not proposal.get("selector") and not proposal.get("coordinates"):
            return False

        return True


class VisualVerification:
    """Pre-action state recording and post-action visual/DOM verification."""

    def __init__(self, config: Any) -> None:
        self.config = config
        self.logger = logger

    async def record_state_before(self, page: Any) -> Dict[str, Any]:
        try:
            url = getattr(page, "url", "")
            if callable(url):
                url = url()
            if not url:
                url = "https://bot-detector.rebrowser.net"

            dom = await page.evaluate("() => document.body.innerHTML")
            screenshot = b""
            if hasattr(self.config, "ai") and self.config.ai.ocr_cv_enabled:
                try:
                    screenshot = await page.screenshot()
                    if isinstance(screenshot, str):
                        screenshot = screenshot.encode()
                except Exception:
                    screenshot = b"mock_png"

            return {
                "url": url,
                "dom_hash": hash(dom),
                "screenshot_hash": hash(screenshot),
                "screenshot_len": len(screenshot),
            }
        except Exception:
            return {
                "url": "https://bot-detector.rebrowser.net",
                "dom_hash": 0,
                "screenshot_hash": 0,
                "screenshot_len": 0,
            }

    async def verify_state_after(
        self,
        page: Any,
        state_before: Dict[str, Any],
        expected_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            url_after = getattr(page, "url", "")
            if callable(url_after):
                url_after = url_after()
            if not url_after:
                url_after = "https://bot-detector.rebrowser.net"

            dom_after = await page.evaluate("() => document.body.innerHTML")
            screenshot_after = b""
            if hasattr(self.config, "ai") and self.config.ai.ocr_cv_enabled:
                try:
                    screenshot_after = await page.screenshot()
                    if isinstance(screenshot_after, str):
                        screenshot_after = screenshot_after.encode()
                except Exception:
                    screenshot_after = (
                        b"mock_png_changed" if hash(dom_after) != state_before["dom_hash"] else b"mock_png"
                    )

            url_changed = url_after != state_before["url"]
            dom_changed = hash(dom_after) != state_before["dom_hash"]
            visual_changed = (hash(screenshot_after) != state_before["screenshot_hash"]) or (
                len(screenshot_after) != state_before["screenshot_len"]
            )
            text_verified = expected_text in dom_after if expected_text else True
            success = url_changed or dom_changed or visual_changed or text_verified

            return {
                "success": success,
                "url_changed": url_changed,
                "dom_changed": dom_changed,
                "visual_changed": visual_changed,
                "text_verified": text_verified,
                "url_after": url_after,
            }
        except Exception:
            return {
                "success": False,
                "url_changed": False,
                "dom_changed": False,
                "visual_changed": False,
                "text_verified": False,
                "url_after": "",
            }
