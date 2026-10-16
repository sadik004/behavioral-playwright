"""Unit tests for Client-Side Rendering (CSR) Drift Auditor."""

from unittest.mock import AsyncMock, patch
import pytest
from pydantic import ValidationError

from behavioral_playwright.models.seo_dtos import CSRDriftReport
from behavioral_playwright.verification.rendering_auditor import (
    CSRRenderingDriftAuditor,
    RenderingDriftAuditor,
)


def test_csr_drift_report_dto_validation():
    """Verify CSRDriftReport validation and risk constraints."""
    report = CSRDriftReport(
        url="https://example.com",
        raw_html_bytes=1000,
        rendered_html_bytes=2500,
        raw_dom_nodes=15,
        rendered_dom_nodes=50,
        raw_text_length=200,
        rendered_text_length=800,
        drift_ratio=0.75,
        missing_in_raw=["H1 headings rendered exclusively via CSR"],
        hydration_drift_detected=True,
        seo_indexation_risk="CRITICAL",
    )
    assert report.drift_ratio == 0.75
    assert report.seo_indexation_risk == "CRITICAL"
    assert report.hydration_drift_detected is True

    # Case normalization for risk
    report2 = CSRDriftReport(
        drift_ratio=0.10,
        seo_indexation_risk="low",
    )
    assert report2.seo_indexation_risk == "LOW"

    # Invalid risk value
    with pytest.raises(ValidationError):
        CSRDriftReport(drift_ratio=0.5, seo_indexation_risk="EXTREME")


def test_audit_html_drift_identical():
    """Verify zero drift when raw SSR and CSR DOM are identical."""
    auditor = CSRRenderingDriftAuditor()
    html = """
    <!DOCTYPE html>
    <html>
      <head><title>Static Page</title></head>
      <body>
        <h1>Primary Heading</h1>
        <p>This is statically rendered text content.</p>
        <a href="/about">About Us</a>
      </body>
    </html>
    """
    report = auditor.audit_html_drift(raw_html=html, rendered_html=html, url="https://example.com")
    assert report.drift_ratio == 0.0
    assert len(report.missing_in_raw) == 0
    assert report.hydration_drift_detected is False
    assert report.seo_indexation_risk == "LOW"


def test_audit_html_drift_missing_h1_and_title():
    """Verify detection of missing H1 and Page Title in raw HTML."""
    auditor = CSRRenderingDriftAuditor()

    raw_html = """
    <html>
      <head></head>
      <body>
        <div id="root">Loading...</div>
      </body>
    </html>
    """

    rendered_html = """
    <html>
      <head><title>CSR Hydrated Title</title></head>
      <body>
        <div id="root">
          <h1>Dynamic Heading</h1>
          <p>Full application rendered via React bundle.</p>
        </div>
      </body>
    </html>
    """

    report = auditor.audit_html_drift(raw_html, rendered_html)
    assert "H1 headings rendered exclusively via CSR" in report.missing_in_raw
    assert "Page <title> tag injected via CSR" in report.missing_in_raw
    assert report.hydration_drift_detected is True
    assert report.seo_indexation_risk in ("HIGH", "CRITICAL")


def test_audit_html_drift_missing_jsonld():
    """Verify detection of client-injected JSON-LD structured schemas."""
    auditor = CSRRenderingDriftAuditor()

    raw_html = "<html><body><p>Product info</p></body></html>"
    rendered_html = """
    <html>
      <body>
        <p>Product info</p>
        <script type="application/ld+json">{"@context": "https://schema.org", "@type": "Product", "name": "Tool"}</script>
      </body>
    </html>
    """

    report = auditor.audit_html_drift(raw_html, rendered_html)
    assert any("JSON-LD schema(s) injected via CSR" in msg for msg in report.missing_in_raw)
    assert report.hydration_drift_detected is True


def test_audit_html_drift_empty_spa_container():
    """Verify empty SPA root container detection."""
    auditor = CSRRenderingDriftAuditor()

    raw_html = '<html><body><div id="root"></div></body></html>'
    rendered_html = f'<html><body><div id="root">{"Content " * 100}</div></body></html>'

    report = auditor.audit_html_drift(raw_html, rendered_html)
    assert "Empty SPA container detected in static HTML" in report.missing_in_raw
    assert report.hydration_drift_detected is True


@pytest.mark.asyncio
async def test_audit_url_drift_mock_page():
    """Verify audit_url_drift with a mock Page instance."""
    auditor = CSRRenderingDriftAuditor()

    raw_html = "<html><head><title>Raw</title></head><body><p>Raw text</p></body></html>"
    rendered_html = "<html><head><title>Rendered</title></head><body><h1>Heading</h1><p>Rendered text</p></body></html>"

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.content = AsyncMock(return_value=rendered_html)

    with patch.object(auditor, "fetch_static_html", new=AsyncMock(return_value=raw_html)):
        report = await auditor.audit_url_drift("https://spa.example.com", page=mock_page)
        assert report.url == "https://spa.example.com"
        assert report.rendered_html_bytes > 0
        assert report.raw_html_bytes > 0
        assert "H1 headings rendered exclusively via CSR" in report.missing_in_raw


def test_alias_export():
    """Verify RenderingDriftAuditor is alias of CSRRenderingDriftAuditor."""
    assert RenderingDriftAuditor is CSRRenderingDriftAuditor
