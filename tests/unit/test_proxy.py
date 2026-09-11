"""Unit tests for proxy pool, rotation, and health management."""

from behavioral_playwright.proxy.models import ProxyNode, ProxyProtocol, ProxyRotationStrategy
from behavioral_playwright.proxy.pool import ProxyPool


def test_proxy_node_properties():
    node = ProxyNode(host="1.2.3.4", port=8080, protocol=ProxyProtocol.HTTP, username="usr", password="pwd")
    assert node.url == "http://usr:pwd@1.2.3.4:8080"
    assert node.is_available is True
    assert node.success_rate == 1.0

    node.record_success(latency_ms=45.0)
    assert node.total_requests == 1
    assert node.last_latency_ms == 45.0
    assert node.success_rate == 1.0

    node.record_failure(quarantine_seconds=10.0)
    assert node.total_requests == 2
    assert node.failed_requests == 1
    assert node.success_rate == 0.5
    assert node.is_available is False


def test_proxy_pool_rotation_strategies():
    pool = ProxyPool(strategy=ProxyRotationStrategy.ROUND_ROBIN)
    p1 = pool.add_proxy("1.1.1.1", 8080, tags=["us"])
    pool.add_proxy("2.2.2.2", 8080, tags=["uk"])
    pool.add_proxy("3.3.3.3", 8080, tags=["us"])

    assert pool.total_count == 3
    assert pool.available_count == 3

    # Round Robin
    n1 = pool.get_proxy()
    n2 = pool.get_proxy()
    n3 = pool.get_proxy()
    assert {n1.host, n2.host, n3.host} == {"1.1.1.1", "2.2.2.2", "3.3.3.3"}

    # Tag filtering
    us_node = pool.get_proxy(tag="us")
    assert us_node.host in ("1.1.1.1", "3.3.3.3")

    # Sticky Session
    s_node1 = pool.get_proxy(session_id="session_abc", sticky_ttl_seconds=5.0)
    s_node2 = pool.get_proxy(session_id="session_abc")
    assert s_node1 == s_node2

    # Quarantine behavior
    pool.report_failure(p1, quarantine_seconds=10.0)
    assert p1.is_available is False
    assert pool.available_count == 2
