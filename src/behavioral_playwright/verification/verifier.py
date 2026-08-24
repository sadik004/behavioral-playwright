"""Verification module."""

from typing import Dict, Any, Optional
from behavioral_playwright.page.session import PageSession
from behavioral_playwright.logging import get_logger

logger = get_logger("verification.verifier")

class StateVerifier:
    """Verifies page state transitions using available primitives."""

    def __init__(self, page: PageSession) -> None:
        self.page = page

    async def verify(self, 
                     state_before: Optional[Dict[str, Any]] = None, 
                     expected_title: Optional[str] = None,
                     expected_url: Optional[str] = None,
                     expected_element_selector: Optional[str] = None,
                     expected_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Validates the current DOM/page state against expectations.
        Returns the current state for future comparisons.
        
        Supported Verification:
        - Title (expected_title)
        - URL (expected_url)
        - Element existence (expected_element_selector)
        - Element content (expected_text) - requires expected_element_selector
        """
        current_title = await self.page.get_title()
        current_url = await self.page.get_url()
        
        logger.info(f"Verifying state for URL: {current_url}")
        
        verification_passed = True
        issues = []
        
        if expected_title and expected_title not in current_title:
            verification_passed = False
            issues.append(f"Expected title to contain '{expected_title}', got '{current_title}'")
            
        if expected_url and expected_url != current_url:
            verification_passed = False
            issues.append(f"Expected URL to be '{expected_url}', got '{current_url}'")
            
        if expected_element_selector:
            # Check element visibility
            loc = self.page.raw_page.locator(expected_element_selector)
            try:
                # wait for it briefly
                await loc.wait_for(state="visible", timeout=2000)
            except Exception:
                verification_passed = False
                issues.append(f"Expected element '{expected_element_selector}' was not visible.")
                
            if verification_passed and expected_text:
                actual_text = await loc.inner_text()
                if expected_text not in actual_text:
                    verification_passed = False
                    issues.append(f"Expected text '{expected_text}' in element '{expected_element_selector}', got '{actual_text}'")

        if state_before:
            if "url" in state_before and state_before["url"] != current_url:
                logger.info(f"Navigation occurred from {state_before['url']} to {current_url}")
                
        return {
            "verified": verification_passed,
            "issues": issues,
            "current_state": {
                "title": current_title,
                "url": current_url
            }
        }
