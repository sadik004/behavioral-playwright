"""
Behavioral models: Linguistic Keystroke Dynamics and Fuzzy Self-Healing Selector matching.
"""

import logging
from typing import List, Optional

logger = logging.getLogger("BehavioralAutomation.Behavior.Models")


class LinguisticKeystrokeDynamics:
    """
    Emulates human linguistic muscle memory by modeling Digraph and Trigraph flight times
    over common English syllable transitions (e.g., 'th', 'he', 'in', 'er', 'an').
    """

    def __init__(self) -> None:
        self.rapid_bigrams = {
            "th",
            "he",
            "in",
            "er",
            "an",
            "re",
            "on",
            "at",
            "es",
            "en",
            "te",
            "ed",
            "to",
            "it",
            "ou",
            "ea",
            "ng",
            "as",
            "or",
            "ti",
        }
        self.rapid_trigrams = {
            "the",
            "and",
            "tha",
            "ent",
            "ing",
            "ion",
            "tio",
            "for",
            "nde",
            "has",
        }

    def calculate_linguistic_factor(
        self,
        prev_char: str,
        current_char: str,
        third_prev_char: Optional[str] = None,
    ) -> float:
        """Calculates linguistic speed scale based on QWERTY muscle memory and common transitions."""
        bigram = (prev_char + current_char).lower()
        factor = 1.0

        if third_prev_char:
            trigram = (third_prev_char + prev_char + current_char).lower()
            if trigram in self.rapid_trigrams:
                logger.info(
                    f"[MOTOR MEMORY] Rapid trigram transition detected: '{trigram}'. Accelerating keystroke flight."
                )
                return 0.55

        if bigram in self.rapid_bigrams:
            logger.info(f"[MOTOR MEMORY] Rapid bigram transition detected: '{bigram}'. Accelerating keystroke flight.")
            factor = 0.70

        return factor


class SelfHealingSelectorEngine:
    """
    Levenshtein-Distance Selector healing engine to recover when CSS selectors or DOM attributes mutate.
    """

    def __init__(self, custom_logger: Optional[logging.Logger] = None) -> None:
        self.logger = custom_logger or logging.getLogger("BehavioralAutomation.Healer")

    @staticmethod
    def calculate_levenshtein(s1: str, s2: str) -> int:
        """Native matrix implementation of the Levenshtein Distance edit metric."""
        if len(s1) < len(s2):
            return SelfHealingSelectorEngine.calculate_levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def heal_selector(self, primary_selector: str, available_elements_snapshot: List[str]) -> Optional[str]:
        self.logger.warning(
            f"SelfHealingSelectorEngine: Primary selector '{primary_selector}' failed. Running fuzzy heal..."
        )
        clean_selector = primary_selector.replace("#", "").replace(".", "").lower()

        best_candidate: Optional[str] = None
        min_distance = 9999

        for candidate in available_elements_snapshot:
            clean_candidate = candidate.replace("#", "").replace(".", "").lower()
            distance = self.calculate_levenshtein(clean_selector, clean_candidate)
            if distance < min_distance:
                min_distance = distance
                best_candidate = candidate

        if best_candidate and min_distance < 15:
            self.logger.info(
                f"SelfHealingSelectorEngine: Healed selector! Falling back from '{primary_selector}' to '{best_candidate}' (Distance: {min_distance})"
            )
            return best_candidate
        return None
