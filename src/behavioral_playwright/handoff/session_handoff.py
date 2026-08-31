"""Handoff module."""

from typing import Dict, Any, Optional, List
from behavioral_playwright.page.session import PageSession
from behavioral_playwright.logging import get_logger

logger = get_logger("handoff.session_handoff")


class SessionHandoff:
    """Manages browser session handoffs (cookies, local/session storage)."""

    def __init__(self, page: PageSession) -> None:
        self.page = page

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def export(self) -> Dict[str, Any]:
        """
        Export the current session state for handoff.

        Captures:
        - cookies (via context.storage_state)
        - localStorage for all origins (via context.storage_state)
        - sessionStorage for the current origin (via page.evaluate)
        - current URL (as metadata)
        """
        context = getattr(self.page.raw_page, "context", None)
        current_url = await self.page.get_url()

        if context is None:
            # Mock/raw pages without a browser context: degrade gracefully
            logger.warning("No browser context available; exporting minimal state")
            return {"cookies": [], "origins": [], "current_url": current_url}

        logger.info("Extracting context state for handoff")
        try:
            state = await context.storage_state()
        except Exception as exc:
            raise RuntimeError(f"Failed to export storage state: {exc}") from exc

        state["current_url"] = current_url

        # sessionStorage is not captured by storage_state(); grab it manually
        try:
            session_storage = await self.page.raw_page.evaluate(
                "() => JSON.stringify(sessionStorage)"
            )
            if session_storage:
                state["session_storage"] = session_storage
        except Exception as exc:
            logger.warning("Could not capture sessionStorage: %s", exc)

        return state

    async def restore(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject a previously exported state into the current session.

        Supported:
        - cookies (via context.add_cookies)
        - localStorage for the current origin (via page.evaluate)
        - sessionStorage for the current origin (via page.evaluate)
        - navigation to the saved URL

        Note: For full cross-origin storage restoration, create a new
        context with `storage_state` instead.
        """
        if not isinstance(context_data, dict):
            raise TypeError("context_data must be a dict")

        context = getattr(self.page.raw_page, "context", None)
        logger.info("Injecting context state from handoff")

        # --- Cookies ---
        cookies = context_data.get("cookies")
        if cookies:
            if not isinstance(cookies, list):
                raise TypeError("'cookies' must be a list")
            if context is None:
                logger.warning("No browser context; skipping cookie injection")
            else:
                try:
                    await context.add_cookies(cookies)
                except Exception as exc:
                    raise RuntimeError(f"Failed to inject cookies: {exc}") from exc

        # --- Navigate first so localStorage/sessionStorage target the right origin ---
        current_url = context_data.get("current_url")
        if current_url:
            try:
                await self.page.goto(current_url)
            except Exception as exc:
                logger.warning("Navigation to %s failed: %s", current_url, exc)

        # --- localStorage (current origin only) ---
        origins = context_data.get("origins")
        if origins:
            if not isinstance(origins, list):
                raise TypeError("'origins' must be a list")
            await self._inject_local_storage(origins, current_url)

        # --- sessionStorage (current origin only) ---
        session_storage = context_data.get("session_storage")
        if session_storage:
            try:
                await self.page.raw_page.evaluate(
                    "(data) => { const items = JSON.parse(data); "
                    "for (const [k, v] of Object.entries(items)) sessionStorage.setItem(k, v); }",
                    session_storage,
                )
            except Exception as exc:
                logger.warning("Could not restore sessionStorage: %s", exc)

        return context_data

    async def handoff(self, context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Backward-compatible wrapper: export when no data given, restore otherwise."""
        if context_data is None:
            return await self.export()
        return await self.restore(context_data)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _inject_local_storage(self, origins: List[Dict[str, Any]], current_url: Optional[str]) -> None:
        """Inject localStorage entries matching the current origin."""
        for origin_data in origins:
            origin = origin_data.get("origin", "")
            if not origin or not current_url or not current_url.startswith(origin):
                logger.debug("Skipping localStorage for non-matching origin: %s", origin)
                continue
            for item in origin_data.get("localStorage", []):
                try:
                    await self.page.raw_page.evaluate(
                        "([k, v]) => localStorage.setItem(k, v)",
                        [item["name"], item["value"]],
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to inject localStorage key '%s' for %s: %s",
                        item.get("name"), origin, exc,
                    )
