# Network Measurement & Diagnostics Guide

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Measuring Server Response Time

Perform low-overhead HTTP `HEAD` probes with automatic `405 Method Not Allowed` fallback to `GET`:

```python
import asyncio
from bp_facade12 import BP

async def test_latency():
    async with BP() as bp:
        # Async latency probe
        latency_ms = await bp.network.measure_response_time_async("https://example.com")
        print(f"Target Server Latency: {latency_ms:.2f} ms")

if __name__ == "__main__":
    asyncio.run(test_latency())
```

---

## 2. Gzip Payload Compression

```python
data_str = "A" * 10000
compressed = bp.network.compress_payload(data_str)
print(f"Original: {len(data_str)} bytes | Compressed: {len(compressed)} bytes")
```
