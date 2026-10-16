"""
Automated Test Suite for Unified Security Auditor v5 (Enterprise Edition)
Testing all 11 Defensive & Auditing Modules including SAML 2.0 & OAuth 2.0/OIDC.
"""
import os
import sys
import base64
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

def test_07_saml_signature_exclusion_and_xsw3():
    auditor = bes.SAMLTrustChainAuditor()
    sample_xml = (
        "<saml2:Assertion xmlns:saml2='urn:oasis:names:tc:SAML:2.0:assertion' ID='_12345'>"
        "<saml2:Signature xmlns:ds='http://www.w3.org/2000/09/xmldsig#'>valid_sig</saml2:Signature>"
        "<saml2:NameID>legit@victim.com</saml2:NameID>"
        "</saml2:Assertion>"
    )
    b64_sig_excl, modified = auditor.test_signature_exclusion(sample_xml, "spoofed@evil.com")
    assert modified is True
    decoded_sig_excl = base64.b64decode(b64_sig_excl).decode('utf-8')
    assert "spoofed@evil.com" in decoded_sig_excl
    assert "Signature" not in decoded_sig_excl

    b64_xsw3, xsw_success = auditor.test_xml_signature_wrapping_xsw3(sample_xml, "admin@victim.com")
    assert xsw_success is True
    decoded_xsw = base64.b64decode(b64_xsw3).decode('utf-8')
    assert "_12345_forged" in decoded_xsw
    assert "admin@victim.com" in decoded_xsw

def test_08_saml_relaystate_open_redirect_none_safety():
    auditor = bes.SAMLTrustChainAuditor()
    none_audit = auditor.test_relaystate_open_redirect(None)
    assert none_audit["relay_state"] == ""
    assert none_audit["open_redirect_risk"] == "LOW"

    bad_audit = auditor.test_relaystate_open_redirect("https://evil.com/login")
    assert bad_audit["open_redirect_risk"] == "HIGH"
    assert "CWE-601" in bad_audit["cwe_id"]

    good_audit = auditor.test_relaystate_open_redirect("/dashboard/home")
    assert good_audit["open_redirect_risk"] == "LOW"

def test_09_oauth2_pkce_enforcement_rfc7636():
    auditor = bes.OAuth2TrustChainAuditor()
    bad_req = {"grant_type": "authorization_code", "code": "abc12345"}
    bad_audit = auditor.audit_pkce_enforcement(bad_req)
    assert bad_audit["pkce_enforced"] is False
    assert "CRITICAL" in bad_audit["risk"]

    good_req = {"grant_type": "authorization_code", "code": "abc12345", "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"}
    good_audit = auditor.audit_pkce_enforcement(good_req)
    assert good_audit["pkce_enforced"] is True
    assert good_audit["risk"] == "NONE"

def test_10_oauth2_redirect_uri_bypasses_rfc9700():
    auditor = bes.OAuth2TrustChainAuditor()
    bypasses = auditor.audit_redirect_uri_patterns("https://app.target.com/callback")
    assert len(bypasses) == 7
    types = [b["type"] for b in bypasses]
    assert "Subdomain Bypass" in types
    assert "Path Traversal" in types
    assert "Parameter Injection" in types
    assert "Fragment Injection" in types
    assert "Open Redirect Chain" in types
    assert "Localhost Bypass" in types
    assert "Scheme Downgrade" in types

def test_11_oauth2_account_linking_sub_claim():
    auditor = bes.OAuth2TrustChainAuditor()
    unsafe_jwt = {"email": "user@target.com", "name": "Target User"}
    unsafe_audit = auditor.audit_account_linking_claims(unsafe_jwt)
    assert unsafe_audit["vulnerable_to_email_account_takeover"] is True
    assert unsafe_audit["risk"] == "HIGH"

    safe_jwt = {"sub": "usr_999888777", "email": "user@target.com"}
    safe_audit = auditor.audit_account_linking_claims(safe_jwt)
    assert safe_audit["vulnerable_to_email_account_takeover"] is False
    assert safe_audit["risk"] == "LOW"

def test_12_poc_engine_dict_payload_serialization():
    req = {
        "url": "https://api.target.com/v1/update",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "post_data": {"action": "promote", "role": "admin"}
    }
    curl_poc = bes.PoCEngine.generate_curl_poc(req)
    assert "--data-raw" in curl_poc
    assert '{"action": "promote", "role": "admin"}' in curl_poc

if __name__ == "__main__":
    test_01_mcp_schema_auditor()
    test_02_poc_engine_curl_generation()
    test_03_desync_engine_header_audit()
    test_04_cve_reproducer_spec()
    test_05_agent_hijack_auditor()
    test_06_state_diff_auditor()
    test_07_saml_signature_exclusion_and_xsw3()
    test_08_saml_relaystate_open_redirect_none_safety()
    test_09_oauth2_pkce_enforcement_rfc7636()
    test_10_oauth2_redirect_uri_bypasses_rfc9700()
    test_11_oauth2_account_linking_sub_claim()
    test_12_poc_engine_dict_payload_serialization()
    print("ALL 12 SECURITY AUDITOR TESTS PASSED 100%!")
