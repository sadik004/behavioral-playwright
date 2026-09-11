# V10 Quantum Core Heritage

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [HISTORICAL & ARCHITECTURAL]

---

## 1. Context of the V10 Architecture

The earliest complete foundation of the project was preserved in commit `8e089b6` (`stealth-playwright-framework-v10-quantum.py`, 3,389 LOC) and the original `src/behavioral_playwright/` tree.

### Key Innovations in V10 Quantum
1. **Mathematical Physics Engine**: Modeled mouse movements using non-linear dynamical systems (Lorenz Attractor differential equations, Bézier curves, and Fractional Brownian Motion micro-tremors).
2. **SigmaDrift Mouse Velocity**: Modeled human muscle inertia with acceleration, jerk limits, and decay constants.
3. **Resilient Circuit Breaker**: Introduced the 3-state state machine (`CLOSED`, `OPEN`, `HALF_OPEN`) to prevent cascading browser crashes.
4. **Cloak Browser Provider**: Dedicated CDP launcher wrapping Chromium with runtime stealth modifications.

---

## 2. Why V10 Was Refactored

While mathematically sophisticated, the V10 monolithic prototype suffered from:
- Heavy dependency coupling (requiring scientific libraries for basic automation).
- Complex, monolithic file structure difficult to test in isolation.
- Lack of high-level workflow abstractions (such as recursive crawling or document extraction).

These insights drove the v1.0.0 clean-room rewrite and the current 9-namespace consolidated facade.
