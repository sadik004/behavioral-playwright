# Feature Specification: Infrastructure Namespace (`bp.infrastructure`)

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Overview & Capabilities
The `InfrastructureNamespace` ([`bp_facade12.py:560`](file:///c:/Users/User/SAA/bp_facade12.py#L560)) manages WAL-mode SQLite priority task queues, encrypted page caching, and proxy rotation.

---

## 2. API Method Reference

### `init_queue(db_path)` & `push_task(db_path, url, op, priority=0)`
- **Signature**: `def push_task(self, db_path: str, url: str, operation: str, priority: int = 0) -> int`
- **Description**: Inserts a new task with integer priority into the SQLite task queue.

### `pop_task(db_path)` & `complete_task(db_path, task_id)`
- **Signature**: `def pop_task(self, db_path: str) -> Optional[Dict[str, Any]]` & `def complete_task(self, db_path: str, task_id: int) -> bool`
- **Description**: Atomically transitions highest-priority pending task to `running` or `completed`.

### `init_cache(db_path)` & `save_to_cache(db_path, url, html, md)`
- **Signature**: `def save_to_cache(self, db_path: str, url: str, html: str, md: str) -> bool`
- **Description**: Applies SHA256-XOR encryption to HTML/Markdown and saves to `cached_pages` table.

### `get_cached_page(db_path, url)`
- **Signature**: `def get_cached_page(self, db_path: str, url: str) -> Optional[Dict[str, Any]]`
- **Description**: Decrypts and returns cached page payload if present.
