"""StateTracker for recording page lifecycle and navigation history."""

from collections import deque
from dataclasses import dataclass, field
import time
from typing import Any, Callable, Dict, List, Optional, Deque


@dataclass
class PageStateEntry:
    """Snapshot entry of a recorded page state."""
    url: str
    title: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateTracker:
    """Tracks page navigation history and detects navigation loops with bounded capacity."""

    def __init__(
        self,
        clock_fn: Optional[Callable[[], float]] = None,
        max_history: int = 500,
    ) -> None:
        self._clock_fn = clock_fn or time.time
        self.max_history = max_history
        self.history: Deque[PageStateEntry] = deque(maxlen=max_history)

    def record_state(self, url: str, title: str = "", metadata: Optional[Dict[str, Any]] = None) -> PageStateEntry:
        """Records a page transition state."""
        entry = PageStateEntry(
            url=url,
            title=title,
            timestamp=self._clock_fn(),
            metadata=metadata or {}
        )
        self.history.append(entry)
        return entry

    @property
    def current_state(self) -> Optional[PageStateEntry]:
        """Returns the most recent page state entry."""
        return self.history[-1] if self.history else None

    @property
    def transition_count(self) -> int:
        return len(self.history)

    def is_in_loop(self, window_size: int = 4, max_repeats: int = 3) -> bool:
        """
        Determines if navigation is trapped in an oscillating redirect loop.
        Checks if the current URL has appeared >= max_repeats within the last window_size transitions.
        """
        if len(self.history) < window_size:
            return False

        recent_entries = list(self.history)[-window_size:]
        recent_urls = [entry.url for entry in recent_entries]
        if not recent_urls:
            return False

        latest_url = recent_urls[-1]
        return recent_urls.count(latest_url) >= max_repeats

    def clear(self) -> None:
        """Clears navigation history."""
        self.history.clear()
