# 🤖 Model Context Protocol (MCP) Server & Tool Registry Guide

> **Framework Version**: `10.0.2 Quantum Architecture`  
> **Total Active Tools**: `51 Tools (42 Modern + 9 Quantum/Legacy Compatibility)`  
> **Status**: [VERIFIED & PASSING 742 GATES]

---

## 1. Overview

Behavioral Playwright includes a high-performance **JSON-RPC 2.0 Stdio MCP Server** (`veil.mcp.server`) designed for integration with AI agents, Claude Desktop, Cursor AI, and Antigravity IDE. It exposes **51 specialized tools** covering stealth browser automation, deep crawling, OCR, RAG chunking, webhooks, search, site mapping, SEO/AEO mining, social intelligence, security auditing, and quantum evasion diagnostics.

---

## 2. Running the MCP Server

### From CLI:
```bash
# Using CLI binary
bp mcp-server

# Or direct module execution
python -m veil.mcp.server
```

### In Claude Desktop or Antigravity IDE Configuration:
Add the server to your `mcp_config.json`:

```json
{
  "mcpServers": {
    "behavioral-playwright": {
      "command": "python",
      "args": [
        "-m",
        "veil.mcp.server"
      ],
      "cwd": "E:/Scraping/behavioral-playwright-main/behavioral-playwright-main",
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONPATH": "E:/Scraping/behavioral-playwright-main/behavioral-playwright-main/src;E:/Scraping/behavioral-playwright-main/behavioral-playwright-main"
      }
    }
  }
}
```

---

## 3. Complete 51-Tool Registry Taxonomy

### A. Core Scraping, Crawling & Vision (8 Tools)
1. **`scrape_page`** / **`scrape`**: Scrapes a webpage using self-healing browser automation and returns markdown/content.
2. **`crawl`** / **`crawl_domain`**: Recursively crawls URLs within a domain with 4-tier adaptive anti-bot escalation.
3. **`search`**: Submits a search query with human-mimetic typing and extracts structured search results.
4. **`map_site`**: Maps out structural links, articles, and hierarchical page graph of a target website.
5. **`take_screenshot`**: Captures a full-page or viewport Base64 PNG screenshot for vision analysis.
6. **`stealth_open_page`**: Initializes an isolated stealth browser session with fingerprint shims.
7. **`stealth_get_snapshot`**: Extracts token-optimized DOM tree snapshot for LLM context windows.
8. **`ocr_image`**: Performs contrast-boosted OCR text extraction and watermark removal on an image file.

### B. Stealth Kinematics & Biometrics (5 Tools)
9. **`stealth_click`**: Simulates human click with cubic Bézier trajectory, overshoot, and micro-tremor.
10. **`stealth_type`**: Simulates organic keystrokes with randomized Weibull hold-times and inter-key cadences.
11. **`stealth_navigate`**: Navigates with humanized referrer trails and viewport jitter.
12. **`audit_biometrics`**: Validates kinematic trajectory authenticity via two-sample Kolmogorov-Smirnov test.
13. **`memory_pid_health`**: Inspects Chromium memory PID controller metrics to prevent heap exhaustion.

### C. Search, SEO, AEO & GEO Mining (6 Tools)
14. **`mine_google_suggest`**: Mines A-Z alphabetical search query suggestions with real-time tree drilldown.
15. **`mine_paa`**: Mines recursive People Also Ask (PAA) question-and-answer trees up to depth 5.
16. **`audit_csr_drift`**: Evaluates Client-Side Rendering (CSR) drift against raw static SSR HTML.
17. **`check_cannibalization`**: Detects SERP keyword cannibalization across competing landing pages.
18. **`audit_aio`**: Audits Google SERPs for Search Generative Experience (SGE) / AI Overview cards, citations, and brand prominence.
19. **`sniff_api_responses`**: Intercepts background JSON/REST API payloads triggered by user interactions.

