# Observability & Metrics Usage Guide

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Trace Latency Timers & QA Reporting

Track operational latencies and generate automated pass/fail QA summary reports:

```python
from bp_facade12 import BP
import time

bp = BP()
db_path = "observability.db"

# 1. Initialize metrics database (schema runs once)
bp.observability.init_metrics_db(db_path)

# 2. Track execution with trace timer
bp.observability.start_trace("checkout_trace")
time.sleep(0.05) # simulate action
elapsed_ms = bp.observability.end_trace("checkout_trace", url="https://example.com/checkout", db_path=db_path)
print(f"Checkout completed in {elapsed_ms:.2f} ms")

# 3. Generate QA Report
qa_report = bp.observability.generate_qa_report(db_path)
print("QA Status:", qa_report["status"])
print("Total Ops Executed:", qa_report["total_executed_ops"])
print("Average Op Duration (ms):", qa_report["average_duration_ms"])
```
