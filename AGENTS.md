# Enterprise Architectural Governance & Multi-Skill Routing

## 1. Multi-Skill Routing Matrix
- **Backend, Database, API, & DSA Tasks**:
  - Strictly enforce and adhere to `.agents/skills/fastapi-production/SKILL.md`.
  - Enforce 3-tier clean architecture (`Routers -> Services -> Repositories -> Models/Schemas`).
  - Never use `float` for financial/currency math (strictly `Decimal(18, 4)`).
  - Never mutate historical database records without double-entry audit trails.
  - Zero raw SQL in routers/services; enforce parameterization and Protocol repository abstractions.
- **Web Automation, Scraping, Playwright, & Crawler Tasks**:
  - Strictly enforce and adhere to `.agents/skills/scraping-production/SKILL.md` and `.agents/skills/browser-automation/SKILL.md`.
  - Enforce Single Browser multi-context pooling (`BrowserPoolManager`); never launch a new browser process per request.
  - Strictly ban arbitrary sleeps (`time.sleep`, `asyncio.sleep` with magic numbers, `page.wait_for_timeout`); enforce auto-waiting and dynamic DOM mutation checks.
  - Enforce route-level asset abortion (images, fonts, stylesheets, tracking beacons) to preserve bandwidth and heap memory.
  - Strictly ban fragile absolute XPaths; prioritize `data-testid`, semantic ARIA roles, and scoped CSS locators.
  - Never allow raw extracted dicts to escape the scraping layer; validate all scraped data through typed Pydantic DTO models.
  - Apply AWS Full-Jitter Exponential Backoff on HTTP 429/503 responses.

## 2. Core Operational Invariants
- **Plan-First**: Generate implementation plan before executing multi-file modifications.
- **Zero Hand-Waving**: Strictly no `# TODO: implement rest` or `pass` placeholders in production code.
- **2-Strike Rule**: If a test, selector, or command fails twice, immediately halt, perform root-cause analysis (RCA), and re-plan.
- **Radical Anti-Sycophancy ("জিরো তেলবাজি" পলিসি)**: Deliver objective, mathematically grounded engineering facts. Flattery, emotional theatrics, or agreeing with flawed premises is strictly prohibited.
- **Mandatory Terminal Verification**: Never declare work complete without executing automated terminal quality gates and confirming exit code 0.
