# Claim Registry & Verification Ledger

**Repository**: `sadik004/behavioral-playwright`  
**Governance Standard**: Radical Anti-Sycophancy & Zero-Fraud Engineering  
**Registry File**: `integrity/claims.json`  

---

## 1. Claim Status Taxonomy
Every claim extracted from documentation, docstrings, or architectural specs is mapped to an independent oracle and classified into one of the following binding states:

- **VERIFIED**: Runtime or AST empirical evidence validates the claim under all conditions.
- **PARTIALLY_VERIFIED**: Core functionality functions, but edge cases, fallback branches, or parameter contracts are incomplete or unverified.
- **UNVERIFIED**: Implementation exists, but lacks independent runtime verification against an external or controlled environment.
- **CONTRADICTED**: Documented claim is directly contradicted by actual source code behavior or runtime failures.
- **PROVIDER_GATED**: Feature depends on an uninstalled optional provider; verified to report `PROVIDER_UNAVAILABLE` honestly without fake success.
- **SIMULATION_ONLY**: Operation is emulated purely in software/memory; claims of hardware execution or physical effects are unsupported.
- **UNIMPLEMENTED**: Declared interface has no underlying implementation (`pass` or `NotImplementedError`).

---

## 2. High-Severity Contradictions & Discovered Malpractice (P0 / P1)

### `EVASION-001` (Severity: P0) — Fake Success via Silent Fallback
- **Documented Claim**: `PowerHandPlaywrightRunner.execute_stealth_session` executes a live browser session with comprehensive evasion.
- **Code Target**: `behavioral_evasion_suite/powerhand_master.py:120-132`
- **Observed Behavior**: If any exception occurs during live Playwright execution, it is caught:
  ```python
  except Exception as e:
      return {"status": "dry_run_success", "error": str(e), ...}
  ```
- **Integrity Violation**: Live execution failure is converted to `"dry_run_success"`. In existing tests, `assert "success" in res["status"]` evaluates to `True`, concealing the browser failure.
- **Status**: **CONTRADICTED**

---

### `EVASION-002` (Severity: P1) — Unseeded Global Jitter in Saccades
- **Documented Claim**: `PowerHandMaster.get_saccade_path` accepts `seed: Optional[int] = None` and provides deterministic, reproducible trajectories.
- **Code Target**: `behavioral_evasion_suite/powerhand_master.py:70-71`
- **Observed Behavior**: The method accepts `seed`, but internal tremor generation invokes:
  ```python
  tremor = random.uniform(0.5, 1.5)  # Global unseeded random generator!
  ```
- **Integrity Violation**: Repeated runs with identical seeds produce drifting coordinates. Determinism contract is breached.
- **Status**: **CONTRADICTED**

---

### `EVASION-005` (Severity: P1) — Physical PCIe Screamer Card DMA Simulation
- **Documented Claim**: `FPGAPCIeDMAHardwareBridge` sends direct PCIe DMA Screamer hardware HID packets.
- **Code Target**: `behavioral_evasion_suite/dma_kernel_bridge.py:150-163`
- **Observed Behavior**: When `/dev/pcie_dma0` or `\\\\.\\PCIe_DMA0` is missing, it falls back to software simulation or OS SendInput.
- **Integrity Status**: Pure software emulation. Classified as **SIMULATION_ONLY**.

---

### `RELIABILITY-001` (Severity: P1) — Duplicate Exception Hierarchy
- **Documented Claim**: `behavioral_playwright.exceptions.ProviderUnavailableError` is the standard exception for missing providers.
- **Code Target**:
  - `src/behavioral_playwright/exceptions.py` (inherits from `BehavioralPlaywrightError`)
  - `src/behavioral_playwright/providers/base.py` (inherits from `RuntimeError`)
- **Integrity Violation**: Missing providers raise `providers.base.ProviderUnavailableError`, which is NOT caught by `except exceptions.ProviderUnavailableError` or `except exceptions.BehavioralPlaywrightError`.
- **Status**: **PARTIALLY_VERIFIED** (Gating is honest, but exception hierarchy is fractured).

