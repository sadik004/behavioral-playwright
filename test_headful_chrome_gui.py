"""
Headful Chromium/Chrome GUI Automation & Biometric Mouse Path Verifier
Demonstrates Costello Saccadic Trajectories, Harris-Wolpert Tremor,
and Human-like Keystroke Cadence in a visible desktop browser window.
"""

import asyncio
import os
import sys
from behavioral_playwright import BP, AutomationConfig
from behavioral_playwright.config.settings import BrowserConfig


async def main():
    print("=" * 70)
    print("🚀 [1/4] Booting Visible Chrome/Chromium GUI (Headful Mode)...")
    print("=" * 70)

    # Detect installed Chrome for real Google Chrome window, fallback to Chromium
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    has_system_chrome = any(os.path.exists(p) for p in chrome_paths)
    channel = "chrome" if has_system_chrome else None
    print(f"🖥️  Browser Engine: {'Google Chrome (System Channel)' if channel else 'Chromium (Bundled)'}")

    # Configure Headful Browser with 1280x800 Viewport
    browser_cfg = BrowserConfig(
        headless=False,
        width=1280,
        height=800,
        channel=channel,
    )
    config = AutomationConfig(
        browser=browser_cfg,
        humanize=True,
    )

    bp = BP(config=config)
    await bp.boot()
    page = bp.page

    # Ensure window is brought to front
    if hasattr(page, "bring_to_front"):
        try:
            await page.bring_to_front()
        except Exception:
            pass

    try:
        target_url = "https://httpbin.org/forms/post"
        print(f"🌐 [2/4] Navigating to Test Target: {target_url}...")
        await page.goto(target_url, timeout=30000)
        await page.wait_for_timeout(1000)

        # Inject visual cursor tracker so mouse movements are visibly traced on screen
        await page.evaluate("""() => {
            const cursor = document.createElement('div');
            cursor.id = 'biometric-cursor-tracker';
            cursor.style.position = 'fixed';
            cursor.style.width = '18px';
            cursor.style.height = '18px';
            cursor.style.borderRadius = '50%';
            cursor.style.backgroundColor = 'rgba(255, 30, 30, 0.95)';
            cursor.style.border = '2px solid white';
            cursor.style.boxShadow = '0 0 14px rgba(255, 30, 30, 1), 0 0 28px rgba(255, 80, 80, 0.7)';
            cursor.style.pointerEvents = 'none';
            cursor.style.zIndex = '2147483647';
            cursor.style.transform = 'translate(-50%, -50%)';
            cursor.style.left = '100px';
            cursor.style.top = '100px';
            cursor.style.transition = 'width 0.1s, height 0.1s, background-color 0.1s';
            document.body.appendChild(cursor);

            window.addEventListener('mousemove', (e) => {
                cursor.style.left = e.clientX + 'px';
                cursor.style.top = e.clientY + 'px';
            });
            window.addEventListener('mousedown', () => {
                cursor.style.width = '26px';
                cursor.style.height = '26px';
                cursor.style.backgroundColor = 'rgba(34, 197, 94, 0.95)';
                cursor.style.boxShadow = '0 0 20px rgba(34, 197, 94, 1)';
            });
            window.addEventListener('mouseup', () => {
                cursor.style.width = '18px';
                cursor.style.height = '18px';
                cursor.style.backgroundColor = 'rgba(255, 30, 30, 0.95)';
                cursor.style.boxShadow = '0 0 14px rgba(255, 30, 30, 1)';
            });
        }""")

        print("🖱️ [3/4] Demonstrating Natural Biometric Mouse Trajectory...")
        print("   📍 Positioning cursor at start: (100, 100)")
        await page.mouse.move(100, 100, humanize=False)
        await page.wait_for_timeout(500)

        print("   〰️ Gliding with Costello Saccadic Curve & Harris-Wolpert Tremor -> (500, 400)...")
        # Moving from (100, 100) to (500, 400) with 35 spline steps
        await page.mouse.move(500, 400, steps=35, humanize=True)
        await page.wait_for_timeout(600)

        print("   🎯 Moving mouse to form input field 'Customer name' and clicking...")
        # Humanized click calculates centroid with subpixel jitter, moves cursor, and clicks
        await page.mouse.click('input[name="custname"]', humanize=True)
        await page.wait_for_timeout(500)

        print("⌨️  [4/4] Demonstrating Human Keystroke Cadence Dynamics...")
        sample_text = "Behavioral-Playwright: Natural Biometrics Active!"
        print(f"   ✍️ Typing sample text with Weibull flight delays: '{sample_text}'")
        await page.keyboard.type(sample_text, humanize=True)

        print("\n" + "=" * 70)
        print("✅ INTERACTION COMPLETE: Holding browser window open for 12 seconds...")
        print("   (Inspect the browser window, input field, and cursor position on your screen)")
        print("=" * 70)
        await page.wait_for_timeout(12000)

    except Exception as e:
        print(f"❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        print("🛑 Gracefully shutting down browser session...")
        if bp.session:
            await bp.session.close()
        print("✨ Done.")


if __name__ == "__main__":
    asyncio.run(main())
