"""Handoff module."""

from typing import Dict, Any, Optional
from behavioral_playwright.page.session import PageSession
from behavioral_playwright.logging import get_logger

logger = get_logger("handoff.session_handoff")

class SessionHandoff:
    """Manages browser session handoffs (cookies, local storage)."""

    def __init__(self, page: PageSession) -> None:
        self.page = page

    async def handoff(self, context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Exports the current context state (if context_data is None)
        or injects the provided context_data into the current session.
        
        Supported State:
        - cookies
        - localStorage
        - current URL (as metadata)
        
        Unsupported State:
        - sessionStorage (not natively supported by context.storage_state)
        - IndexedDB (not natively supported by context.storage_state)
        """
        context = self.page.raw_page.context
        
        if context_data is None:
            logger.info("Extracting context state for handoff")
            # storage_state() captures cookies and localStorage for all origins
            state = await context.storage_state()
            state["current_url"] = await self.page.get_url()
            return state
        else:
            logger.info("Injecting context state from handoff")
            # Note: Injection of storage state (localStorage) mid-session via API is tricky.
            # Playwright normally takes storage_state on context creation.
            # But we can at least add cookies.
            if "cookies" in context_data:
                await context.add_cookies(context_data["cookies"])
            # We can also try to evaluate localStorage if it's for the current origin
            if "origins" in context_data and "current_url" in context_data:
                # We can't inject cross-origin local storage reliably dynamically after context creation
                # Documenting this limitation.
                logger.warning("localStorage injection dynamically mid-session is limited to cookies. Context recreation is recommended for full storage state.")
            
            # Navigate to the restored URL if present
            if "current_url" in context_data:
                await self.page.goto(context_data["current_url"])
                
            return context_data
