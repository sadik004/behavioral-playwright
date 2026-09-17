"""
Automated Test Suite for GraphQL Deep Logic & Protected Attribute Diagnostic Engine (v2.0)
"""
import os, sys
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

import asyncio
import behavioral_evasion_suite as bes


def test_01_introspection_bypasses_generation():
    bypasses = bes.GraphQLIntrospectionAuditor.generate_introspection_bypasses()
    assert len(bypasses) == 5
    for b in bypasses:
        assert "technique" in b
        assert "method" in b
        assert "query" in b
        assert "headers" in b
    techniques = [b["technique"] for b in bypasses]
    assert "Newline Injection" in techniques
    assert "Fragment Wrap Bypass" in techniques
    assert "GET Method URL-Encoding" in techniques


def test_02_clairvoyance_suggestions_parsing():
    error_msg = '{"errors":[{"message":"Cannot query field \\"usr\\". Did you mean \\"user\\", \\"userInfo\\"?"}]}'
    suggestions = bes.GraphQLIntrospectionAuditor.parse_clairvoyance_suggestions(error_msg)
    assert len(suggestions) == 2
    assert "user" in suggestions
    assert "userInfo" in suggestions

    # Test alternate syntax variation
    error_alt = 'Field "secret" not found. Did you mean to query `secretToken` or \'secretKey\'?'
    suggestions_alt = bes.GraphQLIntrospectionAuditor.parse_clairvoyance_suggestions(error_alt)
    assert "secretToken" in suggestions_alt
    assert "secretKey" in suggestions_alt


def test_03_positional_correlation_payload_spec():
    spec = bes.GraphQLProtectedAttributeAuditor.generate_positional_correlation_payloads(
        target_field="title",
        sort_parameter="TITLE_ASC",
        probe_prefix="SEC"
    )
    assert spec["sort_parameter_tested"] == "TITLE_ASC"
    assert "CWE-200" in spec["cwe_id"]
    assert "reports(sort: TITLE_ASC)" in spec["probe_query"]
    assert "$prefix" in spec["boundary_probe_query"]
    assert spec["boundary_variables"]["prefix"] == "SEC"


def test_04_positional_correlation_shift_multi_item():
    items = [
        {"id": "rep_101", "title": "Alpha Report", "status": "TRIAGED"},
        {"id": "rep_102", "title": "[REDACTED]", "status": "CONFIDENTIAL"},
        {"id": "rep_103", "title": "Beta Report", "status": "RESOLVED"}
    ]
    res = bes.GraphQLProtectedAttributeAuditor.analyze_redacted_positional_shift(
        response_items=items,
        target_object_id="rep_102",
        redacted_field_name="title"
    )
    assert res["position_index"] == 1
    assert res["is_attribute_redacted"] is True
    assert res["positional_sidechannel_risk"] == "HIGH"
    assert res["total_items"] == 3
    assert res["inferred_lexical_boundary"]["after"] == "Alpha Report"
    assert res["inferred_lexical_boundary"]["before"] == "Beta Report"


def test_05_positional_correlation_multi_redacted_boundary_walk():
    # If adjacent items are also redacted, verify it walks to find non-redacted anchors
    items = [
        {"id": "1", "title": "Anchor Alpha"},
        {"id": "2", "title": "[REDACTED]"},
        {"id": "3", "title": "[REDACTED]"},  # Target item
        {"id": "4", "title": "[REDACTED]"},
        {"id": "5", "title": "Anchor Omega"}
    ]
    res = bes.GraphQLProtectedAttributeAuditor.analyze_redacted_positional_shift(
        response_items=items,
        target_object_id="3",
        redacted_field_name="title"
    )
    assert res["positional_sidechannel_risk"] == "HIGH"
    assert res["inferred_lexical_boundary"]["after"] == "Anchor Alpha"
    assert res["inferred_lexical_boundary"]["before"] == "Anchor Omega"


def test_06_positional_correlation_single_item_safety():
    single_item = [{"id": "rep_101", "title": "[REDACTED]"}]
    res = bes.GraphQLProtectedAttributeAuditor.analyze_redacted_positional_shift(
        response_items=single_item,
        target_object_id="rep_101",
        redacted_field_name="title"
    )
    assert res["positional_sidechannel_risk"] == "LOW"
    assert "Insufficient items" in res["details"]


