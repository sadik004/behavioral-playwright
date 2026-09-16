"""
Adaptive Dual-Engine Routing (Fast Path Protocol vs Heavy Path Browser)
Performs optimized lightweight HTTP requests first, cascading dynamically
to browser contexts upon WAF blocking detection.
"""
import logging
from typing import Dict, Any
from .tls_ja4_spoofer import TLSJA4Spoofer
from .context_rotator import ContextRotator

logger = logging.getLogger("BehavioralEvasion.SmartRouter")


class SmartAcquisitionRouter:
    """
    Performs optimized lightweight HTTP requests first, cascading dynamically
    to browser contexts upon WAF blocking detection.
    """
    def __init__(self, browser_context_rotator: ContextRotator) -> None:
        self.rotator = browser_context_rotator
        self.spoofer = TLSJA4Spoofer()

    async def acquire_target(self, url: str, force_browser: bool = False) -> Dict[str, Any]:
        logger.info(f"SmartRoute: Assessing routing path for {url}.")

        if not force_browser:
            try:
                # Fast Path: JA4 TCP/TLS spoofed HTTP Session
                session = self.spoofer.get_session()
                response = await session.get(url)

                if response.status_code == 200 and "blocked" not in response.text.lower():
                    logger.info("SmartRoute: Fast Path succeeded ($0 CPU billing cost).")
                    return {"engine": "fast_path_protocol", "html": response.text, "status_code": 200}
            except Exception as e:
                logger.warning(f"SmartRoute: Fast Path exception ({e}). Escalating to Heavy Path.")

        # Heavy Path Fallback: Evasive Browser Engine
        logger.warning("SmartRoute: Escalating transaction to Heavy Path Browser Context.")
        context = await self.rotator.get_healthy_context()
        page = await context.new_page()
        await page.goto(url)
        content = await page.content()
        await page.close()
        return {"engine": "heavy_path_browser", "html": content, "status_code": 200}
