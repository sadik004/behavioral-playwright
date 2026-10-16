"""
Out-Of-Band (OOB) Interaction Gathering Test Suite
Validates Interactsh protocol, Mock OOB Provider, MasterOOBClient,
and Facade integration (BPFacade & UnifiedQuantumFacade).
"""

import pytest
import asyncio
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
for p in [ROOT_DIR, SRC_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from behavioral_evasion_suite.oob_listener import (
    OOBProviderProtocol,
    MockOOBProvider,
    InteractshOOBProvider,
    MasterOOBClient
)
from behavioral_evasion_suite.unified_quantum_facade import UnifiedQuantumFacade
from behavioral_playwright import BP


def test_01_oob_protocol_runtime_checkability():
    """Verify that Mock and Interactsh providers conform to OOBProviderProtocol."""
    mock_prov = MockOOBProvider()
    interactsh_prov = InteractshOOBProvider()

    assert isinstance(mock_prov, OOBProviderProtocol)
    assert isinstance(interactsh_prov, OOBProviderProtocol)
    assert mock_prov.provider_name == "MockOOBProvider"
    assert interactsh_prov.provider_name == "InteractshOOBProvider"


@pytest.mark.asyncio
async def test_02_mock_oob_provider_lifecycle_and_simulation():
    """Verify Mock OOB provider registration, payload creation, simulation, and polling."""
    prov = MockOOBProvider(base_domain="test.oast.internal")
    assert await prov.register() is True

    payload = prov.generate_payload(marker="ssrf_probe_01")
    assert "ssrf_probe_01" in payload
    assert "test.oast.internal" in payload

    # Simulate an incoming DNS callback
    prov.simulate_interaction(
        correlation_marker="ssrf_probe_01",
        protocol="dns",
        remote_addr="192.168.1.100",
        raw_req="DNS A query received"
    )

    events = await prov.poll_interactions()
    assert len(events) == 1
    assert events[0].unique_id == "ssrf_probe_01"
    assert events[0].protocol == "dns"
    assert events[0].remote_address == "192.168.1.100"

    # Verify polling drains the buffer
    empty_events = await prov.poll_interactions()
    assert len(empty_events) == 0

    await prov.close()


@pytest.mark.asyncio
async def test_03_master_oob_client_tracking_and_async_waiting():
    """Verify MasterOOBClient domain tracking and asynchronous wait_for_interaction."""
    mock_prov = MockOOBProvider()
    client = MasterOOBClient(provider=mock_prov)
    await client.initialize()

    info = client.generate_tracking_domain(context_tag="blind_xxe")
    marker = info["marker"]
    assert marker in info["domain"]
    assert info["http_url"].startswith("http://")

    # In background, simulate a callback after a short delay
    async def delayed_callback():
        await asyncio.sleep(0.1)
        mock_prov.simulate_interaction(
            correlation_marker=marker,
            protocol="http",
            remote_addr="10.0.0.1",
            raw_req="GET / HTTP/1.1"
        )

    asyncio.create_task(delayed_callback())

    event = await client.wait_for_interaction(marker=marker, timeout_seconds=2.0, poll_interval=0.05)
    assert event is not None
    assert event.unique_id == marker
    assert event.protocol == "http"

    await client.close()


def test_04_unified_quantum_facade_oob_integration():
    """Verify UnifiedQuantumFacade exposes oob_listener and create_oob_client."""
    facade = UnifiedQuantumFacade()
    assert hasattr(facade.security, "oob")
    assert hasattr(facade.security, "create_oob_client")
    assert hasattr(facade, "oob_listener")

    oob = facade.oob_listener
    assert oob is not None
    assert isinstance(oob, MasterOOBClient)

    custom_oob = facade.security.create_oob_client(use_mock=True)
    assert isinstance(custom_oob.provider, MockOOBProvider)


def test_05_bp_facade_security_oob_integration():
    """Verify BPFacade bp.security.oob_listener() creates functional clients."""
    bp = BP()
    assert hasattr(bp.security, "oob_listener")
    
    oob = bp.security.oob_listener(use_mock=True)
    assert oob is not None
    assert isinstance(oob, MasterOOBClient)
    assert isinstance(oob.provider, MockOOBProvider)

    track = oob.generate_tracking_domain("graphql_webhook")
    assert "graphql_webhook" in track["marker"]


@pytest.mark.asyncio
async def test_06_interactsh_provider_keypair_generation():
    """Verify Interactsh RSA keypair generation and offline fallback resilience."""
    interactsh = InteractshOOBProvider(server_url="https://invalid.oast.local", timeout=1.0)
    # Registration should succeed using either key generation or resilient fallback
    res = await interactsh.register()
    assert res is True
    assert interactsh.correlation_id != ""
    assert len(interactsh.correlation_id) == 20

    payload = interactsh.generate_payload("probe123")
    assert "probe123" in payload
    assert interactsh.correlation_id in payload

    await interactsh.close()
