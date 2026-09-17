# Security & Diagnostic Auditing Architecture

`behavioral-playwright` provides an enterprise-grade client-side and protocol security diagnostic engine designed for authorized testing, vulnerability research, and continuous security validation.

---

## 1. GraphQL Deep Logic Engine

The GraphQL auditing module (`behavioral_evasion_suite/graphql_security_auditor.py`) targets common and nuanced architectural flaws:

### Positional Correlation ($30,000 Gem Bug)
- **Problem**: When databases sort records by protected attributes (`ORDER BY secret_attribute ASC`) before access-control redaction is applied, the relative index position of a redacted item leaks its alphabetical position.
- **Auditor**: `GraphQLProtectedAttributeAuditor` tests sort parameters and detects relative index shifts across multi-item collections.

### Clairvoyance Schema Suggestion Reconstruction
- **Problem**: Even when `__schema` introspection is disabled, GraphQL engines return `"Did you mean ...?"` error messages on typoed queries.
- **Auditor**: `GraphQLIntrospectionAuditor.parse_clairvoyance_suggestions()` parses error strings and reconstructs the API's hidden type definitions.

### Query Complexity & DoS Depth
- **Problem**: Unbounded nested queries (`user { friends { friends { ... } } }`) can exhaust backend memory or CPU.
- **Auditor**: `GraphQLQueryComplexityAuditor` synthesizes deep queries and computes true nesting depth while ignoring braces in string literals and comments.

### Aliased Operation Batching
- **Problem**: API gateways often rate-limit based on HTTP request count rather than operations.
- **Auditor**: `GraphQLAliasedBatchingAuditor` bundles dozens of aliased queries into a single HTTP POST request.

---

## 2. SAML 2.0 & OAuth 2.0 Trust-Chain Auditors

Located in `behavioral_evasion_suite/unified_security_auditor_v5.py`:

### SAML 2.0 Trust-Chain Auditor (`SAMLTrustChainAuditor`)
- **HTTP POST & Redirect Binding Decompression**: Handles both raw Base64 XML and Deflate-compressed payloads with auto-padding.
- **Signature Exclusion**: Tests if removing `<ds:Signature>` and modifying `<NameID>` allows forged assertions to be accepted.
- **XML Signature Wrapping (XSW3)**: Injects an unsigned, forged Assertion prior to the valid signed Assertion with forged IDs.
- **RelayState Open Redirect**: Inspects `RelayState` for protocol smuggling (`//`, `javascript:`, `http://`).

### OAuth 2.0 / OIDC Logic Auditor (`OAuth2TrustChainAuditor`)
- **RFC 9700 Bypass Generator**: Synthesizes 7 redirect URI bypass vectors (subdomain bypass, path traversal, parameter injection, fragment injection, open redirect chains, localhost bypass, and scheme downgrade).
- **RFC 7636 PKCE Enforcement**: Strictly verifies that `/token` exchange requests mandate `code_verifier`.
- **Account Linking Claims**: Flags account takeover risk when identity matching relies on mutable `email` claims rather than immutable `sub` claims.

---

## 3. Dual-Context IDOR & DOM Sink Auditing

- **Dual-Context Access Control (`DualContextAuditor`)**: Replays intercepted API calls between User A and User B with semantic PII leakage detection, empty-body filtering, and bounded `deque(maxlen=500)` memory protection.
- **In-Browser DOM Sinks (`DOM_SINK_HOOK_SCRIPT`)**: Intercepts `eval`, `innerHTML`, `outerHTML`, `document.write`, `setTimeout[string]`, `setInterval[string]`, and `Function(...)`.
- **Reproducible PoC Generation (`PoCEngine`)**: Generates shell-safe, escaped cURL commands with JSON-encoded data structures.
