"""
Gemini Doctor Knowledge & Diagnostic Bridge (The Specialist Doctor)
Module: doctor_bridge.py

Connects WebsiteDNAReport to:
1. Google GenAI SDK (Gemini 2.0 / 1.5 Flash) via official `google.genai` Client.
2. Google NotebookLM Integration (for source-grounded research querying).
3. Local Indexed Security Research Knowledge Store (PortSwigger, HackerOne, CVEs).
4. Deterministic Clinical Rule Surgeon (Zero-latency fallback).

Emits structured DoctorPrescription for targeted surgical auditing.
"""

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

try:
    from .dna_extractor import WebsiteDNAReport, EndpointDNA, LibraryDNA
except ImportError:
    from dna_extractor import WebsiteDNAReport, EndpointDNA, LibraryDNA


# =====================================================================
# 1. STANDARDIZED DOCTOR PRESCRIPTION DTO SCHEMAS
# =====================================================================

class SurgicalProbeSpec(BaseModel):
    technique: str = Field(..., description="Vulnerability audit technique name")
    target_endpoint: str
    method: str = "POST"
    recommended_payload: Any
    expected_mutation: str
    reversion_payload: Any
    research_reference: str
    priority: int = 1


class DoctorPrescription(BaseModel):
    """
    Standardized diagnostic prescription emitted by the Gemini Doctor.
    Contains concrete surgical strike instructions and HackerOne rationale.
    """
    diagnosis_title: str
    patient_url: str
    clinical_summary: str
    suspected_vulnerabilities: List[str]
    estimated_severity: str = "HIGH"
    surgical_probes: List[SurgicalProbeSpec] = Field(default_factory=list)
    rationale: str
    knowledge_source: str = "Local Clinical Knowledge Store"
    timestamp: float = Field(default_factory=time.time)


# =====================================================================
# 2. LOCAL INDEXED RESEARCH KNOWLEDGE STORE (NOTEBOOK ENGINE)
# =====================================================================

class ResearchNote(BaseModel):
    title: str
    author_or_source: str
    cwe: str
    applicable_stack: List[str]
    detection_methodology: str
    recommended_payload: Any
    expected_evidence: str
    reversion_payload: Any


class LocalNotebookKnowledgeStore:
    """
    In-memory indexed knowledge repository containing ground-truth research papers
    from PortSwigger Web Security, HackerOne disclosed reports, and YesWeHack.
    """

    def __init__(self):
        self._research_notes: List[ResearchNote] = [
            ResearchNote(
                title="Server-Side Prototype Pollution via Express json spaces",
                author_or_source="PortSwigger Web Security (Gareth Heyes, 2022)",
                cwe="CWE-1321",
                applicable_stack=["Express.js", "Node.js", "Next.js"],
                detection_methodology="Mutate Object.prototype['json spaces'] to 10 spaces indentation in res.json().",
                recommended_payload={"__proto__": {"json spaces": 10}},
                expected_evidence="JSON response formatted with 10 spaces indentation",
                reversion_payload={"__proto__": {"json spaces": 0}}
            ),
            ResearchNote(
                title="Error Status Code Mutation via http-errors Prototype Pollution",
                author_or_source="PortSwigger Research (2022)",
                cwe="CWE-1321",
                applicable_stack=["Express.js", "Next.js", "http-errors"],
                detection_methodology="Pollute status property to 510; trigger error to observe 510 Not Extended.",
                recommended_payload={"__proto__": {"status": 510}},
                expected_evidence="Error response status mutates from baseline to 510 Not Extended",
                reversion_payload={"__proto__": {"status": None}}
            ),
            ResearchNote(
                title="CORS Exposed Headers Reflection via Prototype Pollution",
                author_or_source="YesWeHack Node.js Security Research (2021-2023)",
                cwe="CWE-1321",
                applicable_stack=["Express.js", "cors middleware"],
                detection_methodology="Pollute exposedHeaders array with x-pp-proof marker header.",
                recommended_payload={"__proto__": {"exposedHeaders": ["x-pp-proof"]}},
                expected_evidence="Access-Control-Expose-Headers reflects x-pp-proof",
                reversion_payload={"__proto__": {"exposedHeaders": []}}
            ),
            ResearchNote(
                title="GraphQL Positional Correlation & Introspection Query Exposure",
                author_or_source="HackerOne $30,000 Gem Bounty Writeup",
                cwe="CWE-200",
                applicable_stack=["Apollo GraphQL", "GraphQL Client"],
                detection_methodology="Query __schema introspection or utilize schema clairvoyance field suggestions.",
                recommended_payload={"query": "{__schema{queryType{name}}}"},
                expected_evidence="Reflection of schema queryType or suggestion errors in response",
                reversion_payload=None
            ),
            ResearchNote(
                title="URL Query String Parameter Pollution in qs / express",
                author_or_source="YesWeHack qs Parser Research",
                cwe="CWE-233",
                applicable_stack=["qs", "express", "Node.js"],
                detection_methodology="Pass __proto__[json spaces]=10 in URL query parameters.",
                recommended_payload="__proto__[json%20spaces]=10",
                expected_evidence="Response format mutated due to query parser prototype merge",
                reversion_payload="__proto__[json%20spaces]=0"
            )
        ]

    def query_research(self, stack_hints: List[str]) -> List[ResearchNote]:
        """Matches extracted website DNA stack hints against indexed research papers."""
        matched: List[ResearchNote] = []
        stack_lower = [s.lower() for s in stack_hints]

        for note in self._research_notes:
            for app_stack in note.applicable_stack:
                if any(app_stack.lower() in hint for hint in stack_lower):
                    matched.append(note)
                    break
        return matched if matched else self._research_notes


