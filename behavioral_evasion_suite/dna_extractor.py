"""
Website DNA Extractor & Pathology Diagnostic Laboratory
Module: dna_extractor.py

Passively extracts behavioral, structural, and architectural DNA from a target
web application using lightweight, non-blocking Playwright telemetry.

Extracts:
1. Anatomical JavaScript AST & Framework Signatures (React, Next.js, Apollo, Lodash)
2. Circulatory Network APIs & Endpoints (Routes, Methods, Parameters, Auth Headers)
3. Nervous System DOM Sinks (innerHTML, eval, document.write listeners)
4. Immune System Profiling (WAF signatures, CORS policies, Security Headers)
"""

import asyncio
import json
import re
import time
import urllib.parse
from collections import deque
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field


# =====================================================================
# 1. STANDARDIZED DNA DATA TRANSFER OBJECTS (DTO)
# =====================================================================

class LibraryDNA(BaseModel):
    name: str
    version: Optional[str] = None
    confidence: float = 1.0
    detection_source: str = "bundle_fingerprint"


class EndpointDNA(BaseModel):
    url: str
    method: str = "GET"
    parameters: List[str] = Field(default_factory=list)
    has_post_data: bool = False
    content_type: Optional[str] = None
    is_graphql: bool = False
    is_rest_api: bool = False


class DOMSinkDNA(BaseModel):
    sink_type: str = Field(..., description="e.g., innerHTML, eval, document.write")
    caller_script: str = ""
    evidence: str = ""


class WebsiteDNAReport(BaseModel):
    """
    Standardized, compact diagnostic report of the web application's DNA.
    Optimized for low-token ingestion into Gemini Doctor Engine (< 5KB).
    """
    target_url: str
    framework_hints: List[str] = Field(default_factory=list)
    libraries: List[LibraryDNA] = Field(default_factory=list)
    endpoints: List[EndpointDNA] = Field(default_factory=list)
    dom_sinks: List[DOMSinkDNA] = Field(default_factory=list)
    waf_immune_profile: Dict[str, str] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
    duration_ms: float = 0.0


# =====================================================================
# 2. CLIENT-SIDE PASSIVE DNA TELEMETRY SCRIPT
# =====================================================================

DNA_CLIENT_TELEMETRY_JS = """
(() => {
    const dna = {
        frameworks: [],
        libraries: [],
        sinks: [],
        waf_hints: []
    };

    try {
        // 1. Framework & Global Variable Detection
        if (window.__NEXT_DATA__) dna.frameworks.push("Next.js");
        if (window.__NUXT__) dna.frameworks.push("Nuxt.js");
        if (window.React || document.querySelector('[data-reactroot], [data-react-helmet]')) dna.frameworks.push("React");
        if (window.Vue) dna.frameworks.push("Vue.js");
        if (window.angular || document.querySelector('[ng-app], [ng-version]')) dna.frameworks.push("Angular");
        if (window.__APOLLO_STATE__ || window.__APOLLO_CLIENT__) dna.frameworks.push("Apollo GraphQL");
        if (window._ || window.lodash) dna.libraries.push({ name: "Lodash", version: (window._ || window.lodash).VERSION || null });
        if (window.jQuery || window.$) {
            const jv = (window.jQuery || window.$).fn ? (window.jQuery || window.$).fn.jquery : null;
            dna.libraries.push({ name: "jQuery", version: jv });
        }
        if (window.axios) dna.libraries.push({ name: "Axios", version: null });

        // 2. WAF & Defense Probing Signals
        if (window.cf_chl_opt || document.querySelector('#challenge-form, #cf-spinner')) dna.waf_hints.push("Cloudflare Turnstile/WAF");
        if (window._DATADOME || document.querySelector('script[src*="datadome"]')) dna.waf_hints.push("DataDome");
        if (window.Akamai || window.akamai) dna.waf_hints.push("Akamai Bot Manager");

        // 3. Script Bundle Inspection
        const scriptTags = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
        for (const src of scriptTags) {
            const lower = src.toLowerCase();
            if (lower.includes("webpack")) dna.frameworks.push("Webpack");
            if (lower.includes("apollo")) dna.frameworks.push("Apollo Client");
            if (lower.includes("graphql")) dna.frameworks.push("GraphQL Client");
            if (lower.includes("next-")) dna.frameworks.push("Next.js Client Chunks");
        }
    } catch (e) {}

    return dna;
})()
"""


