"""
Server-Side Prototype Pollution (SSPP) Black-Box Security Engine (Hardened v5.0 Enterprise)
===========================================================================================
A production-grade, stateful Async Playwright & API security auditor for Server-Side 
Prototype Pollution (SSPP) in Node.js / Express / Fastify / Next.js environments.

Technical Grounding & Standards:
1. PortSwigger Web Security Research: Server-Side Prototype Pollution (Gareth Heyes, 2022)
   - Safe Detection via Express 'json spaces' response formatting mutation.
   - Error status code mutation via http-errors with differential baseline calibration.
2. YesWeHack Research: Prototype Pollution in Node.js Applications (2021-2023)
   - CORS Access-Control-Expose-Headers differential header inspection.
   - Query String parser (qs / express) parameter matrix.
3. Clean Architecture & Resilience Standards:
   - Strict Pydantic DTO data boundaries (Zero raw untyped dict escape).
   - Dynamic Differential Baseline calibration (Eliminating false positives).
   - Safe Reversion & Cleanup Protocol (Preventing persistent process contamination).
   - AWS Full-Jitter Exponential Backoff on rate-limiting (HTTP 429/503).
   - Non-blocking Playwright request sniffing.
"""

import asyncio
import json
import random
import re
import shlex
import time
import urllib.parse
from collections import deque
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field


# =====================================================================
# 1. CLEAN ARCHITECTURE PYDANTIC DTO SCHEMAS
# =====================================================================

class CapturedAPIRequest(BaseModel):
    """Structured DTO for network requests captured via Playwright."""
    url: str
    method: str = "GET"
    post_data: str = ""
    timestamp: float = Field(default_factory=time.time)


class SSPPFinding(BaseModel):
    """Structured, type-safe security vulnerability finding."""
    finding_type: str = Field(..., description="Vulnerability classification identifier")
    url: str
    method: str = "POST"
    technique: str
    evidence: str
    curl_poc: str
    remediated: bool = Field(False, description="Whether safe rollback payload was executed")
    timestamp: float = Field(default_factory=time.time)


class SSPPScanResult(BaseModel):
    """Comprehensive scan outcome and telemetry DTO."""
    target_url: str
    is_vulnerable: bool = False
    probes_executed: int = 0
    findings: List[SSPPFinding] = Field(default_factory=list)
    baseline_status: Optional[int] = None
    baseline_error: Optional[str] = None
    duration_ms: float = 0.0


# =====================================================================
# 2. SAFE PAYLOAD GENERATOR & REVERSION REGISTRY
# =====================================================================

class SSPPPayloadGenerator:
    """
    Generates non-destructive, safe SSPP detection & remediation rollback payloads
    across JSON body, query parameters, and form-urlencoded encodings.
    """

    @staticmethod
    def get_json_space_payloads(spaces: int = 10) -> List[Dict[str, Any]]:
        return [
            {"__proto__": {"json spaces": spaces}},
            {"constructor": {"prototype": {"json spaces": spaces}}},
            {"__proto__": {"json spaces": str(spaces)}},
        ]

    @staticmethod
    def get_json_space_reversion_payloads() -> List[Dict[str, Any]]:
        """Safe rollback payloads to restore default server JSON formatting."""
        return [
            {"__proto__": {"json spaces": 0}},
            {"constructor": {"prototype": {"json spaces": 0}}},
        ]

    @staticmethod
    def get_exposed_headers_payloads(header_name: str = "x-pp-proof") -> List[Dict[str, Any]]:
        return [
            {"__proto__": {"exposedHeaders": [header_name]}},
            {"constructor": {"prototype": {"exposedHeaders": [header_name]}}},
        ]

    @staticmethod
    def get_status_code_payloads(status_code: int = 510) -> List[Dict[str, Any]]:
        return [
            {"__proto__": {"status": status_code}},
            {"constructor": {"prototype": {"status": status_code}}},
        ]

    @staticmethod
    def get_status_code_reversion_payloads(original_status: int = 400) -> List[Dict[str, Any]]:
        """Safe rollback payloads to restore default error handler status."""
        return [
            {"__proto__": {"status": original_status}},
            {"constructor": {"prototype": {"status": original_status}}},
        ]

    @staticmethod
    def get_query_string_payloads(property_name: str = "json spaces", value: Any = 10) -> List[str]:
        encoded_prop = urllib.parse.quote(property_name)
        encoded_val = urllib.parse.quote(str(value))
        return [
            f"__proto__[{encoded_prop}]={encoded_val}",
            f"__proto__%5B{encoded_prop}%5D={encoded_val}",
            f"__proto__.{encoded_prop}={encoded_val}",
            f"constructor[prototype][{encoded_prop}]={encoded_val}",
            f"constructor%5Bprototype%5D%5B{encoded_prop}%5D={encoded_val}",
            f"constructor.prototype.{encoded_prop}={encoded_val}",
        ]

    @staticmethod
    def get_form_urlencoded_payloads(property_name: str = "json spaces", value: Any = 10) -> List[str]:
        encoded_prop = urllib.parse.quote_plus(property_name)
        encoded_val = urllib.parse.quote_plus(str(value))
        return [
            f"__proto__[{encoded_prop}]={encoded_val}",
            f"__proto__%5B{encoded_prop}%5D={encoded_val}",
            f"__proto__.{encoded_prop}={encoded_val}",
            f"constructor[prototype][{encoded_prop}]={encoded_val}",
            f"constructor%5Bprototype%5D%5B{encoded_prop}%5D={encoded_val}"
        ]


