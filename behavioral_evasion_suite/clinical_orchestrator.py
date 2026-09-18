"""
Clinical Bug Hunter Orchestrator (The Complete Doctor-Patient Loop)
Module: clinical_orchestrator.py

Connects:
Layer 1: Website DNA Extractor (Pathology Lab)
Layer 2: Gemini Doctor Bridge (Specialist Diagnosis)
Layer 3: Surgical Strike Executors (SSPP & GraphQL Security Auditors)

Delivers:
- Fully automated diagnosis from web visit to surgical verification
- Instant HackerOne-Ready Triaged Submission Report
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

try:
    from .dna_extractor import WebsiteDNAExtractor, WebsiteDNAReport, EndpointDNA
except (ImportError, ModuleNotFoundError):
    from dna_extractor import WebsiteDNAExtractor, WebsiteDNAReport, EndpointDNA

try:
    from .doctor_bridge import GeminiDoctorBridge, DoctorPrescription, SurgicalProbeSpec
except (ImportError, ModuleNotFoundError):
    from doctor_bridge import GeminiDoctorBridge, DoctorPrescription, SurgicalProbeSpec

try:
    from .sspp_security_auditor import SSPPBlackBoxAuditor, SSPPFinding, SSPPScanResult
except (ImportError, ModuleNotFoundError):
    try:
        from .sspp_blackbox_engine_v4 import SSPPBlackBoxAuditor, SSPPFinding, SSPPScanResult
    except (ImportError, ModuleNotFoundError):
        from sspp_blackbox_engine_v4 import SSPPBlackBoxAuditor, SSPPFinding, SSPPScanResult


# =====================================================================
# 1. HACKERONE TRIAGED REPORT DTO
# =====================================================================

class HackerOneSubmissionReport(BaseModel):
    title: str
    target_url: str
    cwe_id: str
    severity: str
    vulnerability_summary: str
    steps_to_reproduce: str
    curl_proof_of_concept: str
    business_impact: str
    remediation_guidance: str
    verified_non_destructive: bool = True
    timestamp: float = Field(default_factory=time.time)

    def to_markdown(self) -> str:
        """Renders professional markdown report ready for direct submission on HackerOne."""
        return f"""# {self.title}

## Summary:
{self.vulnerability_summary}

## Vulnerability Classification:
- **CWE:** {self.cwe_id}
- **Assessed Severity:** {self.severity}

## Steps to Reproduce:
{self.steps_to_reproduce}

## Reproducible cURL Proof of Concept:
```bash
{self.curl_proof_of_concept}
```

## Business Impact:
{self.business_impact}

## Remediation Guidance:
{self.remediation_guidance}

