"""
Basic Navigation & State Tracking Example.
Demonstrates BrowserSession context manager, navigation, and page metadata extraction.
"""

import asyncio
from behavioral_playwright import AutomationConfig, BrowserConfig, BrowserSession


async def main():
    config = AutomationConfig(
        browser=BrowserConfig(headless=False)
    )

    print("=" * 60)
    print(" behavioral-playwright: Basic Navigation Example")
    print("=" * 60)

    async with BrowserSession(config=config) as browser:
        page = await browser.new_page()
        
        target_url = "https://example.com"
        print(f"[*] Navigating to {target_url}...")
        await page.goto(target_url)

        title = await page.get_title()
        url = await page.get_url()
        print(f"[✓] Page Title : '{title}'")
        print(f"[✓] Current URL: {url}")
        print(f"[✓] Transitions: {page.state_tracker.transition_count}")


if __name__ == "__main__":
    asyncio.run(main())
