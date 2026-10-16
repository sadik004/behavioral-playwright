"""Adversarial Label Permutation Stress Engine.

Tests whether evaluation scores are honestly out-of-sample by asserting that
permuted/shuffled labels cause performance metrics to collapse to chance level.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, Callable, Dict
import numpy as np


def run_permutation_collapse_test(
    train_and_eval_fn: Callable[[np.ndarray, np.ndarray], Dict[str, float]],
    X: np.ndarray,
    y: np.ndarray,
    metric_key: str = "roc_auc",
    max_tolerated_score: float = 0.60,
    random_state: int = 42,
) -> bool:
    """Execute label permutation and assert out-of-sample score collapses to chance level.

    Args:
        train_and_eval_fn: Callable taking (X, y_shuffled) and returning metrics dict.
        X: Feature matrix.
        y: Ground truth labels.
        metric_key: Name of metric to test (e.g. roc_auc, r2, accuracy).
        max_tolerated_score: Upper bound for permuted score (e.g. 0.60 for AUC, 0.05 for R2).
        random_state: Seed for reproducible shuffle.

    Returns:
        True if metric collapsed as expected; raises AssertionError if overfit.
    """
    rng = np.random.RandomState(random_state)
    y_shuffled = rng.permutation(y)

    results = train_and_eval_fn(X, y_shuffled)
    realized_score = results.get(metric_key)

    if realized_score is None:
        raise KeyError(f"Metric '{metric_key}' not returned by evaluation function. Available: {list(results.keys())}")

    if realized_score > max_tolerated_score:
        raise AssertionError(
            f"IN-SAMPLE EVALUATION FRAUD DETECTED!\n"
            f"On randomly shuffled labels, out-of-sample '{metric_key}' achieved {realized_score:.4f}, "
            f"exceeding theoretical chance bound ({max_tolerated_score:.4f}).\n"
            f"Root cause: Preprocessor fit before cross-validation split, or in-sample evaluation leakage."
        )

    print(f"[PASS] Honest out-of-sample metric verified: '{metric_key}' collapsed to {realized_score:.4f} <= {max_tolerated_score:.4f}")
    return True
