"""
Canvas & WebGL Deterministic Idempotent Shader Spoofer (Mulberry32 / Murmur3 PRNG)
Injects deterministic, session-seeded sub-pixel micro-jitter into HTML5 Canvas and WebGL shaders
while guaranteeing CreepJS/DataDome double-run idempotency (hash1 === hash2) and
unmasked vendor compatibility with native toString protection.
"""
from __future__ import annotations

from typing import Optional


class CanvasWebGLShaderSpoofer:
    """Injects sub-pixel deterministic noise into HTML5 Canvas and WebGL shaders via Mulberry32 PRNG."""

    @staticmethod
    def get_canvas_shader_spoofer_script(session_seed: int = 1337) -> str:
        return f"""
        (() => {{
            if (window.__powerhand_canvas_spoofer__) return;
            window.__powerhand_canvas_spoofer__ = true;

            const SESSION_SEED = {session_seed};

            // Deterministic Mulberry32 / Murmur3 coordinate & channel hash generator (pure & idempotent)
            function mulberry32(x, y, channel, sessionSeed) {{
                let h = (Math.imul(x, 374761393) + Math.imul(y, 668265263) + Math.imul(channel, 31) + (sessionSeed || SESSION_SEED)) ^ 0x6D2B79F5;
                h = Math.imul(h ^ (h >>> 15), h | 1);
                h ^= h + Math.imul(h ^ (h >>> 7), h | 61);
                return ((h ^ (h >>> 14)) >>> 0) / 4294967296;
            }}
            const getDeterministicPixelNoise = mulberry32;

            function applyDeterministicNoise(imgData, w, startX, startY) {{
                for (let i = 0; i < imgData.data.length; i += 4) {{
                    const pxIdx = Math.floor(i / 4);
                    const relX = pxIdx % w;
                    const relY = Math.floor(pxIdx / w);
                    const absX = startX + relX;
                    const absY = startY + relY;

                    // Deterministic single-bit micro-jitter with p < 0.002 (< 0.05% total channel delta)
                    if (getDeterministicPixelNoise(absX, absY, 0, SESSION_SEED) < 0.002) {{
                        imgData.data[i] ^= 1;
                    }}
                    if (getDeterministicPixelNoise(absX, absY, 1, SESSION_SEED) < 0.002) {{
                        imgData.data[i + 1] ^= 1;
                    }}
                    if (getDeterministicPixelNoise(absX, absY, 2, SESSION_SEED) < 0.002) {{
                        imgData.data[i + 2] ^= 1;
                    }}
                }}
                return imgData;
            }}

            const origGetImageData = (typeof CanvasRenderingContext2D !== 'undefined' && CanvasRenderingContext2D.prototype.getImageData)
                ? CanvasRenderingContext2D.prototype.getImageData
                : null;

            // Intercept CanvasRenderingContext2D.prototype.getImageData
            if (origGetImageData) {{
                const canvasHandler = function(sx, sy, sw, sh) {{
                    const imgData = origGetImageData.apply(this, arguments);
                    const w = imgData.width || sw;
                    const startX = typeof sx === 'number' ? sx : 0;
                    const startY = typeof sy === 'number' ? sy : 0;
                    return applyDeterministicNoise(imgData, w, startX, startY);
                }};
                if (window.makeNative) window.makeNative(canvasHandler, 'getImageData');
                CanvasRenderingContext2D.prototype.getImageData = canvasHandler;
            }}

            // Intercept HTMLCanvasElement.prototype.toDataURL for deterministic canvas export
            if (typeof HTMLCanvasElement !== 'undefined' && HTMLCanvasElement.prototype.toDataURL) {{
                const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
                const toDataURLHandler = function(type, encoderOptions) {{
                    try {{
                        const w = this.width;
                        const h = this.height;
                        if (w > 0 && h > 0 && origGetImageData) {{
                            const offscreen = document.createElement('canvas');
                            offscreen.width = w;
                            offscreen.height = h;
                            const offCtx = offscreen.getContext('2d');
                            if (offCtx) {{
                                offCtx.drawImage(this, 0, 0);
                                // Call origGetImageData directly so noise is applied EXACTLY ONCE (preventing double-XOR cancellation)
                                const imgData = origGetImageData.call(offCtx, 0, 0, w, h);
                                applyDeterministicNoise(imgData, w, 0, 0);
                                offCtx.putImageData(imgData, 0, 0);
                                return origToDataURL.call(offscreen, type, encoderOptions);
                            }}
                        }}
                    }} catch (e) {{}}
                    return origToDataURL.apply(this, arguments);
                }};
                if (window.makeNative) window.makeNative(toDataURLHandler, 'toDataURL');
                HTMLCanvasElement.prototype.toDataURL = toDataURLHandler;
            }}

            // WebGL unmasked vendor & renderer spoofer
            const UNMASKED_VENDOR_WEBGL = 37445;
            const UNMASKED_RENDERER_WEBGL = 37446;

            if (typeof WebGLRenderingContext !== 'undefined' && WebGLRenderingContext.prototype.getParameter) {{
                const origGetParameter = WebGLRenderingContext.prototype.getParameter;
                const webglHandler = function(param) {{
                    if (param === UNMASKED_VENDOR_WEBGL || param === 37445) return 'Intel Inc.';
                    if (param === UNMASKED_RENDERER_WEBGL || param === 37446) return 'Intel(R) Iris(TM) Xe Graphics Direct3D11 vs_5_0 ps_5_0';
                    return origGetParameter.apply(this, arguments);
                }};
                if (window.makeNative) window.makeNative(webglHandler, 'getParameter');

                WebGLRenderingContext.prototype.getParameter = webglHandler;
                if (typeof window.WebGL2RenderingContext !== 'undefined' && WebGL2RenderingContext.prototype.getParameter) {{
                    WebGL2RenderingContext.prototype.getParameter = webglHandler;
                }}
            }}
        }})();
        """
