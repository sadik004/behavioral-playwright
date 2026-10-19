"""
Coherent Hardware Profile Manager (Level 4 Engine Synchronization)
Loads authentic system profiles containing fully synchronized WebGL, Audio,
Screen, and Font configurations to eliminate Fingerprint Contradictions.
"""
import os
import json
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

logger = logging.getLogger("BehavioralEvasion.CoherentProfile")


@dataclass
class CoherentDeviceProfile:
    profile_id: str
    os_platform: str
    user_agent: str
    viewport: Dict[str, int]
    device_pixel_ratio: float
    webgl: Dict[str, Any]
    audio: Dict[str, Any]
    fonts: List[str]
    locales: List[str]
    timezone_id: str

    def generate_injection_script(self) -> str:
        """Generates synchronized prototype overrides matching exact hardware specifications."""
        extensions_json = json.dumps(self.webgl.get("extensions", []))
        vendor = self.webgl.get("unmasked_vendor", "Google Inc. (NVIDIA)")
        renderer = self.webgl.get("unmasked_renderer", "ANGLE (NVIDIA GeForce RTX 4070)")
        platform = self.os_platform

        return f"""
        (() => {{
            if (window.__coherent_profile_mounted__) return;
            window.__coherent_profile_mounted__ = true;

            // 1. Platform synchronization
            try {{
                Object.defineProperty(navigator, 'platform', {{
                    get: () => '{platform}',
                    configurable: true
                }});
            }} catch(e) {{}}

            // 2. Synchronized WebGL Parameter & Extension Returns
            if (window.WebGLRenderingContext) {{
                const origGetParam = WebGLRenderingContext.prototype.getParameter;
                const origGetExt = WebGLRenderingContext.prototype.getExtension;
                const origGetSupportedExt = WebGLRenderingContext.prototype.getSupportedExtensions;

                const supportedExtensions = {extensions_json};

                const webglParamHandler = function(param) {{
                    if (param === 37445) return '{vendor}';
                    if (param === 37446) return '{renderer}';
                    if (param === 3379) return {self.webgl.get("max_texture_size", 16384)};
                    if (param === 34024) return {self.webgl.get("max_renderbuffer_size", 16384)};
                    return origGetParam.apply(this, arguments);
                }};

                WebGLRenderingContext.prototype.getParameter = webglParamHandler;
                if (window.WebGL2RenderingContext) {{
                    WebGL2RenderingContext.prototype.getParameter = webglParamHandler;
                }}

                WebGLRenderingContext.prototype.getSupportedExtensions = function() {{
                    return supportedExtensions;
                }};
                if (window.WebGL2RenderingContext) {{
                    WebGL2RenderingContext.prototype.getSupportedExtensions = function() {{
                        return supportedExtensions;
                    }};
                }}
            }}
        }})();
        """


class CoherentProfileLoader:
    """Discovers and loads coherent profile presets from disk."""
    def __init__(self, profiles_dir: Optional[str] = None):
        if profiles_dir is None:
            profiles_dir = os.path.join(os.path.dirname(__file__), "profiles")
        self.profiles_dir = profiles_dir

    def list_available_profiles(self) -> List[str]:
        if not os.path.exists(self.profiles_dir):
            return []
        return [f.replace(".json", "") for f in os.listdir(self.profiles_dir) if f.endswith(".json")]

    def load_profile(self, profile_name: str = "win11_nvidia_rtx4070") -> CoherentDeviceProfile:
        filename = f"{profile_name}.json" if not profile_name.endswith(".json") else profile_name
        path = os.path.join(self.profiles_dir, filename)
        if not os.path.exists(path):
            logger.warning(f"Profile '{profile_name}' not found at {path}. Loading default.")
            # Fallback default
            return CoherentDeviceProfile(
                profile_id="default_fallback",
                os_platform="Win32",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                device_pixel_ratio=1.0,
                webgl={"unmasked_vendor": "Google Inc. (NVIDIA)", "unmasked_renderer": "ANGLE (NVIDIA)"},
                audio={"sample_rate": 48000},
                fonts=["Segoe UI", "Arial"],
                locales=["en-US"],
                timezone_id="America/New_York"
            )

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return CoherentDeviceProfile(
            profile_id=data["profile_id"],
            os_platform=data["os_platform"],
            user_agent=data["user_agent"],
            viewport=data["viewport"],
            device_pixel_ratio=data.get("device_pixel_ratio", 1.0),
            webgl=data.get("webgl", {}),
            audio=data.get("audio", {}),
            fonts=data.get("fonts", []),
            locales=data.get("locales", ["en-US"]),
            timezone_id=data.get("timezone_id", "America/New_York")
        )
