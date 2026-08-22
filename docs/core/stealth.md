# Stealth & Anti-Detection Architecture

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. CDP Anti-Detection Shims

Standard Chromium instances controlled by Playwright leak identifiable automation markers. Behavioral Playwright injects JavaScript initialization scripts via Chrome DevTools Protocol (CDP) before any page script executes:

### 1. `navigator.webdriver` Masking
```javascript
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true
});
```

### 2. Prototype Chain Protection
Prevents detection scripts from identifying getter traps by making modified properties appear native:
```javascript
window.chrome = {
    runtime: {},
    app: { isInstalled: false }
};
```

### 3. Speech Synthesis & Audio Context Guard
Anti-bot systems query `window.speechSynthesis.getVoices()`. Injected shims provide simulated voice arrays and forward debug telemetry safely without triggering exceptions.

### 4. Canvas Fingerprint Noise
Injects sub-pixel, non-visual micro-jitter into `HTMLCanvasElement.prototype.toDataURL` to disrupt deterministic canvas hash tracking across sessions.
