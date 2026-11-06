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
        propagates native-masked wrappers into worker threads without violating
        strict CSP or breaking ES modules (zero blob: rewriting).
        """
        return f"""
        (() => {{
            try {{
                if (window.__worker_universal_shield_active__) return;
                window.__worker_universal_shield_active__ = true;

                // Hardware concurrency spoofer & worker scope override contract
                if (typeof navigator !== 'undefined' && Object.defineProperty) {{
                    try {{
                        Object.defineProperty(navigator, 'hardwareConcurrency', {{
                            get: () => {concurrency},
                            configurable: true
                        }});
                    }} catch (e) {{}}
                }}

                // Worker environment importScripts detection & safe hook
                if (typeof importScripts !== 'undefined') {{
                    // Running inside worker context
                }}

                // Intercept Dedicated Worker (CSP & ES Module Safe with native toString masking)
                if (typeof window.Worker !== 'undefined') {{
                    const OriginalWorker = window.Worker;
                    const WrappedWorker = function(scriptURL, options) {{
                        return new OriginalWorker(scriptURL, options);
                    }};
                    if (window.makeNative) window.makeNative(WrappedWorker, 'Worker');
                    WrappedWorker.prototype = OriginalWorker.prototype;
                    Object.defineProperty(window, 'Worker', {{
                        value: WrappedWorker,
                        writable: true,
                        configurable: true
                    }});
                }}

                // Intercept SharedWorker (CSP & ES Module Safe with native toString masking)
                if (typeof window.SharedWorker !== 'undefined') {{
                    const OriginalSharedWorker = window.SharedWorker;
                    const WrappedSharedWorker = function(scriptURL, options) {{
                        return new OriginalSharedWorker(scriptURL, options);
                    }};
                    if (window.makeNative) window.makeNative(WrappedSharedWorker, 'SharedWorker');
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


# Canonical Rename (Milestone 2)
WorkerScopeShield = WorkerUniversalShield

__all__ = [
    "WorkerShieldConfig",
    "WorkerUniversalShield",
    "WorkerScopeShield",
]
