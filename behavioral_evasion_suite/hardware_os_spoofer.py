"""
Patch 4: Hardware and OS Sync (WebGL & Platform Masking)
Aligns canvas hashes, system fonts, and WebGL parameter query returns
on the native prototype chain to eliminate SwiftShader / llvmpipe footprints.
"""
import logging
from typing import Any
from .utils import NATIVE_SPOOF_JS

logger = logging.getLogger("BehavioralEvasion.HardwareOS")


class HardwareOSSpoofer:
    """
    Aligns canvas hashes, system fonts, and WebGL parameter query returns
    on the native prototype chain to eliminate SwiftShader / llvmpipe footprints.
    """
    def __init__(self, page: Any) -> None:
        self.page = page

    async def inject_hardware_stealth(self) -> None:
        """Injects a secure proxy layer over WebGL parameter query calls."""
        logger.info("HardwareOSSpoofer: Spoofing WebGL active hardware profiles on prototype chain.")
        spoof_js = f"""
        (() => {{
            {NATIVE_SPOOF_JS}

            // Sync navigator properties securely
            Object.defineProperty(navigator, 'platform', {{
                get: window.makeNative(() => 'Win32', 'get platform'),
                configurable: true
            }});

            // Intercept WebGL context queries safely
            if (window.WebGLRenderingContext) {{
                const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
                const customGetParameter = function(parameter) {{
                    if (parameter === 37445) {{ // UNMASKED_VENDOR_WEBGL
                        return "Google Inc. (NVIDIA)";
                    }}
                    if (parameter === 37446) {{ // UNMASKED_RENDERER_WEBGL
                        return "ANGLE (NVIDIA GeForce RTX 4070 Laptop GPU Direct3D11 vs_5_0 ps_5_0)";
                    }}
                    return originalGetParameter.apply(this, arguments);
                }};
                window.makeNative(customGetParameter, 'getParameter');
                WebGLRenderingContext.prototype.getParameter = customGetParameter;

                if (window.WebGL2RenderingContext) {{
                    WebGL2RenderingContext.prototype.getParameter = customGetParameter;
                }}
            }}
        }})();
        """
        if hasattr(self.page, "evaluate"):
            await self.page.evaluate(spoof_js)
