# Behavioral Evasion Suite (Hardened Enterprise v5) — Usage Guide & Integration Manual

## Overview
This suite provides 10 enterprise anti-bot evasion and pipeline resilience modules designed for scalable web scraping and automation with Playwright / Patchright and curl_cffi.

---

## 📁 File Structure in this Folder
```text
behavioral_evasion_suite/
├── __init__.py                # Package exports
├── utils.py                   # WeakMap native toString helper & SanitizedLogFormatter
├── cdp_evasion.py             # Patch 1: CDP & Runtime.enable Evasion
├── tls_ja4_spoofer.py         # Patch 2: TLS & JA4 Handshake Spoofing
├── mouse_physics.py           # Patch 3: Biomechanical Mouse Physics (Inertia & Tremors)
├── hardware_os_spoofer.py     # Patch 4: Hardware & WebGL Prototype Spoofing
├── context_rotator.py         # Patch 5: Context Recycling & V8 Cache Drain
├── os_resource_guard.py       # Patch 6: OS File Descriptor & Socket Guard
├── session_vault.py           # Patch 7: Session State Persistence (Cookies/Storage)
├── circuit_breaker.py         # Patch 8: Status-Granular Circuit Breaker & Jitter
├── persistence_pipeline.py    # Patch 9: Non-blocking Async Disk/DB Persistence
├── backpressure_queue.py      # Patch 9 Support: Bounded Concurrency Queue
├── quality_sentinel.py        # Patch 10: Pydantic Schema & Honeypot Sentinel
├── hybrid_router.py           # Adaptive Fast Path / Heavy Path Router
├── strict_context.py          # Proxy Isolation & Soft WebRTC Mask
├── main.py                    # Verification Integrity Runner
└── USAGE_GUIDE.md             # This Documentation File
```

---

## 🛠️ Step-by-Step Usage & Code Examples

### 1. Unified Import
```python
from behavioral_evasion_suite import (
    CDPEvasionShield,
    TLSJA4Spoofer,
    BiomechanicalMousePhysics,
    HardwareOSSpoofer,
    ContextRotator,
    OSResourceGuard,
    SessionStateVault,
    StatusGranularCircuitBreaker,
    BasePersistencePipeline,
    BackpressureQueue,
    QualitySentinel,
    SmartAcquisitionRouter,
    StrictContextManager,
    setup_sanitized_logger,
)
```

---

### 2. Guarding OS Resources & Logging (Patch 6 & 8)
```python
# Setup sensitive-credential log scrubbing
logger = setup_sanitized_logger("MyScraper")

# Clamp concurrency to prevent 'Too many open files' (OSError 24)
guard = OSResourceGuard()
max_concurrency = guard.check_os_limits(concurrency_estimate=100)
print(f"Safe concurrency limit: {max_concurrency}")
```

---

### 3. Fast Path vs Heavy Path Dual-Engine Router (Patch 2 & 6)
```python
from playwright.async_api import async_playwright
from behavioral_evasion_suite import ContextRotator, SmartAcquisitionRouter

async def fetch_page(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        rotator = ContextRotator(browser=browser, recycle_threshold=50)
        router = SmartAcquisitionRouter(browser_context_rotator=rotator)

        # Automatically tries Fast Path (curl_cffi JA4) and cascades to Heavy Path (Playwright) on block
        result = await router.acquire_target(url)
        print(f"Engine used: {result['engine']}, Status: {result['status_code']}")
        await browser.close()
```

---

### 4. CDP Evasion, Hardware Spoofing & Mouse Physics (Patch 1, 3, 4)
```python
from behavioral_evasion_suite import CDPEvasionShield, HardwareOSSpoofer, BiomechanicalMousePhysics

async def scrape_with_stealth(page, target_coords):
    # 1. Apply CDP WeakMap toString Shield
    cdp_shield = CDPEvasionShield(page)
    await cdp_shield.apply_cdp_stealth_binding()

    # 2. Inject Hardware WebGL & Platform Stealth
    hw_spoofer = HardwareOSSpoofer(page)
    await hw_spoofer.inject_hardware_stealth()

    # 3. Navigate
    await page.goto("https://target-site.com")

    # 4. Human-like Mouse Movement with Neuromuscular Inertia
    mouse = BiomechanicalMousePhysics()
    start_pos = (100, 100)
    end_pos = target_coords  # e.g., (450, 320)
    trajectory = mouse.generate_trajectory(start_pos, end_pos, steps=30)

    for x, y in trajectory:
        await page.mouse.move(x, y)
        await asyncio.sleep(0.01)

    await page.mouse.click(end_pos[0], end_pos[1])
```

