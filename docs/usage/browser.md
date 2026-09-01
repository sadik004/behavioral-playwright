# Browser Automation Usage Guide

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Core Browser APIs (`bp.browser`)

### Navigation & Viewport
```python
async with BP() as bp:
    # Navigates with circuit-breaker protection
    await bp.browser.goto("https://example.com/login")
```

### Form Input & Typing
```python
# Dispatches activeElement.blur() -> focuses input -> types with log-normal key delays
await bp.browser.type("input#username", "admin_user")
await bp.browser.type("input#password", "SecureSecret123!")
```

### Checkboxes, Dropdowns & Keyboard Press
```python
# Check/Uncheck checkboxes
await bp.browser.check("input#remember_me")

# Select dropdown option by value
await bp.browser.select_option("select#country", "US")

# Press keyboard key (e.g. Enter, Tab, Escape)
await bp.browser.press("input#password", "Enter")
```

### Hover, Drag-and-Drop & Saccade Scrolling
```python
# Move mouse along a 500-point Newtonian Bézier curve
await bp.browser.hover("nav.dropdown-menu")

# Drag source element to target coordinates
await bp.browser.drag_and_drop("#item-1", "#cart-dropzone")

# Scroll down 400px with stepped optical pauses
await bp.browser.scroll(400.0)
```

### Viewport Screenshots
```python
# Save screenshot to file or return bytes
png_bytes = await bp.browser.screenshot("dashboard.png")
```
