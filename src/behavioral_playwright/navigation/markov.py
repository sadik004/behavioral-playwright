"""
Shannon Entropy Markov Loop Detector for state transition loops.
"""

import math
from typing import Dict, List


class MarkovLoopDetector:
    """
    Detects infinite loops and behavioral traps in automation states
    using Shannon Entropy calculations over a state transition Markov Chain.
    """

    def __init__(self, history_limit: int = 12, entropy_threshold: float = 1.10) -> None:
        self.history_limit = history_limit
        self.entropy_threshold = entropy_threshold
        self.state_history: List[str] = []

    def record_transition(self, state: str) -> None:
        self.state_history.append(state)
        if len(self.state_history) > self.history_limit:
            self.state_history.pop(0)

    def calculate_transition_entropy(self) -> float:
        """Calculates Shannon Entropy of visited states. Low entropy represents cyclic loops."""
        if not self.state_history:
            return 0.0

        counts: Dict[str, int] = {}
        for s in self.state_history:
            counts[s] = counts.get(s, 0) + 1

        entropy = 0.0
        total = len(self.state_history)
        for count in counts.values():
            p = count / total
            if p > 0.0:
                entropy -= p * math.log2(p)

        return float(entropy)

    def is_loop_detected(self, min_history: int = 4) -> bool:
        """Detects if visited states exhibit low entropy indicating repetitive cycles."""
        if len(self.state_history) < min_history:
            return False
        entropy = self.calculate_transition_entropy()
        return entropy < self.entropy_threshold
