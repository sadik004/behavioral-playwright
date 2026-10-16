# Feature Specification: Browser Namespace (`bp.browser`)

> **Last Verified Against Commit**: `v10.0.2`
> **Status**: [VERIFIED]

---

## 1. Overview & Capabilities
The `BrowserNamespace` ([`veil/facade.py`](src/veil/facade.py)) manages stateful Chromium automation, anti-fingerprint shimming, and bio-emulated human actions.

---

## 2. API Method Reference

### `goto(url)`
- **Signature**: `async def goto(self, url: str) -> bool`
- **Description**: Navigates active page to target URL with circuit-breaker protection.

### `click(selector, expected_text=None)`
- **Signature**: `async def click(self, selector: str, expected_text: Optional[str] = None) -> Any`
- **Description**: Triggers focus-blur sequence and clicks element via humanizer or native page fallback.

### `type(selector, text)` & `fill(selector, value)`
- **Signature**: `async def type(self, selector: str, text: str) -> Any`
- **Description**: Simulates human keystroke delays sampled from log-normal distributions.

### `hover(selector)` & `drag_and_drop(source, target)`
- **Signature**: `async def hover(self, selector: str) -> Any`
- **Description**: Moves mouse along a 500-point Newtonian Bézier curve with gravity and inertia.

### `scroll(distance_y=500.0)`
- **Signature**: `async def scroll(self, distance_y: float = 500.0) -> None`
- **Description**: Performs stepped scrolling with variable saccade pauses (50ms–150ms).

### `screenshot(path=None)`
- **Signature**: `async def screenshot(self, path: Optional[str] = None) -> bytes`
- **Description**: Captures PNG screenshot of active browser viewport.
