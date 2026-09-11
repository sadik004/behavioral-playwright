"""Dynamic hardware signature generator."""

from __future__ import annotations

import random
from typing import Optional

from behavioral_playwright.fingerprint.models import FingerprintProfile, OSPlatform
from behavioral_playwright.fingerprint.profiles import CURATED_PROFILES


class FingerprintGenerator:
    """Generates authentic, platform-coherent browser fingerprint profiles."""

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    def generate(
        self,
        platform: Optional[OSPlatform] = None,
        locale: str = "en-US",
        timezone: Optional[str] = None,
    ) -> FingerprintProfile:
        candidates = CURATED_PROFILES
        if platform:
            candidates = [p for p in candidates if p.platform == platform]
            if not candidates:
                candidates = CURATED_PROFILES

        base = self._rng.choice(candidates)
        
        # Clone with optional customization while maintaining hardware coherence
        return FingerprintProfile(
            user_agent=base.user_agent,
            platform=base.platform,
            platform_string=base.platform_string,
            screen=base.screen,
            webgl=base.webgl,
            languages=[locale, "en"] if locale != "en" else ["en-US", "en"],
            hardware_concurrency=base.hardware_concurrency,
            device_memory_gb=base.device_memory_gb,
            canvas_noise_seed=self._rng.randint(1000, 999999),
            audio_noise_seed=round(self._rng.uniform(0.00005, 0.00025), 6),
            timezone=timezone or base.timezone,
        )

    def generate_evasion_script(self, profile: FingerprintProfile) -> str:
        """Produces client-side JS patch tailored to the generated profile."""
        return f"""
        (() => {{
            // 1. WebGL Override
            const getParameterOrig = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                if (parameter === 37445) return '{profile.webgl.vendor}';
                if (parameter === 37446) return '{profile.webgl.renderer}';
                return getParameterOrig.apply(this, arguments);
            }};
            if (window.WebGL2RenderingContext) {{
                const getParameter2Orig = WebGL2RenderingContext.prototype.getParameter;
                WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37445) return '{profile.webgl.vendor}';
                    if (parameter === 37446) return '{profile.webgl.renderer}';
                    return getParameter2Orig.apply(this, arguments);
                }};
            }}
            // 2. Hardware Concurrency & Memory
            Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {profile.hardware_concurrency} }});
            Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {profile.device_memory_gb} }});
            Object.defineProperty(navigator, 'platform', {{ get: () => '{profile.platform_string}' }});
            // 3. Screen Dimensions
            Object.defineProperty(window.screen, 'width', {{ get: () => {profile.screen.width} }});
            Object.defineProperty(window.screen, 'height', {{ get: () => {profile.screen.height} }});
            Object.defineProperty(window.screen, 'availWidth', {{ get: () => {profile.screen.avail_width} }});
            Object.defineProperty(window.screen, 'availHeight', {{ get: () => {profile.screen.avail_height} }});
        }})();
        """
