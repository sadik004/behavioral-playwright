"""MCP Tool definitions and execution dispatchers."""

from __future__ import annotations

import base64
import os
from typing import Any, Dict, List, Optional
from behavioral_playwright.config.settings import AutomationConfig

MCP_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "scrape_page",
        "description": "Scrapes a webpage using self-healing browser automation and returns markdown/content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to scrape"},
                "target": {"type": "string", "enum": ["links", "articles", "raw"], "default": "links"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "crawl_domain",
        "description": "Recursively crawls URLs within a domain up to a maximum page count.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Starting URL for crawl"},
                "max_pages": {"type": "integer", "default": 5},
                "depth": {"type": "integer", "default": 2},
            },
            "required": ["url"],
        },
    },
    {
        "name": "take_screenshot",
        "description": "Navigates to a URL and returns a Base64-encoded PNG screenshot for vision analysis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to screenshot"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "quant_pit_align",
        "description": "Aligns a financial SEC filing payload to prevent Point-in-Time look-ahead bias.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filing": {"type": "object", "description": "Filing metadata dictionary"},
            },
            "required": ["filing"],
        },
    },
    {
        "name": "get_provider_matrix",
        "description": "Retrieves the real-time installation and availability status of all browser and network providers.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "stealth_click",
        "description": "Performs an undetectable, human-mimetic click on a selector or (x, y) coordinates using Costello saccades, Harris-Wolpert noise, and subpixel targeting.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector to click"},
                "x": {"type": "number", "description": "X coordinate"},
                "y": {"type": "number", "description": "Y coordinate"},
                "url": {"type": "string", "description": "Optional URL to navigate to first"},
            },
        },
    },
    {
        "name": "stealth_type",
        "description": "Simulates human typing into an input element using physical QWERTY Euclidean distances and Weibull latency distributions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector to type into"},
                "text": {"type": "string", "description": "Text to type"},
            },
            "required": ["selector", "text"],
        },
    },
    {
        "name": "stealth_navigate",
        "description": "Navigates to URL with automated 3-state CAPTCHA loop protection and Shannon entropy content validation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target URL to navigate to"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "audit_biometrics",
        "description": "Evaluates kinematic or timing trajectories against empirical human reference baselines using Two-Sample KS-test, Mann-Whitney U, and Wasserstein distance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "samples": {"type": "array", "items": {"type": "number"}, "description": "Array of velocities or keystroke latencies"},
                "modality": {"type": "string", "enum": ["mouse", "keystroke"], "default": "mouse"},
            },
            "required": ["samples"],
        },
    },
    {
        "name": "memory_pid_health",
        "description": "Checks Chromium browser memory usage and calculates closed-loop PID regulation recommendations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "current_rss_mb": {"type": "number", "description": "Current process RSS in MB (optional)"},
                "target_rss_mb": {"type": "number", "default": 512.0},
            },
        },
    },
    {
        "name": "extract_metadata",
        "description": "Extracts Next.js __NEXT_DATA__, Nuxt state, JSON-LD schemas (@graph unpacked), and OpenGraph tags from a URL or current page.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target webpage URL to inspect (optional)"},
            },
        },
    },
    {
        "name": "sniff_api_responses",
        "description": "Intercepts and extracts raw JSON payloads from background XHR/Fetch API requests matching URL patterns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Optional URL to navigate to"},
                "url_patterns": {"type": "array", "items": {"type": "string"}, "description": "URL substrings/globs to match"},
                "timeout": {"type": "number", "default": 10.0, "description": "Wait timeout in seconds"},
            },
            "required": ["url_patterns"],
        },
    },
    {
        "name": "mine_google_suggest",
        "description": "Runs Google autocomplete suggestion mining and recursive A-Z alphabet drilldown.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword or query template (e.g. 'fastapi vs')"},
                "alphabet": {"type": "boolean", "default": False, "description": "Whether to run A-Z alphabet drilldown expansion"},
                "lang": {"type": "string", "default": "en", "description": "Language code (default 'en')"},
                "country": {"type": "string", "default": "us", "description": "Country code (default 'us')"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "audit_csr_drift",
        "description": "Audits Client-Side Rendering (CSR) vs Static HTML rendering drift, detecting hydration mismatches and missing SEO elements.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target webpage URL to audit live (optional)"},
                "raw_html": {"type": "string", "description": "Static/SSR HTML content string (optional)"},
                "rendered_html": {"type": "string", "description": "Hydrated/rendered DOM HTML content string (optional)"},
            },
        },
    },
    {
        "name": "mine_paa",
        "description": "Recursively mines People Also Ask (PAA) question tree from Google search SERP or provided HTML.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Seed search query to mine PAA for"},
                "depth": {"type": "integer", "default": 2, "description": "Recursion depth (1 to 5)"},
                "html": {"type": "string", "description": "Optional static SERP HTML to parse directly"},
            },
        },
    },
    {
        "name": "check_cannibalization",
        "description": "Calculates Jaccard overlap similarity between two search queries to detect keyword cannibalization and advise MERGE vs SPLIT.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query_a": {"type": "string", "description": "First comparison search query"},
                "query_b": {"type": "string", "description": "Second comparison search query"},
                "urls_a": {"type": "array", "items": {"type": "string"}, "description": "Optional explicit URLs for query A"},
                "urls_b": {"type": "array", "items": {"type": "string"}, "description": "Optional explicit URLs for query B"},
                "threshold": {"type": "number", "default": 0.40, "description": "Jaccard merge threshold (default 0.40)"},
            },
            "required": ["query_a", "query_b"],
        },
    },
    {
        "name": "linkedin_check_auth",
        "description": "Verifies whether a persistent LinkedIn storage state is authenticated and active without triggering bot detection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "storage_state": {"type": "string", "default": "linkedin_state.json", "description": "Path to exported Playwright storage state JSON"},
            },
        },
    },
    {
        "name": "linkedin_get_profile",
        "description": "Extracts current LinkedIn profile overview including name, headline, about section, and location using stealth context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "storage_state": {"type": "string", "default": "linkedin_state.json", "description": "Path to storage state JSON"},
                "profile_url": {"type": "string", "default": "https://www.linkedin.com/in/me/", "description": "LinkedIn profile URL to inspect"},
            },
        },
    },
    {
        "name": "linkedin_update_headline",
        "description": "Updates the LinkedIn user's headline using human-mimetic mouse trajectories and Weibull typing latencies.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "new_headline": {"type": "string", "description": "New professional headline text to set"},
                "storage_state": {"type": "string", "default": "linkedin_state.json", "description": "Path to storage state JSON"},
            },
            "required": ["new_headline"],
        },
    },
    {
        "name": "linkedin_update_about",
        "description": "Updates the LinkedIn user's About/Summary section with humanized interaction cadences.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "new_about": {"type": "string", "description": "New summary/about text to set"},
                "storage_state": {"type": "string", "default": "linkedin_state.json", "description": "Path to storage state JSON"},
            },
            "required": ["new_about"],
        },
    },
    {
        "name": "reddit_mine_jobs",
        "description": "Mines active high-paying Python, web scraping, and automation client hiring leads across target subreddits.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subreddits": {"type": "array", "items": {"type": "string"}, "description": "Subreddits to scan (default: forhire, webscraping, freelance_forhire)"},
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Custom intent keywords"},
                "limit_per_sub": {"type": "integer", "default": 25, "description": "Number of recent posts per subreddit to inspect"},
            },
        },
    },
    {
        "name": "reddit_analyze_lead",
        "description": "Analyzes a client lead post, diagnoses root-cause technical challenges, and drafts a high-converting technical proposal with GitHub proof.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Client job post title"},
                "selftext": {"type": "string", "default": "", "description": "Client job description text"},
                "author": {"type": "string", "default": "", "description": "Reddit author username"},
                "subreddit": {"type": "string", "default": "forhire", "description": "Source subreddit"},
                "url": {"type": "string", "default": "", "description": "URL to the post"},
                "budget_hint": {"type": "string", "description": "Extracted or provided budget hint"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "reddit_check_auth",
        "description": "Verifies whether a saved Reddit session state provides an active authenticated session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "storage_state": {"type": "string", "default": "reddit_state.json", "description": "Path to storage state JSON"},
            },
        },
    },
]


