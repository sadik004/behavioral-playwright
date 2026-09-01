# Intelligence & Bot Shield Diagnostics Guide

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Detecting Bot Shield Signatures

Scan HTML payloads for anti-bot challenge interstitial markers:

```python
from bp_facade12 import BP

bp = BP()
html_payload = "<div id='cf-turnstile-wrapper'>Please verify you are human</div>"

detection = bp.intelligence.detect_bot_shields(html_payload)
print("Shield Detected:", detection["detected"])
print("Shield Providers:", detection["shields"])
```

---

## 2. Levenshtein Selector Auto-Correction

Recover from broken or slightly modified CSS selectors:

```python
broken_selector = "button.submt-btn"
active_dom_buttons = ["button.submit-btn", "button.cancel-btn", "a.nav-link"]

corrected = bp.intelligence.auto_correct_selectors(broken_selector, active_dom_buttons)
print("Corrected Selector:", corrected) # Returns 'button.submit-btn'
```
