"""
Root AutomationConfig and AIConfig orchestration dataclasses.
"""

from dataclasses import dataclass, field

from .domain import (
    BrowserConfig,
    ClickConfig,
    KeyboardConfig,
    LocaleConfig,
    MouseConfig,
    NetworkConfig,
    RenderingConfig,
)


@dataclass(frozen=True)
class AIConfig:
    enabled: bool = True
    confidence_threshold: float = 0.70
    timeout: float = 5.0
    retry: int = 2
    ocr_cv_enabled: bool = True
    self_healing_enabled: bool = True


@dataclass(frozen=True)
class AutomationConfig:
    """Root configuration object orchestrating all behavioral domain sub-configs via DI."""

    browser: BrowserConfig = field(default_factory=BrowserConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    locale: LocaleConfig = field(default_factory=LocaleConfig)
    rendering: RenderingConfig = field(default_factory=RenderingConfig)
    mouse: MouseConfig = field(default_factory=MouseConfig)
    keyboard: KeyboardConfig = field(default_factory=KeyboardConfig)
    click: ClickConfig = field(default_factory=ClickConfig)
    ai: AIConfig = field(default_factory=AIConfig)
