"""
Comprehensive Architectural Verification for Unified Quantum Facade & MCP Server
Validates that all 31 legacy sub-modules are 100% intact and functional,
and tests the PersistentSessionManager, TokenOptimizedDOMReader, and MCP Server tools.
"""

import sys
import os
import asyncio
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from behavioral_evasion_suite import (
    UnifiedQuantumFacade,
    PersistentSessionManager,
    TokenOptimizedDOMReader,
    HardenedBrowserDomain,
    HardwareNetworkDomain,
    BiometricKinematicsDomain,
    SecurityDataDomain,
    OrchestrationDomain
)


def test_01_all_31_modules_intact_and_imported():
    """Verify that every single one of the 31 sub-modules imports with zero errors."""
    import behavioral_evasion_suite.backpressure_queue
    import behavioral_evasion_suite.canvas_shader_spoofer
    import behavioral_evasion_suite.cdp_evasion
    import behavioral_evasion_suite.circuit_breaker
    import behavioral_evasion_suite.cognitive_gaze_physics
    import behavioral_evasion_suite.context_rotator
    import behavioral_evasion_suite.dma_kernel_bridge
    import behavioral_evasion_suite.hardware_os_spoofer
    import behavioral_evasion_suite.honeypot_shield
    import behavioral_evasion_suite.hybrid_router
    import behavioral_evasion_suite.keystroke_engine
    import behavioral_evasion_suite.main
    import behavioral_evasion_suite.mouse_physics
    import behavioral_evasion_suite.os_network_stack_spoofer
    import behavioral_evasion_suite.os_resource_guard
    import behavioral_evasion_suite.persistence_pipeline
    import behavioral_evasion_suite.persona_matrix
    import behavioral_evasion_suite.powerhand_master
    import behavioral_evasion_suite.quality_sentinel
    import behavioral_evasion_suite.session_vault
    import behavioral_evasion_suite.stealth_session
    import behavioral_evasion_suite.strict_context
    import behavioral_evasion_suite.subpixel_font_shield
    import behavioral_evasion_suite.swarm_orchestrator
    import behavioral_evasion_suite.tls_ja4_spoofer
    import behavioral_evasion_suite.utils
    import behavioral_evasion_suite.v8_shield
    import behavioral_evasion_suite.virtual_hardware_synthesizer
    import behavioral_evasion_suite.webauthn_virtual_tpm
    import behavioral_evasion_suite.worker_universal_shield
    import behavioral_evasion_suite.unified_quantum_facade

    assert True, "All 31 modules successfully imported without circular dependencies"


def test_02_unified_quantum_facade_domains():
    """Verify UnifiedQuantumFacade initializes all 5 domains properly."""
    facade = UnifiedQuantumFacade()

    assert isinstance(facade.browser, HardenedBrowserDomain)
    assert isinstance(facade.network, HardwareNetworkDomain)
    assert isinstance(facade.kinematics, BiometricKinematicsDomain)
    assert isinstance(facade.security, SecurityDataDomain)
    assert isinstance(facade.orchestration, OrchestrationDomain)
    assert isinstance(facade.session_manager, PersistentSessionManager)

    script = facade.get_master_injection_script()
    assert "window.__v8_powerhand_shield_active__" in script
    assert "window.__worker_universal_shield_active__" in script
    assert "window.__subpixel_font_shield_active__" in script
    assert "window.__virtual_hardware_synthesizer_active__" in script


@pytest.mark.asyncio
async def test_03_token_optimized_dom_reader():
    """Verify TokenOptimizedDOMReader parses and extracts compact representation."""
    class FakePage:
        url = "https://example.com/login"
        async def evaluate(self, script):
            return {
                "title": "Secure Login Portal",
                "url": "https://example.com/login",
                "elements": [
                    {"ref": "el_1", "tag": "input", "type": "text", "label": "Username"},
                    {"ref": "el_2", "tag": "input", "type": "password", "label": "Password"},
                    {"ref": "el_3", "tag": "button", "type": "submit", "label": "Sign In"}
                ]
            }

    data = await TokenOptimizedDOMReader.extract_compact_tree(FakePage())
    assert data["title"] == "Secure Login Portal"
    assert len(data["elements"]) == 3
    assert data["elements"][2]["ref"] == "el_3"


def test_04_mcp_tool_discovery_and_specifications():
    """Verify MCP Server tool definitions conform to JSON Schema."""
    from behavioral_evasion_suite.mcp_server import AVAILABLE_TOOLS

    assert len(AVAILABLE_TOOLS) >= 8
    tool_names = [t["name"] for t in AVAILABLE_TOOLS]
    assert "stealth_open_page" in tool_names
    assert "stealth_human_action" in tool_names
    assert "stealth_extract_data" in tool_names
    assert "stealth_get_snapshot" in tool_names
    assert "stealth_close_session" in tool_names
    assert "module_persona_profile" in tool_names
    assert "module_kinematic_eval" in tool_names
    assert "module_shield_status" in tool_names

    for t in AVAILABLE_TOOLS:
        assert "name" in t
        assert "description" in t
        assert "inputSchema" in t
        assert t["inputSchema"]["type"] == "object"


@pytest.mark.asyncio
async def test_05_mcp_tool_executions():
    """Verify execution of standalone MCP diagnostic and kinematic tools."""
    from behavioral_evasion_suite.mcp_server import handle_tool_call

    # Shield Status Check
    status = await handle_tool_call("module_shield_status", {})
    assert status["status"] == "HEALTHY"
    assert status["total_integrated_modules"] == 31
    assert status["all_modules_intact"] is True

    # Persona Profile Check
    persona = await handle_tool_call("module_persona_profile", {"profile_id": "win11_nvidia_rtx4070"})
    assert persona["profile_id"] == "win11_nvidia_rtx4070"
    assert "RTX 4070" in persona["hardware"]["webgl_renderer"]

    # Kinematic Keystroke Plan
    k_res = await handle_tool_call("module_kinematic_eval", {
        "kinematic_type": "keystroke_plan",
        "text": "AdminLogin"
    })
    assert k_res["actions_count"] >= 10
    assert len(k_res["sample_plan"]) > 0

    # Kinematic Inertial Scroll
    s_res = await handle_tool_call("module_kinematic_eval", {
        "kinematic_type": "inertial_scroll",
        "scroll_distance": 600.0
    })
    assert s_res["steps_count"] > 5


def test_06_regression_test_v6_level5_audit():
    """Ensure that the Level 5 verification test suite passes with zero regressions."""
    import subprocess
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_v6_level5_audit.py", "-v"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True
    )
    assert res.returncode == 0, f"Regression detected:\n{res.stdout}\n{res.stderr}"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
