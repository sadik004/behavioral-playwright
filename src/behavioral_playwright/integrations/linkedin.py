"""LinkedIn Behavioral Automation Client.

Integrates stealth Playwright browser pooling, human-mimetic mouse & keyboard
trajectory generation, and typed Pydantic DTO outputs for LinkedIn interactions.
"""

from __future__ import annotations

import os
from typing import Any, Optional
from playwright.async_api import Page, async_playwright

from behavioral_playwright.automation.keyboard import KeyboardController
from behavioral_playwright.automation.mouse import MouseController
from behavioral_playwright.browser.pool import BrowserPoolManager
from behavioral_playwright.config.settings import BrowserConfig
from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.linkedin_dtos import (
    LinkedInAuthStatusDTO,
    LinkedInProfileDTO,
    LinkedInUpdateResultDTO,
)

logger = get_logger("linkedin")



class LinkedInAutomationClient:
    """Enterprise client for human-mimetic LinkedIn profile automation and inspection."""

    def __init__(
        self,
        pool: Optional[BrowserPoolManager] = None,
        default_storage_state: str = "linkedin_state.json",
    ) -> None:
        self.default_storage_state = default_storage_state
        self._pool = pool
        self._owns_pool = pool is None

    async def _get_pool(self) -> BrowserPoolManager:
        if self._pool is None:
            config = BrowserConfig(headless=True, allow_media=False)
            self._pool = BrowserPoolManager(config=config)
            await self._pool.initialize()
        elif not self._pool.is_initialized:
            await self._pool.initialize()
        return self._pool

    async def close(self) -> None:
        """Closes master browser pool if owned by this client."""
        if self._owns_pool and self._pool is not None and self._pool.is_initialized:
            await self._pool.shutdown()

    async def check_auth_status(
        self,
        storage_state_path: Optional[str] = None,
    ) -> LinkedInAuthStatusDTO:
        """Verifies whether the persistent session file provides an active LinkedIn authentication."""
        path = storage_state_path or self.default_storage_state
        if not os.path.exists(path):
            return LinkedInAuthStatusDTO(
                authenticated=False,
                checkpoint_triggered=False,
                message=f"Session file not found at '{path}'. Please export storage_state first.",
            )

        pool = await self._get_pool()
        try:
            async with pool.get_page(storage_state=path, allow_media=False) as page:
                await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
                
                # Check current URL destination
                current_url = page.url.lower()

                if "checkpoint" in current_url or "challenge" in current_url:
                    return LinkedInAuthStatusDTO(
                        authenticated=False,
                        checkpoint_triggered=True,
                        message="Checkpoint / CAPTCHA challenge detected. Interactive verification required.",
                    )

                if "login" in current_url or "authwall" in current_url or "signup" in current_url:
                    return LinkedInAuthStatusDTO(
                        authenticated=False,
                        checkpoint_triggered=False,
                        message="Session expired or invalid. Redirected to login.",
                    )

                # Attempt to extract user identity handle if present
                user_handle: Optional[str] = None
                try:
                    profile_nav_locator = page.locator("a[href*='/in/']:visible").first
                    if await profile_nav_locator.count() > 0:
                        href = await profile_nav_locator.get_attribute("href")
                        if href and "/in/" in href:
                            user_handle = href.split("/in/")[1].split("/")[0].split("?")[0]
                except Exception as exc:
                    logger.debug(f"[LinkedInClient] Non-fatal user handle detection notice: {exc}")

                return LinkedInAuthStatusDTO(
                    authenticated=True,
                    checkpoint_triggered=False,
                    username=user_handle,
                    message="Session is authenticated and active on LinkedIn feed.",
                )
        except Exception as exc:
            logger.error(f"[LinkedInClient] Failed during check_auth_status: {exc}")
            return LinkedInAuthStatusDTO(
                authenticated=False,
                checkpoint_triggered=False,
                message=f"Network or execution error: {str(exc)}",
            )

    async def get_profile_overview(
        self,
        storage_state_path: Optional[str] = None,
        profile_url: str = "https://www.linkedin.com/in/me/",
    ) -> LinkedInProfileDTO:
        """Extracts user headline, about section, and display name from profile."""
        path = storage_state_path or self.default_storage_state
        if not os.path.exists(path):
            raise FileNotFoundError(f"Session file not found at '{path}'.")

        pool = await self._get_pool()
        async with pool.get_page(storage_state=path, allow_media=False) as page:
            await page.goto(profile_url, wait_until="domcontentloaded")

            # Dynamic wait for main content container
            main_container = page.locator("main")
            await main_container.wait_for(state="attached", timeout=15000)

            # Extract full display name
            name_locator = page.locator("h1.text-heading-xlarge, h1:visible").first
            name = await name_locator.inner_text() if await name_locator.count() > 0 else ""

            # Extract headline
            headline_locator = page.locator(
                "div.text-body-medium.break-words, div[data-generated-suggestion-target], .pv-text-details__left-panel div.text-body-medium"
            ).first
            headline = await headline_locator.inner_text() if await headline_locator.count() > 0 else ""

            # Extract location
            loc_locator = page.locator(
                "span.text-body-small.inline.t-black--light.break-words, span.pv-text-details__left-panel"
            ).first
            location = await loc_locator.inner_text() if await loc_locator.count() > 0 else None

            # Extract About summary section if present
            about_text: Optional[str] = None
            about_section = page.locator("section:has(#about) .inline-show-more-text, section:has(#about) div.display-flex span[aria-hidden='true']").first
            if await about_section.count() > 0:
                about_text = await about_section.inner_text()

            return LinkedInProfileDTO(
                name=name.strip(),
                headline=headline.strip(),
                about=about_text.strip() if about_text else None,
                location=location.strip() if location else None,
                profile_url=page.url,
            )

    async def update_headline(
        self,
        new_headline: str,
        storage_state_path: Optional[str] = None,
    ) -> LinkedInUpdateResultDTO:
        """Modifies user headline using humanized typing and semantic ARIA locators."""
        if not new_headline or not new_headline.strip():
            raise ValueError("new_headline cannot be empty.")

        path = storage_state_path or self.default_storage_state
        if not os.path.exists(path):
            return LinkedInUpdateResultDTO(
                success=False,
                field_updated="headline",
                new_value=new_headline,
                message=f"Session state '{path}' not found.",
            )

        pool = await self._get_pool()
        async with pool.get_page(storage_state=path, allow_media=False) as page:
            await page.goto("https://www.linkedin.com/in/me/", wait_until="domcontentloaded")

            # 1. Locate Edit Intro button
            edit_btn = page.locator(
                "button[aria-label*='Edit intro'], button[aria-label*='Edit profile'], a[href*='edit/intro']"
            ).first
            await edit_btn.wait_for(state="visible", timeout=12000)

            # Move and click with human trajectory
            mouse = MouseController(page)
            box = await edit_btn.bounding_box()
            if box:
                await mouse.click(box["x"] + box["width"] / 2.0, box["y"] + box["height"] / 2.0)
            else:
                await edit_btn.click()

            # 2. Wait for modal dialog
            dialog = page.locator("div[role='dialog']").first
            await dialog.wait_for(state="visible", timeout=10000)

            # 3. Locate Headline input field
            headline_input = dialog.locator(
                "input[id*='headline'], input[name*='headline'], textarea[id*='headline']"
            ).first
            await headline_input.wait_for(state="visible", timeout=8000)

            old_headline = await headline_input.input_value()

            # Focus and clear
            await headline_input.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")

            # 4. Humanized typing
            keyboard = KeyboardController(page)
            await keyboard.type(new_headline.strip(), humanize=True)

            # 5. Click Save button
            save_btn = dialog.locator(
                "button:has-text('Save'), button[aria-label*='Save']"
            ).first
            await save_btn.wait_for(state="visible", timeout=5000)
            await save_btn.click()

            # 6. Wait for dialog to disappear (verifying commit)
            await dialog.wait_for(state="hidden", timeout=12000)

            return LinkedInUpdateResultDTO(
                success=True,
                field_updated="headline",
                old_value=old_headline,
                new_value=new_headline.strip(),
                message="Headline successfully updated on LinkedIn.",
            )

    async def update_about(
        self,
        new_about: str,
        storage_state_path: Optional[str] = None,
    ) -> LinkedInUpdateResultDTO:
        """Modifies user About / Summary section."""
        if not new_about or not new_about.strip():
            raise ValueError("new_about cannot be empty.")

        path = storage_state_path or self.default_storage_state
        if not os.path.exists(path):
            return LinkedInUpdateResultDTO(
                success=False,
                field_updated="about",
                new_value=new_about,
                message=f"Session state '{path}' not found.",
            )

        pool = await self._get_pool()
        async with pool.get_page(storage_state=path, allow_media=False) as page:
            await page.goto("https://www.linkedin.com/in/me/", wait_until="domcontentloaded")

            # 1. Locate About section edit button
            edit_about_btn = page.locator(
                "section:has(#about) button[aria-label*='Edit about'], a[href*='edit/about']"
            ).first
            await edit_about_btn.wait_for(state="visible", timeout=12000)
            await edit_about_btn.click()

            # 2. Wait for modal dialog
            dialog = page.locator("div[role='dialog']").first
            await dialog.wait_for(state="visible", timeout=10000)

            # 3. Locate summary textarea
            textarea = dialog.locator(
                "textarea[id*='description'], textarea[id*='summary'], textarea:visible"
            ).first
            await textarea.wait_for(state="visible", timeout=8000)

            old_about = await textarea.input_value()

            # Clear
            await textarea.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")

            # 4. Humanized typing
            keyboard = KeyboardController(page)
            await keyboard.type(new_about.strip(), humanize=True)

            # 5. Save
            save_btn = dialog.locator(
                "button:has-text('Save'), button[aria-label*='Save']"
            ).first
            await save_btn.click()

            # 6. Wait for dialog to dismiss
            await dialog.wait_for(state="hidden", timeout=12000)

            return LinkedInUpdateResultDTO(
                success=True,
                field_updated="about",
                old_value=old_about,
                new_value=new_about.strip(),
                message="About section successfully updated on LinkedIn.",
            )

    @staticmethod
    async def export_session_interactive(
        output_path: str = "linkedin_state.json",
        timeout_seconds: int = 180,
    ) -> LinkedInAuthStatusDTO:
        """
        Launches an interactive, headful browser window for manual human login.
        Dumps the verified storage_state (cookies, tokens) to disk upon successful feed navigation.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context()
            page = await context.new_page()

            logger.info("[LinkedInClient] Opening interactive login window...")
            await page.goto("https://www.linkedin.com/login")

            try:
                # Wait until navigation reaches the authenticated feed
                await page.wait_for_url("**/feed/**", timeout=timeout_seconds * 1000)
                await context.storage_state(path=output_path)
                logger.info(f"[LinkedInClient] Successfully captured and exported storage state to: {output_path}")

                await browser.close()
                return LinkedInAuthStatusDTO(
                    authenticated=True,
                    checkpoint_triggered=False,
                    message=f"Interactive login succeeded. State saved to '{output_path}'.",
                )
            except Exception as exc:
                await browser.close()
                return LinkedInAuthStatusDTO(
                    authenticated=False,
                    checkpoint_triggered=True,
                    message=f"Interactive login timed out or failed: {exc}",
                )
