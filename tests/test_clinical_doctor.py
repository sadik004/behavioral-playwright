"""
Automated Test Suite for Clinical Bug Hunter Engine (DNA Extractor + Gemini Doctor)
"""
import os, sys
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

import asyncio
import pytest
from behavioral_evasion_suite.dna_extractor import (
    WebsiteDNAExtractor,
    WebsiteDNAReport,
    EndpointDNA,
    LibraryDNA
)
from behavioral_evasion_suite.doctor_bridge import (
    GeminiDoctorBridge,
    ClinicalRuleSurgeon,
    DoctorPrescription,
    SurgicalProbeSpec
)
from behavioral_evasion_suite.clinical_orchestrator import (
    ClinicalBugHunterOrchestrator,
    HackerOneSubmissionReport
)


def test_01_website_dna_serialization():
    dna = WebsiteDNAReport(
        target_url="https://api.vulnerable.com",
        framework_hints=["Next.js", "Express.js"],
        libraries=[LibraryDNA(name="Lodash", version="4.17.4")],
        endpoints=[
            EndpointDNA(url="https://api.vulnerable.com/api/v1/profile", method="POST", is_rest_api=True)
        ]
    )
    assert len(dna.endpoints) == 1
    assert "Next.js" in dna.framework_hints
    dumped = dna.model_dump()
    assert dumped["libraries"][0]["name"] == "Lodash"


def test_02_doctor_clinical_prescription_matching():
    dna = WebsiteDNAReport(
        target_url="https://api.vulnerable.com",
        framework_hints=["Express.js"],
        endpoints=[
            EndpointDNA(url="https://api.vulnerable.com/api/user", method="POST", is_rest_api=True)
        ]
    )
    prescription = ClinicalRuleSurgeon.diagnose_dna(dna)
    assert isinstance(prescription, DoctorPrescription)
    assert len(prescription.surgical_probes) > 0
    assert "CWE-1321" in " ".join(prescription.suspected_vulnerabilities)

    # Verify that json spaces prescription exists
    techniques = [p.technique for p in prescription.surgical_probes]
    assert any("json spaces" in t.lower() for t in techniques)


def test_03_graphql_doctor_prescription():
    dna = WebsiteDNAReport(
        target_url="https://api.vulnerable.com",
        framework_hints=["Apollo GraphQL"],
        endpoints=[
            EndpointDNA(url="https://api.vulnerable.com/graphql", method="POST", is_graphql=True)
        ]
    )
    prescription = ClinicalRuleSurgeon.diagnose_dna(dna)
    techniques = [p.technique for p in prescription.surgical_probes]
    assert any("introspection" in t.lower() for t in techniques)


def test_04_hackerone_report_rendering():
    h1 = HackerOneSubmissionReport(
        title="Server-Side Prototype Pollution on https://api.vulnerable.com",
        target_url="https://api.vulnerable.com",
        cwe_id="CWE-1321",
        severity="HIGH",
        vulnerability_summary="Prototype pollution confirmed via Express json spaces.",
        steps_to_reproduce="Execute reproducible cURL command.",
        curl_proof_of_concept="curl -i -X POST https://api.vulnerable.com",
        business_impact="Denial of service and attribute override.",
        remediation_guidance="Sanitize prototype keys and freeze Object.prototype.",
        verified_non_destructive=True
    )
    md = h1.to_markdown()
    assert "# Server-Side Prototype Pollution" in md
    assert "CWE-1321" in md
    assert "curl -i -X POST" in md

def test_05_notebooklm_library_auto_discovery():
    from behavioral_evasion_suite.doctor_bridge import NotebookLMBridge, GeminiDoctorBridge
    url = NotebookLMBridge.get_active_or_first_notebook_url()
    assert url is not None
    assert "f1eac2a4-57d0-427e-a90e-b55fab14b8f4" in url
    doc = GeminiDoctorBridge()
    assert doc.notebook_url == url
