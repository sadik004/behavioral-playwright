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

    @classmethod
    def get_stealth_js(cls) -> str:
        return f"""
        (() => {{
            {NATIVE_SPOOF_JS}

            // Layer 1: Webdriver concealment
            try {{
                const webdriverGetter = () => undefined;
                if (window.makeNative) window.makeNative(webdriverGetter, 'get webdriver');
                Object.defineProperty(Navigator.prototype, 'webdriver', {{
                    get: webdriverGetter,
                    set: undefined,
                    enumerable: true,
                    configurable: true
                }});
            }} catch (e) {{}}

            // Layer 2: Chrome runtime & csi / loadTimes emulation
            try {{
                if (!window.chrome) {{
                    window.chrome = {{}};
                }}
                if (!window.chrome.runtime) {{
                    window.chrome.runtime = {{
                        PlatformOs: {{ MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd' }},
                        PlatformArch: {{ ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' }},
                        PlatformNaclArch: {{ ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' }},
                        connect: function() {{}},
                        sendMessage: function() {{}}
                    }};
                }}
                if (!window.chrome.csi) {{
                    window.chrome.csi = function() {{
                        return {{ startE: Date.now(), onloadT: Date.now() + 100, pageT: 100, tran: 15 }};
                    }};
                    if (window.makeNative) window.makeNative(window.chrome.csi, 'csi');
                }}
                if (!window.chrome.loadTimes) {{
                    window.chrome.loadTimes = function() {{
                        return {{
                            requestTime: Date.now() / 1000,
                            startLoadTime: Date.now() / 1000,
                            commitLoadTime: Date.now() / 1000,
                            finishDocumentLoadTime: Date.now() / 1000,
                            finishLoadTime: Date.now() / 1000,
                            firstPaintTime: Date.now() / 1000,
                            firstPaintAfterLoadTime: 0,
                            navigationType: 'Other',
                            wasFetchedViaSpdy: false,
                            wasNpnNegotiated: false,
                            npnNegotiatedProtocol: '',
                            wasAlternateProtocolAvailable: false,
                            connectionInfo: 'http/1.1'
                        }};
                    }};
                    if (window.makeNative) window.makeNative(window.chrome.loadTimes, 'loadTimes');
                }}
            }} catch (e) {{}}

            // Layer 3: Permissions query neutralization
            try {{
                if (navigator.permissions && navigator.permissions.query) {{
                    const originalQuery = navigator.permissions.query;
                    const queryProxy = function(parameters) {{
                        if (parameters && parameters.name === 'notifications') {{
                            return Promise.resolve({{
                                state: Notification.permission === 'denied' ? 'denied' : 'prompt',
                                onchange: null
                            }});
                        }}
                        return originalQuery.apply(this, arguments);
                    }};
                    if (window.makeNative) window.makeNative(queryProxy, 'query');
                    navigator.permissions.query = queryProxy;
                }}
            }} catch (e) {{}}

            // Layer 6: Plugins array reconstruction
            try {{
                if (navigator.plugins && navigator.plugins.length === 0) {{
                    const fakePlugins = [
                        {{ name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }},
                        {{ name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }},
                        {{ name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }},
                        {{ name: 'Microsoft Edge PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }},
                        {{ name: 'WebKit built-in PDF', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }}
                    ];
                    if (window.PluginArray) {{
                        Object.setPrototypeOf(fakePlugins, PluginArray.prototype);
                    }}
                    Object.defineProperty(Navigator.prototype, 'plugins', {{
                        get: () => fakePlugins,
                        configurable: true
                    }});
                }}
            }} catch (e) {{}}

            // Layer 9: Console profiling shield
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

            if (window.makeNative) window.makeNative(logProxy, 'log');
            console.log = logProxy;

            // Layer 10: V8 Error Stack Trace & CDP Serialization Leak Protection
            try {{
                const filterCDPStack = (stack) => {{
                    if (typeof stack !== 'string') return stack;
                    return stack.split('\n')
                        .filter(line => !line.includes('__playwright_evaluation_script__') &&
                                        !line.includes('__puppeteer_evaluation_script__') &&
                                        !line.includes('eval at <anonymous>') &&
                                        !line.includes('Runtime.enable'))
                        .join('\n');
                }};

                const stackDesc = Object.getOwnPropertyDescriptor(Error.prototype, 'stack');
                if (stackDesc && stackDesc.get) {{
                    const origStackGetter = stackDesc.get;
                    Object.defineProperty(Error.prototype, 'stack', {{
                        get: function() {{
                            const raw = origStackGetter.call(this);
                            return filterCDPStack(raw);
                        }},
                        configurable: true,
                        enumerable: false
                    }});
                }}
            }} catch (e) {{}}
        }})();
        """

    @classmethod
    async def apply(cls, target: Any) -> None:
        """
        Class method to apply stealth script to a Playwright BrowserContext or Page.
        """
        stealth_js = cls.get_stealth_js()
        if hasattr(target, "add_init_script"):
            await target.add_init_script(stealth_js)
        elif hasattr(target, "evaluate"):
            await target.evaluate(stealth_js)

    async def apply_cdp_stealth_binding(self) -> None:
        """Injects non-serializable WeakMap-based toString protection into the page."""
        logger.info("CDPEvasionShield: Mounting V8 native representation toString wrappers.")
        await self.apply(self.page)

