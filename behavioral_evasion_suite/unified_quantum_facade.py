"""
Unified Quantum Facade - Level 5+ Enterprise Architecture
Aggregates and organizes all 31 sub-modules into 5 cohesive operational domains.
Provides PersistentSessionManager for stateful MCP calls and TokenOptimizedDOMReader.
Guarantees 100% backward compatibility and zero modification to underlying modules.
"""

import sys
import os
import uuid
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field

# Ensure package root is available
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)

# -----------------------------------------------------------------------------
# DOMAIN 1: HARDENED BROWSER & PROTOTYPE SHIELDS
# -----------------------------------------------------------------------------
from .cdp_evasion import CDPEvasionShield
from .v8_shield import V8BytecodeShield
from .worker_universal_shield import WorkerUniversalShield, WorkerShieldConfig
from .subpixel_font_shield import SubpixelFontShield, FontMetricConfig
from .canvas_shader_spoofer import CanvasWebGLShaderSpoofer
from .hardware_os_spoofer import HardwareOSSpoofer

class HardenedBrowserDomain:
    """Domain aggregator for V8, CDP, Web Worker, Subpixel Font, and WebGL Shields."""
    def __init__(self, page: Any = None):
        self.cdp = CDPEvasionShield(page=page)
        self.v8 = V8BytecodeShield()
        self.worker = WorkerUniversalShield()
        self.font = SubpixelFontShield()
        self.canvas = CanvasWebGLShaderSpoofer()
        self.hardware_spoofer = HardwareOSSpoofer(page=page)

    def get_bundled_shield_scripts(self) -> str:
        """Returns consolidated JS injection payloads from all browser shields."""
        return "\n".join([
            CDPEvasionShield.get_stealth_js(),
            self.v8.get_v8_masking_script(),
            self.worker.get_script(),
            self.font.get_script(),
            self.canvas.get_canvas_shader_spoofer_script(),
            HardwareOSSpoofer.get_spoof_js()
        ])


# -----------------------------------------------------------------------------
# DOMAIN 2: HARDWARE & NETWORK SIGNATURES
# -----------------------------------------------------------------------------
from .virtual_hardware_synthesizer import VirtualHardwareSynthesizer, HardwareSynthesisConfig
from .os_network_stack_spoofer import OSNetworkStackSpoofer, NetworkStackConfig
from .tls_ja4_spoofer import TLSJA4Spoofer, AsyncSession
from .dma_kernel_bridge import OSKernelInputEventBridge, FPGAPCIeDMAHardwareBridge
from .webauthn_virtual_tpm import VirtualTPMWebAuthnRelay, attach_cdp_virtual_authenticator

class HardwareNetworkDomain:
    """Domain aggregator for media devices, TCP/IP stack, TLS, DMA, and WebAuthn."""
    def __init__(self):
        self.hardware_synthesizer = VirtualHardwareSynthesizer()
        self.network_spoofer = OSNetworkStackSpoofer()
        self.tls_spoofer = TLSJA4Spoofer()
        self.dma_hardware = FPGAPCIeDMAHardwareBridge()
        self.webauthn_relay = VirtualTPMWebAuthnRelay()

    def get_bundled_hardware_scripts(self) -> str:
        return "\n".join([
            self.hardware_synthesizer.get_script(),
            self.webauthn_relay.get_webauthn_relay_script()
        ])


# -----------------------------------------------------------------------------
# DOMAIN 3: BIOMETRIC & KINEMATIC ENGINES
# -----------------------------------------------------------------------------
from .mouse_physics import BiomechanicalMousePhysics
from .keystroke_engine import CognitiveKeystrokeEngine
from .cognitive_gaze_physics import CognitiveGazePhysics, human_scroll, cognitive_reading_pause

class BiometricKinematicsDomain:
    """Domain aggregator for neuromuscular mouse physics, typing, and inertial scroll."""
    def __init__(self):
        self.mouse = BiomechanicalMousePhysics()
        self.keystroke = CognitiveKeystrokeEngine()
        self.gaze = CognitiveGazePhysics()


