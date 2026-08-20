"""
Lorenz Chaotic Attractor and Affine Coordinate Matrix transformations.
"""

from typing import Tuple


class LorenzAttractorGenerator:
    """
    Generates continuous 3D chaotic attractor coordinates using the Lorenz system.
    Injects physical chaotic micro-jitter to prevent mechanical linear detection.
    """

    def __init__(self, sigma: float = 10.0, rho: float = 28.0, beta: float = 2.6667, dt: float = 0.005) -> None:
        self.sigma = sigma
        self.rho = rho
        self.beta = beta
        self.dt = dt
        self.x = 0.1
        self.y = 0.0
        self.z = 0.0

    def next_step(self) -> Tuple[float, float, float]:
        dx = self.sigma * (self.y - self.x) * self.dt
        dy = (self.x * (self.rho - self.z) - self.y) * self.dt
        dz = (self.x * self.y - self.beta * self.z) * self.dt
        self.x += dx
        self.y += dy
        self.z += dz
        return self.x, self.y, self.z


class AffineCoordinateMapper:
    """
    Maps viewport coordinates (clientX, clientY) into physical screen space (screenX, screenY)
    using 2x3 Affine Matrix transformations.
    """

    def __init__(
        self,
        matrix_a: float = 1.0,
        matrix_b: float = 0.0,
        matrix_tx: float = 120.0,
        matrix_c: float = 0.0,
        matrix_d: float = 1.0,
        matrix_ty: float = 150.0,
    ) -> None:
        self.a = matrix_a
        self.b = matrix_b
        self.tx = matrix_tx
        self.c = matrix_c
        self.d = matrix_d
        self.ty = matrix_ty

    def map_viewport_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        screen_x = self.a * x + self.b * y + self.tx
        screen_y = self.c * x + self.d * y + self.ty
        return screen_x, screen_y
