"""
Structured DOM Extraction Example.
Demonstrates extracting links and article elements into typed Python data models.
"""

import asyncio
from behavioral_playwright import AutomationConfig, BrowserConfig, BrowserSession


async def main():
    config = AutomationConfig(
        browser=BrowserConfig(headless=False)
    )

    print("=" * 60)
    print(" behavioral-playwright: Structured DOM Extraction Example")
    print("=" * 60)

    async with BrowserSession(config=config) as browser:
        page = await browser.new_page()
        
        target_url = "https://news.ycombinator.com/"
        print(f"[*] Navigating to {target_url}...")
        await page.goto(target_url)

        print("[*] Extracting structured links...")
        records = await page.extract_links()

        print(f"[✓] Extracted {len(records)} structured links.")
        print("\nTop 5 Extracted Links:")
        for idx, rec in enumerate(records[:5], 1):
            print(f"  [{idx}] {rec.text[:50]} -> {rec.href}")


if __name__ == "__main__":
    asyncio.run(main())
