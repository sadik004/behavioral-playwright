"""
Standalone end-to-end framework execution demonstration (V10.0.0).
"""

import asyncio
import logging
import sys

from behavioral_playwright import (
    AIConfig,
    AutomationConfig,
    BehavioralHumanizer,
    BrowserLifecycleManager,
    BrowserProviderFactory,
    CircuitBreaker,
    NavigationManager,
)
from tests.test_suite import SelfTestSuite

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("BehavioralAutomation.Demo")


async def main() -> None:
    logger.info("---------------------------------------------------------------------")
    logger.info("🎭 Initializing Behavioral Automation System V10.0.0 (Quantum Edition)...")
    logger.info("---------------------------------------------------------------------")

    # 1. Execute full self-contained Verification Layer
    tests_ok = await SelfTestSuite.run_all_tests()
    if not tests_ok:
        logger.critical("E2E Lifecycle aborted due to self-test failure.")
        sys.exit(1)

    # 2. Complete DI configuration instantiations
    config = AutomationConfig(ai=AIConfig(enabled=True, self_healing_enabled=True, ocr_cv_enabled=True))

    # 3. Request provider context using Factory (CDP -> Cloak -> Playwright -> Mock)
    context, provider = await BrowserProviderFactory.launch_stabilized_lifecycle(config)

    async with BrowserLifecycleManager(provider, context=context) as manager:
        active_page = (
            manager.context.pages[0]
            if (manager.context and manager.context.pages)
            else await manager.context.new_page()
        )

        # 4. Bind behavioral input layers and circuit breaker
        cb = CircuitBreaker()
        navigator = NavigationManager(config, cb)
        humanizer = BehavioralHumanizer(active_page, config)

        # 5. Navigate safely with exponential backoff & trigger page simulations
        target_url = "https://bot-detector.rebrowser.net"
        success = await navigator.safe_goto(active_page, target_url)
        if success:
            logger.info("Simulating realistic humanized and self-healing page actions...")
            await humanizer.move_mouse_to(200.0, 300.0, steps=20)
            await humanizer.execute_safe_click("#login-button")
            await humanizer.execute_safe_type("#text-input", "Quantum Modular Framework V10")

            logger.info("Flow executed flawlessly.")


if __name__ == "__main__":
    asyncio.run(main())
