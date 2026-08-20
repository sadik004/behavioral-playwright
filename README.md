<div align="center">

# 🎭 Behavioral Playwright `v10.0.0` (Quantum Edition)

### *Production-Grade Humanized Automation, Resilient Browser Orchestration & Self-Healing AI/CV Framework*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square&logo=opensourceinitiative&logoColor=white)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Engine-Playwright%20Chromium-green.svg?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev/)
[![Tests: 100% Pass](https://img.shields.io/badge/Tests-33%2F33%20Passed-brightgreen.svg?style=flat-square)](https://github.com/)
[![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-000000.svg?style=flat-square&logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![Type Checked: Mypy](https://img.shields.io/badge/Type%20Checked-Mypy-informational.svg?style=flat-square&logo=python&logoColor=white)](https://mypy-lang.org/)

<p align="center">
  <b><code>behavioral-playwright</code></b> is a modular, deterministic, and highly testable Python automation framework designed to simulate realistic human physiology over web browsers. It integrates biological muscle dynamics (C1-Smoothstep, SigmaDrift lognormal CDF, Ornstein-Uhlenbeck lateral drift, Signal-Dependent Noise), Weibull typing latency models, a 3-state Circuit Breaker, Shannon entropy Markov loop detection, and a 4-tier Cascading Self-Healing AI/CV resolver.
</p>

---

</div>

## 📑 Table of Contents

- [✨ Key Features](#-key-features)
- [📦 Installation Guide](#-installation-guide)
- [📖 Step-by-Step Usage Guide](#-step-by-step-usage-guide)
  - [Step 1: Configuration Setup](#step-1-configuration-setup)
  - [Step 2: Launching Browser via Factory](#step-2-launching-browser-via-factory)
  - [Step 3: Resilient Navigation with Circuit Breaker](#step-3-resilient-navigation-with-circuit-breaker)
  - [Step 4: Biomechanical Mouse Movements](#step-4-biomechanical-mouse-movements)
  - [Step 5: Realistic Human Typing & Typo Handling](#step-5-realistic-human-typing--typo-handling)
  - [Step 6: Newtonian Physics Inertial Scroll](#step-6-newtonian-physics-inertial-scroll)
  - [Step 7: 4-Tier Self-Healing Dynamic Selectors](#step-7-4-tier-self-healing-dynamic-selectors)
  - [Step 8: Captcha Challenge Handling](#step-8-captcha-challenge-handling)
  - [Step 9: Connecting to Existing Chrome (CDP Remote Debugger)](#step-9-connecting-to-existing-chrome-cdp-remote-debugger)
  - [Step 10: Deterministic Fast CI Testing](#step-10-deterministic-fast-ci-testing)
- [📋 Complete Copy-Paste Templates](#-complete-copy-paste-templates)
  - [Template 1: Full E-Commerce / Login & Form Submission](#template-1-full-e-commerce--login--form-submission)
  - [Template 2: Anti-Bot Web Scraping & Data Extraction](#template-2-anti-bot-web-scraping--data-extraction)
- [🏛️ Architecture & System Design](#️-architecture--system-design)
- [📐 Mathematical Biomechanics](#-mathematical-biomechanics)
- [🤖 4-Tier Self-Healing AI & CV Pipeline](#-4-tier-self-healing-ai--cv-pipeline)
- [🔌 Resilient Circuit Breaker Navigation](#-resilient-circuit-breaker-navigation)
- [🏭 Multi-Provider Cascading Fallback](#-multi-provider-cascading-fallback)
- [⚙️ Full Configuration Reference](#️-full-configuration-reference)
- [🔍 Real Implementation vs Simulation Matrix](#-real-implementation-vs-simulation-matrix)
- [🧪 Testing & Quality Assurance](#-testing--quality-assurance)
- [📄 License](#-license)

---

## ✨ Key Features

* **🧠 Physiological Humanizer**: Replaces synthetic browser clicks with biomechanical mouse trajectories modeled on human motor control laws (Fitts's Law, Lorenz Attractors, Fractional Brownian Motion muscle tremors).
* **⌨️ Realistic Typing Engine**: Simulates authentic human keystroke rhythms using Weibull distributions, motor memory bigram acceleration, QWERTY Euclidean key distance penalties, and natural typo injection with backspace auto-correction.
* **🛡️ 4-Tier Self-Healing Selectors**: When DOM elements shift or change dynamic IDs, the cascading engine automatically resolves target elements via:
  1. **L1**: Deterministic Levenshtein distance matching against interactive DOM candidates.
  2. **L2**: Semantic Accessibility DOM attribute matching (`role`, `aria`, `text`, `name`).
  3. **L3**: Computer Vision & OCR spatial coordinate localization.
  4. **L4**: LLM cognitive visual reasoning and structured JSON action proposal.
* **🔄 Resilient Circuit Breaker**: Protects automation pipelines from cascade failures using a 3-state state machine (`CLOSED`, `OPEN`, `HALF_OPEN`) combined with exponential backoff and jitter.
* **🌀 Markov Loop Detection**: Calculates exact Shannon entropy across state transitions to instantly identify and escape cyclic navigation deadlocks and redirection loops.
* **🔀 Multi-Provider Orchestration**: Seamlessly cascades across browser providers: **CDP Remote Debugger** $\rightarrow$ **CloakBrowser C++** $\rightarrow$ **Hardened Playwright** $\rightarrow$ **Zero-Dependency Mock Container**.
* **🧩 100% Dependency Injection**: Fully decoupled from system clocks and entropy sources via `Clock` and `RandomSource` protocols, allowing instant, deterministic unit testing without wall-clock sleep delays.

---

## 📦 Installation Guide

### Option 1: Install from PyPI (Recommended)
```bash
pip install behavioral-playwright
playwright install chromium
```

### Option 2: Install from Source (Editable Mode)
```bash
git clone https://github.com/sadik004/behavioral-playwright.git
cd behavioral-playwright
pip install -e .
playwright install chromium
```

---

## 📖 Step-by-Step Usage Guide

### Step 1: Configuration Setup
All parameters are structured into strongly-typed, immutable dataclasses:

```python
from behavioral_playwright import (
    AutomationConfig,
    BrowserConfig,
    ClickConfig,
    KeyboardConfig,
    MouseConfig,
    NetworkConfig,
    AIConfig,
)

# Configure according to your automation requirements
config = AutomationConfig(
    browser=BrowserConfig(
        headless=False,            # Set to False to view browser UI; True for background headless execution
        user_data_dir="./profile"  # Directory to persist user cookies, session tokens, and local cache
    ),
    click=ClickConfig(
        pre_click_delay_min=0.08,  # Human eye-hand hesitation delay (80ms - 150ms)
        pre_click_delay_max=0.15
    ),
    keyboard=KeyboardConfig(
        mistake_probability=0.015  # 1.5% natural typo injection with automatic backspace correction
    ),
    ai=AIConfig(
        enabled=True,
        self_healing_enabled=True  # Enables dynamic element self-healing
    )
)
```

---

### Step 2: Launching Browser via Factory
`BrowserProviderFactory` initializes the browser context and automatically falls back to healthy alternatives if initialization fails:

```python
import asyncio
from behavioral_playwright import BrowserProviderFactory, BrowserLifecycleManager, AutomationConfig

async def main():
    config = AutomationConfig()
    # Launch browser provider (cascades: CDP -> Cloak -> Playwright -> Mock)
    context, provider = await BrowserProviderFactory.launch_stabilized_lifecycle(config)

    # Use BrowserLifecycleManager for guaranteed graceful cleanup and pipe drainage
    async with BrowserLifecycleManager(provider, context=context) as manager:
        page = manager.context.pages[0] if manager.context.pages else await manager.context.new_page()
        print(f"Browser launched successfully: {page}")

asyncio.run(main())
```

---

### Step 3: Resilient Navigation with Circuit Breaker
Safely open URLs with automated exponential backoff, retry mechanisms, and Markov loop detection:

```python
from behavioral_playwright import NavigationManager, CircuitBreaker

# Initialize Circuit Breaker and Navigation Manager
circuit_breaker = CircuitBreaker()
navigator = NavigationManager(config, circuit_breaker)

# safe_goto automatically handles retries, backoff delays, and cyclic redirection loops
success = await navigator.safe_goto(page, "https://example.com")
if not success:
    print("Navigation failed or circuit breaker tripped open.")
```

---

### Step 4: Biomechanical Mouse Movements
Generates natural cursor trajectories using C1-Continuous Smoothstep Bézier curves, Lorenz chaotic attractors, and Fitts's Law:

```python
from behavioral_playwright import BehavioralHumanizer

human = BehavioralHumanizer(page, config)

# 1. Move cursor smoothly to designated screen coordinates
await human.move_mouse_to(target_x=450.0, target_y=300.0, steps=25)

# 2. Perform chained sequential mouse sweeps across multiple waypoints
await human.move_mouse_sequence([(100.0, 100.0), (300.0, 200.0), (500.0, 400.0)])
```

---

### Step 5: Realistic Human Typing & Typo Handling
Simulates natural typing cadence, motor-memory bigram acceleration, and typo recovery:

```python
# Types string using human keystroke rhythms and QWERTY distance penalties
await human.human_type("#username-field", "admin@company.com")
await human.human_type("#password-field", "SecureP@ssw0rd2026")
```

---

### Step 6: Newtonian Physics Inertial Scroll
Simulates smooth mouse-wheel or trackpad scrolling with Newtonian inertial deceleration:

```python
# Smoothly scroll down 500 pixels along the Y-axis
await human.human_scroll(distance_y=500.0)

# Pass negative values to scroll upward
await human.human_scroll(distance_y=-300.0)
```

---

### Step 7: 4-Tier Self-Healing Dynamic Selectors
Interacts with elements whose IDs or classes change dynamically (e.g., `#btn-submit-9821`):

```python
# execute_safe_click resolves dynamic target selectors across 4 cascading tiers
click_success = await human.execute_safe_click(
    target_selector="#dynamic-checkout-btn-xyz",
    expected_content="Checkout"
)

# execute_safe_type resolves dynamic input fields with self-healing verification
type_success = await human.execute_safe_type(
    target_selector="#promo-code-input-dynamic",
    text_to_type="DISCOUNT2026",
    expected_content="Promo Code"
)
```

---

### Step 8: Captcha Challenge Handling
Intercepts and solves verification challenges using pluggable solvers:

```python
# Detect and solve verification challenges (e.g., Cloudflare Turnstile)
solver = human.solver
solved = await solver.solve(page, "Cloudflare Turnstile")
```

---

### Step 9: Connecting to Existing Chrome (CDP Remote Debugger)
Connects directly to an already running Chrome browser instance:

```python
# 1. Start Chrome with remote debugging enabled from your terminal:
# chrome.exe --remote-debugging-port=9222

# 2. Configure the CDP debugger URL in AutomationConfig:
cdp_config = AutomationConfig(
    browser=BrowserConfig(remote_cdp_url="http://127.0.0.1:9222")
)
context, provider = await BrowserProviderFactory.launch_stabilized_lifecycle(cdp_config)
```

---

### Step 10: Deterministic Fast CI Testing
Executes unit tests in milliseconds without real-time wall-clock delays:

```python
import pytest
from behavioral_playwright import MockPage, VirtualTestClock, DeterministicRandomSource

@pytest.mark.asyncio
async def test_fast_automation():
    page = MockPage(initial_html="<button id='login-btn'>Login</button>")
    clock = VirtualTestClock()
    rng = DeterministicRandomSource(42)

    human = BehavioralHumanizer(page, AutomationConfig(), rng=rng, clock=clock)
    await human.human_click("#login-btn")
    
    # Virtual clock advances deterministically without waiting real-world seconds
    assert clock.time() > 0.0
```

---

## 📋 Complete Copy-Paste Templates

### Template 1: Full E-Commerce / Login & Form Submission

```python
import asyncio
from behavioral_playwright import (
    AutomationConfig,
    BrowserConfig,
    BrowserProviderFactory,
    BrowserLifecycleManager,
    BehavioralHumanizer,
    NavigationManager,
    CircuitBreaker,
    AIConfig,
)

async def run_automation():
    # 1. Configuration Setup
    config = AutomationConfig(
        browser=BrowserConfig(headless=False), # Set to True for headless mode
        ai=AIConfig(enabled=True, self_healing_enabled=True)
    )

    # 2. Initialize Provider Factory & Context
    context, provider = await BrowserProviderFactory.launch_stabilized_lifecycle(config)

    async with BrowserLifecycleManager(provider, context=context) as manager:
        page = manager.context.pages[0] if (manager.context and manager.context.pages) else await manager.context.new_page()

        # 3. Resilient Navigation
        navigator = NavigationManager(config, CircuitBreaker())
        print("[*] Navigating to target portal...")
        success = await navigator.safe_goto(page, "https://bot-detector.rebrowser.net")
        if not success:
            print("[!] Navigation failed.")
            return

        # 4. Humanized Interaction Flow
        human = BehavioralHumanizer(page, config)
        
        print("[*] Typing credentials with natural typing cadence...")
        await human.human_type("#text-input", "admin_user_2026")
        
        print("[*] Scrolling to action section...")
        await human.human_scroll(200.0)

        print("[*] Performing physiological click...")
        await human.human_click("#btn-login")

        print("[+] Automation workflow executed successfully!")

if __name__ == "__main__":
    asyncio.run(run_automation())
```

---

### Template 2: Anti-Bot Web Scraping & Data Extraction

```python
import asyncio
from behavioral_playwright import (
    AutomationConfig,
    BrowserProviderFactory,
    BrowserLifecycleManager,
    BehavioralHumanizer,
    NavigationManager,
    CircuitBreaker,
)

async def scrape_protected_site(target_url: str):
    config = AutomationConfig()
    context, provider = await BrowserProviderFactory.launch_stabilized_lifecycle(config)

    async with BrowserLifecycleManager(provider, context=context) as manager:
        page = manager.context.pages[0] if manager.context.pages else await manager.context.new_page()
        navigator = NavigationManager(config, CircuitBreaker())
        human = BehavioralHumanizer(page, config)

        print(f"[*] Accessing: {target_url}")
        arrived = await navigator.safe_goto(page, target_url)
        if not arrived:
            print("[!] Unable to load target page.")
            return

        # Natural browsing gestures and scrolling
        await human.move_mouse_to(300.0, 400.0, steps=15)
        await human.human_scroll(350.0)

        # Extract page metadata
        title = await page.title()
        print(f"[+] Successfully loaded: '{title}'")

if __name__ == "__main__":
    asyncio.run(scrape_protected_site("https://example.com"))
```

---

## 🏛️ Architecture & System Design

```
                            ┌───────────────────────────────────┐
                            │         AutomationConfig          │
                            │  (Composed domain dataclasses)    │
                            └─────────────────┬─────────────────┘
                                              │
                                              ▼
┌──────────────────┐        ┌─────────────────┴─────────────────┐        ┌─────────────────────┐
│   Clock / RNG    ├───────>│      BehavioralHumanizer          │<───────┤   PageProtocol      │
│  (Abstractions)  │        │ (C1 Smoothstep / SigmaDrift / AI) │        │ (Structural Duck)   │
└──────────────────┘        └─────────────────┬─────────────────┘        └──────────┬──────────┘
                                              │                                     ▲
                                              ▼                                     │
                            ┌───────────────────────────────────┐                   │
                            │         AIOrchestrator            │                   │
                            │ (L1->L2->L3->L4 Cascading Healing)│                   │
                            └───────────────────────────────────┘                   │
                                                                                    │
                            ┌───────────────────────────────────┐                   │
                            │         NavigationManager         ├───────────────────┘
                            │ (CircuitBreaker & Markov Entropy) │
                            └─────────────────┬─────────────────┘
                                              │
                                              ▼
                            ┌───────────────────────────────────┐
                            │      BrowserProviderFactory       │
                            │(CDP -> Cloak -> Playwright ->Mock)│
                            └───────────────────────────────────┘
```

---

## 📐 Mathematical Biomechanics

### 1. Velocity Profiling (C1-Continuous Smoothstep & SigmaDrift)
$$f(t) = t^2(3 - 2t) \quad \text{for } t \in [0, 1]$$
Guarantees $C^1$ continuity and zero boundary acceleration at the start and end of cursor movements.

### 2. Biological Muscle Tremor (Sine Jitter Envelope)
$$J_{\text{multiplier}}(t) = \sin(t \cdot \pi) \quad \text{for } t \in [0, 1]$$
Ensures tremor noise peaks at movement midpoint ($t=0.5$) and dampens to $0.0$ at target arrival, preventing coordinate overshoot.

### 3. Fitts's Law Movement Duration
$$T = a + b \cdot \log_2\left(1 + \frac{D}{W}\right)$$

### 4. Markov Navigation Entropy
$$H(S) = -\sum_{i=1}^{k} p(s_i) \log_2 p(s_i) \quad \text{where } p(s_i) = \frac{\text{count}(s_i)}{N}$$
When $H(S) < 1.10$, a cyclic loop or stuck error state is detected, prompting the circuit breaker to trigger recovery.

---

## 🤖 4-Tier Self-Healing AI & CV Pipeline

```text
Target Selector Fails / Broken
   │
   ├── [Level 1: Deterministic Levenshtein] ──> Fuzzy string matching against interactive DOM nodes
   │
   ├── [Level 2: DOM Accessibility] ──────────> Scans text, role, aria-label, and name attributes
   │
   ├── [Level 3: Computer Vision & OCR] ──────> Spatial coordinate bounding-box detection
   │
   └── [Level 4: LLM Cognitive Reasoning] ────> Vision prompt -> Structured JSON action proposal
           │
           └── [Action Validator] ─────────────> Confirms proposal confidence >= threshold (0.80)
                   │
                   ├── [Execution] ────────────> Biomechanical Mouse / Key action dispatched
                   │
                   └── [Visual Verification] ──> Pre/post DOM & visual state diff assertion
```

---

## 🔌 Resilient Circuit Breaker Navigation

* **`CLOSED`**: Normal state. Navigation requests proceed directly.
* **`OPEN`**: Tripped after 3 consecutive failures. Fast-fails immediately to conserve system resources.
* **`HALF_OPEN`**: Automatically enters trial state after a 30-second cooldown to test endpoint recovery.

---

## 🏭 Multi-Provider Cascading Fallback

1. **`CDPBrowserProvider`**: Connects to an existing Chrome/Chromium instance via Chrome DevTools Protocol.
2. **`CloakBrowserProvider`**: Connects to specialized C++ native browser bindings when license keys are configured.
3. **`PlaywrightProvider`**: Launches local Chromium persistent context with advanced JavaScript evasion prototype masking scripts.
4. **`MockBrowserProvider`**: Zero-dependency mock container for lightweight, isolated execution in headless CI environments.

---

## ⚙️ Full Configuration Reference

```python
from behavioral_playwright import (
    AutomationConfig,
    BrowserConfig,
    ClickConfig,
    KeyboardConfig,
    MouseConfig,
    NetworkConfig,
    AIConfig,
)

config = AutomationConfig(
    browser=BrowserConfig(
        headless=True,
        width=1920,
        height=1080,
        user_data_dir="./stealth_profile",
    ),
    mouse=MouseConfig(
        min_steps=15,
        jitter_std=0.15,
        fitts_a=50.0,
        fitts_b=150.0,
    ),
    click=ClickConfig(
        duration_mean=0.080,
        pre_click_delay_min=0.08,
        pre_click_delay_max=0.15,
    ),
    keyboard=KeyboardConfig(
        avg_delay_mean=0.095,
        mistake_probability=0.012,
    ),
    network=NetworkConfig(
        max_attempts=3,
        markov_entropy_limit=1.10,
        navigation_timeout_ms=30000,
    ),
    ai=AIConfig(
        enabled=True,
        self_healing_enabled=True,
        confidence_threshold=0.80,
    ),
)
```

---

## 🔍 Real Implementation vs Simulation Matrix

| Subsystem | Component | Implementation Status | Description |
| :--- | :--- | :--- | :--- |
| **Physics / Math** | `BezierTrajectoryGenerator` | **`REAL`** | C1 Smoothstep continuous velocity curves |
| **Physics / Math** | `SigmaDriftTrajectoryGenerator` | **`REAL`** | Lognormal CDF, Ornstein-Uhlenbeck drift, Fitts's Law |
| **Physics / Math** | `LorenzAttractorGenerator` | **`REAL`** | Chaotic Lorenz integration step calculation |
| **Behavior** | `LinguisticKeystrokeDynamics` | **`REAL`** | QWERTY Euclidean key distance and typo auto-correction |
| **Navigation** | `CircuitBreaker` | **`REAL`** | 3-state state machine (`CLOSED`/`OPEN`/`HALF_OPEN`) |
| **Navigation** | `MarkovLoopDetector` | **`REAL`** | Shannon information entropy calculation |
| **AI / Self-Healing** | `SelfHealingSelectorEngine` | **`REAL`** | Levenshtein distance matrix matching |
| **AI / Self-Healing** | `SelfHealingResolver` (L1, L2) | **`REAL`** | DOM candidate extraction & semantic accessibility matching |
| **AI / Self-Healing** | `VisionEngine` / `Detector` | **`REAL`** | Layout client-rect & OCR text extraction |
| **AI / Self-Healing** | `LLMProvider` / `Reasoning` | **`REAL`** | Multi-endpoint REST client with offline fallback heuristics |
| **Providers** | `PlaywrightProvider` | **`REAL`** | Chromium launcher with client-side prototype masking |
| **Providers** | `MockBrowserProvider` | **`REAL`** | Standalone zero-dependency CSS DOM parser & mock engine |
| **Diagnostics** | `ExploitPoCExporter` | **`REAL`** | Standalone Python requests script generator |
| **Diagnostics** | `EbpfTcpSpoofBridge` | *Simulation* | Emulated TCP options parameter generator |
| **Diagnostics** | `HardwareAttestationRelay` | *Simulation* | Simulated WebAuthn enclave signature generator |
| **Diagnostics** | `MFAOtpPollingBridge` | *Simulation* | Simulated TOTP / SMS polling stub |

---

## 🧪 Testing & Quality Assurance

```bash
# 1. Run all 33 Pytest test cases
pytest

# 2. Run standalone Legacy Self-Test Suite
python tests/test_suite.py

# 3. Static code analysis & linting
ruff check src/ tests/ demo.py

# 4. Strict type validation
mypy src/

# 5. Run end-to-end smoke demonstration
python demo.py
```

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](file:///e:/api/LICENSE) for details.