---

### 5. Session State Persistence (Patch 7)
```python
from behavioral_evasion_suite import SessionStateVault

vault = SessionStateVault(filepath="session_state.json")

# Save authenticated session after login
await vault.save_state(context)

# Load stored cookies and localStorage into a new isolated context
new_context = await vault.load_state(browser, proxy_config={"server": "http://127.0.0.1:8080"})
```

---

### 6. Circuit Breaker & Quality Sentinel (Patch 8 & 10)
```python
from pydantic import BaseModel
from behavioral_evasion_suite import StatusGranularCircuitBreaker, QualitySentinel

class ListingItem(BaseModel):
    title: str
    price: float

circuit = StatusGranularCircuitBreaker(threshold=3, cooldown_window=10.0)
sentinel = QualitySentinel(max_allowed_failure_ratio=0.4, window_size=5)

if circuit.allow_request():
    try:
        # Perform extraction
        raw_data = {"title": "Product A", "price": 49.99}
        
        # Check honeypot
        if not sentinel.check_honeypots(element_metadata):
            sentinel.monitor_data_quality("https://example.com/p1", raw_data, ListingItem)
    except Exception as ex:
        circuit.register_failure("ip_ban_429_403")
```

---

### 7. Non-blocking Persistence & Backpressure Queue (Patch 9)
```python
from behavioral_evasion_suite import BasePersistencePipeline, BackpressureQueue

async def pipeline_worker():
    queue = BackpressureQueue(maxsize=50)
    pipeline = BasePersistencePipeline(output_path="results.ndjson")
    pipeline.open()

    # Producers push items safely with bounded memory
    await queue.push_item({"id": 101, "name": "Item A"})

    # Worker consumes and writes asynchronously via threadpool
    item = await queue.get_item()
    await pipeline.append_record(item)

    await pipeline.close()
```

---

## 🧪 Verification
To run the automated verification test suite:
```bash
python -m behavioral_evasion_suite.main
```

---

# 🚀 Level 5 Quantum Edition: Fluent Developer API (Code UX)

For the cleanest developer experience with **zero boilerplate**, use `StealthBrowser` and `Preset`:

```python
import asyncio
from behavioral_evasion_suite import StealthBrowser, Preset

async def main():
    # Launches Chromium with all 31 shields, DirectWrite fonts, and Windows kernel input
    async with StealthBrowser.launch(preset=Preset.MAX_QUANTUM, headless=True) as page:
        await page.goto("https://bot.sannysoft.com")
        
        # Biomechanical neuromuscular human click
        await page.human_click("#submit-btn")
        
        # Cognitive human typing with typo correction
        await page.human_type("#username", "john_doe")
        
        # Newtonian inertial human scroll
        await page.human_scroll(delta_y=800, duration_s=1.2)
        
        # Statistical cognitive comprehension reading pause
        await page.cognitive_pause(min_seconds=1.0, max_seconds=2.0)
        
        # Token-optimized interactive DOM tree for LLMs
        dom_tree = await page.extract_compact_dom()
        print(f"Discovered {len(dom_tree['elements'])} interactive elements")

asyncio.run(main())
```

### Available Presets:
1. `Preset.MAX_QUANTUM`: All 31 shields, DirectWrite ClearType font metrics, WebWorker isolation, 1ms Windows timer, and OS kernel input bridge.
2. `Preset.BALANCED`: Optimal for high-throughput distributed scraping.
3. `Preset.HEADLESS_UNDETECTABLE`: Tuned specifically to defeat headless heuristics on Cloudflare and DataDome.
4. `Preset.FAST_BYPASS`: Lightweight CDP and TLS JA4 bypass with minimal CPU overhead.
