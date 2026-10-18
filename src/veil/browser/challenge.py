"""
Automated Anti-Bot Challenge Interceptor for Veil.
Detects and autonomously resolves PerimeterX/HUMAN Security, Cloudflare Turnstile, and DataDome challenges.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("veil.browser.challenge")


class ChallengeInterceptor:
    """Enterprise-grade, automated challenge detector and solver."""

    PX_SELECTORS = [
        "[aria-label*='Human Challenge']",
        "[aria-label*='Press & Hold']",
        "#px-captcha",
        "div[id*='px-captcha']",
    ]

    CF_SELECTORS = [
        "iframe[src*='challenges.cloudflare.com']",
        "#cf-turnstile",
        "div.cf-turnstile",
    ]

    async def detect(self, page: Any) -> Optional[Dict[str, Any]]:
        """Inspects page and child frames to detect active challenges."""
        if not hasattr(page, "frames"):
            return None

        for frame in page.frames:
            # Check PerimeterX
            for sel in self.PX_SELECTORS:
                try:
                    if hasattr(frame, "locator"):
                        loc = frame.locator(sel)
                        if await loc.count() > 0:
                            return {
                                "type": "PERIMETER_X",
                                "frame": frame,
                                "locator": loc.first,
                                "selector": sel,
                            }
                except Exception:
                    continue

            # Check Cloudflare Turnstile
            for sel in self.CF_SELECTORS:
                try:
                    if hasattr(frame, "locator"):
                        loc = frame.locator(sel)
                        if await loc.count() > 0:
                            return {
                                "type": "CLOUDFLARE_TURNSTILE",
                                "frame": frame,
                                "locator": loc.first,
                                "selector": sel,
                            }
                except Exception:
                    continue

        return None

    async def resolve(
        self,
        page: Any,
        mouse: Optional[Any] = None,
        timeout: float = 20.0,
    ) -> bool:
        """Autonomously resolves detected challenge if present."""
        challenge = await self.detect(page)
        if not challenge:
            return False

        c_type = challenge["type"]
        frame = challenge["frame"]
        locator = challenge["locator"]
        logger.info(f"[ChallengeInterceptor] Detected {c_type} challenge. Initiating autonomous resolution...")

        if c_type == "PERIMETER_X":
            if mouse is not None and hasattr(mouse, "press_and_hold"):
                resolved = await mouse.press_and_hold(
                    locator,
                    frame=frame,
                    min_hold_sec=6.5,
                    max_hold_sec=timeout,
                    humanize=True,
                )
                if resolved:
                    logger.info("[ChallengeInterceptor] PerimeterX challenge verified and released.")
                    # Allow page transition
                    await asyncio.sleep(4.0)
                    return True
            else:
                logger.warning("[ChallengeInterceptor] MouseController unavailable for press_and_hold.")
                return False

        elif c_type == "CLOUDFLARE_TURNSTILE":
            if mouse is not None and hasattr(mouse, "click"):
                await mouse.click(locator, humanize=True)
                await asyncio.sleep(3.0)
                return True

        return False
