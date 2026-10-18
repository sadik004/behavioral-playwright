"""
Biomechanical & Resilient MouseController for Browser Input Automation.
Integrated with Costello Saccadic Trajectory Generation and Sub-Pixel Micro-Jitter.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional, Tuple

from behavioral_playwright.logging import get_logger

logger = get_logger("automation.mouse")


class MouseController:
    """
    Provides human-mimetic mouse automation with biometric spline interpolation.
    """

    def __init__(
        self,
        page: Any,
        biomechanics: Optional[Any] = None,
        vision_guard: Optional[Any] = None,
        initial_pos: Tuple[float, float] = (0.0, 0.0)
    ) -> None:
        self.page = page
        self._biomechanics = biomechanics
        self._vision_guard = vision_guard
        self.current_x = float(initial_pos[0])
        self.current_y = float(initial_pos[1])

    @property
    def biomechanics(self) -> Any:
        if self._biomechanics is None:
            from behavioral_playwright.powerplay.biomechanics import BiomechanicalTremorEngine
            self._biomechanics = BiomechanicalTremorEngine()
        return self._biomechanics

    @property
    def vision_guard(self) -> Any:
        if self._vision_guard is None:
            from behavioral_playwright.powerplay.vision_guard import UltimateVisionLanguageActionGuard
            self._vision_guard = UltimateVisionLanguageActionGuard()
        return self._vision_guard

    async def move(
        self,
        x: float,
        y: float,
        steps: int = 25,
        humanize: bool = True
    ) -> None:
        """
        Moves mouse cursor to coordinate (x, y).
        When humanize=True, generates a Costello two-phase saccadic trajectory with Harris-Wolpert noise.
        """
        target_x = float(x)
        target_y = float(y)

        if hasattr(self.page, "mouse") and hasattr(self.page.mouse, "move"):
            if humanize:
                trajectory = self.biomechanics.generate_bezier_trajectory(
                    start_pos=(self.current_x, self.current_y),
                    target_pos=(target_x, target_y),
                    steps=steps
                )
                for pt_x, pt_y in trajectory:
                    await self.page.mouse.move(pt_x, pt_y)
                    # Micro-delay between trajectory points to maintain realistic velocity curve
                    await asyncio.sleep(0.002)
            else:
                await self.page.mouse.move(target_x, target_y)

        self.current_x = target_x
        self.current_y = target_y

    async def click(
        self,
        selector_or_x: Any,
        y: Optional[float] = None,
        humanize: bool = True
    ) -> None:
        """
        Clicks on a CSS selector or at coordinates (x, y).
        When humanize=True, applies subpixel targeting and authentic button down/up dwell time.
        """
        if y is not None:
            raw_x = float(selector_or_x)
            raw_y = float(y)

            if humanize and hasattr(self.page, "mouse"):
                # Apply subpixel jitter so coordinate clicks do not hit robotic integer centroids
                sub_x, sub_y = self.vision_guard.synthesize_subpixel_click((raw_x, raw_y))
                await self.move(sub_x, sub_y, humanize=True)
                await self.down()
                await asyncio.sleep(0.035)  # Authentic button dwell latency
                await self.up()
            else:
                if hasattr(self.page, "mouse") and hasattr(self.page.mouse, "click"):
                    await self.page.mouse.click(raw_x, raw_y)
                self.current_x = raw_x
                self.current_y = raw_y
        else:
            # Selector string
            selector_str = str(selector_or_x)
            if humanize and hasattr(self.page, "locator"):
                try:
                    locator = self.page.locator(selector_str).first
                    box = await locator.bounding_box()
                    if box:
                        cx = box["x"] + box["width"] / 2.0
                        cy = box["y"] + box["height"] / 2.0
                        await self.click(cx, cy, humanize=True)
                        return
                except Exception as exc:
                    logger.debug(f"Unable to compute element bounding box for '{selector_str}', falling back to direct click: {exc}")

            # Fallback to direct page click
            if hasattr(self.page, "click"):
                await self.page.click(selector_str)

    async def double_click(self, selector: str) -> None:
        """Double clicks on the specified element."""
        if hasattr(self.page, "dblclick"):
            await self.page.dblclick(selector)
        else:
            await self.click(selector)
            await asyncio.sleep(0.05)
            await self.click(selector)

    async def down(self) -> None:
        """Presses mouse button down."""
        if hasattr(self.page, "mouse") and hasattr(self.page.mouse, "down"):
            await self.page.mouse.down()

    async def up(self) -> None:
        """Releases mouse button up."""
        if hasattr(self.page, "mouse") and hasattr(self.page.mouse, "up"):
            await self.page.mouse.up()

    async def press_and_hold(
        self,
        selector_or_x: Any,
        y: Optional[float] = None,
        min_hold_sec: float = 7.0,
        max_hold_sec: float = 15.0,
        resolve_predicate: Optional[Any] = None,
        frame: Optional[Any] = None,
        humanize: bool = True,
    ) -> bool:
        """Presses and holds on an element or coordinate with biomechanical tremor injection.

        Designed for time-gated verification challenges (PerimeterX, Arkose Labs, GeeTest, Cloudflare).

        Args:
            selector_or_x: CSS selector string, coordinate x (float), or Locator/ElementHandle.
            y: Coordinate y if selector_or_x is float.
            min_hold_sec: Minimum seconds to hold down.
            max_hold_sec: Maximum timeout before releasing.
            resolve_predicate: Optional async or sync callable returning bool when challenge is passed.
            frame: Optional frame if target is within an iframe.
            humanize: Whether to apply Costello saccadic trajectories and Harris-Wolpert tremor.

        Returns:
            bool: True if verified/resolved, False if timeout.
        """
        import time

        target_x: float = 0.0
        target_y: float = 0.0

        if y is not None:
            target_x = float(selector_or_x)
            target_y = float(y)
        else:
            target_obj = frame or self.page
            box = None
            if hasattr(selector_or_x, "bounding_box"):
                box = await selector_or_x.bounding_box()
            elif isinstance(selector_or_x, str) and hasattr(target_obj, "locator"):
                loc = target_obj.locator(selector_or_x).first
                box = await loc.bounding_box()
            elif isinstance(selector_or_x, str) and hasattr(target_obj, "query_selector"):
                el = await target_obj.query_selector(selector_or_x)
                box = await el.bounding_box() if el else None

            if box:
                target_x = float(box["x"] + box["width"] / 2.0)
                target_y = float(box["y"] + box["height"] / 2.0)
            else:
                target_x = self.current_x
                target_y = self.current_y

        # Move to target
        await self.move(target_x, target_y, humanize=humanize)
        await asyncio.sleep(0.05)

        # Press down
        await self.down()
        start = time.time()
        resolved = False

        try:
            while (time.time() - start) < max_hold_sec:
                elapsed = time.time() - start

                # Apply micro-tremor
                if humanize and hasattr(self.page, "mouse") and hasattr(self.page.mouse, "move"):
                    jx, jy = self.biomechanics.compute_human_noise(speed=0.15, elapsed_time=elapsed)
                    await self.page.mouse.move(target_x + jx * 0.3, target_y + jy * 0.3)

                # Check predicate if provided
                if resolve_predicate is not None:
                    try:
                        res = resolve_predicate()
                        if asyncio.iscoroutine(res):
                            res = await res
                        if res and elapsed >= min_hold_sec:
                            resolved = True
                            break
                    except Exception:
                        pass
                else:
                    try:
                        check_target = frame or self.page
                        if hasattr(check_target, "evaluate"):
                            has_draw = await check_target.evaluate(
                                "() => !!document.querySelector('#checkmark.draw, .draw, [aria-label*=\"completed\"]')"
                            )
                            if has_draw and elapsed >= min_hold_sec:
                                resolved = True
                                break
                    except Exception:
                        pass

                await asyncio.sleep(0.12)
        finally:
            await self.up()
            await asyncio.sleep(0.05)

        return resolved
