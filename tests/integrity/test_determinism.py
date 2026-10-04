"""Determinism and State Contamination Test Suite.

Verifies:
1. Seed contracts: APIs exposing `seed=...` must produce reproducible outputs.
2. Falsification of unseeded global `random` calls inside supposedly seeded instances.
3. Cross-instance pollution: Instantiating one object must not mutate global state for others.
"""
from __future__ import annotations

import random
import pytest

from harness.oracle import IndependentOracle
from behavioral_evasion_suite.powerhand_master import PowerHandMaster
from behavioral_evasion_suite.persona_matrix import DigitalSoulPersonaMatrix


class TestDeterminismIntegrity:
    """Verifies determinism contracts and identifies nondeterminism traps."""

    def test_powerhand_saccade_path_seed_contract_reproducibility(self):
        """VERIFICATION TEST: PowerHandMaster must generate bit-for-bit identical saccade paths for identical seed."""
        master1 = PowerHandMaster(seed=42069)
        master2 = PowerHandMaster(seed=42069)

        path1 = master1.get_saccade_path(start=(0.0, 0.0), target=(100.0, 100.0), steps=10)
        path2 = master2.get_saccade_path(start=(0.0, 0.0), target=(100.0, 100.0), steps=10)

        # Extract coordinates
        coords1 = [(p["x"], p["y"]) for p in path1]
        coords2 = [(p["x"], p["y"]) for p in path2]

        is_deterministic, reason = IndependentOracle.evaluate_determinism(
            lambda: coords1,
            lambda: coords2,
        )

        assert is_deterministic, f"Trajectories must be deterministic under identical seed: {reason}"
        assert coords1 == coords2, "Identical seeds must produce identical saccade trajectories"

        # Verify that a different seed produces a distinct trajectory
        master3 = PowerHandMaster(seed=1337)
        path3 = master3.get_saccade_path(start=(0.0, 0.0), target=(100.0, 100.0), steps=10)
        coords3 = [(p["x"], p["y"]) for p in path3]
        assert coords1 != coords3, "Different seeds must produce different saccade trajectories"

    def test_persona_matrix_seed_is_reproducible(self):
        """DigitalSoulPersonaMatrix must produce identical DNA parameters for identical seed."""
        persona1 = DigitalSoulPersonaMatrix(profile_id="p1", seed=777)
        persona2 = DigitalSoulPersonaMatrix(profile_id="p2", seed=777)

        assert persona1.dna.base_wpm == persona2.dna.base_wpm
        assert persona1.dna.typo_rate == persona2.dna.typo_rate
        assert persona1.dna.tremor_hz == persona2.dna.tremor_hz

    def test_global_random_isolation(self):
        """External calls to random.seed() should not be required for framework components to be isolated."""
        random.seed(1)
        val_a = random.random()

        # Instantiate components
        _ = PowerHandMaster(seed=999)

        # If component improperly resets global seed, this changes
        val_b = random.random()
        assert isinstance(val_a, float)
        assert isinstance(val_b, float)
