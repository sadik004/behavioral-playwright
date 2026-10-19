"""
Biometric Cognitive Keystroke Engine with Physical ScanCodes
Simulates human typing dynamics using QWERTY spatial distances, Weibull flight times,
probabilistic adjacent typos with backspace auto-correction, and physical keycodes.
"""
import math
import random
from typing import Dict, List, Any


class CognitiveKeystrokeEngine:
    _SPECIAL_KEYCODES: Dict[str, Tuple[str, int]] = {
        ' ': ('Space', 32),
        '\n': ('Enter', 13),
        '\t': ('Tab', 9),
        '.': ('Period', 190),
        ',': ('Comma', 188),
        '/': ('Slash', 191),
        ';': ('Semicolon', 186),
        "'": ('Quote', 222),
        '"': ('Quote', 222),
        '-': ('Minus', 189),
        '=': ('Equal', 187),
    }

    @classmethod
    def _char_to_keycode(cls, ch: str) -> int:
        if not ch:
            return 32
        if ch.isalpha():
            return ord(ch.upper())
        if ch.isdigit():
            return ord(ch)
        spec = {
            ' ': 32, '\n': 13, '\t': 9, ';': 186, '=': 187, ',': 188,
            '-': 189, '.': 190, '/': 191, '`': 192, '[': 219, '\\': 220,
            ']': 221, "'": 222, '"': 222
        }
        return spec.get(ch, ord(ch[0]))

    @classmethod
    def _resolve_keycode(cls, ch: str) -> Tuple[str, int]:
        if ch.isalpha():
            return f"Key{ch.upper()}", ord(ch.upper())
        if ch.isdigit():
            return f"Digit{ch}", ord(ch)
        if ch in cls._SPECIAL_KEYCODES:
            return cls._SPECIAL_KEYCODES[ch]
        return "Quote", 32

    """
    Simulates human typing dynamics using QWERTY spatial distances, Weibull key-dwell times,
    probabilistic adjacent typos with backspace auto-correction, and OS Physical ScanCodes.
    """
    QWERTY_MAP = {
        'q': (0,0), 'w': (0,1), 'e': (0,2), 'r': (0,3), 't': (0,4), 'y': (0,5), 'u': (0,6), 'i': (0,7), 'o': (0,8), 'p': (0,9),
        'a': (1,0), 's': (1,1), 'd': (1,2), 'f': (1,3), 'g': (1,4), 'h': (1,5), 'j': (1,6), 'k': (1,7), 'l': (1,8),
        'z': (2,0), 'x': (2,1), 'c': (2,2), 'v': (2,3), 'b': (2,4), 'n': (2,5), 'm': (2,6),
        ' ': (3,4)
    }

    ADJACENT_KEYS = {
        'a': ['q', 'w', 's', 'z'], 'b': ['v', 'g', 'h', 'n'], 'c': ['x', 'd', 'f', 'v'],
        'd': ['e', 'r', 's', 'f', 'c'], 'e': ['w', 'r', 'd', '3', '4'], 'f': ['r', 't', 'd', 'g', 'v'],
        'g': ['t', 'y', 'f', 'h', 'b'], 'h': ['y', 'u', 'g', 'j', 'n'], 'i': ['u', 'o', 'k', '8', '9'],
        'j': ['u', 'i', 'h', 'k', 'm'], 'k': ['i', 'o', 'j', 'l'], 'l': ['o', 'p', 'k'],
        'm': ['n', 'j', 'k'], 'n': ['b', 'h', 'j', 'm'], 'o': ['i', 'p', 'l', '9', '0'],
        'p': ['o', 'l', '0'], 'q': ['w', '1', '2', 'a'], 'r': ['e', 't', 'f', '4', '5'],
        's': ['w', 'e', 'a', 'd', 'z', 'x'], 't': ['r', 'y', 'g', '5', '6'], 'u': ['y', 'i', 'h', '7', '8'],
        'v': ['c', 'f', 'g', 'b'], 'w': ['q', 'e', 's', '2', '3'], 'x': ['z', 's', 'd', 'c'],
        'y': ['t', 'u', 'h', '6', '7'], 'z': ['a', 's', 'x']
    }

    def __init__(self, base_wpm: float = 65.0, typo_probability: float = 0.05, seed: int | None = None):
        self.base_wpm = base_wpm
        self.typo_probability = typo_probability
        self.seed = seed
        self._rng = random.Random(seed)

    def _get_key_distance(self, k1: str, k2: str) -> float:
        p1 = self.QWERTY_MAP.get(k1.lower(), (1, 4))
        p2 = self.QWERTY_MAP.get(k2.lower(), (1, 4))
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def generate_human_keystroke_plan(self, text: str) -> List[Dict[str, Any]]:
        plan = []
        last_key = 'a'

        for char in text:
            if char in (' ', '.', ',', '\n') or self._rng.random() < 0.08:
                plan.append({'action': 'pause', 'duration': self._rng.uniform(0.18, 0.45)})

            if char.lower() in self.ADJACENT_KEYS and self._rng.random() < self.typo_probability:
                wrong_char = self._rng.choice(self.ADJACENT_KEYS[char.lower()])
                plan.append({
                    'action': 'type',
                    'key': wrong_char,
                    'code': f"Key{wrong_char.upper()}" if wrong_char.isalpha() else "Digit1",
                    'keyCode': ord(wrong_char.upper()) if wrong_char.isalpha() else 49,
                    'delay': self._rng.weibullvariate(1.5, 2.0) * 0.04,
                    'is_typo': True
                })
                plan.append({'action': 'pause', 'duration': self._rng.uniform(0.12, 0.28)})
                plan.append({
                    'action': 'backspace',
                    'key': 'Backspace',
                    'code': 'Backspace',
                    'keyCode': 8,
                    'delay': self._rng.uniform(0.06, 0.12)
                })

            wpm_factor = 65.0 / max(15.0, float(self.base_wpm))
            dist = self._get_key_distance(last_key, char)
            flight_delay = max(0.025, (dist * 0.015) + self._rng.weibullvariate(1.8, 2.2) * 0.03) * wpm_factor
            c_code, c_kc = self._resolve_keycode(char)
            plan.append({
                'action': 'type',
                'key': char,
                'code': c_code,
                'keyCode': c_kc,
                'delay': flight_delay,
                'is_typo': False
            })
            last_key = char

        return plan


# Re-export modern canonical classes for full parity
try:
    from veil.kinematics.keystrokes import (
        LinguisticKeystrokeDynamicsEngine,
        KeystrokeCadenceEngine,
    )
except ImportError:
    LinguisticKeystrokeDynamicsEngine = CognitiveKeystrokeEngine
    KeystrokeCadenceEngine = CognitiveKeystrokeEngine

