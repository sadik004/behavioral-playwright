"""
Subpixel Font Shield - Level 5 Quantum Edition
DirectWrite ClearType Font Metric Converter.
Counters Kasada, Cloudflare, and CreepJS subpixel font rendering and layout discrepancy heuristics.
"""

from typing import Dict, Any, Optional
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("BehavioralEvasion.SubpixelFontShield")


class FontMetricConfig(BaseModel):
    """Configuration schema for Subpixel Font Shield."""
    simulate_directwrite: bool = Field(default=True, description="Enforce DirectWrite subpixel anti-aliasing simulation")
    smoothing_factor: float = Field(default=0.03125, description="1/32th pixel subpixel grid delta")
    target_os: str = Field(default="windows", description="Target platform font rasterizer profile")


class SubpixelFontShield:
    """
    Simulates Windows DirectWrite ClearType fractional glyph metric precision across
    CanvasRenderingContext2D.measureText and DOM Range/Element bounding boxes.
    """

    def __init__(self, config: Optional[FontMetricConfig] = None):
        self.config = config or FontMetricConfig()

    @staticmethod
    def get_subpixel_font_script(smoothing_factor: float = 0.03125) -> str:
        """
        Defensive JavaScript payload that intercepts measureText and getBoundingClientRect
        to enforce consistent DirectWrite ClearType fractional metric outputs.
        """
        return f"""
        (() => {{
            try {{
                if (window.__subpixel_font_shield_active__) return;
                window.__subpixel_font_shield_active__ = true;

                const delta = {smoothing_factor};

                // Intercept 2D Canvas measureText
                if (typeof CanvasRenderingContext2D !== 'undefined') {{
                    const origMeasureText = CanvasRenderingContext2D.prototype.measureText;
                    CanvasRenderingContext2D.prototype.measureText = function(text) {{
                        const metrics = origMeasureText.call(this, text);
                        try {{
                            // Deterministic subpixel micro-fractional offset
                            const len = (text || '').length;
                            const hash = ((len * 2654435761) % 1000) / 1000.0;
                            const subpixelOffset = (hash * delta) - (delta / 2.0);

                            const origWidth = metrics.width;
                            const newWidth = Math.round((origWidth + subpixelOffset) * 100) / 100;

                            return new Proxy(metrics, {{
                                get(target, prop, receiver) {{
                                    if (prop === 'width') return newWidth;
                                    const val = Reflect.get(target, prop, receiver);
                                    return typeof val === 'function' ? val.bind(target) : val;
                                }}
                            }});
                        }} catch (e) {{
                            return metrics;
                        }}
                    }};
                }}

                // Intercept Element getBoundingClientRect for font test spans
                const origGetBoundingClientRect = Element.prototype.getBoundingClientRect;
                Element.prototype.getBoundingClientRect = function() {{
                    const rect = origGetBoundingClientRect.call(this);
                    try {{
                        if (this.tagName === 'SPAN' && (this.style.fontFamily || this.style.fontSize)) {{
                            const len = (this.textContent || '').length;
                            if (len > 0) {{
                                const hash = ((len * 1597334677) % 1000) / 1000.0;
                                const subpixelOffset = (hash * delta) - (delta / 2.0);
                                const newWidth = Math.round((rect.width + subpixelOffset) * 100) / 100;
                                return new DOMRect(rect.x, rect.y, newWidth, rect.height);
                            }}
                        }}
                    }} catch (e) {{}}
                    return rect;
                }};
            }} catch (e) {{}}
        }})();
        """

    def get_script(self) -> str:
        return self.get_subpixel_font_script(smoothing_factor=self.config.smoothing_factor)
