"""
Automated Test Suite for Server-Side Prototype Pollution (SSPP) Security Auditor (v5.0 Enterprise)
"""
import os, sys
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

import asyncio
import behavioral_evasion_suite as bes


def test_01_pydantic_dto_validation():
    auditor = bes.SSPPBlackBoxAuditor(target_url="https://api.example.com/v1/user")
    finding = auditor.log_finding(
        finding_type="SSPP_JSON_SPACES_VULNERABILITY",
        url="https://api.example.com/v1/user",
        method="POST",
        technique="Express json spaces mutation",
        evidence="Indentation increased to 10 spaces",
        poc="curl -i -X POST https://api.example.com/v1/user",
        remediated=True
    )
    assert isinstance(finding, bes.SSPPFinding)
    dumped = finding.model_dump()
    assert dumped["remediated"] is True
    assert dumped["method"] == "POST"


def test_02_differential_json_spaces_html_filter():
    html_error = "<html>\n          <body>500 Internal Server Error</body>\n</html>"
    base_json = '{"status": "ok"}'
    # False positive prevention: HTML error must be rejected
    assert bes.SSPPResponseAnalyzer.analyze_json_spaces(base_json, html_error, 10) is False

    valid_polluted = '{\r\n          "status": "ok"\r\n}'
    assert bes.SSPPResponseAnalyzer.analyze_json_spaces(base_json, valid_polluted, 10) is True


def test_03_differential_cors_header_baseline():
    base_headers = {"Access-Control-Expose-Headers": "Authorization, X-Custom"}
    probe_hit = {"Access-Control-Expose-Headers": "Authorization, X-Custom, x-pp-proof"}
    probe_base_only = {"Access-Control-Expose-Headers": "Authorization, X-Custom"}

    assert bes.SSPPResponseAnalyzer.analyze_exposed_headers(base_headers, probe_hit, "x-pp-proof") is True
    assert bes.SSPPResponseAnalyzer.analyze_exposed_headers(base_headers, probe_base_only, "x-pp-proof") is False


def test_04_differential_status_mutation_baseline():
    # If baseline is already 510, mutation to 510 is NOT a pollution signal
    assert bes.SSPPResponseAnalyzer.analyze_status_mutation(510, 510, 510) is False
    # If baseline is 400 and mutated to 510, pollution is confirmed
    assert bes.SSPPResponseAnalyzer.analyze_status_mutation(400, 510, 510) is True


def test_05_reversion_payload_generation():
    space_revert = bes.SSPPPayloadGenerator.get_json_space_reversion_payloads()
    assert len(space_revert) == 2
    assert space_revert[0]["__proto__"]["json spaces"] == 0

    status_revert = bes.SSPPPayloadGenerator.get_status_code_reversion_payloads(400)
    assert len(status_revert) == 2
    assert status_revert[0]["__proto__"]["status"] == 400


def test_06_shell_safe_curl_poc_multimethod():
    put_poc = bes.SSPPBlackBoxAuditor.generate_curl_poc("https://api.example.com/user/1", "PUT", body={"test": 1})
    assert "-X PUT" in put_poc and "Content-Type: application/json" in put_poc

    get_poc = bes.SSPPBlackBoxAuditor.generate_curl_poc("https://api.example.com/user/1?__proto__[a]=1", "GET")
    assert "-X GET" in get_poc and "Content-Type" not in get_poc


def test_07_master_deep_logic_engine_protocol():
    engine = bes.MasterSSPPDeepLogicEngine(target_url="https://api.example.com/audit")
    assert isinstance(engine, bes.BaseSecurityAuditor)
    assert engine.auditor_name == "SSPP_BLACKBOX_SECURITY_ENGINE"

    bundle = asyncio.run(engine.run_audit())
    assert bundle["status"] == "BUNDLE_GENERATED"
    assert "payload_matrix" in bundle
