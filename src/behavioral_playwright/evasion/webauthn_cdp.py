"""
Dual-Mode WebAuthn Hardware Assertion Provider
Supports both Chromium Native CDP Virtual Authenticator (true cryptographic verification)
and Fallback P-256 Mock Assertion Script.
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("BehavioralEvasion.WebAuthnVirtualTPM")


async def attach_cdp_virtual_authenticator(page: Any, protocol: str = "ctap2", transport: str = "usb") -> Optional[Dict[str, Any]]:
    """
    Enables native Chromium CDP WebAuthn Virtual Authenticator.
    Generates genuine ECDSA P-256 keys and mathematically valid challenge signatures.
    """
    try:
        cdp = await page.context.new_cdp_session(page)
        await cdp.send("WebAuthn.enable")
        res = await cdp.send("WebAuthn.addVirtualAuthenticator", {
            "options": {
                "protocol": protocol,
                "transport": transport,
                "hasResidentKey": True,
                "hasUserVerification": True,
                "isUserVerified": True
            }
        })
        auth_id = res.get("authenticatorId") if isinstance(res, dict) else "active"
        logger.info(f"Attached Native Chromium CDP Virtual Authenticator: {auth_id}")
        return res
    except Exception as e:
        logger.warning(f"CDP Virtual Authenticator setup failed (fallback to JS injection): {e}")
        return None


class VirtualTPMWebAuthnRelay:
    """
    Mocks WebAuthn / FIDO2 hardware assertion challenge relay.
    Handles sandboxed and cross-origin iframe origins cleanly.
    """
    @staticmethod
    def get_webauthn_relay_script() -> str:
        return """
        (() => {
            if (window.__webauthn_cdp_relay__) return;
            window.__webauthn_cdp_relay__ = true;

            if (navigator.credentials && navigator.credentials.get) {
                const origGet = navigator.credentials.get;
                navigator.credentials.get = async function(options) {
                    if (options && options.publicKey) {
                        const challengeBuf = options.publicKey.challenge;
                        let challengeB64 = "";
                        if (challengeBuf instanceof ArrayBuffer) {
                            challengeB64 = btoa(String.fromCharCode(...new Uint8Array(challengeBuf)));
                        } else if (ArrayBuffer.isView(challengeBuf)) {
                            challengeB64 = btoa(String.fromCharCode(...new Uint8Array(challengeBuf.buffer)));
                        } else if (typeof challengeBuf === 'string') {
                            challengeB64 = challengeBuf;
                        }

                        let targetOrigin = window.location.origin || "https://localhost";
                        try {
                            if (window.top && window.top.location && window.top.location.origin) {
                                targetOrigin = window.top.location.origin;
                            }
                        } catch (e) {
                            targetOrigin = window.location.origin || "https://localhost";
                        }

                        const authData = new Uint8Array(37);
                        if (window.crypto && window.crypto.getRandomValues) {
                            window.crypto.getRandomValues(authData.subarray(0, 32));
                        }
                        authData[32] = 0x05;
                        authData[33] = 0x00; authData[34] = 0x00; authData[35] = 0x00; authData[36] = 0x01;

                        const clientData = {
                            type: "webauthn.get",
                            challenge: challengeB64,
                            origin: targetOrigin,
                            crossOrigin: false
                        };
                        const clientDataJSON = new TextEncoder().encode(JSON.stringify(clientData));

                        const sigData = new Uint8Array(64);
                        if (window.crypto && window.crypto.getRandomValues) {
                            window.crypto.getRandomValues(sigData);
                        }

                        return {
                            id: btoa(targetOrigin).replace(/=/g, '').slice(0, 22),
                            rawId: new Uint8Array([1, 3, 3, 7]).buffer,
                            response: {
                                clientDataJSON: clientDataJSON.buffer,
                                authenticatorData: authData.buffer,
                                signature: sigData.buffer,
                                userHandle: null
                            },
                            type: 'public-key'
                        };
                    }
                    return origGet.apply(this, arguments);
                };
            }
        })();
        """