### D. Social Media & B2B Intelligence (7 Tools)
20. **`linkedin_check_auth`**: Validates whether the active browser session has authenticated LinkedIn cookies.
21. **`linkedin_get_profile`**: Extracts structured public profile data (experience, education, skills).
22. **`linkedin_update_headline`**: Updates user headline with verification sentinels.
23. **`linkedin_update_about`**: Updates profile about/summary section safely.
24. **`reddit_mine_jobs`**: Mines hiring subreddits for remote engineering and freelance leads.
25. **`reddit_analyze_lead`**: Scores sentiment, budget indicators, and contact details from Reddit posts.
26. **`reddit_check_auth`**: Validates Reddit session state and karma metrics.

### E. Agentic Workflow Orchestration (7 Tools)
27. **`execute_workflow`**: Runs a declarative multi-step JSON workflow with precondition verification.
28. **`inspect_state`**: Retrieves session runtime state, cookies, variables, and step history.
29. **`workflow_navigate`**: Dispatches a step-level navigation with SLA timeouts.
30. **`workflow_resolve`**: Resolves an element using multi-tier selector engines (Exact ➔ Semantic ➔ Fuzzy).
31. **`workflow_extract`**: Extracts targeted text, links, attributes, or tables from matched DOM elements.
32. **`workflow_search`**: Searches interactive DOM nodes via visual and text queries.
33. **`workflow_verify`**: Asserts postconditions on page state before proceeding.

### F. Deep Security Auditing (2 Tools)
34. **`run_graphql_security_audit`**: Audits GraphQL endpoints for introspection leaks, batching attacks, and CSRF vulnerabilities.
35. **`run_security_audit_on_page`**: Runs passive OWASP Top 10 client-side audit on live DOM.

### G. Financial Precision & System Diagnostics (3 Tools)
36. **`quant_pit_align`**: Aligns SEC Edgar filings to eliminate Point-in-Time look-ahead bias in financial ML models.
37. **`get_provider_matrix`**: Probes availability of Playwright, Patchright, Undetected Chromedriver, and curl_cffi.
38. **`extract_metadata`**: Extracts OpenGraph, Twitter Cards, Schema.org JSON-LD, and meta tags.

### H. Quantum Evasion & Diagnostic Suite (6 Tools)
39. **`module_shield_status`**: Inspects real-time operational status, integrity, and readiness of all 31 stealth evasion shields.
40. **`module_persona_profile`**: Inspects hardware persona matrix, WebGL parameters, audio latency, and DirectWrite font profiles.
41. **`module_kinematic_eval`**: Evaluates and simulates biometric mouse saccade paths, Weibull keystroke plans, or Newtonian scroll physics.
42. **`stealth_human_action`**: Performs human biometric actions (click, type, scroll, hover, pause) on active session elements.
43. **`stealth_extract_data`**: Extracts structured text or table data while automatically filtering out honeypot trap elements.
44. **`stealth_close_session`**: Closes a specific active browser session and releases associated memory.

### I. RAG, Extraction & Webhook Delivery (2 Tools)
45. **`rag_chunk`**: Splits markdown into token-budgeted chunks with H1>H2>H3 breadcrumbs and lexical cohesion boundaries.
46. **`trigger_webhook`**: Sends a JSON payload to an external webhook endpoint (e.g. n8n workflow, Slack, Discord).

### J. Legacy & Standalone Automation Aliases (5 Tools)
47. **`human_interact`**: High-level human-mimetic biometric interaction with natural physics, micro-jitter, and cognitive delays.
48. **`stealth_fetch`**: Fetches a URL using stealth browser automation with 31 evasion shields and returns page text, markdown, or HTML.
49. **`generate_stealth_script`**: Generates a complete, autonomous Python script using BP with full stealth evasion.
50. **`crawl`**: Explicit alias for `crawl_domain` with depth and page constraints.
51. **`scrape`**: Explicit alias for `scrape_page` with target selectors.

---

## 4. Programmatic Tool Dispatcher Example

```python
import asyncio
from veil.mcp.server import McpServer

async def main():
    server = McpServer()
    
    # Execute tool directly via JSON-RPC dispatcher
    response = await server.handle_request({
        "jsonrpc": "2.0",
        "id": "req-1",
        "method": "tools/call",
        "params": {
            "name": "scrape_page",
            "arguments": {
                "url": "https://news.ycombinator.com",
                "target": "links"
            }
        }
    })
    
    print("Tool Output:", response["result"]["content"][0]["text"])

if __name__ == "__main__":
    asyncio.run(main())
```
