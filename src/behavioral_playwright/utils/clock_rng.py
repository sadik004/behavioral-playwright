"""
Clock and Randomness abstraction implementations.
"""

import asyncio
import math
import random
import time
from typing import Any


class SystemRandomSource:
    """Production system randomness source using standard library random module."""

    def uniform(self, a: float, b: float) -> float:
        return random.uniform(a, b)

    def gauss(self, mu: float, sigma: float) -> float:
        return random.gauss(mu, sigma)

    def random(self) -> float:
        return random.random()

    def choice(self, seq: Any) -> Any:
        return random.choice(seq)

    def weibull(self, alpha: float, beta: float) -> float:
        return random.weibullvariate(alpha, beta)

    def beta(self, a: float, b: float) -> float:
        return random.betavariate(a, b)

    def gamma(self, alpha: float, beta: float) -> float:
        return random.gammavariate(alpha, beta)


class DeterministicRandomSource:
    """Fixed-seed deterministic randomness provider to guarantee reproducibility in testing."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    def uniform(self, a: float, b: float) -> float:
        return self.rng.uniform(a, b)

    def gauss(self, mu: float, sigma: float) -> float:
        return self.rng.gauss(mu, sigma)

    def random(self) -> float:
        return self.rng.random()

    def choice(self, seq: Any) -> Any:
        return self.rng.choice(seq)

    def weibull(self, alpha: float, beta: float) -> float:
        # Inverse transform sampling for deterministic Weibull
        u = float(self.rng.random())
        return float(alpha * ((-math.log(1.0 - u)) ** (1.0 / beta)))

    def beta(self, a: float, b: float) -> float:
        # Johnk's generator for beta variables with deterministic seed
        while True:
            u1 = self.rng.random()
            u2 = self.rng.random()
            y1 = u1 ** (1.0 / a)
            y2 = u2 ** (1.0 / b)
            if (y1 + y2) <= 1.0:
                if (y1 + y2) == 0:
                    continue
                return float(y1 / (y1 + y2))

    def gamma(self, alpha: float, beta: float) -> float:
        return float(self.rng.gammavariate(alpha, beta))


class SystemClock:
    """Real-time system clock utilizing asyncio.sleep."""

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    def time(self) -> float:
        return time.time()


class VirtualTestClock:
    """Hyper-accelerated mock clock for speeding up integration and unit tests."""

    def __init__(self, initial_time: float = 1774780000.0) -> None:
        self.virtual_time: float = initial_time

    async def sleep(self, seconds: float) -> None:
        self.virtual_time += seconds

    def time(self) -> float:
        return self.virtual_time
