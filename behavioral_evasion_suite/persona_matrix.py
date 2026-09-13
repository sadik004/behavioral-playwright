"""
Digital Soul & Persona Continuity Matrix
Manages persistent identity profiles, behavioral DNA, and deadlock-free proxy rotation.
"""
import os
import json
import time
import random
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("BehavioralEvasion.PersonaMatrix")


class ProfileVault:
    """Persistent storage vault for cookies, cache, and session state history with portable fallback."""
    def __init__(self, profile_id: str, storage_dir: Optional[str] = None):
        self.profile_id = profile_id
        if storage_dir is None:
            storage_dir = os.getenv("POWERHAND_PROFILE_DIR", os.path.expanduser("~/.powerhand/profiles"))
        
        try:
            os.makedirs(storage_dir, exist_ok=True)
            self.storage_dir = storage_dir
        except Exception:
            self.storage_dir = "/tmp/powerhand_profiles"
            os.makedirs(self.storage_dir, exist_ok=True)

        self.profile_file = os.path.join(self.storage_dir, f"{profile_id}.json")

    def load_state(self) -> Dict[str, Any]:
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading profile vault: {e}. Falling back to clean state.")
        return {"cookies": [], "origins": [], "trust_score": 0.85}

    def save_state(self, cookies: List[Dict[str, Any]], storage_state: Dict[str, Any], trust_score: float = 0.9):
        state = {
            "profile_id": self.profile_id,
            "cookies": cookies,
            "storage_state": storage_state,
            "trust_score": trust_score,
            "last_active": time.time()
        }
        with open(self.profile_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)


class BehavioralDNA:
    """Persona-seeded deterministic typing, movement, and neuromuscular parameters."""
    def __init__(self, persona_seed: int = 42069):
        rnd = random.Random(persona_seed)
        self.base_wpm = rnd.uniform(55.0, 75.0)
        self.typo_rate = rnd.uniform(0.03, 0.06)
        self.tremor_hz = rnd.uniform(8.0, 12.0)
        self.saccade_velocity_mult = rnd.uniform(0.9, 1.15)

    def get_config(self) -> Dict[str, float]:
        return {
            "wpm": self.base_wpm,
            "typo_rate": self.typo_rate,
            "tremor_hz": self.tremor_hz,
            "saccade_mult": self.saccade_velocity_mult
        }


class IdentityAnchor:
    """
    Sticky Residential Proxy, User-Agent, Viewport, and Timezone Mapping.
    TLA+ Patch #3: Deadlock-free proxy pool rotation and fallback state machine.
    """
    def __init__(self, proxy_pool: Optional[List[str]] = None, user_agent: Optional[str] = None):
        self.proxy_pool = proxy_pool or [
            "http://residential.proxy.internal:8080",
            "http://residential.proxy.internal:8081"
        ]
        self.current_proxy_idx = 0
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        self.viewport = {"width": 1920, "height": 1080}
        self.timezone_id = "America/New_York"
        self.locale = "en-US"

    def get_current_proxy(self) -> Optional[str]:
        if not self.proxy_pool:
            return None
        return self.proxy_pool[self.current_proxy_idx % len(self.proxy_pool)]

    def rotate_proxy_on_failure(self) -> Optional[str]:
        """TLA+ Deadlock Fix: Safely rotates proxy or transitions to direct connection if pool is exhausted."""
        if not self.proxy_pool:
            logger.warning("Proxy pool empty. Fallback to direct clean connection.")
            return None

        self.current_proxy_idx += 1
        if self.current_proxy_idx >= len(self.proxy_pool):
            logger.warning("Proxy pool exhausted. Fallback to direct clean connection state.")
            return None
        return self.get_current_proxy()

    def get_playwright_context_options(self) -> Dict[str, Any]:
        opts = {
            "user_agent": self.user_agent,
            "viewport": self.viewport,
            "timezone_id": self.timezone_id,
            "locale": self.locale,
            "permissions": ["geolocation", "notifications"]
        }
        proxy = self.get_current_proxy()
        if proxy:
            opts["proxy"] = {"server": proxy}
        return opts


class DigitalSoulPersonaMatrix:
    """Unified persona manager maintaining persistent identity, trust score, and session state."""
    def __init__(self, profile_id: str = "persona_alpha_1", seed: int = 42069):
        self.profile_id = profile_id
        self.vault = ProfileVault(profile_id)
        self.dna = BehavioralDNA(seed)
        self.anchor = IdentityAnchor()
