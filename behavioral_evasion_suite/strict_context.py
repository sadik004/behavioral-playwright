"""
Proxy & Session Isolation with Soft WebRTC Interception & HTTP/2 Header Synchronization
Enforces 1-Proxy = 1-Isolated-Context lifecycle boundaries with WebRTC masking and persona coherence.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("BehavioralEvasion.StrictContext")


class StrictContextManager:
    """Enforces 1-Proxy = 1-Isolated-Context lifecycle boundaries with WebRTC masking and header sync."""
    def __init__(self, browser: Any) -> None:
        self.browser = browser

    async def create_isolated_context(
        self,
        proxy_config: Optional[Dict[str, str]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        abort_tracking_assets: bool = True
    ) -> Any:
        logger.info("StrictContextManager: Resetting session boundaries. Initializing isolated context.")
        
        default_headers = {
            "sec-ch-ua": '"Chromium";v="126", "Not/A)Brand";v="8", "Google Chrome";v="126"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Accept-Language": "en-US,en;q=0.9",
            "Upgrade-Insecure-Requests": "1"
        }
        if custom_headers:
            default_headers.update(custom_headers)

        context_args = {
            "ignore_https_errors": True,
            "viewport": {"width": 1920, "height": 1080},
            "extra_http_headers": default_headers
        }
        if proxy_config:
            context_args["proxy"] = proxy_config

        context = await self.browser.new_context(**context_args)

        # Route-level telemetry & tracking beacon abortion
        if abort_tracking_assets:
            async def route_filter(route):
                request = route.request
                url = request.url.lower()
                # Abort known bot telemetry and tracking beacons
                if any(beacon in url for beacon in ["google-analytics.com", "doubleclick.net", "datadoghq.com", "hotjar.com", "segment.io"]):
                    await route.abort()
                else:
                    await route.continue_()
            try:
                await context.route("**/*", route_filter)
            except Exception as e:
                logger.debug(f"Route filter attach warning: {e}")

        # Soft-masking WebRTC candidates to block leakages securely without throwing errors
        webrtc_mask_js = """
        (() => {
            const OriginalPeerConnection = window.RTCPeerConnection;
            if (OriginalPeerConnection) {
                window.RTCPeerConnection = function(config, constraints) {
                    const pc = new OriginalPeerConnection(config, constraints);

                    pc.createOffer = async function() {
                        return {
                            type: 'offer',
                            sdp: 'v=0\no=- 12345 12345 IN IP4 127.0.0.1\ns=MockSession\nt=0 0\na=group:BUNDLE sdp-group\n'
                        };
                    };

                    Object.defineProperty(pc, 'localDescription', {
                        get: () => ({ type: 'offer', sdp: 'v=0\no=- 12345 12345 IN IP4 127.0.0.1\ns=MockSession\nt=0 0\na=group:BUNDLE sdp-group\n' }),
                        configurable: true
                    });

                    return pc;
                };
                window.RTCPeerConnection.prototype = OriginalPeerConnection.prototype;
            }
        })();
        """
        await context.add_init_script(webrtc_mask_js)
        return context
