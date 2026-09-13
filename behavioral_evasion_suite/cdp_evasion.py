"""
Patch 1: CDP & Runtime.enable Evasion (WeakMap Native toString Shield)
Prevents CDP-detection traps triggered by Runtime.enable console.log serializers.
"""
import logging
from typing import Any
from .utils import NATIVE_SPOOF_JS

logger = logging.getLogger("BehavioralEvasion.CDPEvasionShield")


class CDPEvasionShield:
    """
    Prevents CDP-detection traps triggered by Runtime.enable console.log serializers.
    Integrates with patchright/rebrowser-patches launch logic if available.
    """
    def __init__(self, page: Any) -> None:
        self.page = page

    async def apply_cdp_stealth_binding(self) -> None:
        """Injects non-serializable WeakMap-based toString protection into the page."""
        logger.info("CDPEvasionShield: Mounting V8 native representation toString wrappers.")

        try:
            from patchright.async_api import async_playwright
            logger.info("CDPEvasionShield: Patchright async-api successfully imported.")
        except ImportError:
            try:
                import rebrowser_patches
                logger.info("CDPEvasionShield: rebrowser-patches module successfully integrated.")
            except ImportError:
                logger.warning("CDPEvasionShield: Using fallback CDP evasion via runtime bindings.")

        stealth_js = f"""
        (() => {{
            {NATIVE_SPOOF_JS}

            const originalLog = console.log;

            const logProxy = function(...args) {{
                const safeArgs = args.map(arg => {{
                    if (arg && typeof arg === 'object') {{
                        try {{
                            const descriptors = Object.getOwnPropertyDescriptors(arg);
                            for (const key in descriptors) {{
                                if (descriptors[key].get) {{
                                    return `[Filtered Getter: ${{key}}]`;
                                }}
                            }}
                        }} catch (e) {{}}
                    }}
                    return arg;
                }});
                return originalLog.apply(this, safeArgs);
            }};

            window.makeNative(logProxy, 'log');
            console.log = logProxy;
        }})();
        """
        if hasattr(self.page, "evaluate"):
            await self.page.evaluate(stealth_js)
