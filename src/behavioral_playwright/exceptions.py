"""
Exception hierarchy for the Behavioral Playwright Automation Framework.
"""


class AutomationError(Exception):
    """Base exception for all errors occurring within the Behavioral Automation Framework."""

    pass


class ConfigurationError(AutomationError):
    """Raised when configuration validation, structure, or URL protocols are malformed."""

    pass


class ProviderError(AutomationError):
    """Raised when browser providers cannot be located, mapped, or fail to resolve interfaces."""

    pass


class BrowserLaunchError(AutomationError):
    """Raised when native Chromium or CloakBrowser binary initialization fails."""

    pass


class NavigationError(AutomationError):
    """Raised on critical web navigation errors, non-retryable status codes, or timeouts."""

    pass


class InteractionError(AutomationError):
    """Raised during automated human emulation failures, coordinate slips, or input blockades."""

    pass