# =====================================================================
# 3. DIFFERENTIAL RESPONSE ANALYZER (ZERO FALSE-POSITIVE ENGINE)
# =====================================================================

class SSPPResponseAnalyzer:
    """
    Differential analysis engine: Strictly verifies mutations against true pre-probe baselines.
    """

    @staticmethod
    def is_valid_json(content: str) -> bool:
        """Validates that a string is syntactically valid JSON (filtering out HTML / stack traces)."""
        if not content or not content.strip():
            return False
        try:
            json.loads(content)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def analyze_json_spaces(
        baseline_body: str,
        probe_body: str,
        expected_spaces: int = 10
    ) -> bool:
        """
        Detects Express 'json spaces' mutation. Requires probe body to be valid JSON
        to eliminate false positives from pre-formatted HTML stack traces.
        """
        if not probe_body or not baseline_body:
            return False

        # Prevent HTML/Stack trace false positives: Must be valid JSON
        if not SSPPResponseAnalyzer.is_valid_json(probe_body):
            return False

        indent_pattern = r'\r?\n' + (' ' * expected_spaces) + r'\S'
        has_probe_indent = bool(re.search(indent_pattern, probe_body))
        has_base_indent = bool(re.search(indent_pattern, baseline_body))

        return has_probe_indent and not has_base_indent

    @staticmethod
    def analyze_exposed_headers(
        baseline_headers: Dict[str, Any],
        probe_headers: Dict[str, Any],
        header_name: str = "x-pp-proof"
    ) -> bool:
        """
        Performs differential CORS analysis: Ensures the test header was not already exposed
        in the baseline before declaring vulnerability.
        """
        def extract_exposed(hdrs: Dict[str, Any]) -> Set[str]:
            lower_hdrs = {str(k).lower(): str(v).lower() for k, v in hdrs.items()}
            raw = lower_hdrs.get("access-control-expose-headers", "")
            if not raw:
                return set()
            return {h.strip() for h in raw.split(",")}

        base_set = extract_exposed(baseline_headers)
        probe_set = extract_exposed(probe_headers)

        target = header_name.lower()
        # Must appear in probe response and must NOT have existed in baseline
        return (target in probe_set) and (target not in base_set) and ("*" not in base_set)

    @staticmethod
    def analyze_status_mutation(
        measured_malformed_baseline_status: int,
        probe_trigger_status: int,
        expected_status: int = 510
    ) -> bool:
        """
        Differential status mutation: Verifies that the malformed trigger response
        mutated to expected_status strictly away from the measured baseline status.
        """
        return (
            probe_trigger_status == expected_status
            and measured_malformed_baseline_status != expected_status
        )


# =====================================================================
# 4. MASTER SSPP BLACK-BOX AUDITOR
# =====================================================================

