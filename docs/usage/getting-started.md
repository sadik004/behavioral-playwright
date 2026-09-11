# Getting Started with Behavioral Playwright

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Installation

Install Behavioral Playwright along with its optional document processing dependencies:

```bash
# Clone the repository
git clone https://github.com/sadik004/behavioral-playwright.git
cd behavioral-playwright

# Install dependencies
pip install playwright beautifulsoup4 Pillow pytesseract pypdf python-docx

# Install Playwright browser binaries
playwright install chromium
```

---

## 2. Quickstart Idiom (Async Context Manager)

The standard way to use Behavioral Playwright is through the `async with BP() as bp:` context manager. This handles browser bootstrapping, viewport locking, stealth script injection, and automatic resource cleanup on exit:

```python
import asyncio
from bp_facade12 import BP

async def main():
    async with BP() as bp:
        # 1. Navigate to a webpage
        await bp.browser.goto("https://example.com")

        # 2. Interact with bio-emulated human typing
        await bp.browser.type("input#search", "Playwright automation")
        await bp.browser.click("button#submit")

        # 3. Capture a screenshot
        await bp.browser.screenshot("output.png")
        print("Workflow completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
```
