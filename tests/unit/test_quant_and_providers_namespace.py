"""Unit tests for BP facade quant and providers namespaces."""

from behavioral_playwright import BP
from behavioral_playwright.core.itch_binary import ItchBinaryParser


def test_bp_quant_namespace():
    bp = BP()
    # ITCH binary parser creation
    parser = bp.quant.create_itch_parser(dollar_threshold=25000.0)
    assert isinstance(parser, ItchBinaryParser)
    assert parser.dollar_threshold == 25000.0

    # Entity resolution (SYNTH-* identifiers)
    resolved = bp.quant.resolve_entity("Nonexistent Startup Corp")
    assert resolved["synthetic"] is True
    assert resolved["isin"].startswith("SYNTH-")

    # EDGAR PiT aligner
    filing = {
        "cik": "0000320193",
        "period_of_report_epoch": 1000.0,
        "sec_dissemination_epoch": 1005.0,
    }
    aligned = bp.quant.align_edgar_filing(filing)
    assert aligned["event_timestamp"] == 1000.0
    assert aligned["knowledge_timestamp"] == 1005.0


def test_bp_providers_namespace():
    bp = BP()
    matrix = bp.providers.matrix()
    assert "browser/playwright" in matrix
    assert "network/curl_cffi" in matrix

    # create browser provider
    pw = bp.providers.create_browser("playwright")
    assert pw.display_name == "playwright"

    # create network provider
    net = bp.providers.create_network("curl_cffi")
    assert net.display_name == "curl_cffi"



