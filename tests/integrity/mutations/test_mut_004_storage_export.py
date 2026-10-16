"""Independent verifier for MUT-004: Storage Export Silent Failure."""
import pytest
from behavioral_playwright.storage.exporters import DataStorageManager


def test_storage_export_must_not_swallow_errors():
    """Writing to an impossible/invalid path must raise an exception and not return None."""
    sm = DataStorageManager()
    with pytest.raises((OSError, ValueError, IOError)):
        sm.export([{"key": "value"}], "\0illegal_export_path")
