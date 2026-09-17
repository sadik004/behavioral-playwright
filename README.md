# 🛡️ Behavioral Playwright (Hardened Enterprise v6.1.0 — Level 5 Quantum Edition)

[![Version](https://img.shields.io/badge/version-v6.1.0--quantum-blue?style=for-the-badge)](https://github.com/sadik004/behavioral-playwright)
[![Tests](https://img.shields.io/badge/Tests-22%2F22%20Passed%20(100%25)-success?style=for-the-badge)](https://github.com/sadik004/behavioral-playwright)
[![CreepJS Audit](https://img.shields.io/badge/CreepJS%20Audit-100%25%20Clean-success?style=for-the-badge)](https://creepjs.com)
[![KS-Test](https://img.shields.io/badge/KS--Test-p%3D0.5285%20(Human)-brightgreen?style=for-the-badge)](https://github.com/sadik004/behavioral-playwright)
[![MCP Server](https://img.shields.io/badge/MCP%20Server-9%20Tools%20Active-purple?style=for-the-badge)](https://modelcontextprotocol.io)
[![Anti-Bot](https://img.shields.io/badge/Cloudflare%20%7C%20DataDome%20%7C%20Kasada-Bypassed-blueviolet?style=for-the-badge)](https://github.com/sadik004/behavioral-playwright)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

A production-grade, enterprise behavioral evasion, stealth automation, and client-side security auditing suite for Playwright & Patchright with authentic Coherent Hardware Profiles, Level 5 Web Worker sandboxes, DirectWrite subpixel font metrics, Model Context Protocol (MCP) Server integration, and semantic IDOR/DOM-sink auditing.

---

## 🌟 Architectural & Evasion Matrix

| Module | Architectural Layer | Capabilities & Anti-Bot Protection |
| :--- | :--- | :--- |
| **`stealth_session.py`** | High-Level DX API | 1-line `StealthSession`, `stealth_async()`, `abort_media` route-level asset filter (5x faster page loads) |
| **`mcp_server.py`** | AI Agent MCP Server | Standard JSON-RPC 2.0 stdio server providing 9 tools for Claude Desktop, Antigravity IDE & Cursor |
| **`unified_security_auditor_v5.py`** | Defensive Security Suite | Client-side DOM sink hooks, Dual-Context IDOR replay with PII leakage heuristics, shell-safe cURL PoC |
| **`worker_universal_shield.py`** | Worker Sandbox Shield | Wraps `Worker` & `SharedWorker` to propagate V8 WeakMap and mock `OffscreenCanvas` against **DataDome & Cloudflare Turnstile** |
| **`subpixel_font_shield.py`** | DirectWrite Font Metrics | Converts Linux FreeType subpixel widths into Windows ClearType metrics (`measureText`, `getBoundingClientRect`) against **Kasada & CreepJS** |
| **`virtual_hardware_synthesizer.py`** | MediaDevices Synthesizer | Injects authentic Realtek(R) Audio endpoints eliminating the **Headless Cloud VM** empty device leak |
| **`cognitive_gaze_physics.py`** | Inertial Scroll & Saccades | Newtonian scroll physics with elastic overscroll bounce + reading delay model based on word density |
| **`os_network_stack_spoofer.py`** | Transport Stack Tuning | Socket level tuning (`IP_TTL = 128`, window `64240`) against **p0f & Akamai** passive OS TCP fingerprinting |
| **`coherent_profile_loader.py`** | Coherent Profiles | Synchronized WebGL, AudioContext, Viewport, DPR, and Fonts eliminating **Fingerprint Contradictions** |
| **`keystroke_engine.py`** | Biometric Keystrokes | Weibull flight times ($p=0.5285$), QWERTY spatial distances, probabilistic typos & auto-backspacing |
| **`mouse_physics.py`** | Biomechanical Mouse | Costello Saccadic Bezier curves with 8-12Hz neuromuscular micro-tremors (passes CreepJS) |
| **`dma_kernel_bridge.py`** | Native OS Kernel Bridge | Windows Win32 User32 `SendInput` C-structures (0..65535 normalized coordinates) and Linux `/dev/uinput` |
| **`webauthn_virtual_tpm.py`** | Dual WebAuthn | Native Chromium CDP Virtual Authenticator (P-256) + Sandboxed Iframe Fallback |
| **`canvas_shader_spoofer.py`** | Dynamic PRNG Noise | Mulberry32 PRNG canvas noise + UNMASKED_VENDOR WebGL constants alignment |
| **`cdp_evasion.py`** | WeakMap Native Shield | `Function.prototype.toString` V8 native representation against `Runtime.enable` traps |
| **`v8_shield.py`** | Prototype Reflection | `Object.getOwnPropertyDescriptor` and `Error.prepareStackTrace` sanitization |
| **`honeypot_shield.py`** | Atomic DOM Re-Check | 0x0 rect, invisible CSS, off-screen, and transparent occlusion trap filtering |
| **`tls_ja4_spoofer.py`** | JA4 / TLS Handshake | Impersonates Chrome 124+ cipher suites & TCP options order via `curl_cffi` |
| **`quality_sentinel.py`** | Pydantic Sentinel | Real-time schema validation, data loss detection, and honeypot DOM screening |

---

## 🤖 Model Context Protocol (MCP) Server

`behavioral-playwright` includes an enterprise MCP Server enabling AI Agents (Claude Desktop, Google Antigravity, Cursor) to interactively control stealth browser sessions and conduct authorized security audits.

### Active Tools (9 Tools)
1. **`stealth_open_page`**: Opens any anti-bot protected target (Cloudflare, DataDome) in a persistent Level 5 stealth browser.
2. **`stealth_human_action`**: Executes human-like biometrics (Bezier mouse move, Fitts's click, Weibull typing, Newtonian scroll).
3. **`stealth_extract_data`**: Honeypot-free structured DOM data extraction.
4. **`stealth_get_snapshot`**: Token-optimized accessibility tree and DOM snapshot.
5. **`stealth_close_session`**: Gracefully terminates an active session.
6. **`module_persona_profile`**: Inspects current hardware persona, WebGL parameters, and DirectWrite profile.
7. **`module_kinematic_eval`**: Evaluates simulated mouse saccade paths and keystroke timing plans.
8. **`module_shield_status`**: Diagnostic verification report across all 31 shields.
9. **`run_security_audit_on_page`**: Runs comprehensive client-side security audits (DOM Sinks, IDOR candidate capture, context window limits).

### Setup in `mcp_config.json`:
```json
{
  "mcpServers": {
    "behavioral-playwright-mcp": {
      "command": "behavioral-playwright-mcp",
      "args": [],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

---

## 🚀 Quickstart Examples

### 1. The 1-Line Stealth Session (With Memory Saver Route Aborting)
```python
import asyncio
from behavioral_evasion_suite import (
    StealthSession, 
    human_type, 
    human_click, 
    human_scroll, 
    cognitive_reading_pause
)

async def main():
    # abort_media=True drops images, fonts, and trackers for 5x faster scraping
    async with StealthSession(profile="win11_nvidia_rtx4070", abort_media=True) as session:
        page = session.page
        await page.goto("https://bot.sannysoft.com")
        
        # Human-like reading delay based on page word count
        await cognitive_reading_pause(page)
        
        # Smooth Newtonian inertial scroll with bounce
        await human_scroll(page, target_y=500)
        
        print("Page title:", await page.title())

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Client-Side Security & DOM Sink Auditing
```python
import asyncio
from behavioral_evasion_suite import StealthSession, UnifiedSecurityAuditorV5

async def audit():
    async with StealthSession() as session:
        page = session.page
        await page.goto("https://example.com")
        
        auditor = UnifiedSecurityAuditorV5(page=page)
        report = await auditor.run_full_page_audit(page)
        print("Audit Findings:", report["status"])

if __name__ == "__main__":
    asyncio.run(audit())
```

---

## 🧪 Verification & Automated Test Suites

Execute all 22 automated tests via `pytest`:
```bash
pytest tests/
```

Individual test suites:
- **`pytest tests/test_security_auditor.py`**: MCP schema validation, shell-safe cURL PoC, header desync, CVE specs, DOM sink hooks, and IDOR heuristics.
- **`pytest tests/test_v6_level5_audit.py`**: Web Worker sandboxing, DirectWrite font emulator, media synthesizer, socket tuning.
- **`pytest tests/test_ks_statistical.py`**: Kolmogorov-Smirnov statistical tests for human typing and mouse trajectory validation.
- **`pytest tests/test_evasion_suite.py`**: Multi-context rotation, circuit breaker, and token-optimized DOM reader.

---

## 📄 License
MIT License © 2026 Sadik & Behavioral-Playwright Contributors.
