"""
Self-Healing Selector Example.
Demonstrates:
  1. Page loads
  2. Fixed selector fails
  3. Resolver performs semantic recovery
  4. Element is recovered
  5. Action succeeds
  6. ResolutionResult is printed
"""

import asyncio
from behavioral_playwright import (
    AutomationConfig,
    BrowserConfig,
    BrowserSession,
    ResolverConfig,
)


async def main():
    config = AutomationConfig(
        browser=BrowserConfig(headless=False),
        resolver=ResolverConfig(confidence_threshold=0.65)
    )

    print("=" * 60)
    print(" behavioral-playwright: Self-Healing Resolution Example")
    print("=" * 60)

    async with BrowserSession(config=config) as session:
        page = await session.new_page()
        
        target_url = "https://example.com"
        print(f"[*] Navigating to {target_url}...")
        await page.goto(target_url)

        # 1. Provide an intentionally broken / mutated selector
        broken_selector = "a.broken-more-info-v1#nonexistent-id"
        print(f"\n[*] Resolving broken selector: '{broken_selector}'...")

        # 2. SelfHealingResolver executes cascade: L1 (fails) -> L2 (recovers 'More information...')
        result = await page.resolve(broken_selector)

        # If pure selector failed, resolve by semantic intent:
        if not result.success:
            print("[*] Target was not semantically inferable from selector string alone.")
            print("[*] Resolving by semantic intent: 'More information'...")
            result = await page.resolve("More information")

        # 3. Print ResolutionResult
        print("\n" + "=" * 60)
        print(" RESOLUTION RESULT")
        print("=" * 60)
        print(f"Success       : {result.success}")
        print(f"Strategy      : {result.strategy.value}")
        print(f"Confidence    : {result.confidence:.2f}")
        print(f"Healed        : {result.is_healed}")
        print(f"Healed Target : {result.selector}")
        print(f"Elapsed Time  : {result.elapsed_ms:.1f}ms")
        print(f"Reason        : {result.reason}")
        print("=" * 60)

        # 4. Execute action with healed element
        if result.success and result.selector:
            print(f"\n[*] Executing safe click on healed element: '{result.selector}'...")
            await page.click_healed(result.selector)
            await asyncio.sleep(2.0)
            print(f"[✓] Navigated to: {await page.get_url()}")


if __name__ == "__main__":
    asyncio.run(main())
