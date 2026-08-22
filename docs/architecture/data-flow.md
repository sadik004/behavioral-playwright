# Data Flow & Storage Architecture

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Storage Layers

Behavioral Playwright utilizes SQLite in Write-Ahead Logging (`WAL`) mode for all local persistence needs, guaranteeing ACID compliance and high-concurrency multi-process read/write performance.

```text
Local Storage Engines (SQLite WAL)
├── 1. crawl_state.db        (Crawl URL queue, depths, and completion statuses)
├── 2. cache.db              (SHA256-XOR Encrypted HTML and Markdown page cache)
├── 3. tasks.db              (FIFO / Priority task queue with retry counters)
└── 4. metrics.db            (Execution latencies, error states, and session replay DOMs)
```

---

## 2. Encryption Mechanism (`InfrastructureNamespace`)

To protect cached HTML payloads from leaking personally identifiable information (PII) on disk, the infrastructure namespace applies symmetric stream encryption:

$$\text{Ciphertext} = \text{Plaintext Bytes} \oplus \text{SHA256}(\text{Encryption Key})$$

This lightweight cipher introduces sub-millisecond encryption/decryption overhead while preventing plaintext DOM exposure in SQLite dumps.
