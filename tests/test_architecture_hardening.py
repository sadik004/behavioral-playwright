"""
Architectural Hardening Verification Test Suite
Validates Clean Architecture protocols, Facade-level security namespaces,
Unified Quantum Facade domain integration, and MCP server tooling.
"""

import pytest
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
for p in [ROOT_DIR, SRC_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import behavioral_evasion_suite as bes
from behavioral_evasion_suite.security_protocol import (
    SecurityAuditorProtocol,
    SecurityFinding,
    AuditResultDTO
)
from behavioral_evasion_suite.unified_quantum_facade import UnifiedQuantumFacade
from behavioral_evasion_suite.mcp_server import AVAILABLE_TOOLS, handle_tool_call
from behavioral_playwright import BP


def test_01_security_protocol_runtime_checkability():
    """Verify that all auditors conform to SecurityAuditorProtocol at runtime."""
    gql_engine = bes.MasterGraphQLDeepLogicEngine(target_url="https://api.target.com/graphql")
    unified_v5 = bes.UnifiedSecurityAuditorV5(target_url="https://api.target.com")

    assert isinstance(gql_engine, SecurityAuditorProtocol)
    assert gql_engine.auditor_name == "MasterGraphQLDeepLogicEngine"
    assert hasattr(gql_engine, "run_audit")

    assert isinstance(unified_v5, SecurityAuditorProtocol)
    assert unified_v5.auditor_name == "UnifiedSecurityAuditorV5"
    assert hasattr(unified_v5, "run_audit")


def test_02_security_finding_and_dto_contracts():
    """Verify structured DTO construction and immutability contracts."""
    finding = SecurityFinding(
        title="GraphQL Introspection Enabled",
        severity="MEDIUM",
        cwe_id="CWE-200",
        description="Full schema exposed via introspection query.",
        remediation="Disable introspection in production environment."
    )
    assert finding.severity == "MEDIUM"
    assert finding.cwe_id == "CWE-200"
    assert finding.timestamp is not None

    report = AuditResultDTO(
        auditor_name="TestAuditor",
        status="SUCCESS",
        target="https://api.target.com/graphql",
        timestamp="2026-09-17T21:00:00Z",
        findings=[finding]
    )
    assert report.auditor_name == "TestAuditor"
    assert len(report.findings) == 1


def test_03_unified_quantum_facade_security_domain():
    """Verify that UnifiedQuantumFacade exposes GraphQL and Security auditors on its domain."""
    facade = UnifiedQuantumFacade()
    
    assert hasattr(facade.security, "graphql")
    assert hasattr(facade.security, "auditor")
    assert hasattr(facade.security, "create_graphql_auditor")
    assert hasattr(facade.security, "audit_graphql_endpoint")

    assert facade.graphql_auditor is not None
    assert facade.security_auditor is not None
    assert isinstance(facade.graphql_auditor, SecurityAuditorProtocol)

    custom_auditor = facade.security.create_graphql_auditor("https://staging.target.com/graphql")
    assert custom_auditor.target_url == "https://staging.target.com/graphql"


def test_04_bp_facade_security_namespace():
    """Verify that core BPFacade exposes bp.security with full auditing capabilities."""
    bp = BP()
    assert hasattr(bp, "security")
    assert hasattr(bp.security, "graphql_auditor")
    assert hasattr(bp.security, "unified_auditor")
    assert hasattr(bp.security, "audit_graphql")

    auditor_instance = bp.security.graphql_auditor("https://prod.target.com/graphql")
    assert auditor_instance is not None
    assert auditor_instance.target_url == "https://prod.target.com/graphql"
    assert isinstance(auditor_instance, SecurityAuditorProtocol)


@pytest.mark.asyncio
async def test_05_mcp_server_graphql_tool_integration():
    """Verify that MCP server registers and executes run_graphql_security_audit."""
    tool_names = [t["name"] for t in AVAILABLE_TOOLS]
    assert "run_graphql_security_audit" in tool_names

    # Test tool schema
    tool_spec = next(t for t in AVAILABLE_TOOLS if t["name"] == "run_graphql_security_audit")
    assert "target_url" in tool_spec["inputSchema"]["properties"]
    assert "target_url" in tool_spec["inputSchema"]["required"]

    # Test tool invocation
    res = await handle_tool_call("run_graphql_security_audit", {
        "target_url": "https://api.target.com/graphql"
    })
    assert res["status"] == "SUCCESS"
    assert res["graphql_url"] == "https://api.target.com/graphql"
    assert "audit_report" in res
    assert res["audit_report"]["generated_modules"]["introspection_bypasses_count"] == 5


@pytest.mark.asyncio
async def test_06_async_bp_security_audit_graphql_delegation():
    """Verify async execution of bp.security.audit_graphql."""
    bp = BP()
    report = await bp.security.audit_graphql("https://api.test-target.com/graphql")
    assert "status" in report
    assert report["generated_modules"]["introspection_bypasses_count"] == 5