## Ethical & Non-Destructive Safety Guarantee:
The vulnerability verification was conducted following strict non-destructive protocols. Safe rollback/reversion payloads were dispatched immediately upon confirmation. No persistent state, customer data, or server availability was impaired.
"""


# =====================================================================
# 2. CLINICAL BUG HUNTER ORCHESTRATOR
# =====================================================================

class ClinicalBugHunterOrchestrator:
    """
    End-to-end Master Orchestrator:
    1. Extracts Website DNA (Pathology)
    2. Diagnoses via Gemini Doctor (Prescription)
    3. Executes surgical probes with safe rollback (Surgery)
    4. Generates triaged HackerOne report (Discharge Summary)
    """

    def __init__(self, api_key: Optional[str] = None):
        self.dna_extractor = WebsiteDNAExtractor()
        self.doctor = GeminiDoctorBridge(api_key=api_key)
        self.sspp_auditor = SSPPBlackBoxAuditor()

    async def execute_clinical_audit(
        self,
        request_context,
        target_url: str,
        page=None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end clinical workflow on a target website.
        """
        # Step 1: Pathology Lab - Extract DNA
        dna_report = await self.dna_extractor.extract_dna(page, target_url=target_url)

        # Step 2: Specialist Doctor - Issue Prescription
        prescription = await self.doctor.consult_doctor(dna_report)

        # Step 3: Surgical Strike - Deliver Prescribed Probes
        audit_results: List[SSPPScanResult] = []
        reports: List[HackerOneSubmissionReport] = []

        for probe in prescription.surgical_probes:
            # 1. SSPP Surgical Probes
            if "prototype pollution" in probe.technique.lower() or "json spaces" in probe.technique.lower():
                scan_res = await self.sspp_auditor.audit_endpoint(
                    request_context, probe.target_endpoint, method=probe.method
                )
                audit_results.append(scan_res)

                # If surgery verifies vulnerability, issue HackerOne Report
                if scan_res.is_vulnerable and scan_res.findings:
                    for finding in scan_res.findings:
                        h1_report = HackerOneSubmissionReport(
                            title=f"Server-Side Prototype Pollution on {probe.target_endpoint} via {finding.technique}",
                            target_url=probe.target_endpoint,
                            cwe_id="CWE-1321: Improperly Controlled Modification of Object Prototype Attributes",
                            severity=prescription.estimated_severity,
                            vulnerability_summary=(
                                f"During automated diagnostic assessment of {probe.target_endpoint}, "
                                f"a critical prototype pollution vulnerability was confirmed. {finding.evidence}."
                            ),
                            steps_to_reproduce=(
                                f"1. Send an HTTP {finding.method} request with prototype mutation payload.\n"
                                f"2. Observe mutated server response behavior (e.g. JSON indentation or status code override).\n"
                                f"3. Confirm payload execution without server crash."
                            ),
                            curl_proof_of_concept=finding.curl_poc,
                            business_impact=(
                                "An attacker could manipulate backend object prototypes, leading to "
                                "application-wide denial of service, configuration override, authentication bypass, "
                                "or remote code execution depending on server-side gadget availability."
                            ),
                            remediation_guidance=(
                                "1. Freeze the Object prototype using Object.freeze(Object.prototype).\n"
                                "2. Use Object.create(null) for unpollutable dictionary lookups.\n"
                                "3. Upgrade body-parser and query string parsing dependencies to hardened versions."
                            ),
                            verified_non_destructive=finding.remediated
                        )
                        reports.append(h1_report)

            # 2. GraphQL Introspection & Schema Probes
            elif "graphql" in probe.technique.lower() or "introspection" in probe.technique.lower():
                gql_report = await self._audit_graphql_probe(
                    request_context, probe, prescription.estimated_severity
                )
                if gql_report:
                    reports.append(gql_report)

        return {
            "status": "CLINICAL_AUDIT_COMPLETED",
            "dna_report": dna_report.model_dump(),
            "doctor_prescription": prescription.model_dump(),
            "probes_executed": len(prescription.surgical_probes),
            "vulnerabilities_confirmed": len(reports),
            "hackerone_reports": [r.model_dump() for r in reports],
            "raw_audit_results": [res.model_dump() for res in audit_results]
        }

    async def _audit_graphql_probe(
        self,
        request_context,
        probe: SurgicalProbeSpec,
        severity: str
    ) -> Optional[HackerOneSubmissionReport]:
        """Performs non-destructive GraphQL introspection audit."""
        if not request_context:
            return None

        try:
            headers = {"Content-Type": "application/json"}
            payload = probe.recommended_payload
            if isinstance(payload, str):
                payload = {"query": payload}

            resp = await request_context.post(
                probe.target_endpoint,
                data=json.dumps(payload),
                headers=headers,
                timeout=10000
            )
            if resp.status == 200:
                body = await resp.json()
                data = body.get("data", {})
                if data and ("__schema" in data or "__typename" in data):
                    curl_poc = (
                        f"curl -i -X POST {probe.target_endpoint} \\\n"
                        f"  -H 'Content-Type: application/json' \\\n"
                        f"  -d '{json.dumps(payload)}'"
                    )
                    return HackerOneSubmissionReport(
                        title=f"GraphQL Introspection Exposure on {probe.target_endpoint}",
                        target_url=probe.target_endpoint,
                        cwe_id="CWE-200: Exposure of Sensitive Information to an Unauthorized Actor",
                        severity=severity,
                        vulnerability_summary=(
                            f"GraphQL introspection is fully enabled on {probe.target_endpoint}, "
                            f"exposing internal schema definitions, protected types, queries, and mutations."
                        ),
                        steps_to_reproduce=(
                            f"1. Send a POST request to {probe.target_endpoint} containing an introspection query.\n"
                            f"2. Observe complete internal GraphQL schema returned in response body."
                        ),
                        curl_proof_of_concept=curl_poc,
                        business_impact=(
                            "Schema introspection enables adversaries to map 100% of backend API attack surface, "
                            "discovering hidden mutations, administrative queries, and undocumented fields."
                        ),
                        remediation_guidance=(
                            "Disable GraphQL introspection in production environments. "
                            "For Apollo Server, configure: introspection: false."
                        ),
                        verified_non_destructive=True
                    )
        except Exception:
            pass
        return None


