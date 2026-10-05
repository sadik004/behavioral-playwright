"""Independent verifier for MUT-006: Saccade Path Generation."""
import pytest
from behavioral_evasion_suite.powerhand_master import PowerHandMaster


def test_saccade_path_must_be_non_empty_and_valid():
    """Saccade generation must produce non-empty trajectory points."""
    master = PowerHandMaster(seed=42)
    path = master.get_saccade_path((10.0, 10.0), (350.0, 250.0), steps=25)
    assert isinstance(path, list)
    assert len(path) == 25, f"Expected 25 trajectory points, got {len(path)}"
    assert path[0]["x"] != path[-1]["x"] or path[0]["y"] != path[-1]["y"]