# -----------------------------------------------------------------------------
# DOMAIN 4: DATA INTEGRITY & SECURITY GUARDS
# -----------------------------------------------------------------------------
from .honeypot_shield import HoneypotIsolationShield
from .quality_sentinel import QualitySentinel
from .persistence_pipeline import BasePersistencePipeline
from .backpressure_queue import BackpressureQueue

class SecurityDataDomain:
    """Domain aggregator for honeypot traps, Pydantic validation, and persistence."""
    def __init__(self):
        self.honeypot = HoneypotIsolationShield()
        self.quality = QualitySentinel()
        self.queue = BackpressureQueue()


# -----------------------------------------------------------------------------
# DOMAIN 5: RESILIENCE & SWARM ORCHESTRATION
# -----------------------------------------------------------------------------
from .persona_matrix import DigitalSoulPersonaMatrix, ProfileVault, IdentityAnchor
from .session_vault import SessionStateVault
from .circuit_breaker import StatusGranularCircuitBreaker
from .os_resource_guard import OSResourceGuard
from .hybrid_router import SmartAcquisitionRouter
from .strict_context import StrictContextManager
from .context_rotator import ContextRotator
from .swarm_orchestrator import MultiTabSwarmOrchestrator
from .powerhand_master import PowerHandMaster

class OrchestrationDomain:
    """Domain aggregator for personas, circuit breaker, resource guarding, and swarms."""
    def __init__(self, browser: Any = None):
        self.persona = DigitalSoulPersonaMatrix(profile_id="quantum_default")
        self.vault = SessionStateVault()
        self.circuit_breaker = StatusGranularCircuitBreaker()
        self.resource_guard = OSResourceGuard()
        self.swarm = MultiTabSwarmOrchestrator()
        self.powerhand = PowerHandMaster()

        self.context_rotator = ContextRotator(browser=browser) if browser else None
        self.strict_context = StrictContextManager(browser=browser) if browser else None
        self.router = SmartAcquisitionRouter(browser_context_rotator=self.context_rotator) if self.context_rotator else None

    def bind_browser(self, browser: Any):
        """Binds an active browser instance to context rotator, router, and strict context."""
        self.context_rotator = ContextRotator(browser=browser)
        self.strict_context = StrictContextManager(browser=browser)
        self.router = SmartAcquisitionRouter(browser_context_rotator=self.context_rotator)


# =============================================================================
# TOKEN-OPTIMIZED ACCESSIBILITY & DOM READER (FOR AI CONTEXT LIMITS)
# =============================================================================

class TokenOptimizedDOMReader:
    """
    Parses live Playwright pages into a high-density, token-efficient representation
    (Accessibility Tree + Interactive Element Registry) specifically designed to prevent
    LLM Context Window overflow.
    """
    JS_ELEMENT_SCANNER = """
    (() => {
        const interactiveTags = ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'];
        const elements = [];
        let counter = 0;

        function isVisible(elem) {
            const style = window.getComputedStyle(elem);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
            const rect = elem.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        }

        const nodes = document.querySelectorAll('*');
        for (const el of nodes) {
            if (counter > 150) break; // Limit elements to protect context
            if (interactiveTags.includes(el.tagName) || el.getAttribute('role') === 'button' || el.hasAttribute('onclick')) {
                if (isVisible(el)) {
                    counter++;
                    const refId = 'el_' + counter;
                    el.setAttribute('data-mcp-ref', refId);

                    let label = (el.innerText || el.value || el.getAttribute('placeholder') || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim().replace(/\\s+/g, ' ');
                    if (label.length > 50) label = label.substring(0, 50) + '...';

                    elements.push({
                        ref: refId,
                        tag: el.tagName.toLowerCase(),
                        type: el.getAttribute('type') || '',
                        label: label,
                        id: el.id || null,
                        name: el.getAttribute('name') || null
                    });
                }
            }
        }
        return {
            title: document.title,
            url: window.location.href,
            elements: elements
        };
    })();
    """

    @classmethod
    async def extract_compact_tree(cls, page: Any) -> Dict[str, Any]:
        """Runs the element scanner and returns compact interactive map."""
        if hasattr(page, "evaluate"):
            try:
                data = await page.evaluate(cls.JS_ELEMENT_SCANNER)
                return data
            except Exception as e:
                return {"title": "Error", "url": getattr(page, "url", ""), "elements": [], "error": str(e)}
        return {"title": getattr(page, "title", lambda: "")(), "url": getattr(page, "url", ""), "elements": []}