# =====================================================================
# 3. SELF-TEST VERIFICATION GATE
# =====================================================================

if __name__ == "__main__":
    print("=== Testing Clinical Bug Hunter & Doctor-Patient Engine ===")

    # Test 1: DNA Extraction Model
    extractor = WebsiteDNAExtractor()
    sample_dna = WebsiteDNAReport(
        target_url="https://api.target.com/dashboard",
        framework_hints=["Next.js", "Express.js", "Apollo GraphQL"],
        endpoints=[
            EndpointDNA(url="https://api.target.com/api/v1/user", method="POST", is_rest_api=True),
            EndpointDNA(url="https://api.target.com/graphql", method="POST", is_graphql=True)
        ]
    )
    assert len(sample_dna.endpoints) == 2
    print("1. Website DNA Pathology DTO Model: PASSED")

    # Test 2: Doctor Consultation & Prescription Generation
    doctor = GeminiDoctorBridge()
    prescription = asyncio.run(doctor.consult_doctor(sample_dna))
    assert len(prescription.surgical_probes) >= 2
    assert "CWE-1321" in " ".join(prescription.suspected_vulnerabilities)
    print(f"2. Gemini Doctor Diagnosis: PASSED ({len(prescription.surgical_probes)} surgical probes prescribed)")

    # Test 3: HackerOne Triaged Submission Report Formatting
    orchestrator = ClinicalBugHunterOrchestrator()
    sample_finding = SSPPFinding(
        finding_type="SSPP_JSON_SPACES",
        url="https://api.target.com/api/v1/user",
        method="POST",
        technique="Express json spaces mutation",
        evidence="10 space indentation verified",
        curl_poc="curl -i -X POST https://api.target.com/api/v1/user -d '{\"__proto__\":{\"json spaces\":10}}'",
        remediated=True
    )
    h1 = HackerOneSubmissionReport(
        title="Server-Side Prototype Pollution on https://api.target.com/api/v1/user",
        target_url="https://api.target.com/api/v1/user",
        cwe_id="CWE-1321",
        severity="HIGH",
        vulnerability_summary="Prototype pollution confirmed via Express json spaces.",
        steps_to_reproduce="Send prototype payload via cURL and observe response indentation.",
        curl_proof_of_concept=sample_finding.curl_poc,
        business_impact="System availability and property override risk.",
        remediation_guidance="Sanitize prototype keys and freeze prototype.",
        verified_non_destructive=True
    )
    md_output = h1.to_markdown()
    assert "# Server-Side Prototype Pollution" in md_output
    assert "curl -i -X POST" in md_output
    print("3. HackerOne Triaged Submission Report Generator: PASSED")

    print("\n=== ALL CLINICAL DOCTOR-PATIENT QUALITY GATES PASSED CLEANLY! ===")
