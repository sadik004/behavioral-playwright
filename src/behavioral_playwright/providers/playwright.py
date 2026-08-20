"""
Vanilla Playwright Provider with client-side anti-detection JavaScript prototype masking.
"""

import asyncio
import logging
from typing import Any, Optional, Tuple, cast

from ..config.root import AutomationConfig
from ..exceptions import BrowserLaunchError
from ..utils.protocols import BrowserContextProtocol, BrowserProtocol

logger = logging.getLogger("BehavioralAutomation.Providers.Playwright")


class PlaywrightProvider:
    """Orchestrates Vanilla Playwright launched under anti-detect evasion flags."""

    def __init__(self, config: AutomationConfig) -> None:
        self.cfg = config
        self.playwright_manager: Optional[Any] = None
        self.context: Optional[BrowserContextProtocol] = None

    async def launch_context(self) -> Tuple[BrowserContextProtocol, Optional[BrowserProtocol]]:
        logger.info("Initializing Vanilla Playwright provider with evasion flags...")
        if self.playwright_manager or self.context:
            await self.shutdown()

        try:
            from playwright.async_api import async_playwright
        except ImportError as ie:
            raise BrowserLaunchError("Playwright framework is not installed in current workspace.") from ie

        try:
            self.playwright_manager = await async_playwright().start()

            chrome_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check",
                "--use-mock-keychain",
            ]

            if self.cfg.rendering.webrtc_media_spoof:
                chrome_args.extend(
                    [
                        "--use-fake-device-for-media-stream",
                        "--use-fake-ui-for-media-stream",
                    ]
                )
                if self.cfg.rendering.fake_video_stream_path:
                    chrome_args.append(f"--use-file-for-fake-video-capture={self.cfg.rendering.fake_video_stream_path}")
                if self.cfg.rendering.fake_audio_stream_path:
                    chrome_args.append(f"--use-file-for-fake-audio-capture={self.cfg.rendering.fake_audio_stream_path}")
            else:
                chrome_args.extend(
                    [
                        "--use-fake-device-for-media-stream",
                        "--use-fake-ui-for-media-stream",
                    ]
                )

            if self.cfg.network.burp_suite_ca_inject:
                chrome_args.append("--ignore-certificate-errors")

            if self.cfg.network.ja4_tls_emulation:
                chrome_args.append("--disable-http2-grease-settings")
            if self.cfg.rendering.disable_webgl:
                chrome_args.append("--disable-webgl")
            if self.cfg.rendering.disable_canvas_aa:
                chrome_args.append("--disable-canvas-aa")
            if self.cfg.rendering.fingerprint_font_metrics:
                chrome_args.append("--fingerprint-windows-font-metrics")
            if self.cfg.rendering.storage_quota_mb > 0:
                chrome_args.append(f"--fingerprint-storage-quota={self.cfg.rendering.storage_quota_mb}")

            self.context = cast(
                BrowserContextProtocol,
                await self.playwright_manager.chromium.launch_persistent_context(
                    user_data_dir=self.cfg.browser.user_data_dir,
                    headless=self.cfg.browser.headless,
                    viewport={"width": self.cfg.browser.width, "height": self.cfg.browser.height},
                    user_agent=self.cfg.locale.user_agent,
                    locale=self.cfg.locale.locale,
                    timezone_id=self.cfg.locale.timezone_id,
                    geolocation={"longitude": self.cfg.locale.longitude, "latitude": self.cfg.locale.latitude},
                    permissions=self.cfg.locale.permissions,
                    args=chrome_args,
                    ignore_default_args=["--enable-automation"],
                ),
            )

            # Client-side failsafe script to mask navigator, functions, and deflect CDP traps
            failsafe_script = """
            // Deflect console.log serialization getter traps (anti-CDP probes)
            const originalLog = console.log;
            console.log = function(...args) {
                for (let arg of args) {
                    if (arg && typeof arg === 'object') {
                        try {
                            JSON.stringify(arg);
                        } catch (e) {
                            return; // Shield triggered! Block getter serialization probe
                        }
                    }
                }
                originalLog.apply(console, args);
            };

            // Shield against V8 timing resolution probes
            const originalPrepare = Error.prepareStackTrace;
            Object.defineProperty(Error, 'prepareStackTrace', {
                get: () => originalPrepare,
                set: (val) => {
                    if (typeof val === 'function') {
                        return;
                    }
                },
                configurable: false
            });

            const originalToString = Function.prototype.toString;
            Function.prototype.toString = function () {
                if (this === Function.prototype.toString) return originalToString.call(this);
                if (this.name === 'webdriver') return 'function webdriver() { [native code] }';
                return originalToString.call(this);
            };

            // WebGL Fingerprint Masking
            try {
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
                        return 'Intel Open Source Technology Center';
                    }
                    if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
                        return 'Mesa DRI Intel(R) Iris(R) Xe Graphics (ADL GT2)';
                    }
                    return getParameter.call(this, parameter);
                };
                if (typeof WebGL2RenderingContext !== 'undefined') {
                    const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
                    WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                        if (parameter === 37445) {
                            return 'Intel Open Source Technology Center';
                        }
                        if (parameter === 37446) {
                            return 'Mesa DRI Intel(R) Iris(R) Xe Graphics (ADL GT2)';
                        }
                        return getParameter2.call(this, parameter);
                    };
                }
            } catch (e) {}

            // Navigator Plugins & Languages Spoofing
            try {
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            } catch (e) {}

            // High Resolution Timer Jitter
            try {
                const originalNow = performance.now;
                performance.now = function() {
                    const t = originalNow.call(performance);
                    return t + (Math.random() * 0.003);
                };
            } catch (e) {}

            // Canvas / WebGL Chromatic Noise Spoofing
            try {
                const addMicroNoise = (data) => {
                    for (let i = 0; i < data.length; i += 4) {
                        data[i] = Math.min(255, Math.max(0, data[i] + (i % 3 === 0 ? 1 : -1)));
                        data[i+1] = Math.min(255, Math.max(0, data[i+1] + (i % 3 === 1 ? 1 : -1)));
                    }
                };

                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(...args) {
                    const ctx = this.getContext('2d');
                    if (ctx) {
                        try {
                            const imgData = ctx.getImageData(0, 0, this.width, this.height);
                            addMicroNoise(imgData.data);
                            ctx.putImageData(imgData, 0, 0);
                        } catch (e) {}
                    }
                    return originalToDataURL.apply(this, args);
                };

                const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
                CanvasRenderingContext2D.prototype.getImageData = function(...args) {
                    const imgData = originalGetImageData.apply(this, args);
                    addMicroNoise(imgData.data);
                    return imgData;
                };

                if (typeof WebGLRenderingContext !== 'undefined') {
                    const originalReadPixels = WebGLRenderingContext.prototype.readPixels;
                    WebGLRenderingContext.prototype.readPixels = function(x, y, width, height, format, type, pixels) {
                        originalReadPixels.call(this, x, y, width, height, format, type, pixels);
                        for (let i = 0; i < pixels.length; i++) {
                            pixels[i] = pixels[i] ^ (i % 2 === 0 ? 1 : 0);
                        }
                    };
                }
            } catch (e) {}

            // WebRTC ICE Candidate Masking
            try {
                const originalCreateOffer = RTCPeerConnection.prototype.createOffer;
                RTCPeerConnection.prototype.createOffer = function(options) {
                    return originalCreateOffer.call(this, options).then(offer => {
                        offer.sdp = offer.sdp.replace(/a=candidate:.+ \\d+\\.\\d+\\.\\d+\\.\\d+ \\d+ typ host.+/g, (match) => {
                            return match.replace(/\\d+\\.\\d+\\.\\d+\\.\\d+/, 'f8aa18e1-4562-4db1-9e7f-73c3503a7a93.local');
                        });
                        return offer;
                    });
                };

                const originalSetLocalDescription = RTCPeerConnection.prototype.setLocalDescription;
                RTCPeerConnection.prototype.setLocalDescription = function(desc) {
                    if (desc && desc.sdp) {
                        desc.sdp = desc.sdp.replace(/a=candidate:.+ \\d+\\.\\d+\\.\\d+\\.\\d+ \\d+ typ host.+/g, (match) => {
                            return match.replace(/\\d+\\.\\d+\\.\\d+\\.\\d+/, 'f8aa18e1-4562-4db1-9e7f-73c3503a7a93.local');
                        });
                    }
                    return originalSetLocalDescription.call(this, desc);
                };
            } catch (e) {}

            // Nested Iframe Webdriver Shield Injection
            try {
                const originalCreateElement = Document.prototype.createElement;
                Document.prototype.createElement = function(tagName, options) {
                    const el = originalCreateElement.call(this, tagName, options);
                    if (tagName.toLowerCase() === 'iframe') {
                        el.addEventListener('load', () => {
                            try {
                                if (el.contentWindow) {
                                    Object.defineProperty(el.contentWindow.navigator, 'webdriver', { get: () => undefined });
                                    el.contentWindow.chrome = { runtime: {}, app: {}, csi: () => {}, loadTimes: () => {} };
                                }
                            } catch (err) {}
                        });
                    }
                    return el;
                };
            } catch (e) {}
            """
            if self.context is None:
                raise BrowserLaunchError("Vanilla Playwright persistent context launch failed to initialize context.")
            await self.context.add_init_script(failsafe_script)
            return self.context, None
        except Exception as ex:
            await self.shutdown()
            raise BrowserLaunchError(f"Vanilla Playwright launch failed: {ex}") from ex

    async def shutdown(self) -> None:
        if self.context:
            try:
                await self.context.close()
            except Exception as e:
                logger.debug(f"Context close exception: {e}")
            finally:
                self.context = None

        if self.playwright_manager:
            try:
                await self.playwright_manager.stop()
            except Exception as e:
                logger.debug(f"Playwright manager stop exception: {e}")
            finally:
                self.playwright_manager = None

        # Allow proactor event loop on Windows to cleanly process transport close callbacks
        await asyncio.sleep(0.05)
