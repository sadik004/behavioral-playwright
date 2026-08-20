"""Utils package providing protocols, clock/RNG abstractions, and mock objects."""

from .clock_rng import (
    DeterministicRandomSource,
    SystemClock,
    SystemRandomSource,
    VirtualTestClock,
)
from .mocks import (
    MockBrowserContext,
    MockElement,
    MockKeyboard,
    MockMouse,
    MockPage,
)
from .protocols import (
    BrowserContextProtocol,
    BrowserProtocol,
    BrowserProvider,
    ChallengeSolverProtocol,
    Clock,
    ElementHandleProtocol,
    KeyboardProtocol,
    MouseProtocol,
    PageProtocol,
    RandomSource,
)

__all__ = [
    "RandomSource",
    "Clock",
    "MouseProtocol",
    "KeyboardProtocol",
    "ElementHandleProtocol",
    "PageProtocol",
    "BrowserContextProtocol",
    "BrowserProtocol",
    "BrowserProvider",
    "ChallengeSolverProtocol",
    "SystemRandomSource",
    "DeterministicRandomSource",
    "SystemClock",
    "VirtualTestClock",
    "MockMouse",
    "MockKeyboard",
    "MockElement",
    "MockPage",
    "MockBrowserContext",
]
