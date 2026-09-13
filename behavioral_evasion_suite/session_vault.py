"""
Patch 7: Automated Session State Persistence Vault
Manages authenticated cookies, local storage, and IndexedDB state snapshots
to persist browser login sessions across ContextRotator cycles.
"""
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("BehavioralEvasion.SessionVault")


class SessionStateVault:
    """
    Manages authenticated cookies, local storage, and IndexedDB state snapshots
    to persist browser login sessions across ContextRotator cycles.
    """
    def __init__(self, filepath: str = "storage_state.json") -> None:
        self.filepath = filepath

    async def save_state(self, context: Any) -> None:
        """Dumps storage_state of the active context to a localized JSON file."""
        logger.info(f"SessionStateVault: Saving authenticated session state to {self.filepath}")
        if hasattr(context, "storage_state"):
            await context.storage_state(path=self.filepath)
        else:
            dummy_state = {"cookies": [], "origins": []}
            with open(self.filepath, "w") as f:
                json.dump(dummy_state, f)
        logger.info("SessionStateVault: State snapshot written.")

    async def load_state(self, browser: Any, proxy_config: Optional[Dict[str, str]] = None) -> Any:
        """Loads persistent session state variables back into a fresh context."""
        logger.info(f"SessionStateVault: Loading stored session cookies from {self.filepath}")
        context_args = {
            "ignore_https_errors": True,
            "viewport": {"width": 1280, "height": 720}
        }
        if proxy_config:
            context_args["proxy"] = proxy_config

        if os.path.exists(self.filepath):
            context_args["storage_state"] = self.filepath

        return await browser.new_context(**context_args)
