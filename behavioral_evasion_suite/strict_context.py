"""
Proxy & Session Isolation with Soft WebRTC Interception
Enforces 1-Proxy = 1-Isolated-Context lifecycle boundaries with WebRTC masking.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("BehavioralEvasion.StrictContext")


class StrictContextManager:
    """Enforces 1-Proxy = 1-Isolated-Context lifecycle boundaries with WebRTC masking."""
    def __init__(self, browser: Any) -> None:
        self.browser = browser

    async def create_isolated_context(self, proxy_config: Optional[Dict[str, str]] = None) -> Any:
        logger.info("StrictContextManager: Resetting session boundaries. Initializing isolated context.")
        context_args = {
            "ignore_https_errors": True,
            "viewport": {"width": 1280, "height": 720}
        }
        if proxy_config:
            context_args["proxy"] = proxy_config

        context = await self.browser.new_context(**context_args)

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
