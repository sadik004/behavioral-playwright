# Dependency Map & Boundary Architecture

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. System Dependency Graph

Behavioral Playwright is designed with strict layering to prevent circular imports and minimize mandatory external packages.

```text
Layer 4: Unified Facade (BP)
    │
    ▼
Layer 3: Domain Namespaces
    ├── WebNamespace
    ├── BrowserNamespace
    ├── DocumentNamespace
    ├── AINamespace
    ├── NetworkNamespace
    ├── IntegrationsNamespace
    ├── InfrastructureNamespace
    ├── ObservabilityNamespace
    └── AdvancedIntelligenceNamespace
    │
    ▼
Layer 2: Engine Protocols & Core Subsystems
    ├── AcquisitionRouter & Models (AcquisitionRequest / AcquisitionResult)
    ├── BehavioralHumanizer (Mouse/Keyboard/Scroll math)
    ├── SelfHealingResolver (L1 Exact -> L2 Semantic -> L3 Fuzzy)
    ├── SQLite Session & Cache Layer
    └── Stealth CDP Injections
    │
    ▼
Layer 1: External Libraries & Standard Library
    ├── Core Standard Lib: asyncio, urllib.request, sqlite3, json, math, random, time, re
    ├── Web & DOM: beautifulsoup4
    ├── Browser: playwright (Chromium)
    ├── Document & OCR: Pillow, pytesseract, pypdf, python-docx
    └── Security: hashlib (SHA256)
```

---

## 2. Hard vs. Optional Dependencies

| Component / Subsystem | Hard Dependency | Optional / External Binary | Fallback Behavior if Missing |
| :--- | :--- | :--- | :--- |
| **`bp.web`** | `beautifulsoup4` | None | None (Required for DOM parsing) |
| **`bp.browser`** | `playwright` | Playwright Chromium binary | Raises `BrowserLaunchError` on boot |
| **`bp.document` (OCR)** | `Pillow`, `pytesseract` | System `tesseract` binary | Raises `ProviderUnavailableError` |
| **`bp.document` (PDF)** | `pypdf` | None | Raises `ImportError` if not installed |
| **`bp.ai` (Ranking)** | Python standard library | None | Self-contained UTF-8 TF-IDF engine |
| **`bp.network`** | Python standard library | None | Self-contained `urllib.request` prober |
| **`bp.integrations`**| Python standard library | None | Self-contained JSON HTTP POST dispatcher |
| **`bp.infrastructure`**| Python standard library (`sqlite3`) | None | Self-contained WAL-mode storage |
| **`bp.observability`** | Python standard library (`sqlite3`) | None | Self-contained metric engine |
