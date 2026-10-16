"""Unit tests for SEO/AEO/GEO Mining Engine & Pydantic v2 DTOs."""

from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError

from behavioral_playwright.facade import BP
from behavioral_playwright.mining import (
    AIOAuditor,
    PAAMiner,
    SERPCannibalizationEngine,
)
from behavioral_playwright.models.seo_dtos import (
    AIOAuditResult,
    CannibalizationReport,
    PAANode,
)


# ==============================================================================
# 1. Pydantic v2 DTO Validation Tests
# ==============================================================================


def test_paa_node_validation():
    """Verify PAANode validation, default depth, and URL normalization."""
    node = PAANode(
        question="What is Playwright?",
        snippet_text="Playwright is an automation library.",
        source_title="Playwright Official Docs",
        source_url="playwright.dev/docs",
        depth=1,
    )
    assert node.question == "What is Playwright?"
    assert node.source_url == "https://playwright.dev/docs"
    assert node.depth == 1
    assert node.parent_question is None

    # Invalid depth < 1
    with pytest.raises(ValidationError):
        PAANode(
            question="Invalid?",
            snippet_text="Text",
            source_title="Title",
            source_url="https://example.com",
            depth=0,
        )

    # Invalid depth > 5
    with pytest.raises(ValidationError):
        PAANode(
            question="Invalid?",
            snippet_text="Text",
            source_title="Title",
            source_url="https://example.com",
            depth=6,
        )


def test_aio_audit_result_validation():
    """Verify AIOAuditResult fields and defaults."""
    res = AIOAuditResult(
        query="best headless browser for python",
        has_aio_card=True,
        summary_text="Playwright and Selenium are top options.",
        citations=["https://playwright.dev", "https://selenium.dev"],
        brand_cited=True,
        brand_rank=1,
        competitors_cited=["https://selenium.dev"],
    )
    assert res.has_aio_card is True
    assert res.brand_cited is True
    assert res.brand_rank == 1
    assert len(res.citations) == 2


def test_cannibalization_report_validation():
    """Verify CannibalizationReport fields and recommendation enum enforcement."""
    report = CannibalizationReport(
        query_a="browser automation python",
        query_b="python web scraping playwright",
        jaccard_score=0.67,
        common_urls=["https://playwright.dev", "https://github.com"],
        recommendation="MERGE_INTO_SINGLE_CANONICAL",
    )
    assert report.jaccard_score == 0.67
    assert report.recommendation == "MERGE_INTO_SINGLE_CANONICAL"

    # Invalid recommendation value
    with pytest.raises(ValidationError):
        CannibalizationReport(
            query_a="q1",
            query_b="q2",
            jaccard_score=0.1,
            common_urls=[],
            recommendation="INVALID_ACTION",
        )


# ==============================================================================
# 2. PAAMiner Tests
# ==============================================================================


def test_paa_miner_parse_html():
    """Verify PAAMiner parsing from mock SERP HTML."""
    miner = PAAMiner(max_depth=3)

    mock_html = """
    <html>
      <body>
        <div class="related-question-pair">
          <div role="button">
            <div>How does Playwright bypass bot detection?</div>
          </div>
          <div>
            <div data-attrid="wa:/description">Playwright uses stealth plugins and CDP runtime modifications.</div>
            <a href="https://example.com/stealth"><span>Stealth Guide 2026</span></a>
          </div>
        </div>
        <div class="related-question-pair">
          <div role="button">
            <div>Is Playwright faster than Selenium?</div>
          </div>
          <div>
            <div>Yes, Playwright communicates directly via Chrome DevTools Protocol.</div>
            <a href="https://speed.com/benchmarks"><span>Benchmark Report</span></a>
          </div>
        </div>
      </body>
    </html>
    """

    nodes = miner.parse_from_html(mock_html, base_depth=1)
    assert len(nodes) == 2
    assert nodes[0].question == "How does Playwright bypass bot detection?"
    assert "stealth plugins" in nodes[0].snippet_text
    assert nodes[0].source_url == "https://example.com/stealth"
    assert nodes[1].question == "Is Playwright faster than Selenium?"
    assert nodes[1].source_url == "https://speed.com/benchmarks"


@pytest.mark.asyncio
async def test_paa_miner_extract_from_page():
    """Verify PAAMiner interactive extraction on mock Page."""
    miner = PAAMiner(max_depth=2)

    mock_page = AsyncMock()
    mock_page.content = AsyncMock(return_value="""
    <div class="related-question-pair">
      <div role="button"><div>What is AEO?</div></div>
      <div>
        <div>Answer Engine Optimization optimizes for generative search engines.</div>
        <a href="https://seo.com/aeo"><span>AEO Overview</span></a>
      </div>
    </div>
    """)
    mock_page.query_selector_all = AsyncMock(return_value=[])

    nodes = await miner.extract_from_page(mock_page, target_query="what is aeo")
    assert len(nodes) == 1
    assert nodes[0].question == "What is AEO?"
    assert nodes[0].source_url == "https://seo.com/aeo"


