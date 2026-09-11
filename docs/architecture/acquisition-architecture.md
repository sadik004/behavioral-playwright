# Acquisition Architecture

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. The Acquisition Pipeline

The acquisition subsystem abstracts web content retrieval through a standardized request/response model.

```text
[Input URL / HTML]
        │
        ▼
[AcquisitionRequest] ──► {url, format, include_tags, exclude_tags, timeout}
        │
        ▼
[AcquisitionRouter] ──► Checks local vs. provider availability
        │
        ├────────────────────────────────┐
        ▼                                ▼
[Local BeautifulSoup Engine]     [Optional Cloud Provider]
   (DOM Tag Stripping)             (Firecrawl / External)
        │                                │
        └────────────────┬───────────────┘
                         ▼
                [AcquisitionResult] ──► {content, markdown, status, metadata}
```

---

## 2. Recursive Crawling Engine ([`WebNamespace.crawl_recursive`](file:///c:/Users/User/SAA/bp_facade12.py#L90))

The crawler operates as a bounded, breadth-first traversal system backed by SQLite persistence:

1. **Session Initialization**: Creates a table `crawl_state (url PRIMARY KEY, depth, status, discovered_at)` in the local SQLite database.
2. **Queueing & Domain Boundary**: Seeds the starting URL at `depth=0`. For every acquired page, extracts links via `<a>` tags and filters them using `filter_crawl_links` to enforce domain isolation and strip binary assets.
3. **Loop Detection**: Evaluates redirect sequences against `detect_redirection_loops` to halt traversal if cyclical URL traps are detected.
4. **Resilience**: Errors on individual pages are caught and recorded as `failed` without halting the overarching crawl session.
