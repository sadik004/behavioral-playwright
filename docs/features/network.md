# Feature Specification: Network Namespace (`bp.network`)

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Overview & Capabilities
The `NetworkNamespace` ([`bp_facade12.py:1177`](file:///c:/Users/User/SAA/bp_facade12.py#L1177)) provides real HTTP/network latency probing, custom header injection, and Gzip payload compression.

---

## 2. API Method Reference

### `measure_response_time(url)` & `measure_response_time_async(url)`
- **Signature**: `def measure_response_time(self, url: str) -> float` & `async def measure_response_time_async(self, url: str) -> float`
- **Description**: Probes target URL using HTTP `HEAD` (with `405` fallback to `GET`) and returns round-trip duration in milliseconds using monotonic timers (`time.perf_counter`).
- **Throws**: `ValueError` on invalid URL scheme; `TimeoutError` on socket timeout; `ConnectionError` on host failure.

### `compress_payload(data)` & `decompress_payload(data_bytes)`
- **Signature**: `def compress_payload(self, data: str) -> bytes` & `def decompress_payload(self, data: bytes) -> str`
- **Description**: Compresses string payloads via `gzip` with internal tracking of bandwidth savings.