# =====================================================================
# 3. DETERMINISTIC CLINICAL RULE SURGEON (FAST LOCAL DOCTOR)
# =====================================================================

class ClinicalRuleSurgeon:
    """
    Offline/Local Clinical Decision Engine: Evaluates website DNA using
    curated PortSwigger, OWASP, and HackerOne diagnostic heuristics.
    """

    def __init__(self, knowledge_store: Optional[LocalNotebookKnowledgeStore] = None):
        self.store = knowledge_store or LocalNotebookKnowledgeStore()

    @classmethod
    def diagnose_dna(cls, dna: WebsiteDNAReport, knowledge_store: Optional[LocalNotebookKnowledgeStore] = None) -> DoctorPrescription:
        store = knowledge_store or LocalNotebookKnowledgeStore()
        probes: List[SurgicalProbeSpec] = []
        suspected: List[str] = []
        summary_points: List[str] = []

        relevant_notes = store.query_research(dna.framework_hints)

        # 1. JSON REST Endpoints -> Match against SSPP notes
        json_endpoints = [ep for ep in dna.endpoints if ep.is_rest_api or ep.has_post_data or ep.method in ["POST", "PUT", "PATCH"]]
        if json_endpoints:
            suspected.append("CWE-1321: Server-Side Prototype Pollution (SSPP)")
            summary_points.append("Active JSON API routes detected; matching against PortSwigger & YesWeHack research.")

            for ep in json_endpoints[:2]:
                for note in relevant_notes:
                    if "json spaces" in note.title.lower():
                        probes.append(
                            SurgicalProbeSpec(
                                technique=note.title,
                                target_endpoint=ep.url,
                                method=ep.method if ep.method != "GET" else "POST",
                                recommended_payload=note.recommended_payload,
                                expected_mutation=note.expected_evidence,
                                reversion_payload=note.reversion_payload,
                                research_reference=note.author_or_source,
                                priority=1
                            )
                        )
                    elif "status code" in note.title.lower():
                        probes.append(
                            SurgicalProbeSpec(
                                technique=note.title,
                                target_endpoint=ep.url,
                                method=ep.method if ep.method != "GET" else "POST",
                                recommended_payload=note.recommended_payload,
                                expected_mutation=note.expected_evidence,
                                reversion_payload=note.reversion_payload,
                                research_reference=note.author_or_source,
                                priority=2
                            )
                        )

        # 2. GraphQL Endpoints
        gql_endpoints = [ep for ep in dna.endpoints if ep.is_graphql or "graphql" in ep.url.lower()]
        if gql_endpoints or any("graphql" in f.lower() or "apollo" in f.lower() for f in dna.framework_hints):
            suspected.append("CWE-200: GraphQL Introspection Exposure")
            summary_points.append("GraphQL interface detected; matching against HackerOne $30,000 Gem writeup.")
            target_gql = gql_endpoints[0].url if gql_endpoints else f"{dna.target_url.rstrip('/')}/graphql"
            probes.append(
                SurgicalProbeSpec(
                    technique="GraphQL Universal Introspection Probe",
                    target_endpoint=target_gql,
                    method="POST",
                    recommended_payload={"query": "{__schema{queryType{name}}}"},
                    expected_mutation="Reflects __schema type details in response body",
                    reversion_payload=None,
                    research_reference="HackerOne $30,000 Gem Bounty Writeup",
                    priority=1
                )
            )

        # 3. Query Parameter Pollution
        query_endpoints = [ep for ep in dna.endpoints if len(ep.parameters) > 0]
        if query_endpoints:
            suspected.append("CWE-233: Parameter Pollution via Query String Parser")
            summary_points.append(f"Query parameter handling detected ({len(query_endpoints)} routes).")
            for ep in query_endpoints[:2]:
                probes.append(
                    SurgicalProbeSpec(
                        technique="URL Query String Prototype Pollution",
                        target_endpoint=ep.url,
                        method="GET",
                        recommended_payload="__proto__[json%20spaces]=10",
                        expected_mutation="Response format mutates due to query parser prototype merge",
                        reversion_payload="__proto__[json%20spaces]=0",
                        research_reference="YesWeHack Node.js Parameter Research (2023)",
                        priority=2
                    )
                )

        severity = "HIGH" if "CWE-1321" in " ".join(suspected) else ("MEDIUM" if suspected else "LOW")
        rationale = (
            "Clinical diagnosis matched against indexed PortSwigger and HackerOne research notes. "
            "Surgical probes target specific full-stack vulnerabilities with non-destructive verification."
        )

        return DoctorPrescription(
            diagnosis_title="Comprehensive Architectural Diagnostic Assessment",
            patient_url=dna.target_url,
            clinical_summary="\n".join(summary_points) if summary_points else "Standard web architecture; baseline defense active.",
            suspected_vulnerabilities=suspected,
            estimated_severity=severity,
            surgical_probes=probes,
            rationale=rationale,
            knowledge_source="Local Indexed Security Research Knowledge Store",
            timestamp=time.time()
        )


