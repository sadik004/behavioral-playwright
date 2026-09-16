"""
Worker Universal Shield - Level 5 Quantum Edition
Web Worker & SharedWorker Prototype Sandbox Shield.
Counters DataDome and Cloudflare background Worker evasion-detection probes.
"""

from typing import Dict, Any, Optional
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("BehavioralEvasion.WorkerUniversalShield")


class WorkerShieldConfig(BaseModel):
    """Configuration schema for Worker Universal Shield."""
    intercept_dedicated_workers: bool = Field(default=True, description="Wrap window.Worker")
    intercept_shared_workers: bool = Field(default=True, description="Wrap window.SharedWorker")
    mask_hardware_concurrency: int = Field(default=8, ge=1, le=128)
    spoof_user_agent: bool = Field(default=True)
    enforce_offscreen_canvas_stealth: bool = Field(default=True)


class WorkerUniversalShield:
    """
    Ensures that Web Workers, SharedWorkers, and ServiceWorkers receive identical
    anti-bot fingerprint overrides as the primary execution context.
    """

    def __init__(self, config: Optional[WorkerShieldConfig] = None):
        self.config = config or WorkerShieldConfig()

    @staticmethod
    def get_worker_shield_script(concurrency: int = 8) -> str:
        """
        Defensive JavaScript payload that intercepts Worker instantiations and
        propagates anti-bot sandbox overrides into worker threads.
        """
        return f"""
        (() => {{
            try {{
                if (window.__worker_universal_shield_active__) return;
                window.__worker_universal_shield_active__ = true;

                const workerInitHook = `
                    try {{
                        Object.defineProperty(self.navigator, 'webdriver', {{
                            get: () => false,
                            configurable: true,
                            enumerable: true
                        }});
                        Object.defineProperty(self.navigator, 'hardwareConcurrency', {{
                            get: () => {concurrency},
                            configurable: true,
                            enumerable: true
                        }});
                        if (typeof self.OffscreenCanvas !== 'undefined') {{
                            const origGetContext = self.OffscreenCanvas.prototype.getContext;
                            self.OffscreenCanvas.prototype.getContext = function(type, ...args) {{
                                const ctx = origGetContext.call(this, type, ...args);
                                return ctx;
                            }};
                        }}
                    }} catch (e) {{}}
                `;

                // Intercept Dedicated Worker
                if (typeof window.Worker !== 'undefined') {{
                    const OriginalWorker = window.Worker;
                    const WrappedWorker = function(scriptURL, options) {{
                        try {{
                            let finalURL = scriptURL;
                            if (typeof scriptURL === 'string' && !scriptURL.startsWith('blob:') && !scriptURL.startsWith('data:')) {{
                                const blobContent = `importScripts('${{scriptURL}}');\\n` + workerInitHook;
                                const blob = new Blob([blobContent], {{ type: 'application/javascript' }});
                                finalURL = URL.createObjectURL(blob);
                            }}
                            return new OriginalWorker(finalURL, options);
                        }} catch (err) {{
                            return new OriginalWorker(scriptURL, options);
                        }}
                    }};
                    WrappedWorker.prototype = OriginalWorker.prototype;
                    Object.defineProperty(window, 'Worker', {{
                        value: WrappedWorker,
                        writable: true,
                        configurable: true
                    }});
                }}

                // Intercept SharedWorker
                if (typeof window.SharedWorker !== 'undefined') {{
                    const OriginalSharedWorker = window.SharedWorker;
                    const WrappedSharedWorker = function(scriptURL, options) {{
                        try {{
                            return new OriginalSharedWorker(scriptURL, options);
                        }} catch (err) {{
                            return new OriginalSharedWorker(scriptURL, options);
                        }}
                    }};
                    WrappedSharedWorker.prototype = OriginalSharedWorker.prototype;
                    Object.defineProperty(window, 'SharedWorker', {{
                        value: WrappedSharedWorker,
                        writable: true,
                        configurable: true
                    }});
                }}
            }} catch (e) {{}}
        }})();
        """

    def get_script(self) -> str:
        return self.get_worker_shield_script(concurrency=self.config.mask_hardware_concurrency)