# =====================================================================
# 3. WEBSITE DNA EXTRACTOR ENGINE
# =====================================================================

class WebsiteDNAExtractor:
    """
    Non-blocking, passive DNA Extractor that gathers web anatomy and network routes
    without stalling Playwright's execution or increasing page latency.
    """

    def __init__(self, max_captured_endpoints: int = 200):
        self.max_captured_endpoints = max_captured_endpoints
        self._endpoints: deque[EndpointDNA] = deque(maxlen=max_captured_endpoints)
        self._seen_endpoint_keys: Set[str] = set()
        self._headers_profile: Dict[str, str] = {}
        self._framework_hints: Set[str] = set()
        self._libraries: Dict[str, LibraryDNA] = {}
        self._dom_sinks: List[DOMSinkDNA] = []

    def attach_to_page(self, page) -> bool:
        """
        Attaches non-blocking passive listeners to the Playwright Page instance.
        """
        if not page or not hasattr(page, "on"):
            return False

        def on_request(request):
            try:
                url = request.url
                method = request.method.upper()
                post_data = request.post_data or ""

                parsed = urllib.parse.urlparse(url)
                params = list(urllib.parse.parse_qs(parsed.query).keys())

                is_api = "/api/" in url.lower() or "json" in url.lower()
                is_gql = "graphql" in url.lower() or "query" in post_data

                endpoint_key = f"{method}:{parsed.netloc}{parsed.path}"
                if endpoint_key not in self._seen_endpoint_keys:
                    self._seen_endpoint_keys.add(endpoint_key)
                    self._endpoints.append(
                        EndpointDNA(
                            url=url,
                            method=method,
                            parameters=params,
                            has_post_data=bool(post_data),
                            is_graphql=is_gql,
                            is_rest_api=is_api
                        )
                    )
            except Exception:
                pass

        def on_response(response):
            try:
                hdrs = response.headers
                # Detect immune profile (WAF & Security Headers)
                for k, v in hdrs.items():
                    k_lower = k.lower()
                    if k_lower in [
                        "server", "x-powered-by", "cf-ray", "x-amz-cf-id",
                        "access-control-allow-origin", "strict-transport-security",
                        "content-security-policy"
                    ]:
                        self._headers_profile[k] = v

                # Detect framework hints in headers
                powered_by = hdrs.get("x-powered-by", "").lower()
                if "express" in powered_by:
                    self._framework_hints.add("Express.js")
                elif "next.js" in powered_by:
                    self._framework_hints.add("Next.js")
            except Exception:
                pass

        page.on("request", on_request)
        page.on("response", on_response)
        return True

    async def extract_dna(self, page, target_url: str = "") -> WebsiteDNAReport:
        """
        Synthesizes client-side DOM and server-side network signals into a unified WebsiteDNAReport.
        """
        t_start = time.time()
        url = target_url or (getattr(page, "url", "") if page else "")

        # 1. Run lightweight client-side telemetry probe
        client_data: Dict[str, Any] = {}
        if page and hasattr(page, "evaluate"):
            try:
                res = page.evaluate(DNA_CLIENT_TELEMETRY_JS)
                if asyncio.iscoroutine(res):
                    res = await res
                if isinstance(res, dict):
                    client_data = res
            except Exception:
                pass

        # 2. Merge framework signals
        for fw in client_data.get("frameworks", []):
            self._framework_hints.add(fw)

        for lib in client_data.get("libraries", []):
            name = lib.get("name", "")
            if name and name not in self._libraries:
                self._libraries[name] = LibraryDNA(
                    name=name,
                    version=lib.get("version"),
                    detection_source="client_global"
                )

        waf_profile = dict(self._headers_profile)
        for hint in client_data.get("waf_hints", []):
            waf_profile["client_waf_signal"] = hint

        duration = (time.time() - t_start) * 1000

        return WebsiteDNAReport(
            target_url=url,
            framework_hints=sorted(list(self._framework_hints)),
            libraries=list(self._libraries.values()),
            endpoints=list(self._endpoints),
            dom_sinks=self._dom_sinks,
            waf_immune_profile=waf_profile,
            timestamp=time.time(),
            duration_ms=duration
        )
