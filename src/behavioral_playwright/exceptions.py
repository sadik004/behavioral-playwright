"""Exceptions for the behavioral-playwright framework."""

from typing import Any, Optional


class BehavioralPlaywrightError(Exception):
    """Base exception for all behavioral-playwright errors."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class BrowserProviderError(BehavioralPlaywrightError):
    """Raised when a browser provider operation fails."""
    pass


class NavigationError(BehavioralPlaywrightError):
    """Raised when page navigation fails or times out."""
    pass


class ElementResolutionError(BehavioralPlaywrightError):
    """Raised when an element cannot be resolved across all healing strategies."""
    pass


class ExtractionError(BehavioralPlaywrightError):
    """Raised when structured DOM extraction fails."""
    pass


class ConfigurationError(BehavioralPlaywrightError):
    """Raised when invalid or inconsistent configuration is provided."""
    pass


class CircuitBreakerError(BehavioralPlaywrightError):
    """Raised when an operation is rejected because the circuit breaker is OPEN."""
    pass


class TimeoutError(BehavioralPlaywrightError):
    """Raised when an asynchronous operation exceeds the configured timeout."""
    pass


class ProviderUnavailableError(BehavioralPlaywrightError, RuntimeError):
    """Raised when a required provider/dependency is missing or not booted.

    Canonical exception uniting top-level framework errors and provider subsystem errors.
    Inherits from both BehavioralPlaywrightError and RuntimeError for complete backward compatibility.
    """

    def __init__(
        self,
        message_or_provider: str,
        module: Optional[str] = None,
        install_hint: Optional[str] = None,
        details: Optional[Any] = None,
    ) -> None:
        if module is not None or install_hint is not None:
            provider = message_or_provider
            msg = (
                f"{provider} provider is UNAVAILABLE: module {module!r} cannot be "
                f"imported. Optional install: {install_hint}. "
                "No fallback or fabricated behavior is provided."
            )
            self.provider = provider
            self.module = module or ""
            self.install_hint = install_hint or ""
            super().__init__(message=msg, details=details or {"provider": provider, "module": module, "install_hint": install_hint})
        else:
            self.provider = ""
            self.module = ""
            self.install_hint = ""
            super().__init__(message=message_or_provider, details=details)


class ProviderError(BehavioralPlaywrightError):
    """Raised when an underlying provider operation fails at runtime."""
    pass
