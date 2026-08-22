# Infrastructure Usage Guide (Queue & Cache)

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. SQLite WAL Task Queue

Manage asynchronous automation queues across background worker processes:

```python
from bp_facade12 import BP

bp = BP()
db_path = "crawler_tasks.db"

# Initialize queue
bp.infrastructure.init_queue(db_path)

# Push high-priority task
task_id = bp.infrastructure.push_task(
    db_path,
    url="https://example.com/item/101",
    operation="extract",
    priority=10
)

# Pop task in worker
task = bp.infrastructure.pop_task(db_path)
if task:
    print(f"Processing Task ID {task['id']} on {task['url']}")
    # ... do work ...
    bp.infrastructure.complete_task(db_path, task["id"])
```

---

## 2. Encrypted Page Caching

```python
# Encrypt and save DOM payload
bp.infrastructure.init_cache("page_cache.db")
bp.infrastructure.save_to_cache(
    "page_cache.db",
    url="https://example.com",
    html="<html>Secret DOM</html>",
    md="# Secret DOM"
)

# Retrieve and decrypt
cached = bp.infrastructure.get_cached_page("page_cache.db", "https://example.com")
print("Cached HTML:", cached["html"])
```
