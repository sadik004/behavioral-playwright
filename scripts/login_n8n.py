"""n8n Cloud Behavioral Login and API Key Setup Script.

Utilizes behavioral-playwright for stealth browser automation, human-mimetic
keystroke cadence (KeyboardController), and dynamic DOM mutation checks to log
into https://arnan.app.n8n.cloud, capture the session, or auto-generate/export
the REST API key directly into mcp_config.json and n8n.mcp/.env.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Page, async_playwright

# Add src to sys.path for direct imports from workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))

from behavioral_playwright.automation.keyboard import KeyboardController
from behavioral_playwright.browser.pool import BrowserPoolManager
from behavioral_playwright.config.settings import BrowserConfig
from behavioral_playwright.logging import get_logger

logger = get_logger("n8n_login")


async def login_and_extract_key(
    target_url: str = "http://localhost:5678",
    email: Optional[str] = None,
    password: Optional[str] = None,
    headless: bool = False,
    timeout_seconds: int = 180,
) -> bool:
    """Logs into n8n via behavioral-playwright, dismisses modals, and generates API key."""
    signin_url = f"{target_url.rstrip('/')}/signin"
    storage_state_path = WORKSPACE_ROOT / "n8n_storage_state.json"

    print(f"[*] Initializing BrowserPoolManager (headless={headless})...")
    print(f"[*] Target URL: {target_url}")

    browser_config = BrowserConfig(
        headless=headless,
        allow_media=True,
        width=1280,
        height=800,
    )
    pool = BrowserPoolManager(config=browser_config)
    await pool.initialize()

    try:
        async with pool.get_context() as context:
            page = await context.new_page()

            try:
                await page.goto(signin_url, wait_until="domcontentloaded", timeout=45000)

                email_input = page.locator("#emailOrLdapLoginId, input[name='emailOrLdapLoginId']")
                try:
                    await email_input.wait_for(state="visible", timeout=6000)
                    if email and password:
                        print("[*] Automated credential entry using behavioral KeyboardController...")
                        await email_input.click()
                        keyboard = KeyboardController(page)
                        await keyboard.type(email, humanize=True)

                        pwd_input = page.locator("#password, input[name='password']")
                        await pwd_input.wait_for(state="visible", timeout=5000)
                        await pwd_input.click()
                        await keyboard.type(password, humanize=True)

                        sign_in_btn = page.get_by_role("button", name="Sign in")
                        await sign_in_btn.wait_for(state="visible", timeout=5000)
                        await sign_in_btn.click()
                    else:
                        print("[*] Interactive login active: Please sign in with your local password in the opened browser window.")
                        print(f"[*] Waiting up to {timeout_seconds} seconds for successful authentication...")
                except Exception:
                    print("[*] Already signed in or setup in progress...")

                # Wait until navigated away from signin
                await page.wait_for_function(
                    "() => !window.location.pathname.includes('/signin') && !window.location.pathname.includes('/setup')",
                    timeout=timeout_seconds * 1000,
                )

                print("[+] Successfully authenticated into n8n!")
                await context.storage_state(path=str(storage_state_path))
                print(f"[+] Saved storage state to: {storage_state_path}")

                # Dismiss any modal (like 'Connect a model' onboarding dialog)
                print("[*] Dismissing any onboarding modal dialogs...")
                for _ in range(3):
                    await page.keyboard.press("Escape")
                    try:
                        close_btn = page.locator("button.el-dialog__headerbtn, button[aria-label='Close'], button:has-text('✕'), .el-dialog__close").first
                        if await close_btn.is_visible():
                            await close_btn.click()
                    except Exception:
                        pass

                # Navigate to API settings to generate Public API key
                api_settings_url = f"{target_url.rstrip('/')}/settings/api"
                print(f"[*] Navigating to API settings: {api_settings_url}")
                await page.goto(api_settings_url, wait_until="domcontentloaded", timeout=30000)
                await page.keyboard.press("Escape")

                # Wait for Create API key button
                create_btn = page.locator("button:has-text('Create an API key'), button:has-text('Create API key'), button:has-text('Create key')").first
                api_key: Optional[str] = None

                try:
                    await create_btn.wait_for(state="visible", timeout=12000)
                    print("[*] Found 'Create API key' button. Clicking to generate new MCP key...")
                    await create_btn.click()

                    name_input = page.locator("input[placeholder*='key name' i], input[id*='name' i], input:visible").first
                    await name_input.wait_for(state="visible", timeout=5000)
                    keyboard = KeyboardController(page)
                    await keyboard.type("antigravity-mcp-key", humanize=True)

                    # Confirm creation inside modal
                    dialog = page.locator("[role='dialog'], .el-dialog").first
                    if await dialog.is_visible():
                        confirm_btn = dialog.locator("button:has-text('Create'), button:has-text('Save')").first
                        await confirm_btn.click()
                    else:
                        confirm_btn = page.locator("button:has-text('Create'), button:has-text('Save')").first
                        await confirm_btn.click()

                    # Extract the modal key value
                    key_display = page.locator("input[readonly], code, pre, .key-display, [data-test-id*='api-key' i]").first
                    await key_display.wait_for(state="visible", timeout=8000)
                    api_key = await key_display.input_value() if (await key_display.count() > 0 and await key_display.evaluate("el => 'value' in el")) else await key_display.inner_text()
                    api_key = api_key.strip()
                    print(f"[+] Successfully generated new API Key: {api_key}")
                except Exception as e:
                    print(f"[*] Note during API key creation: {e}")
                    print("[*] If an API key is already present or displayed, you can also copy it directly.")

                if api_key:
                    _update_configs(api_key, target_url)

                return True

            except Exception as exc:
                print(f"[-] Login or API extraction failed: {exc}", file=sys.stderr)
                return False
    finally:
        await pool.shutdown()


def _update_configs(api_key: str, target_url: str) -> None:
    """Updates .agents/mcp_config.json and n8n.mcp/.env with the discovered API key."""
    mcp_config_path = WORKSPACE_ROOT / ".agents" / "mcp_config.json"
    if mcp_config_path.exists():
        try:
            data = json.loads(mcp_config_path.read_text(encoding="utf-8"))
            if "mcpServers" in data and "n8n-mcp" in data["mcpServers"]:
                data["mcpServers"]["n8n-mcp"]["env"]["N8N_API_KEY"] = api_key
                data["mcpServers"]["n8n-mcp"]["env"]["N8N_HOST"] = target_url
                mcp_config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                print(f"[+] Updated {mcp_config_path} with N8N_API_KEY.")
        except Exception as e:
            print(f"[-] Failed to update mcp_config.json: {e}")

    env_path = WORKSPACE_ROOT / "n8n.mcp" / ".env"
    if env_path.exists():
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
            new_lines = []
            for line in lines:
                if line.startswith("N8N_API_KEY="):
                    new_lines.append(f"N8N_API_KEY={api_key}")
                elif line.startswith("N8N_HOST="):
                    new_lines.append(f"N8N_HOST={target_url}")
                else:
                    new_lines.append(line)
            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            print(f"[+] Updated {env_path} with N8N_API_KEY.")
        except Exception as e:
            print(f"[-] Failed to update n8n.mcp/.env: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="n8n Behavioral Login and Session Exporter")
    parser.add_argument("--url", default="http://localhost:5678", help="n8n instance URL")
    parser.add_argument("--email", default=os.getenv("N8N_USER_EMAIL"), help="Login Email")
    parser.add_argument("--password", default=os.getenv("N8N_USER_PASSWORD"), help="Login Password")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--timeout", type=int, default=180, help="Login timeout in seconds")

    args = parser.parse_args()

    success = asyncio.run(
        login_and_extract_key(
            target_url=args.url,
            email=args.email,
            password=args.password,
            headless=args.headless,
            timeout_seconds=args.timeout,
        )
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
