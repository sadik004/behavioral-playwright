"""
AIOrchestrator coordinating safe click and safe type execution with automated healing and state verification.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger("BehavioralAutomation.AI.Orchestrator")


class AIOrchestrator:
    """Main coordinator for Click & Typing safe orchestration loops."""

    def __init__(
        self,
        config: Any,
        humanizer: Any,
        resolver: Any,
        validator: Any,
        verification: Any,
    ) -> None:
        self.config = config
        self.humanizer = humanizer
        self.resolver = resolver
        self.validator = validator
        self.verification = verification
        self.logger = logger

    async def execute_safe_click(
        self,
        page: Any,
        selector: str,
        expected_text: Optional[str] = None,
    ) -> bool:
        if hasattr(self.config, "ai") and not self.config.ai.enabled:
            await self.humanizer.human_click(selector)
            return True

        self.logger.info(f"[ORCHESTRATOR] Secure click on '{selector}' initiated...")
        state_before = await self.verification.record_state_before(page)

        try:
            await self.humanizer.human_click(selector)
            verify_res = await self.verification.verify_state_after(page, state_before, expected_text)
            return bool(verify_res.get("success", False))
        except Exception:
            pass

        resolution = await self.resolver.resolve_element(page, selector)
        if not resolution or not self.validator.validate_proposal(resolution):
            return False

        try:
            if resolution.get("selector"):
                await self.humanizer.human_click(resolution["selector"])
            elif resolution.get("coordinates"):
                cx, cy = resolution["coordinates"]
                await self.humanizer.move_mouse_to(cx, cy)
                await self.humanizer.page.mouse.down()
                duration = self.config.click.duration_mean if hasattr(self.config, "click") else 0.08
                await self.humanizer.clock.sleep(duration)
                await self.humanizer.page.mouse.up()

            verify_res = await self.verification.verify_state_after(page, state_before, expected_text)
            return bool(verify_res.get("success", False))
        except Exception:
            return False

    async def execute_safe_type(
        self,
        page: Any,
        selector: str,
        text: str,
        expected_text: Optional[str] = None,
    ) -> bool:
        if hasattr(self.config, "ai") and not self.config.ai.enabled:
            await self.humanizer.human_type(selector, text)
            return True

        self.logger.info(f"[ORCHESTRATOR] Secure type on '{selector}' initiated...")
        state_before = await self.verification.record_state_before(page)

        try:
            await self.humanizer.human_type(selector, text)
            verify_res = await self.verification.verify_state_after(page, state_before, expected_text)
            return bool(verify_res.get("success", False))
        except Exception:
            pass

        resolution = await self.resolver.resolve_element(page, selector)
        if not resolution or not self.validator.validate_proposal(resolution):
            return False

        try:
            if resolution.get("selector"):
                await self.humanizer.human_type(resolution["selector"], text)
            elif resolution.get("coordinates"):
                cx, cy = resolution["coordinates"]
                await self.humanizer.move_mouse_to(cx, cy)
                await self.humanizer.page.mouse.down()
                await self.humanizer.clock.sleep(0.08)
                await self.humanizer.page.mouse.up()
                await self.humanizer.page.keyboard.type(text)

            verify_res = await self.verification.verify_state_after(page, state_before, expected_text)
            return bool(verify_res.get("success", False))
        except Exception:
            return False
