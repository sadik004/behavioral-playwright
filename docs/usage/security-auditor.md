# Security Auditing Usage Guide

Step-by-step guides for executing security diagnostics using `behavioral-playwright`.

---

## 1. Running a Client-Side Security Audit

```python
import asyncio
from behavioral_evasion_suite import StealthSession, UnifiedSecurityAuditorV5

async def run_audit():
    async with StealthSession() as session:
        page = session.page
        await page.goto("https://target.com/dashboard")
        
        auditor = UnifiedSecurityAuditorV5(page=page, target_url="https://target.com")
        report = await auditor.run_full_page_audit(page)
        
        print("DOM Sink Events Triggered:", len(report["captured_dom_sink_events"]))
        print("Captured API Requests:", report["captured_api_requests"])

if __name__ == "__main__":
    asyncio.run(run_audit())
```

---

## 2. Auditing GraphQL Endpoints

```python
import asyncio
from behavioral_evasion_suite import (
    MasterGraphQLDeepLogicEngine,
    GraphQLProtectedAttributeAuditor,
    GraphQLPoCEngine
)

async def audit_graphql():
    engine = MasterGraphQLDeepLogicEngine(target_url="https://target.com/graphql")
    
    # 1. Full diagnostic scan
    report = await engine.run_full_graphql_audit()
    print("GraphQL Audit Status:", report["status"])
    
    # 2. Positional correlation ($30k Gem Bug) analysis
    sample_response = [
        {"id": "obj_1", "title": "Apple"},
        {"id": "obj_2", "title": "[REDACTED]"},
        {"id": "obj_3", "title": "Banana"}
    ]
    res = GraphQLProtectedAttributeAuditor.analyze_redacted_positional_shift(
        response_items=sample_response,
        target_object_id="obj_2",
        redacted_field_name="title"
    )
    print("Positional Side-Channel Risk:", res["positional_sidechannel_risk"])
    
    # 3. Generate reproducible cURL PoC
    poc = GraphQLPoCEngine.generate_graphql_curl_poc(
        graphql_url="https://target.com/graphql",
        query="query { __schema { queryType { name } } }",
        method="POST"
    )
    print("Reproducible PoC Command:\n", poc)

if __name__ == "__main__":
    asyncio.run(audit_graphql())
```

---

## 3. Auditing SAML 2.0 & OAuth 2.0 Flows

```python
from behavioral_evasion_suite import (
    SAMLTrustChainAuditor,
    OAuth2TrustChainAuditor
)

# SAML Signature Exclusion
saml = SAMLTrustChainAuditor()
raw_xml = "<saml2:Assertion ID='_abc'><saml2:NameID>victim@target.com</saml2:NameID></saml2:Assertion>"
b64_nosig, was_modified = saml.test_signature_exclusion(raw_xml, "attacker@evil.com")
print("Signature Exclusion Payload Created:", was_modified)

# OAuth 2.0 PKCE Code Verifier Audit
oauth = OAuth2TrustChainAuditor()
token_request = {"grant_type": "authorization_code", "code": "xyz"}
pkce_res = oauth.audit_pkce_enforcement(token_request)
print("PKCE Risk:", pkce_res["risk"])
```
