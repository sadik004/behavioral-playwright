"""Storage base interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Sequence


class BaseExporter(ABC):
    """Abstract interface for exporting structured extraction records."""

    @abstractmethod
    def export(self, records: Sequence[Dict[str, Any]], target_path: str, **kwargs: Any) -> str:
        """Exports records to destination path and returns the resolved target path."""
        pass