class McpToolDispatcher:
    """Dispatches MCP tool calls to the BP engine."""

    def __init__(
        self,
        bp: Optional[Any] = None,
        config: Optional[AutomationConfig] = None,
        linkedin_client: Optional[Any] = None,
        reddit_client: Optional[Any] = None,
    ) -> None:
        self._bp = bp
        self._config = config
        self._linkedin_client = linkedin_client
        self._reddit_client = reddit_client

    def _get_bp(self) -> Any:
        if self._bp is not None:
            return self._bp
        from behavioral_playwright import BP
        return BP(config=self._config)

    def _get_linkedin_client(self) -> Any:
        if self._linkedin_client is not None:
            return self._linkedin_client
        from behavioral_playwright.integrations.linkedin import LinkedInAutomationClient
        bp = self._get_bp()
        pool = getattr(bp, "pool", None) or getattr(bp, "_pool", None)
        self._linkedin_client = LinkedInAutomationClient(pool=pool)
        return self._linkedin_client

    def _get_reddit_client(self) -> Any:
        if self._reddit_client is not None:
            return self._reddit_client
        from behavioral_playwright.integrations.reddit import RedditAutomationClient
        bp = self._get_bp()
        pool = getattr(bp, "pool", None) or getattr(bp, "_pool", None)
        self._reddit_client = RedditAutomationClient(pool=pool)
        return self._reddit_client



    async def execute_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            arguments = {}
        bp = self._get_bp()
        res: Any = None

        try:
            if tool_name == "scrape_page":
                url = arguments.get("url")
                target = arguments.get("target", "links")
                if not url:
                    return {"error": "Missing required argument 'url'"}

                async with bp:
                    await bp.goto(url)
                    if target in ("links", "articles"):
                        records = await bp.extract(target=target)
                        res = [r.to_dict() if hasattr(r, "to_dict") else vars(r) for r in records]
                    else:
                        res = await bp.page.evaluate("() => document.documentElement.outerHTML")
                    return {"status": "success", "result": res}

            elif tool_name == "crawl_domain":
                url = arguments.get("url")
                max_pages = arguments.get("max_pages", 5)
                if not url:
                    return {"error": "Missing required argument 'url'"}

                async with bp:
                    records = await bp.crawl(url, max_pages=max_pages)
                    res = [r.to_dict() if hasattr(r, "to_dict") else vars(r) for r in records]
                    return {"status": "success", "result": res}

            elif tool_name == "take_screenshot":
                url = arguments.get("url")
                if not url:
                    return {"error": "Missing required argument 'url'"}

                async with bp:
                    await bp.goto(url)
                    png_bytes = await bp.screenshot()
                    b64 = base64.b64encode(png_bytes).decode("utf-8")
                    return {
                        "status": "success",
                        "mime_type": "image/png",
                        "data": b64,
                    }

            elif tool_name == "quant_pit_align":
                filing = arguments.get("filing", {})
                aligned = bp.quant.align_edgar_filing(filing)
                return {"status": "success", "result": aligned}

            elif tool_name == "get_provider_matrix":
                matrix = bp.providers.matrix()
                res = {k: {"provider": v.provider, "installed": v.installed} for k, v in matrix.items()}
                return {"status": "success", "result": res}

            elif tool_name == "stealth_click":
                selector = arguments.get("selector")
                x = arguments.get("x")
                y = arguments.get("y")
                url = arguments.get("url")

                async with bp:
                    if url:
                        await bp.goto(url)
                    if y is not None and x is not None:
                        await bp.click(x, y=y, humanize=True)
                        return {"status": "success", "action": "coordinate_click", "x": x, "y": y}
                    elif selector:
                        await bp.click(selector, humanize=True)
                        return {"status": "success", "action": "selector_click", "selector": selector}
                    return {"error": "Must provide selector or both x and y"}

            elif tool_name == "stealth_type":
                selector = arguments.get("selector")
                text = arguments.get("text", "")
                if not selector or not text:
                    return {"error": "Missing required arguments 'selector' and 'text'"}

                async with bp:
                    await bp.click(selector, humanize=True)
                    await bp.type(text, humanize=True)
                    return {"status": "success", "action": "typed", "chars": len(text)}

            elif tool_name == "stealth_navigate":
                url = arguments.get("url")
                if not url:
                    return {"error": "Missing required argument 'url'"}

                async with bp:
                    await bp.goto(url)
                    title = await bp.page.get_title()
                    loop_eval = bp.powerplay.loop_detector.record_navigation(url)
                    audit_res = bp.powerplay.audit_content_entropy(title)
                    return {
                        "status": "success",
                        "url": url,
                        "title": title,
                        "loop_evaluation": loop_eval,
                        "content_audit": audit_res,
                    }

            elif tool_name == "audit_biometrics":
                samples = arguments.get("samples", [])
                modality = arguments.get("modality", "mouse")
                if modality == "keystroke":
                    res = bp.validator.validate_keystroke_latencies(samples)
                else:
                    res = bp.validator.validate_mouse_kinematics(samples)
                return {"status": "success", "result": res}

            elif tool_name == "memory_pid_health":
                target_mb = float(arguments.get("target_rss_mb", 512.0))
                current_mb = arguments.get("current_rss_mb")
                if current_mb is None:
                    try:
                        import psutil
                        process = psutil.Process(os.getpid())
                        current_mb = float(process.memory_info().rss) / (1024.0 * 1024.0)
                    except Exception:
                        current_mb = 250.0  # Fallback nominal RSS
                else:
                    current_mb = float(current_mb)

                correction = bp.powerplay.compute_memory_adjustment(current_rss_mb=current_mb, target_rss_mb=target_mb)
                return {
                    "status": "success",
                    "current_rss_mb": round(current_mb, 2),
                    "target_rss_mb": round(target_mb, 2),
                    "regulation": correction,
                }

            elif tool_name == "extract_metadata":
                url = arguments.get("url")
                async with bp:
                    if url:
                        await bp.goto(url)
                    elif not bp.page:
                        await bp.boot()
                    next_data = await bp.mining.extract_next_data()
                    nuxt_data = await bp.mining.extract_nuxt_data()
                    json_ld = await bp.mining.extract_json_ld()
                    open_graph = await bp.mining.extract_open_graph()
                    return {
                        "status": "success",
                        "url": url or getattr(bp.page, "url", ""),
                        "next_data": next_data,
                        "nuxt_data": nuxt_data,
                        "json_ld": json_ld,
                        "open_graph": open_graph,
                    }

            elif tool_name == "sniff_api_responses":
                url = arguments.get("url")
                patterns = arguments.get("url_patterns", [])
                timeout = float(arguments.get("timeout", 10.0))
                if not patterns:
                    return {"error": "Missing required argument 'url_patterns'"}

                async with bp:
                    if not bp.page:
                        await bp.boot()
                    sniffer = bp.network.create_sniffer(bp.page)
                    if url:
                        await bp.goto(url)
                    payloads = await sniffer.intercept_json(patterns, timeout=timeout)
                    sniffer.detach()
                    return {
                        "status": "success",
                        "url_patterns": patterns,
                        "matched_payloads_count": len(payloads),
                        "payloads": payloads,
                    }

            elif tool_name == "mine_google_suggest":
                query = arguments.get("query")
                if not query:
                    return {"error": "Missing required argument 'query'"}
                alphabet = bool(arguments.get("alphabet", False))
                lang = arguments.get("lang", "en")
                country = arguments.get("country", "us")
                res = await bp.mining.mine_suggest(query=query, alphabet=alphabet, lang=lang, country=country)
                return {
                    "status": "success",
                    "result": res.model_dump() if hasattr(res, "model_dump") else res,
                }

            elif tool_name == "audit_csr_drift":
                url = arguments.get("url")
                raw_html = arguments.get("raw_html")
                rendered_html = arguments.get("rendered_html")
                if not url and (raw_html is None or rendered_html is None):
                    return {"error": "Must provide either 'url' or both 'raw_html' and 'rendered_html'"}
                report = await bp.mining.audit_csr_drift(url=url, raw_html=raw_html, rendered_html=rendered_html)
                return {
                    "status": "success",
                    "result": report.model_dump() if hasattr(report, "model_dump") else report,
                }

            elif tool_name == "mine_paa":
                query = arguments.get("query")
                html_body = arguments.get("html")
                depth = int(arguments.get("depth", 2))
                if not query and not html_body:
                    return {"error": "Must provide either 'query' or 'html'"}
                async with bp:
                    nodes = await bp.mining.mine_paa(page_or_html=html_body, query=query, max_depth=depth)
                    raw_nodes = [n.model_dump() if hasattr(n, "model_dump") else n for n in nodes]
                    return {
                        "status": "success",
                        "query": query,
                        "count": len(raw_nodes),
                        "nodes": raw_nodes,
                    }

            elif tool_name == "check_cannibalization":
                query_a = arguments.get("query_a")
                query_b = arguments.get("query_b")
                if not query_a or not query_b:
                    return {"error": "Missing required arguments 'query_a' and 'query_b'"}
                urls_a = arguments.get("urls_a")
                urls_b = arguments.get("urls_b")
                threshold = float(arguments.get("threshold", 0.40))
                report = await bp.mining.check_overlap(
                    query_a=query_a, query_b=query_b, urls_a=urls_a, urls_b=urls_b, threshold=threshold
                )
                return {
                    "status": "success",
                    "result": report.model_dump() if hasattr(report, "model_dump") else report,
                }

            elif tool_name == "linkedin_check_auth":
                storage_state = arguments.get("storage_state", "linkedin_state.json")
                client = self._get_linkedin_client()
                auth_res = await client.check_auth_status(storage_state_path=storage_state)
                return {
                    "status": "success",
                    "result": auth_res.model_dump(),
                }

            elif tool_name == "linkedin_get_profile":
                storage_state = arguments.get("storage_state", "linkedin_state.json")
                profile_url = arguments.get("profile_url", "https://www.linkedin.com/in/me/")
                client = self._get_linkedin_client()
                profile = await client.get_profile_overview(storage_state_path=storage_state, profile_url=profile_url)
                return {
                    "status": "success",
                    "result": profile.model_dump(),
                }

            elif tool_name == "linkedin_update_headline":
                new_headline = arguments.get("new_headline")
                if not new_headline:
                    return {"error": "Missing required argument 'new_headline'"}
                storage_state = arguments.get("storage_state", "linkedin_state.json")
                client = self._get_linkedin_client()
                update_res = await client.update_headline(new_headline=new_headline, storage_state_path=storage_state)
                return {
                    "status": "success" if update_res.success else "failed",
                    "result": update_res.model_dump(),
                }

            elif tool_name == "linkedin_update_about":
                new_about = arguments.get("new_about")
                if not new_about:
                    return {"error": "Missing required argument 'new_about'"}
                storage_state = arguments.get("storage_state", "linkedin_state.json")
                client = self._get_linkedin_client()
                update_res = await client.update_about(new_about=new_about, storage_state_path=storage_state)
                return {
                    "status": "success" if update_res.success else "failed",
                    "result": update_res.model_dump(),
                }

            elif tool_name == "reddit_mine_jobs":
                subreddits = arguments.get("subreddits")
                keywords = arguments.get("keywords")
                limit_per_sub = int(arguments.get("limit_per_sub", 25))
                client = self._get_reddit_client()
                leads = await client.mine_hiring_leads(
                    subreddits=subreddits,
                    keywords=keywords,
                    limit_per_sub=limit_per_sub,
                )
                return {
                    "status": "success",
                    "count": len(leads),
                    "leads": [lead.model_dump() for lead in leads],
                }

            elif tool_name == "reddit_analyze_lead":
                title = arguments.get("title")
                if not title:
                    return {"error": "Missing required argument 'title'"}
                from behavioral_playwright.models.reddit_dtos import RedditLeadDTO
                lead = RedditLeadDTO(
                    title=title,
                    selftext_snippet=arguments.get("selftext", ""),
                    author=arguments.get("author", ""),
                    subreddit=arguments.get("subreddit", "forhire"),
                    url=arguments.get("url", ""),
                    budget_hint=arguments.get("budget_hint"),
                )
                client = self._get_reddit_client()
                audit = client.analyze_lead_and_generate_pitch(lead)
                return {
                    "status": "success",
                    "analysis": audit.model_dump(),
                }

            elif tool_name == "reddit_check_auth":
                storage_state = arguments.get("storage_state", "reddit_state.json")
                client = self._get_reddit_client()
                auth_res = await client.check_auth_status(storage_state_path=storage_state)
                return {
                    "status": "success",
                    "result": auth_res.model_dump(),
                }

            return {"error": f"Unknown tool: {tool_name}"}

        except Exception as exc:
            return {"error": str(exc), "status": "failed"}

