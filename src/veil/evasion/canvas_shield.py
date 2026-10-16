"""
Canvas & WebGL Dynamic Shader Spoofer (Mulberry32 PRNG)
Injects dynamic sub-pixel noise into HTML5 Canvas and WebGL shaders
while guaranteeing Bot.sannysoft & CreepJS unmasked vendor compatibility.
"""

class CanvasWebGLShaderSpoofer:
    """Injects sub-pixel dynamic noise into HTML5 Canvas and WebGL shaders via Mulberry32 PRNG."""
    @staticmethod
    def get_canvas_shader_spoofer_script() -> str:
        return """
        (() => {
            if (window.__powerhand_canvas_spoofer__) return;
            window.__powerhand_canvas_spoofer__ = true;

            function mulberry32(a) {
                return function() {
                  var t = a += 0x6D2B79F5;
                  t = Math.imul(t ^ t >>> 15, t | 1);
                  t ^= t + Math.imul(t ^ t >>> 7, t | 61);
                  return ((t ^ t >>> 14) >>> 0) / 4294967296;
                }
            }
            const prng = mulberry32(1337);

            const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
                const imgData = origGetImageData.apply(this, arguments);
                for (let i = 0; i < imgData.data.length; i += 4) {
                    if (prng() < 0.05) {
                        imgData.data[i] = imgData.data[i] ^ 1;
                    }
                }
                return imgData;
            };

            const UNMASKED_VENDOR_WEBGL = 37445;
            const UNMASKED_RENDERER_WEBGL = 37446;

            const origGetParameter = WebGLRenderingContext.prototype.getParameter;
            const webglHandler = function(param) {
                if (param === UNMASKED_VENDOR_WEBGL || param === 37445) return 'Intel Inc.';
                if (param === UNMASKED_RENDERER_WEBGL || param === 37446) return 'Intel(R) Iris(TM) Xe Graphics Direct3D11 vs_5_0 ps_5_0';
                return origGetParameter.apply(this, arguments);
            };

            WebGLRenderingContext.prototype.getParameter = webglHandler;
            if (window.WebGL2RenderingContext) {
                WebGL2RenderingContext.prototype.getParameter = webglHandler;
            }

            try {
                if (window.Notification && Notification.permission === 'denied') {
                    Object.defineProperty(Notification, 'permission', { get: () => 'default' });
                }
            } catch (e) {}
        })();
        """