# ==============================================================================
# 3. AIOAuditor Tests
# ==============================================================================


def test_aio_auditor_html():
    """Verify AIO overview card parsing, brand rank, and competitor detection."""
    auditor = AIOAuditor(
        brand_domain_or_name="mycompany.com",
        competitor_domains=["competitor-a.com", "competitor-b.org"],
    )

    mock_html = """
    <html>
      <body>
        <div class="YzSd6">
          <div class="xpdopen">
            Here is an AI-generated summary of the top solutions.
          </div>
          <a href="https://competitor-a.com/features">Competitor A</a>
          <a href="https://www.mycompany.com/product">My Company</a>
          <a href="https://competitor-b.org/docs">Competitor B</a>
        </div>
      </body>
    </html>
    """

    res = auditor.audit_html(mock_html, query="best solutions 2026")
    assert res.has_aio_card is True
    assert "AI-generated summary" in (res.summary_text or "")
    assert len(res.citations) == 3
    assert res.brand_cited is True
    # Brand is 2nd in citations list -> rank 2
    assert res.brand_rank == 2
    assert "https://competitor-a.com/features" in res.competitors_cited
    assert "https://competitor-b.org/docs" in res.competitors_cited


def test_aio_auditor_no_card():
    """Verify AIOAuditor behavior when no card is present."""
    auditor = AIOAuditor(brand_domain_or_name="mycompany.com")
    html_without_aio = "<html><body><h1>Standard SERP</h1></body></html>"
    res = auditor.audit_html(html_without_aio, query="random search")
    assert res.has_aio_card is False
    assert res.brand_cited is False
    assert res.brand_rank is None
    assert len(res.citations) == 0


# ==============================================================================
# 4. SERPCannibalizationEngine Tests
# ==============================================================================


def test_cannibalization_engine_high_overlap():
    """Verify Jaccard computation and MERGE recommendation for high overlap."""
    engine = SERPCannibalizationEngine(merge_threshold=0.40)

    urls_a = [
        "https://example.com/guide?utm_source=google",
        "https://example.com/pricing",
        "https://github.com/project",
        "https://docs.example.com/",
    ]
    urls_b = [
        "https://example.com/guide",  # Matches after query stripping
        "https://example.com/pricing/",  # Matches after trailing slash strip
        "https://github.com/project?ref=serp",  # Matches after ref strip
        "https://otherblog.org/article",
    ]

    report = engine.evaluate_cannibalization(
        "query alpha", "query beta", urls_a, urls_b
    )
    # Common URLs: example.com/guide, example.com/pricing, github.com/project (3 urls)
    # Total unique: 3 common + docs.example.com + otherblog.org = 5 total
    # Jaccard = 3 / 5 = 0.60 >= 0.40
    assert report.jaccard_score == 0.60
    assert report.recommendation == "MERGE_INTO_SINGLE_CANONICAL"
    assert len(report.common_urls) == 3


def test_cannibalization_engine_low_overlap():
    """Verify SPLIT recommendation when Jaccard similarity is below threshold."""
    engine = SERPCannibalizationEngine(merge_threshold=0.40)

    urls_a = ["https://site1.com/a", "https://site2.com/b"]
    urls_b = ["https://site3.com/c", "https://site4.com/d"]

    report = engine.evaluate_cannibalization(
        "query alpha", "query beta", urls_a, urls_b
    )
    assert report.jaccard_score == 0.0
    assert report.recommendation == "SPLIT_INTO_SEPARATE_PAGES"
    assert len(report.common_urls) == 0


# ==============================================================================
# 5. Facade BP.mining / BP.seo Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_facade_mining_integration():
    """Verify bp.mining and bp.seo namespace delegations on BP facade."""
    bp = BP()
    assert hasattr(bp, "mining")
    assert hasattr(bp, "seo")
    assert bp.seo is bp.mining

    # Cannibalization via facade
    report = bp.mining.audit_cannibalization(
        query_a="q1",
        query_b="q2",
        urls_a=["https://a.com/page"],
        urls_b=["https://a.com/page"],
    )
    assert report.jaccard_score == 1.0
    assert report.recommendation == "MERGE_INTO_SINGLE_CANONICAL"

    # AIO Audit via facade with raw HTML
    aio_html = """
    <div data-attrid="wa:/description">
      <div>AI Summary content</div>
      <a href="https://target.com">Target</a>
    </div>
    """
    aio_res = await bp.mining.audit_aio(
        query="test query",
        page_or_html=aio_html,
        brand="target.com",
    )
    assert aio_res.has_aio_card is True
    assert aio_res.brand_cited is True
    assert aio_res.brand_rank == 1

    # PAA Mining via facade with raw HTML
    paa_html = """
    <div class="related-question-pair">
      <div role="button"><div>Facade Question?</div></div>
      <div>
        <div>Facade Answer Snippet</div>
        <a href="https://facade.com">Facade Link</a>
      </div>
    </div>
    """
    paa_nodes = await bp.mining.mine_paa(page_or_html=paa_html)
    assert len(paa_nodes) == 1
    assert paa_nodes[0].question == "Facade Question?"
