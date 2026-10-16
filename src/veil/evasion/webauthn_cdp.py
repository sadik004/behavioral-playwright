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
            if (window.__powerhand_webauthn_relay__) return;
            window.__powerhand_webauthn_relay__ = true;

            if (navigator.credentials && navigator.credentials.get) {
                const origGet = navigator.credentials.get;
                navigator.credentials.get = async function(options) {
                    if (options && options.publicKey) {
                        const authData = new Uint8Array(37);
                        for (let i = 0; i < 32; i++) authData[i] = (i * 7) % 256;
                        authData[32] = 0x05;
                        authData[33] = 0x00; authData[34] = 0x00; authData[35] = 0x00; authData[36] = 0x01;

                        const dummySig = new Uint8Array([
                            0x30, 0x44, 0x02, 0x20,
                            0x7F, 0x3A, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE,
                            0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x01,
                            0x02, 0x20,
                            0x6A, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF,
                            0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x02
                        ]);

                        let targetOrigin = "https://localhost";
                        try {
                            if (window.location.origin && window.location.origin !== "null") {
                                targetOrigin = window.location.origin;
                            } else if (window.top && window.top.location && window.top.location.origin) {
                                targetOrigin = window.top.location.origin;
                            }
                        } catch (e) {
                            targetOrigin = document.referrer ? new URL(document.referrer).origin : "https://localhost";
                        }

                        const clientDataJSON = new TextEncoder().encode(JSON.stringify({
                            type: "webauthn.get",
                            challenge: "powerhand_crypto_challenge_base64",
                            origin: targetOrigin,
                            crossOrigin: false
                        }));

                        return {
                            id: 'powerhand_p256_credential_1337',
                            rawId: new Uint8Array([1, 3, 3, 7]).buffer,
                            response: {
                                clientDataJSON: clientDataJSON.buffer,
                                authenticatorData: authData.buffer,
                                signature: dummySig.buffer,
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