---

## 3. Full 28-Claim Audit Summary Table

| Claim ID | Category | Target Component | Status | Severity |
|:---|:---|:---|:---|:---|
| `EVASION-001` | Evasion | `PowerHandPlaywrightRunner` | **CONTRADICTED** | P0 |
| `EVASION-002` | Evasion | `PowerHandMaster.get_saccade_path` | **CONTRADICTED** | P1 |
| `EVASION-003` | Evasion | `PowerHandMaster.get_all_stealth_scripts` | **PARTIALLY_VERIFIED** | P2 |
| `EVASION-004` | Evasion | `WindowsKernelInputEventBridge` | **PARTIALLY_VERIFIED** | P2 |
| `EVASION-005` | Evasion | `FPGAPCIeDMAHardwareBridge` | **SIMULATION_ONLY** | P1 |
| `RESILIENCE-001` | Resilience | `CircuitBreaker` 3-State Machine | **VERIFIED** | P1 |
| `RESILIENCE-002` | Resilience | `BrowserPoolManager` Lifecycle | **VERIFIED** | P0 |
| `SELECTORS-001` | Selectors | `SelfHealingSelectorEngine` | **PARTIALLY_VERIFIED** | P1 |
| `STORAGE-001` | Storage | `DataStorageManager.export` | **VERIFIED** | P1 |
| `STORAGE-002` | Storage | `CrawlStateManager` SQLite State | **VERIFIED** | P2 |
| `OBSERVABILITY-001`| Observability | `ObservabilityMetrics` O(1) Lookups | **VERIFIED** | P2 |
| `OBSERVABILITY-002`| Observability | `JSONResponseSniffer` Non-destructive | **VERIFIED** | P2 |
| `POWERPLAY-001` | PowerPlay | `BiomechanicalTrajectoryEngine` | **PARTIALLY_VERIFIED** | P1 |
| `POWERPLAY-002` | PowerPlay | `LinguisticKeystrokeDynamics` Weibull | **VERIFIED** | P2 |
| `POWERPLAY-003` | PowerPlay | `ChromiumMemoryPIDController` | **PARTIALLY_VERIFIED** | P2 |
| `POWERPLAY-004` | PowerPlay | `ResolvedSchemaIntegrityGuard` Entropy | **VERIFIED** | P1 |
| `POWERPLAY-005` | PowerPlay | `VisionActionLanguageGuard` GIoU Click | **PARTIALLY_VERIFIED** | P1 |
| `POWERPLAY-006` | PowerPlay | `BiometricKSValidator` Two-Sample KS | **PARTIALLY_VERIFIED** | P1 |
| `POWERPLAY-007` | PowerPlay | `AdaptiveCaptchaLoopBreaker` | **VERIFIED** | P1 |
| `QUANT-001` | Quant | `GumbelCopulaEngine` Multi-touch Jitter| **VERIFIED** | P2 |
| `QUANT-002` | Quant | `MarketStructureAnalyzer` Price Levels | **VERIFIED** | P2 |
| `PROVIDERS-001` | Providers | `PatchrightProvider` Honest Gating | **PROVIDER_GATED** | P1 |
| `PROVIDERS-002` | Providers | `UndetectedChromedriverProvider` | **PROVIDER_GATED** | P1 |
| `PROVIDERS-003` | Providers | `BrowserUseProvider` Honest Gating | **PROVIDER_GATED** | P1 |
| `MCP-001` | MCP | `McpToolDispatcher` Tool Registry | **VERIFIED** | P1 |
| `MCP-002` | MCP | `McpToolDispatcher` Input Validation | **VERIFIED** | P1 |
| `API-001` | Facade | `BP` High-Level Unified Facade | **PARTIALLY_VERIFIED** | P1 |
| `API-002` | CLI | `behavioral-playwright` Click CLI | **VERIFIED** | P2 |
