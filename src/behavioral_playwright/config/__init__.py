"""Configuration package exposing domain and root configs."""

from .domain import (
    BrowserConfig,
    ClickConfig,
    KeyboardConfig,
    LocaleConfig,
    MouseConfig,
    NetworkConfig,
    RenderingConfig,
)
from .root import (
    AIConfig,
    AutomationConfig,
)

__all__ = [
    "MouseConfig",
    "KeyboardConfig",
    "ClickConfig",
    "BrowserConfig",
    "NetworkConfig",
    "LocaleConfig",
    "RenderingConfig",
    "AIConfig",
    "AutomationConfig",
]
