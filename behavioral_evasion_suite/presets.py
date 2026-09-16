"""
Unified Preset Configuration & Profiles for Behavioral Evasion Suite (v6.0.0 Level 5 Quantum Edition)
Provides simple, zero-friction configuration presets for modern developers and AI agents.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any


class Preset(str, Enum):
    """Execution presets balancing evasion depth vs speed/resource overhead."""
    MAX_QUANTUM = "max_quantum"                  # SOTA Level 5: All 31 shields + kernel input + subpixel fonts
    BALANCED = "balanced"                        # High evasion + optimized performance for mass scraping
    HEADLESS_UNDETECTABLE = "headless_undetectable" # Tuned specifically for Cloudflare / DataDome headless bypass
    FAST_BYPASS = "fast_bypass"                  # Low overhead, essential CDP + TLS + Canvas evasion


@dataclass
class StealthConfig:
    """Centralized, ergonomic configuration for the entire suite."""
    preset: Preset = Preset.MAX_QUANTUM
    headless: bool = True
    proxy: Optional[str] = None
    user_data_dir: Optional[str] = None
    hardware_profile: Optional[str] = None
    use_kernel_input: bool = False
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    locale: str = "en-US"
    timezone_id: str = "America/New_York"
    enable_worker_shield: bool = True
    enable_subpixel_font_shield: bool = True
    enable_media_devices: bool = True
    enable_v8_shield: bool = True
    enable_network_stack_spoof: bool = True
    custom_options: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_preset(cls, preset: Preset | str = Preset.MAX_QUANTUM, **overrides) -> "StealthConfig":
        """Factory method to create a tailored configuration from a preset."""
        if isinstance(preset, str):
            try:
                preset = Preset(preset.lower())
            except ValueError:
                preset = Preset.MAX_QUANTUM

        cfg = cls(preset=preset)

        if preset == Preset.FAST_BYPASS:
            cfg.enable_worker_shield = False
            cfg.enable_subpixel_font_shield = False
            cfg.enable_media_devices = False
            cfg.enable_network_stack_spoof = False
            cfg.use_kernel_input = False
        elif preset == Preset.HEADLESS_UNDETECTABLE:
            cfg.headless = True
            cfg.enable_worker_shield = True
            cfg.enable_subpixel_font_shield = True
            cfg.enable_v8_shield = True
        elif preset == Preset.BALANCED:
            cfg.enable_worker_shield = True
            cfg.enable_subpixel_font_shield = True
            cfg.enable_media_devices = True
            cfg.use_kernel_input = False
        elif preset == Preset.MAX_QUANTUM:
            cfg.enable_worker_shield = True
            cfg.enable_subpixel_font_shield = True
            cfg.enable_media_devices = True
            cfg.enable_v8_shield = True
            cfg.enable_network_stack_spoof = True
            cfg.use_kernel_input = True

        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
            else:
                cfg.custom_options[k] = v

        return cfg
