"""Interactive LinkedIn Session Exporter.

Launches a headful browser session allowing the user to manually log in and solve
any 2FA / CAPTCHA challenge once. Saves the authenticated session state to disk
for subsequent headless MCP tool invocations.
"""

import asyncio
import sys
from behavioral_playwright.integrations.linkedin import LinkedInAutomationClient


async def main() -> None:
    output_path = sys.argv[1] if len(sys.argv) > 1 else "linkedin_state.json"
    print(f"[*] Launching interactive headful browser to capture LinkedIn session...")
    print(f"[*] Target storage state output: {output_path}")
    print("[*] Please log in and complete 2FA in the opened window. Waiting up to 180 seconds...")

    res = await LinkedInAutomationClient.export_session_interactive(
        output_path=output_path,
        timeout_seconds=180,
    )

    if res.authenticated:
        print(f"[+] SUCCESS: {res.message}")
    else:
        print(f"[-] FAILED: {res.message}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
