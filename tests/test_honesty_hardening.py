"""Phase 2 honesty/data-integrity hardening regression tests.

Each test pins one honesty wart fix in the V15 baseline:

  A. Frida fallback        -> never fabricates intercepted payloads.
  B. Mitmproxy fallback    -> never fabricates decoded protobuf payloads.
  C. FIGI                  -> unknown identifiers are None, never synthesized.
  D. Event time            -> supplied values (incl. 0.0) preserved verbatim;
                              missing values explicitly flagged, never jittered.
  E. Entity identifiers    -> synthetic references are visibly SYNTH-prefixed
                              and machine-detectably flagged (synthetic=True).
"""
import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent.parent
V15_PATH = BASE / "behavioral_evasion_ten_patches_hardened_v15.py"


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def v15():
    return _load_module("hardened_baseline_v15", V15_PATH)


# ---------------------------------------------------------------- A. Frida
def test_frida_fallback_never_invokes_payload_callback(v15):
    """Without the frida provider, no fabricated payload may reach the
    message callback that real hooks also use (silent fake-success channel)."""
    if importlib.util.find_spec("frida") is not None:
        pytest.skip("frida installed on this host; absent-provider path not exercised")
    engine = v15.FridaNativeHookEngine(target_process="com.example.audit")
    received = []
    result = engine.spawn_and_hook(lambda message, data: received.append(message))
    assert result is False
    assert received == []


# ------------------------------------------------------------ B. Mitmproxy
class _StubPipeline:
    def __init__(self):
        self.ingested = []

    async def ingest_market_record(self, record, schema_class):
        self.ingested.append((record, schema_class))


class _FakeRequest:
    pretty_url = "https://market.example/api/v3/market-depth"
    host = "market.example"


class _FakeResponse:
    content = b"RAW-CAPTURED-BYTES-FROM-FLOW"


class _FakeFlow:
    request = _FakeRequest()
    response = _FakeResponse()


def test_mitmproxy_without_decoder_never_ingests_synthetic_data(v15):
    pipeline = _StubPipeline()
    addon = v15.MitmproxyStreamInterceptor(quant_pipeline=pipeline, schema_class=object)
    addon.response(_FakeFlow())
    assert pipeline.ingested == []


def test_mitmproxy_with_decoder_ingests_only_decoded_records(v15):
    pipeline = _StubPipeline()

    def _decoder(raw: bytes):
        return {"decoded_marker": raw.decode("utf-8", "replace")}

    addon = v15.MitmproxyStreamInterceptor(
        quant_pipeline=pipeline, schema_class=object, payload_decoder=_decoder
    )
    addon.response(_FakeFlow())
    assert len(pipeline.ingested) == 1
    record, schema_class = pipeline.ingested[0]
    assert record["decoded_marker"].startswith("RAW-CAPTURED-BYTES")
    assert schema_class is addon.schema_class


def test_mitmproxy_ignores_unmatched_endpoints(v15):
    pipeline = _StubPipeline()

    class _OtherRequest:
        pretty_url = "https://market.example/unrelated/path"

    class _OtherFlow:
        request = _OtherRequest()
        response = _FakeResponse()

    def _decoder(raw: bytes):
        return {"decoded_marker": raw.decode("utf-8", "replace")}

    addon = v15.MitmproxyStreamInterceptor(
        quant_pipeline=pipeline, schema_class=object, payload_decoder=_decoder
    )
    addon.response(_OtherFlow())
    assert pipeline.ingested == []


# ------------------------------------------------------------------ C. FIGI
PIT_EVENTS = [
    {"ticker": "AAPL", "event_time": "2026-08-25 03:00:00",
     "knowledge_time": "2026-08-25 03:05:00", "metric_value": 182.5},
    {"ticker": "MSFT", "event_time": "2026-08-25 03:10:00",
     "knowledge_time": "2026-08-25 03:15:00", "metric_value": 415.6},
]


def test_pit_engine_reports_figi_unavailable_pandas_path(v15):
    feed = v15.PITQuantEngine().generate_quant_ready_feed(
        [dict(e) for e in PIT_EVENTS], "2026-08-25 03:50:00"
    )
    assert feed["composite_figi"].isna().all()


def test_pit_engine_reports_figi_unavailable_fallback_path(v15, monkeypatch):
    monkeypatch.setitem(sys.modules, "pandas", None)
    feed = v15.PITQuantEngine().generate_quant_ready_feed(
        [dict(e) for e in PIT_EVENTS], "2026-08-25 03:50:00"
    )
    assert all(ev["composite_figi"] is None for ev in feed)


# ------------------------------------------------------------ D. Event time
class Quote(BaseModel):
    ticker: str
    price: float
    event_timestamp: float
    knowledge_timestamp: float


def _ingest_and_read(v15, tmp_path, record, event_time):
    pipeline = v15.QuantPersistencePipeline(output_path=str(tmp_path / "pit.ndjson"))
    asyncio.run(pipeline.ingest_market_record(record, Quote, event_time=event_time))
    asyncio.run(pipeline.close())
    lines = (tmp_path / "pit.ndjson").read_text(encoding="utf-8").splitlines()
    return json.loads(lines[0])


def test_pipeline_preserves_explicit_zero_event_time(v15, tmp_path):
    stored = _ingest_and_read(
        v15, tmp_path, {"ticker": "AAPL", "price": 100.0}, event_time=0.0
    )
    assert stored["event_timestamp"] == 0.0
    assert "event_time_estimated" not in stored


def test_pipeline_flags_missing_event_time_instead_of_inventing_it(v15, tmp_path):
    stored = _ingest_and_read(
        v15, tmp_path, {"ticker": "MSFT", "price": 200.0}, event_time=None
    )
    assert stored["event_time_estimated"] is True
    assert stored["event_timestamp"] == stored["knowledge_timestamp"]


# ------------------------------------------------- E. Entity identifiers
def test_resolver_unknown_company_returns_visibly_synthetic_ids(v15):
    resolver = v15.CapitalMarketEntityResolver()
    resolved = resolver.resolve("Unknown Interstellar Trading Corp")
    assert resolved["synthetic"] is True
    assert resolved["isin"].startswith("SYNTH-")
    assert resolved["cusip"].startswith("SYNTH-")
    assert resolved["figi"].startswith("SYNTH-")
    # Must NOT look like a real ISIN/CUSIP/FIGI:
    assert not resolved["isin"].startswith("US")
    assert not resolved["figi"].startswith("BBG")


def test_resolver_registry_entries_are_non_synthetic(v15):
    resolver = v15.CapitalMarketEntityResolver()
    resolved = resolver.resolve("apple")
    assert resolved["synthetic"] is False
    assert resolved["isin"] == "US0378331005"
    assert resolved["cusip"] == "037833100"
    assert resolved["figi"] == "BBG000B9XVV8"


def test_pipeline_persists_synthetic_markers_for_unresolved_entities(v15, tmp_path):
    class CompanyRecord(BaseModel):
        company: str
        price: float
        isin: str
        cusip: str
        figi: str
        ticker: str
        event_timestamp: float
        knowledge_timestamp: float

    pipeline = v15.QuantPersistencePipeline(output_path=str(tmp_path / "ent.ndjson"))
    asyncio.run(pipeline.ingest_market_record(
        {"company": "Mystery Corp", "price": 5.0}, CompanyRecord
    ))
    asyncio.run(pipeline.close())
    stored = json.loads(
        (tmp_path / "ent.ndjson").read_text(encoding="utf-8").splitlines()[0]
    )
    assert stored["isin"].startswith("SYNTH-")
    assert stored["event_time_estimated"] is True
