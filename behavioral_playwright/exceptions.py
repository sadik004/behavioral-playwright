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