class SSPPBlackBoxAuditor:
    """
    Production-grade SSPP Auditor with differential baseline calibration,
    safe reversion, AWS Full-Jitter Backoff, and Playwright session binding.
    """

    def __init__(self, target_url: str = "", max_captured_requests: int = 500):
        self.target_url = target_url
        self.captured_requests: deque[CapturedAPIRequest] = deque(maxlen=max_captured_requests)
        self.findings: List[SSPPFinding] = []
        self._finding_hashes: Set[str] = set()

    def log_finding(
        self,
        finding_type: str,
        url: str,
        method: str,
        technique: str,
        evidence: str,
        poc: str,
        remediated: bool = False
    ) -> SSPPFinding:
        finding = SSPPFinding(
            finding_type=finding_type,
            url=url,
            method=method,
            technique=technique,
            evidence=evidence,
            curl_poc=poc,
            remediated=remediated,
            timestamp=time.time()
        )
        f_hash = f"{finding_type}:{url}:{method}:{technique}"
        if f_hash not in self._finding_hashes:
            self._finding_hashes.add(f_hash)
            self.findings.append(finding)
        return finding

    @staticmethod
    def generate_curl_poc(
        url: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        body: Any = None
    ) -> str:
        """Generates shell-safe, reproducible cURL proof-of-concept command."""
        method_upper = str(method or "POST").upper()
        hdrs = dict(headers or {})

        # Standardize Content-Type for payload-bearing methods
        if method_upper in ["POST", "PUT", "PATCH"]:
            has_ct = any(k.lower() == "content-type" for k in hdrs)
            if not has_ct:
                hdrs["Content-Type"] = "application/json"

        curl_cmd = ["curl", "-i", "-X", method_upper, url]

        for k, v in hdrs.items():
            if k.lower() not in ["host", "content-length"]:
                curl_cmd.extend(["-H", f"{k}: {v}"])

        if body is not None and method_upper != "GET":
            if isinstance(body, (dict, list)):
                body_str = json.dumps(body)
            else:
                body_str = str(body)
            curl_cmd.extend(["--data-raw", body_str])

        return " ".join(shlex.quote(arg) for arg in curl_cmd)

    async def _fetch_with_backoff(
        self,
        request_context,
        url: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        max_retries: int = 3
    ):
        """
        Executes HTTP fetch with AWS Full-Jitter Exponential Backoff on 429/503.
        """
        base_delay = 0.5
        max_delay = 4.0

        for attempt in range(max_retries + 1):
            try:
                fetch_kwargs: Dict[str, Any] = {"method": method}
                if headers:
                    fetch_kwargs["headers"] = headers
                if data is not None:
                    fetch_kwargs["data"] = data

                res = await request_context.fetch(url, **fetch_kwargs)
                if res.status in (429, 503) and attempt < max_retries:
                    # Full Jitter formula: sleep = random(0, min(max_delay, base_delay * 2^attempt))
                    ceiling = min(max_delay, base_delay * (2 ** attempt))
                    jitter_sleep = random.uniform(0.1, ceiling)
                    await asyncio.sleep(jitter_sleep)
                    continue
                return res
            except asyncio.CancelledError:
                raise
            except Exception:
                if attempt == max_retries:
                    raise
                await asyncio.sleep(0.3)
        raise RuntimeError(f"Failed to fetch {url} after {max_retries} retries")

    # -----------------------------------------------------------------
    # Playwright Integration: Passive Sniffer & Scoped Router
    # -----------------------------------------------------------------

    def attach_passive_sniffer(self, page) -> bool:
        """
        Attaches non-blocking request sniffer via Playwright event listener.
        Zero overhead: Does not hijack routing or stall page execution.
        """
        if not page or not hasattr(page, "on"):
            return False

        def on_request(request):
            try:
                url = request.url
                method = request.method
                post_data = request.post_data or ""

                if "/api" in url.lower() or "json" in url.lower() or post_data:
                    self.captured_requests.append(
                        CapturedAPIRequest(url=url, method=method, post_data=post_data)
                    )
            except Exception:
                pass

        page.on("request", on_request)
        return True

    async def attach_scoped_router(self, page, api_glob: str = "**/api/**") -> bool:
        """
        Attaches scoped router strictly targeting API endpoints.
        Bypasses static assets to preserve bandwidth and heap memory.
        """
        if not page or not hasattr(page, "route"):
            return False

        async def handle_api_route(route, request=None):
            try:
                req = request or (route.request if hasattr(route, "request") else route)
                url = getattr(req, "url", "")
                method = getattr(req, "method", "GET")
                post_data = getattr(req, "post_data", "") or ""

                self.captured_requests.append(
                    CapturedAPIRequest(url=url, method=method, post_data=post_data)
                )
            finally:
                try:
                    res = route.continue_()
                    if asyncio.iscoroutine(res):
                        await res
                except Exception:
                    pass

        try:
            res = page.route(api_glob, handle_api_route)
            if asyncio.iscoroutine(res):
                await res
            return True
        except Exception:
            return False

    async def attach_to_playwright(self, bp_session=None, page=None, passive: bool = True) -> bool:
        """
        Unified Playwright attachment method for behavioral-playwright.
        Defaults to passive non-blocking request sniffing; falls back to scoped routing if requested.
        """
        active_page = page or getattr(bp_session, "page", None) or (bp_session if hasattr(bp_session, "route") else None)
        if not active_page:
            return False
        if passive:
            return self.attach_passive_sniffer(active_page)
        return await self.attach_scoped_router(active_page)

    # -----------------------------------------------------------------
    # Active Audit Probing Suites
    # -----------------------------------------------------------------

    async def audit_json_endpoint_active(
        self,
        request_context,
        url: str,
        method: str = "POST"
    ) -> SSPPScanResult:
        """
        Audits JSON endpoint using strictly calibrated differential baselines
        and dispatches immediate cleanup payloads upon confirmed pollution.
        """
        t_start = time.time()
        findings: List[SSPPFinding] = []
        probes_executed = 0

        # Step 1: Capture True Baselines (Normal + Malformed JSON Error)
        try:
            base_res = await self._fetch_with_backoff(
                request_context, url, method=method,
                headers={"Content-Type": "application/json"},
                data=json.dumps({"test_baseline": 1})
            )
            base_status = base_res.status
            base_body = await base_res.text()
            base_headers = dict(base_res.headers)

            # Measure true malformed baseline to prevent 510 False Positives
            malformed_base_res = await self._fetch_with_backoff(
                request_context, url, method=method,
                headers={"Content-Type": "application/json"},
                data='{"__malformed_baseline_check__":'
            )
            true_malformed_status = malformed_base_res.status
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return SSPPScanResult(
                target_url=url,
                is_vulnerable=False,
                baseline_error=str(e),
                duration_ms=(time.time() - t_start) * 1000
            )

        # -------------------------------------------------------------
        # Technique 1: Express 'json spaces' formatting mutation
        # -------------------------------------------------------------
        for probe in SSPPPayloadGenerator.get_json_space_payloads(10):
            probes_executed += 1
            try:
                probe_res = await self._fetch_with_backoff(
                    request_context, url, method=method,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(probe)
                )
                probe_body = await probe_res.text()

                if SSPPResponseAnalyzer.analyze_json_spaces(base_body, probe_body, 10):
                    # Remediation: Immediately reset json spaces to 0
                    remediated = False
                    for rev_payload in SSPPPayloadGenerator.get_json_space_reversion_payloads():
                        try:
                            await self._fetch_with_backoff(
                                request_context, url, method=method,
                                headers={"Content-Type": "application/json"},
                                data=json.dumps(rev_payload)
                            )
                            remediated = True
                        except Exception:
                            pass

                    poc = self.generate_curl_poc(url, method, {"Content-Type": "application/json"}, probe)
                    finding = self.log_finding(
                        "SSPP_JSON_SPACES_VULNERABILITY", url, method,
                        "Express json spaces prototype pollution (PortSwigger Research)",
                        "JSON response formatting mutated to 10 spaces indentation",
                        poc, remediated=remediated
                    )
                    findings.append(finding)
                    break
            except asyncio.CancelledError:
                raise
            except Exception:
                continue

        # -------------------------------------------------------------
        # Technique 2: CORS Access-Control-Expose-Headers pollution
        # -------------------------------------------------------------
        for probe in SSPPPayloadGenerator.get_exposed_headers_payloads("x-pp-proof"):
            probes_executed += 1
            try:
                probe_res = await self._fetch_with_backoff(
                    request_context, url, method=method,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(probe)
                )
                probe_headers = dict(probe_res.headers)

                if SSPPResponseAnalyzer.analyze_exposed_headers(base_headers, probe_headers, "x-pp-proof"):
                    poc = self.generate_curl_poc(url, method, {"Content-Type": "application/json"}, probe)
                    finding = self.log_finding(
                        "SSPP_CORS_EXPOSED_HEADERS", url, method,
                        "CORS exposedHeaders prototype pollution (YesWeHack Research)",
                        "Access-Control-Expose-Headers reflected injected x-pp-proof header",
                        poc, remediated=False
                    )
                    findings.append(finding)
                    break
            except asyncio.CancelledError:
                raise
            except Exception:
                continue

        # -------------------------------------------------------------
        # Technique 3: Status Code Mutation with calibrated error baseline
        # -------------------------------------------------------------
        for probe in SSPPPayloadGenerator.get_status_code_payloads(510):
            probes_executed += 1
            try:
                # Dispatch status pollution probe
                await self._fetch_with_backoff(
                    request_context, url, method=method,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(probe)
                )

                # Trigger error handler with malformed payload
                trigger_res = await self._fetch_with_backoff(
                    request_context, url, method=method,
                    headers={"Content-Type": "application/json"},
                    data='{"__trigger_check__":'
                )
                trigger_status = trigger_res.status

                if SSPPResponseAnalyzer.analyze_status_mutation(true_malformed_status, trigger_status, 510):
                    # Remediation: Reset status property back to baseline status
                    remediated = False
                    for rev_payload in SSPPPayloadGenerator.get_status_code_reversion_payloads(true_malformed_status):
                        try:
                            await self._fetch_with_backoff(
                                request_context, url, method=method,
                                headers={"Content-Type": "application/json"},
                                data=json.dumps(rev_payload)
                            )
                            remediated = True
                        except Exception:
                            pass

                    poc = self.generate_curl_poc(url, method, {"Content-Type": "application/json"}, probe)
                    finding = self.log_finding(
                        "SSPP_STATUS_CODE_MUTATION", url, method,
                        "http-errors status code prototype pollution (PortSwigger Research)",
                        f"Error status mutated from {true_malformed_status} to 510 Not Extended",
                        poc, remediated=remediated
                    )
                    findings.append(finding)
                    break
            except asyncio.CancelledError:
                raise
            except Exception:
                continue

        duration = (time.time() - t_start) * 1000
        return SSPPScanResult(
            target_url=url,
            is_vulnerable=len(findings) > 0,
            probes_executed=probes_executed,
            findings=findings,
            baseline_status=base_status,
            duration_ms=duration
        )

    async def audit_query_params_active(self, request_context, url: str) -> SSPPScanResult:
        """Audits URL query parameters using differential JSON spaces analysis."""
        t_start = time.time()
        findings: List[SSPPFinding] = []
        probes_executed = 0

        try:
            base_res = await self._fetch_with_backoff(request_context, url, method="GET")
            base_status = base_res.status
            base_body = await base_res.text()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return SSPPScanResult(
                target_url=url,
                is_vulnerable=False,
                baseline_error=str(e),
                duration_ms=(time.time() - t_start) * 1000
            )

        for query_payload in SSPPPayloadGenerator.get_query_string_payloads("json spaces", 10):
            probes_executed += 1
            try:
                delimiter = "&" if "?" in url else "?"
                target_qs_url = f"{url}{delimiter}{query_payload}"
                probe_res = await self._fetch_with_backoff(request_context, target_qs_url, method="GET")
                probe_body = await probe_res.text()

                if SSPPResponseAnalyzer.analyze_json_spaces(base_body, probe_body, 10):
                    # Remediation: Immediately reset json spaces via query string rollback
                    remediated = False
                    try:
                        revert_url = f"{url}{delimiter}__proto__[json%20spaces]=0"
                        await self._fetch_with_backoff(request_context, revert_url, method="GET")
                        remediated = True
                    except Exception:
                        pass

                    poc = self.generate_curl_poc(target_qs_url, "GET")
                    finding = self.log_finding(
                        "SSPP_QUERY_PARAM_VULNERABILITY", target_qs_url, "GET",
                        "URL Query String Prototype Pollution (qs / express research)",
                        "Query parameter polluted json spaces formatting",
                        poc, remediated=remediated
                    )
                    findings.append(finding)
                    break
            except asyncio.CancelledError:
                raise
            except Exception:
                continue

        return SSPPScanResult(
            target_url=url,
            is_vulnerable=len(findings) > 0,
            probes_executed=probes_executed,
            findings=findings,
            baseline_status=base_status,
            duration_ms=(time.time() - t_start) * 1000
        )

    async def audit_form_urlencoded_active(self, request_context, url: str) -> SSPPScanResult:
        """Audits x-www-form-urlencoded body parsing using differential analysis."""
        t_start = time.time()
        findings: List[SSPPFinding] = []
        probes_executed = 0

        try:
            base_res = await self._fetch_with_backoff(
                request_context, url, method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data="test_baseline=1"
            )
            base_status = base_res.status
            base_body = await base_res.text()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return SSPPScanResult(
                target_url=url,
                is_vulnerable=False,
                baseline_error=str(e),
                duration_ms=(time.time() - t_start) * 1000
            )

        for form_payload in SSPPPayloadGenerator.get_form_urlencoded_payloads("json spaces", 10):
            probes_executed += 1
            try:
                probe_res = await self._fetch_with_backoff(
                    request_context, url, method="POST",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data=form_payload
                )
                probe_body = await probe_res.text()

                if SSPPResponseAnalyzer.analyze_json_spaces(base_body, probe_body, 10):
                    # Remediation: Immediately reset json spaces via form rollback
                    remediated = False
                    try:
                        revert_data = "__proto__[json+spaces]=0"
                        await self._fetch_with_backoff(
                            request_context, url, method="POST",
                            headers={"Content-Type": "application/x-www-form-urlencoded"},
                            data=revert_data
                        )
                        remediated = True
                    except Exception:
                        pass

                    poc = self.generate_curl_poc(
                        url, "POST",
                        {"Content-Type": "application/x-www-form-urlencoded"},
                        form_payload
                    )
                    finding = self.log_finding(
                        "SSPP_FORM_URLENCODED_VULNERABILITY", url, "POST",
                        "Body-Parser x-www-form-urlencoded Prototype Pollution",
                        "Form body parameter polluted json spaces formatting",
                        poc, remediated=remediated
                    )
                    findings.append(finding)
                    break
            except asyncio.CancelledError:
                raise
            except Exception:
                continue

        return SSPPScanResult(
            target_url=url,
            is_vulnerable=len(findings) > 0,
            probes_executed=probes_executed,
            findings=findings,
            baseline_status=base_status,
            duration_ms=(time.time() - t_start) * 1000
        )

    async def audit_endpoint(
        self,
        request_context,
        url: str,
        method: str = "AUTO"
    ) -> SSPPScanResult:
        """
        Unified polymorphic audit orchestrator: Dynamically dispatches to JSON, Query, or Form audit
        based on HTTP method or URL structure.
        """
        method_upper = str(method or "AUTO").upper()
        if method_upper == "AUTO":
            method_upper = "GET" if "?" in url else "POST"

        if method_upper == "GET":
            return await self.audit_query_params_active(request_context, url)
        elif method_upper in ["POST", "PUT", "PATCH"]:
            return await self.audit_json_endpoint_active(request_context, url, method=method_upper)
        else:
            return await self.audit_json_endpoint_active(request_context, url, method="POST")

    async def audit_endpoints_batch(
        self,
        request_context,
        endpoints: List[Dict[str, str]],
        max_concurrency: int = 3
    ) -> List[SSPPScanResult]:
        """
        Executes bounded concurrent audits across multiple endpoints using asyncio.Semaphore.
        Prevents server overwhelm while maximizing auditing velocity.
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _bounded_audit(ep: Dict[str, str]) -> SSPPScanResult:
            async with semaphore:
                u = ep.get("url", "")
                m = ep.get("method", "AUTO")
                return await self.audit_endpoint(request_context, u, method=m)

        tasks = [_bounded_audit(ep) for ep in endpoints if ep.get("url")]
        return await asyncio.gather(*tasks)


# =====================================================================
# 5. AUTOMATED VERIFICATION TEST SUITE
# =====================================================================

if __name__ == "__main__":
    print("=== Testing Hardened SSPP Black-Box Security Engine (v5.0 Enterprise) ===")
    auditor = SSPPBlackBoxAuditor(target_url="https://api.target.com/v1/profile")

    # Gate 1: Pydantic DTO Serialization & Type-Safety
    sample_finding = auditor.log_finding(
        finding_type="SSPP_JSON_SPACES_VULNERABILITY",
        url="https://api.target.com/v1/profile",
        method="POST",
        technique="Express json spaces mutation",
        evidence="10 space indentation detected in valid JSON response",
        poc="curl -i -X POST https://api.target.com/v1/profile",
        remediated=True
    )
    assert isinstance(sample_finding, SSPPFinding), "Finding must be an instance of SSPPFinding DTO"
    dumped = sample_finding.model_dump()
    assert dumped["remediated"] is True and dumped["method"] == "POST"
    print("1. Pydantic DTO Schema & Validation Test: PASSED")

    # Gate 2: True JSON Verification (Filtering HTML/Stack Trace False Positives)
    html_error_with_indent = "<html>\n          <body>Internal Server Error: Stack Trace</body>\n</html>"
    base_json = '{"status": "ok"}'
    false_positive_check = SSPPResponseAnalyzer.analyze_json_spaces(base_json, html_error_with_indent, 10)
    assert false_positive_check is False, "HTML stack trace must NOT trigger JSON spaces mutation"
    
    valid_polluted_json = '{\r\n          "status": "ok",\r\n          "code": 200\r\n}'
    true_positive_check = SSPPResponseAnalyzer.analyze_json_spaces(base_json, valid_polluted_json, 10)
    assert true_positive_check is True, "Valid formatted JSON must correctly trigger mutation"
    print("2. Differential JSON Indentation & HTML Filtering Test: PASSED")

    # Gate 3: Differential Baseline CORS Header Check
    baseline_cors = {"Access-Control-Expose-Headers": "Authorization, X-Custom-Header"}
    probe_cors_hit = {"Access-Control-Expose-Headers": "Authorization, X-Custom-Header, x-pp-proof"}
    probe_cors_false_pos = {"Access-Control-Expose-Headers": "Authorization, X-Custom-Header"}
    
    assert SSPPResponseAnalyzer.analyze_exposed_headers(baseline_cors, probe_cors_hit, "x-pp-proof") is True
    assert SSPPResponseAnalyzer.analyze_exposed_headers(baseline_cors, probe_cors_false_pos, "x-pp-proof") is False
    print("3. Differential CORS Header Baseline Calibration Test: PASSED")

    # Gate 4: Differential Error Status Mutation Check
    # Scenario A: Server naturally returns 510 on malformed JSON (Must NOT report vulnerability!)
    is_vuln_when_baseline_510 = SSPPResponseAnalyzer.analyze_status_mutation(510, 510, 510)
    assert is_vuln_when_baseline_510 is False, "Status 510 in baseline must reject false positive"
    
    # Scenario B: Server naturally returns 400, but mutates to 510 after probe
    is_vuln_when_baseline_400 = SSPPResponseAnalyzer.analyze_status_mutation(400, 510, 510)
    assert is_vuln_when_baseline_400 is True, "Status mutation from 400 to 510 must detect vulnerability"
    print("4. Differential Error Status Calibration Test: PASSED")

    # Gate 5: Reversion Payload Integrity
    rev_spaces = SSPPPayloadGenerator.get_json_space_reversion_payloads()
    rev_status = SSPPPayloadGenerator.get_status_code_reversion_payloads(400)
    assert len(rev_spaces) == 2 and rev_spaces[0]["__proto__"]["json spaces"] == 0
    assert len(rev_status) == 2 and rev_status[0]["__proto__"]["status"] == 400
    print("5. Anti-DoS Reversion & Safe Rollback Matrix Test: PASSED")

    # Gate 6: Multi-Method cURL PoC Generation (POST, PUT, PATCH, GET)
    put_poc = SSPPBlackBoxAuditor.generate_curl_poc("https://api.target.com/user/1", "PUT", body={"__proto__": {"test": 1}})
    assert "Content-Type: application/json" in put_poc and "-X PUT" in put_poc
    get_poc = SSPPBlackBoxAuditor.generate_curl_poc("https://api.target.com/user/1?__proto__[a]=1", "GET")
    assert "Content-Type" not in get_poc and "-X GET" in get_poc
    print("6. Shell-Safe Multi-Method cURL PoC Generation Test: PASSED")

    # Gate 7: Unified Playwright Attachment & CapturedAPIRequest Validation
    class DummyPage:
        def __init__(self):
            self.events = {}
        def on(self, event, cb):
            self.events[event] = cb

    dummy_page = DummyPage()
    attach_ok = asyncio.run(auditor.attach_to_playwright(page=dummy_page, passive=True))
    assert attach_ok is True and "request" in dummy_page.events
    print("7. Unified Playwright Attachment & Non-Blocking Sniffer Test: PASSED")

    print("\n=== ALL 7 QUALITY & RESILIENCE GATES PASSED CLEANLY (v5.0 Enterprise) ===")

# =====================================================================
# 6. MASTER ENTERPRISE ENGINE (SECURITY AUDITOR PROTOCOL COMPLIANT)
# =====================================================================

try:
    from .security_protocol import BaseSecurityAuditor, SecurityFinding, AuditResultDTO
except ImportError:
    try:
        from security_protocol import BaseSecurityAuditor, SecurityFinding, AuditResultDTO
    except ImportError:
        BaseSecurityAuditor = object
        SecurityFinding = None
        AuditResultDTO = None


class MasterSSPPDeepLogicEngine(BaseSecurityAuditor, SSPPBlackBoxAuditor):
    """
    Unified Master SSPP Security Engine conforming to SecurityAuditorProtocol.
    """
    def __init__(self, target_url: str = "", max_captured_requests: int = 500):
        if hasattr(BaseSecurityAuditor, "__init__") and BaseSecurityAuditor is not object:
            BaseSecurityAuditor.__init__(self, name="SSPP_BLACKBOX_SECURITY_ENGINE")
        else:
            self._name = "SSPP_BLACKBOX_SECURITY_ENGINE"
        SSPPBlackBoxAuditor.__init__(self, target_url=target_url, max_captured_requests=max_captured_requests)

    async def run_audit(self, target: str = "", **kwargs) -> dict:
        target_url = target or self.target_url or kwargs.get("url", "")
        request_context = kwargs.get("request_context") or kwargs.get("context")

        if request_context and target_url:
            method = kwargs.get("method", "AUTO")
            scan_result = await self.audit_endpoint(request_context, target_url, method=method)
            return {
                "auditor_name": getattr(self, "auditor_name", "SSPP_BLACKBOX_SECURITY_ENGINE"),
                "status": "COMPLETED",
                "target": target_url,
                "timestamp": time.time(),
                "scan_result": scan_result.model_dump(),
                "findings": [f.model_dump() for f in scan_result.findings]
            }

        return {
            "auditor_name": getattr(self, "auditor_name", "SSPP_BLACKBOX_SECURITY_ENGINE"),
            "status": "BUNDLE_GENERATED",
            "target": target_url or "https://api.target.com",
            "timestamp": time.time(),
            "payload_matrix": {
                "json_spaces_probes_count": len(SSPPPayloadGenerator.get_json_space_payloads(10)),
                "reversion_payloads_count": len(SSPPPayloadGenerator.get_json_space_reversion_payloads()),
                "status_code_probes_count": len(SSPPPayloadGenerator.get_status_code_payloads(510)),
                "query_string_probes_count": len(SSPPPayloadGenerator.get_query_string_payloads("json spaces", 10)),
                "form_payloads_count": len(SSPPPayloadGenerator.get_form_urlencoded_payloads("json spaces", 10)),
            },
            "findings": [f.model_dump() for f in self.findings]
        }
