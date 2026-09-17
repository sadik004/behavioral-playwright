"""
Automated Test Suite for Unified Security Auditor v5
"""
import os, sys
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

import behavioral_evasion_suite as bes

def test_01_mcp_schema_auditor():
    tool = {
        "name": "read_file",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}}
        }
    }
    res = bes.MCPSchemaAuditor.audit_tool_schema(tool)
    assert res["status"] == "WARNING"
    assert len(res["risks"]) > 0

    safe_msg = {"jsonrpc": "2.0", "method": "tools/list", "params": {}}
    assert bes.MCPSchemaAuditor.audit_mcp_message(safe_msg) is True

    unsafe_msg = {"jsonrpc": "2.0", "method": "eval", "params": {"cmd": "rm -rf /"}}
    assert bes.MCPSchemaAuditor.audit_mcp_message(unsafe_msg) is False

def test_02_poc_engine_curl_generation():
    req = {
        "url": "https://api.target.com/user/profile",
        "method": "POST",
        "headers": {"Authorization": "Bearer token123", "Content-Type": "application/json"},
        "post_data": '{"admin": true}'
    }
    curl_str = bes.PoCEngine.generate_curl_poc(req)
    assert "curl -i -X POST https://api.target.com/user/profile" in curl_str
    assert "Authorization: Bearer token123" in curl_str

def test_03_desync_engine_header_audit():
    clean_headers = {"Host": "target.com", "User-Agent": "Mozilla/5.0"}
    res_clean = bes.DesyncEngine.audit_header_desync_risk(clean_headers)
    assert res_clean["risk"] == "LOW"

    conflict_headers = {"Host": "target.com", "Content-Length": "42", "Transfer-Encoding": "chunked"}
    res_conflict = bes.DesyncEngine.audit_header_desync_risk(conflict_headers)
    assert res_conflict["risk"] == "CRITICAL"

def test_04_cve_reproducer_spec():
    spec = bes.CVEReproducer.generate_docker_testbed_spec("CVE-2026-9999", "ubuntu:24.04")
    assert "FROM ubuntu:24.04" in spec
    assert 'cve_verification="CVE-2026-9999"' in spec

def test_05_agent_hijack_auditor():
    auditor = bes.AgentHijackAuditor(max_token_budget=100)
    normal_text = "This is a safe and concise document summary."
    res_normal = auditor.audit_context_window(normal_text)
    assert res_normal["overflow_risk"] is False

    long_text = "word " * 120
    res_long = auditor.audit_context_window(long_text)
    assert res_long["overflow_risk"] is True

def test_06_state_diff_auditor():
    auditor = bes.StateDiffAuditor()
    h1 = auditor._sanitize_dom('<div id="app">Hello<script>var t=1234567890;</script></div>')
    assert "<script" not in h1
    assert "Hello" in h1

if __name__ == "__main__":
    test_01_mcp_schema_auditor()
    print('Test 01 passed')
    test_02_poc_engine_curl_generation()
    print('Test 02 passed')
    test_03_desync_engine_header_audit()
    print('Test 03 passed')
    test_04_cve_reproducer_spec()
    print('Test 04 passed')
    test_05_agent_hijack_auditor()
    print('Test 05 passed')
    test_06_state_diff_auditor()
    print('Test 06 passed')
    print('ALL 6 AUDIT TESTS PASSED 100%!')