def test_07_aliased_batching_generation():
    query = bes.GraphQLAliasedBatchingAuditor.generate_aliased_bruteforce_batch(
        operation_name="checkPin",
        param_name="pin",
        payload_list=["0001", "0002", "0003"],
        operation_type="mutation",
        selection_fields="token status",
        batch_size=2
    )
    assert query.startswith("mutation AliasedBatchBypass")
    assert "alias_0: checkPin(pin: \"0001\") { token status }" in query
    assert "alias_1: checkPin(pin: \"0002\") { token status }" in query
    assert "alias_2" not in query  # respects batch_size=2


def test_08_query_depth_lexical_computation():
    # Test query containing braces inside triple-quoted block strings, strings, and comments
    complex_query = '''
    query GetProfile {
      """
      Block string with {fake_brace}
      """
      user(bio: "Nested {fake_brace} inside string") {
        # Single line comment with {fake_nested_brace}
        profile {
          settings {
            theme
          }
        }
      }
    }
    '''
    # Real nesting: GetProfile -> user -> profile -> settings -> theme (depth 4)
    depth = bes.GraphQLQueryComplexityAuditor.compute_query_depth(complex_query)
    assert depth == 4


def test_09_csrf_content_type_audit():
    res_vulnerable = bes.GraphQLCSRFAuditor.audit_content_type_csrf_risk(
        accepted_method="GET",
        content_type="text/html",
        has_csrf_token=False
    )
    assert res_vulnerable["csrf_vulnerable"] is True
    assert res_vulnerable["risk_level"] == "HIGH"

    res_safe = bes.GraphQLCSRFAuditor.audit_content_type_csrf_risk(
        accepted_method="POST",
        content_type="application/json",
        has_csrf_token=True
    )
    assert res_safe["csrf_vulnerable"] is False
    assert res_safe["risk_level"] == "LOW"


def test_10_graphql_poc_curl_generation():
    post_poc = bes.GraphQLPoCEngine.generate_graphql_curl_poc(
        graphql_url="https://api.target.com/graphql",
        query="query { __typename }",
        variables={"env": "prod"},
        headers={"Authorization": "Bearer sample_token"},
        method="POST"
    )
    assert "curl -i -X POST" in post_poc
    assert "https://api.target.com/graphql" in post_poc
    assert "Content-Type: application/json" in post_poc
    assert "Authorization: Bearer sample_token" in post_poc
    assert "--data-raw" in post_poc

    get_poc = bes.GraphQLPoCEngine.generate_graphql_curl_poc(
        graphql_url="https://api.target.com/graphql?env=prod",
        query="query { __typename }",
        variables={"limit": 5},
        method="GET"
    )
    assert "curl -i -X GET" in get_poc
    assert "?env=prod&" in get_poc
    assert "variables=" in get_poc


def test_11_master_engine_full_audit():
    master = bes.MasterGraphQLDeepLogicEngine(target_url="https://api.target.com/graphql")
    report = asyncio.run(master.run_full_graphql_audit())
    assert report["status"] == "GRAPHQL_DEEP_LOGIC_AUDIT_COMPLETED_SUCCESSFULLY"
    assert report["generated_modules"]["introspection_bypasses_count"] == 5
    assert len(report["findings"]) == 0


if __name__ == "__main__":
    test_01_introspection_bypasses_generation()
    test_02_clairvoyance_suggestions_parsing()
    test_03_positional_correlation_payload_spec()
    test_04_positional_correlation_shift_multi_item()
    test_05_positional_correlation_multi_redacted_boundary_walk()
    test_06_positional_correlation_single_item_safety()
    test_07_aliased_batching_generation()
    test_08_query_depth_lexical_computation()
    test_09_csrf_content_type_audit()
    test_10_graphql_poc_curl_generation()
    test_11_master_engine_full_audit()
    print("ALL 11 GRAPHQL SECURITY AUDITOR TESTS PASSED 100%!")
