"""Independent verifier for MUT-007: Entropy Anomaly Guard."""
import pytest
from behavioral_playwright.powerplay.schema_guard import ResolvedSchemaIntegrityGuard


def test_empty_input_entropy_strictly_zero():
    """Mathematical invariant: Shannon entropy of an empty string is strictly 0.0."""
    entropy = ResolvedSchemaIntegrityGuard.compute_shannon_entropy("")
    assert entropy == 0.0, f"Expected Shannon entropy 0.0 for empty input, got {entropy}"
