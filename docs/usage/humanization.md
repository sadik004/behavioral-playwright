# Humanization Guide & Biomechanical Patterns

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. How Humanization Works in Behavioral Playwright

Standard headless browser bots emit unnatural execution signals that trigger anti-bot algorithms:
1. **Instant typing**: Submitting 50 characters in 2 milliseconds.
2. **Linear mouse vectors**: Teleporting the cursor across coordinates in a straight line.
3. **No focus-blur sequence**: Injecting values into inputs without unfocusing the previous element.
4. **Rigid scrolling**: Moving the viewport with mechanical exactness.

---

## 2. Automatic Protections

When you call `bp.browser.type()`, `bp.browser.click()`, or `bp.browser.hover()`, Behavioral Playwright automatically applies:
- **Focus Lifecycle**: `document.activeElement.blur()` -> `target.focus()`.
- **Log-Normal Delays**: 40ms–120ms randomized hold and keypress delays.
- **500-Point Bézier Curves**: Smooth curved cursor movement with virtual gravity.
- **Saccadic Pauses**: Variable stepped pauses between scroll steps.

No manual math or configuration is required; humanization is enabled by default.