# =============================================================================
# PERSISTENT SESSION REGISTRY (STATEFUL AGENT MANAGER)
# =============================================================================

class ActiveSession:
    """Wrapper holding persistent Playwright browser, context, page, and shields."""
    def __init__(self, session_id: str, profile_id: str, playwright, browser, context, page):
        self.session_id = session_id
        self.profile_id = profile_id
        self.playwright = playwright
        self.browser = browser
        self.context = context
        self.page = page
        self.created_at = time.time()
        self.last_accessed = time.time()

    def touch(self):
        self.last_accessed = time.time()

    async def close(self):
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass


class PersistentSessionManager:
    """
    Manages long-lived browser sessions across sequential MCP tool calls.
    Includes automated idle cleanup to prevent memory exhaustion.
    """
    def __init__(self, default_timeout_seconds: int = 1800):
        self.sessions: Dict[str, ActiveSession] = {}
        self.default_timeout = default_timeout_seconds
        self.dom_reader = TokenOptimizedDOMReader()

    async def create_session(
        self,
        profile_id: str = "win11_nvidia_rtx4070",
        headless: bool = True,
        facade: Optional["UnifiedQuantumFacade"] = None
    ) -> ActiveSession:
        """Launches a persistent browser session with all 31 shields active."""
        from playwright.async_api import async_playwright

        session_id = str(uuid.uuid4())[:8]
        facade = facade or UnifiedQuantumFacade()

        playwright = await async_playwright().start()
        launch_args = facade.network.network_spoofer.get_browser_network_launch_args()

        browser = await playwright.chromium.launch(
            headless=headless,
            args=launch_args
        )

        ctx_opts = facade.orchestration.persona.anchor.get_playwright_context_options()
        context = await browser.new_context(**ctx_opts)

        # Inject consolidated Level 5+ scripts
        all_scripts = facade.get_master_injection_script()
        await context.add_init_script(all_scripts)

        page = await context.new_page()
        session = ActiveSession(session_id, profile_id, playwright, browser, context, page)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ActiveSession]:
        session = self.sessions.get(session_id)
        if session:
            session.touch()
        return session

    async def close_session(self, session_id: str) -> bool:
        session = self.sessions.pop(session_id, None)
        if session:
            await session.close()
            return True
        return False

    async def close_all(self):
        for s in list(self.sessions.values()):
            await s.close()
        self.sessions.clear()

    async def reap_idle_sessions(self):
        """Closes sessions exceeding idle timeout."""
        now = time.time()
        for sid, s in list(self.sessions.items()):
            if now - s.last_accessed > self.default_timeout:
                await self.close_session(sid)


# =============================================================================
# TOP-LEVEL FACADE: UNIFIED QUANTUM FACADE
# =============================================================================

class UnifiedQuantumFacade:
    """
    Master Architectural Hub coordinating all 31 sub-modules into a coherent,
    enterprise-grade stealth automation suite with zero legacy modifications.
    """
    def __init__(self):
        self.browser = HardenedBrowserDomain()
        self.network = HardwareNetworkDomain()
        self.kinematics = BiometricKinematicsDomain()
        self.security = SecurityDataDomain()
        self.orchestration = OrchestrationDomain()
        self.session_manager = PersistentSessionManager()

    def get_master_injection_script(self) -> str:
        """Bundles all JS scripts from all operational domains into one payload."""
        return "\n".join([
            self.browser.get_bundled_shield_scripts(),
            self.network.get_bundled_hardware_scripts(),
            self.security.honeypot.get_honeypot_js_payload()
        ])