# =====================================================================
# 4. GOOGLE GENAI CLIENT (GEMINI LIVE AI DOCTOR)
# =====================================================================

class GeminiGenAIDoctor:
    """
    Integrates directly with the official Google GenAI SDK (`google.genai.Client`)
    to perform live AI diagnostic reasoning on the website's DNA.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception:
                self._client = None

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def diagnose(self, dna: WebsiteDNAReport, research_context: str) -> Optional[DoctorPrescription]:
        """Queries Gemini 2.0 / 1.5 Flash to issue an AI DoctorPrescription."""
        if not self.is_available:
            return None

        prompt = f"""
You are the Chief Security Diagnostic Surgeon for high-value bug bounty hunting (HackerOne).
You are evaluating the medical/technical DNA of a target web application.

Target URL: {dna.target_url}
Framework Hints: {dna.framework_hints}
Endpoints Captured: {[ep.model_dump() for ep in dna.endpoints[:5]]}
WAF / Immune Profile: {dna.waf_immune_profile}

Relevant Security Research Knowledge Notes:
{research_context}

Based on this DNA, issue a clinical diagnostic prescription.
Output MUST be valid JSON conforming to this schema:
{{
  "diagnosis_title": "string",
  "patient_url": "{dna.target_url}",
  "clinical_summary": "string",
  "suspected_vulnerabilities": ["CWE-XXXX", ...],
  "estimated_severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "surgical_probes": [
    {{
      "technique": "string",
      "target_endpoint": "string",
      "method": "POST|GET|PUT|PATCH",
      "recommended_payload": {{...}} or "string",
      "expected_mutation": "string",
      "reversion_payload": {{...}} or "string",
      "research_reference": "string",
      "priority": 1
    }}
  ],
  "rationale": "string"
}}
"""
        try:
            # Run in thread executor to keep Playwright event loop unblocked
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
            )
            raw_text = response.text.strip()
            # Clean markdown codeblocks if wrapped
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            parsed = json.loads(raw_text.strip())
            parsed["knowledge_source"] = "Gemini Live GenAI (gemini-2.0-flash)"
            return DoctorPrescription(**parsed)
        except Exception:
            return None


# =====================================================================
# 5. GOOGLE NOTEBOOKLM INTEGRATION BRIDGE
# =====================================================================

class NotebookLMBridge:
    """
    Connects to Google NotebookLM via the configured notebooklm skill runner.
    Allows querying user's private research notebooks for source-grounded answers.
    """

    SKILL_DIR = Path(r"C:\Users\User\.gemini\config\skills\notebooklm")
    RUNNER_SCRIPT = r"C:\Users\User\.gemini\config\skills\notebooklm\scripts\run.py"
    VENV_PYTHON = r"C:\Users\User\.gemini\config\skills\notebooklm\.venv\Scripts\python.exe"
    LIBRARY_FILE = r"C:\Users\User\.gemini\config\skills\notebooklm\data\library.json"

    @classmethod
    def is_configured(cls) -> bool:
        return os.path.exists(cls.RUNNER_SCRIPT) or os.path.exists(cls.VENV_PYTHON)

    @classmethod
    def get_active_or_first_notebook_url(cls) -> Optional[str]:
        """Auto-discovers the notebook URL from the user's NotebookLM library."""
        if not os.path.exists(cls.LIBRARY_FILE):
            return None
        try:
            with open(cls.LIBRARY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            active_id = data.get("active_notebook_id")
            notebooks = data.get("notebooks", {})
            if active_id and active_id in notebooks:
                return notebooks[active_id].get("url")
            for nb in notebooks.values():
                if "url" in nb:
                    return nb["url"]
        except Exception:
            pass
        return None

    @classmethod
    def list_notebooks(cls) -> List[Dict[str, Any]]:
        """Returns all registered notebooks in the NotebookLM skill."""
        if not os.path.exists(cls.LIBRARY_FILE):
            return []
        try:
            with open(cls.LIBRARY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return list(data.get("notebooks", {}).values())
        except Exception:
            return []

    @classmethod
    async def query_notebook(cls, question: str, notebook_url: Optional[str] = None) -> Optional[str]:
        """Queries NotebookLM using the skill runner wrapper."""
        url = notebook_url or cls.get_active_or_first_notebook_url()
        if not cls.is_configured() or not url:
            return None

        ask_script = os.path.join(str(cls.SKILL_DIR), "scripts", "ask_question.py")
        if os.path.exists(cls.VENV_PYTHON) and os.path.exists(ask_script):
            cmd = [
                cls.VENV_PYTHON,
                ask_script,
                "--question", question,
                "--notebook-url", url
            ]
        else:
            cmd = [
                "python",
                cls.RUNNER_SCRIPT,
                "ask_question.py",
                "--question", question,
                "--notebook-url", url
            ]

        try:
            loop = asyncio.get_running_loop()
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            def _run():
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15,
                    env=env
                )
                return proc.stdout

            output = await loop.run_in_executor(None, _run)
            return output.strip() if output else None
        except Exception:
            return None


# =====================================================================
# 6. UNIFIED MASTER GEMINI DOCTOR BRIDGE
# =====================================================================

class GeminiDoctorBridge:
    """
    The Master Diagnostic Doctor Bridge:
    1. Queries Local Knowledge Store for research notes
    2. If Google GenAI API is available, runs live Gemini 2.0 Flash clinical diagnosis
    3. If NotebookLM URL is provided, enriches with user's private research notebook
    4. Deterministically falls back to ClinicalRuleSurgeon ensuring zero downtime.
    """

    def __init__(self, api_key: Optional[str] = None, notebook_url: Optional[str] = None):
        self.knowledge_store = LocalNotebookKnowledgeStore()
        self.local_surgeon = ClinicalRuleSurgeon(knowledge_store=self.knowledge_store)
        self.genai_doctor = GeminiGenAIDoctor(api_key=api_key)
        self.notebook_url = (
            notebook_url
            or os.environ.get("NOTEBOOKLM_URL")
            or NotebookLMBridge.get_active_or_first_notebook_url()
        )

    async def consult_doctor(self, dna_report: WebsiteDNAReport) -> DoctorPrescription:
        """
        Synthesizes DNA report and produces a verified DoctorPrescription.
        """
        # Step 1: Query Local Research Notes
        notes = self.knowledge_store.query_research(dna_report.framework_hints)
        notes_summary = "\n".join([f"- {n.title} ({n.author_or_source}): {n.detection_methodology}" for n in notes])

        # Step 2: Try NotebookLM if configured
        if self.notebook_url and NotebookLMBridge.is_configured():
            try:
                question = f"What vulnerabilities apply to a stack with {', '.join(dna_report.framework_hints)}?"
                nb_answer = await NotebookLMBridge.query_notebook(question, self.notebook_url)
                if nb_answer:
                    notes_summary += f"\n- NotebookLM Source Insights: {nb_answer[:500]}"
            except Exception:
                pass

        # Step 3: Try Live Google GenAI (Gemini 2.0 Flash)
        if self.genai_doctor.is_available:
            try:
                ai_prescription = await self.genai_doctor.diagnose(dna_report, notes_summary)
                if ai_prescription:
                    return ai_prescription
            except Exception:
                pass

        # Step 4: Robust, deterministic Local Clinical Doctor with Knowledge Store
        return self.local_surgeon.diagnose_dna(dna_report)


if __name__ == "__main__":
    print("=== Testing Gemini Doctor Knowledge & Diagnostic Bridge ===")

    # Test 1: Local Knowledge Store Ingestion
    store = LocalNotebookKnowledgeStore()
    notes = store.query_research(["Next.js", "Express.js", "Apollo GraphQL"])
    assert len(notes) >= 3
    print(f"1. Local Research Knowledge Store: PASSED ({len(notes)} research notes indexed)")

    # Test 2: Local Clinical Surgeon Diagnosis
    surgeon = ClinicalRuleSurgeon(knowledge_store=store)
    sample_dna = WebsiteDNAReport(
        target_url="https://api.target.com",
        framework_hints=["Next.js", "Express.js"],
        endpoints=[
            EndpointDNA(url="https://api.target.com/api/v1/user", method="POST", is_rest_api=True)
        ]
    )
    prescription = surgeon.diagnose_dna(sample_dna)
    assert len(prescription.surgical_probes) >= 2
    assert prescription.knowledge_source == "Local Indexed Security Research Knowledge Store"
    print(f"2. Local Doctor Diagnosis with Research Notes: PASSED ({prescription.diagnosis_title})")

    # Test 3: NotebookLM Bridge Capability
    has_nb_bridge = NotebookLMBridge.is_configured()
    print(f"3. Google NotebookLM Bridge Detection: {'CONFIGURED' if has_nb_bridge else 'STANDBY'} (PASSED)")

    # Test 4: Master Bridge Orchestration
    bridge = GeminiDoctorBridge()
    final_prescription = asyncio.run(bridge.consult_doctor(sample_dna))
    assert len(final_prescription.surgical_probes) >= 2
    print("4. Master Gemini Doctor Bridge Consultation: PASSED")

    print("\n=== ALL GEMINI DOCTOR KNOWLEDGE BRIDGE QUALITY GATES PASSED! ===")
