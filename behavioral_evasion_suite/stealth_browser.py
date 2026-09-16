"""
Fluent High-Level Developer API (Code UX) for Behavioral Evasion Suite (v6.0.0 Level 5 Quantum Edition)
Provides a clean, drop-in async context manager and page wrapper for Playwright with zero boilerplate.
"""
import sys
import asyncio
from typing import Optional, Union, Tuple, Dict, Any
from playwright.async_api import Page, async_playwright, Playwright, Browser, BrowserContext

from .presets import Preset, StealthConfig
from .unified_quantum_facade import UnifiedQuantumFacade, TokenOptimizedDOMReader
from .cognitive_gaze_physics import human_scroll, cognitive_reading_pause
from .utils import setup_sanitized_logger

logger = setup_sanitized_logger("BehavioralPlaywright.FluentAPI")


class StealthPage:
    """
    Ergonomic wrapper around Playwright's Page.
    Transparently delegates all standard Playwright methods while adding rich human kinematics & DOM extraction.
    """
    def __init__(self, raw_page: Page, facade: UnifiedQuantumFacade, config: StealthConfig):
        self._raw_page = raw_page
        self._facade = facade
        self._config = config

    @property
    def raw_page(self) -> Page:
        """Direct access to the underlying Playwright Page instance."""
        return self._raw_page

    async def human_click(self, selector_or_coords: Union[str, Tuple[int, int]], click_count: int = 1, button: str = "left"):
        """
        Executes a biomechanically simulated neuromuscular click on a selector or (x, y) coordinates.
        Uses Bezier velocity curves, sub-millisecond micro-jitters, and native OS kernel input if configured.
        """
        if isinstance(selector_or_coords, (tuple, list)):
            coords = (float(selector_or_coords[0]), float(selector_or_coords[1]))
            return await self._facade.kinematics.human_click_coords(self._raw_page, coords, click_count=click_count, button=button)
        else:
            return await self._facade.kinematics.human_click(self._raw_page, selector_or_coords, click_count=click_count, button=button)

    async def human_type(self, selector: str, text: str, min_delay_ms: float = 35.0, max_delay_ms: float = 120.0):
        """
        Executes cognitive typing with burst rhythm, digram latency modeling, and typo autocorrection.
        """
        return await self._facade.kinematics.human_type(self._raw_page, selector, text, min_delay_ms=min_delay_ms, max_delay_ms=max_delay_ms)

    async def human_scroll(self, delta_y: int = 600, duration_s: float = 1.2):
        """
        Executes a Newtonian inertial scroll trajectory with deceleration curves and micro-adjustments.
        """
        return await human_scroll(self._raw_page, delta_y=delta_y, duration_s=duration_s)

    async def cognitive_pause(self, min_seconds: float = 0.8, max_seconds: float = 2.5):
        """
        Executes a log-normal statistical reading pause simulating human cognitive comprehension.
        """
        return await cognitive_reading_pause(min_seconds, max_seconds)

    async def extract_compact_dom(self) -> Dict[str, Any]:
        """
        Extracts token-optimized semantic interactive DOM tree suitable for LLMs.
        """
        return await TokenOptimizedDOMReader.extract_compact_tree(self._raw_page)

    def __getattr__(self, name: str) -> Any:
        """Transparently forwards any attribute or method lookup to the underlying Playwright Page."""
        return getattr(self._raw_page, name)


class StealthBrowser:
    """
    Fluent 1-liner Entrypoint & Context Manager.
    Allows effortless, zero-friction usage with full Level 5 Quantum evasion under the hood.
    
    Usage:
        async with StealthBrowser.launch(headless=True, preset="max_quantum") as page:
            await page.goto("https://example.com")
            await page.human_click("button#submit")
    """
    def __init__(self, config: Optional[StealthConfig] = None, preset: Preset | str = Preset.MAX_QUANTUM, **kwargs):
        if config is not None:
            self.config = config
        else:
            self.config = StealthConfig.from_preset(preset, **kwargs)

        self.facade = UnifiedQuantumFacade()
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[StealthPage] = None

    @classmethod
    def launch(cls, preset: Preset | str = Preset.MAX_QUANTUM, **kwargs) -> "StealthBrowser":
        """Factory constructor for use as an async context manager."""
        return cls(preset=preset, **kwargs)

    async def start(self) -> StealthPage:
        """Starts the browser instance and returns a hardened StealthPage."""
        self._pw = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-first-run",
            "--no-service-autorun",
            "--password-store=basic"
        ]

        proxy_dict = None
        if self.config.proxy:
            proxy_dict = {"server": self.config.proxy}

        self._browser = await self._pw.chromium.launch(
            headless=self.config.headless,
            args=launch_args,
            proxy=proxy_dict
        )

        context_options = {
            "viewport": self.config.viewport,
            "locale": self.config.locale,
            "timezone_id": self.config.timezone_id
        }

        self._context = await self._browser.new_context(**context_options)
        raw_page = await self._context.new_page()

        # Apply hardened shields via UnifiedQuantumFacade
        await self.facade.browser.harden_page(raw_page)

        self._page = StealthPage(raw_page, self.facade, self.config)
        logger.info(f"StealthBrowser initialized successfully with preset '{self.config.preset}'")
        return self._page

    async def close(self):
        """Gracefully closes page, context, browser, and playwright handles."""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        except Exception as e:
            logger.debug(f"Error during StealthBrowser shutdown: {e}")

    async def __aenter__(self) -> StealthPage:
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
