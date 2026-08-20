"""
Unit tests for mathematical models, Bezier curves, SigmaDrift, Lorenz attractor, and Affine transformations.
"""

import math

from behavioral_playwright import (
    AffineCoordinateMapper,
    BezierTrajectoryGenerator,
    CanvasGridMappingDriver,
    DeterministicRandomSource,
    LorenzAttractorGenerator,
    MouseConfig,
    SigmaDriftTrajectoryGenerator,
)


def test_smoothstep_boundaries() -> None:
    assert BezierTrajectoryGenerator.smoothstep(0.0) == 0.0
    assert BezierTrajectoryGenerator.smoothstep(1.0) == 1.0
    assert BezierTrajectoryGenerator.smoothstep(0.5) == 0.5
    assert BezierTrajectoryGenerator.smoothstep(-0.5) == 0.0
    assert BezierTrajectoryGenerator.smoothstep(1.5) == 1.0


def test_bezier_trajectory_envelope() -> None:
    start = (10.0, 20.0)
    end = (500.0, 400.0)
    config = MouseConfig()
    rng = DeterministicRandomSource(42)

    path = BezierTrajectoryGenerator.generate_path(start, end, 50, config, rng)

    assert len(path) == 50
    # Sine Jitter Envelope guarantees dampening to 0 at boundaries
    assert path[0][0] == start[0] and path[0][1] == start[1]
    assert abs(path[-1][0] - end[0]) < 1e-4 and abs(path[-1][1] - end[1]) < 1e-4

    for x, y in path:
        assert not math.isnan(x) and not math.isinf(x)
        assert not math.isnan(y) and not math.isinf(y)


def test_sigmadrift_trajectory_generation() -> None:
    start = (0.0, 0.0)
    end = (300.0, 400.0)
    config = MouseConfig()
    rng = DeterministicRandomSource(42)

    path = SigmaDriftTrajectoryGenerator.generate_biomechanical_path(start, end, config, rng)
    assert len(path) > 10
    # Tremor jitter envelope is present at start and exact landing at destination
    assert abs(path[0][0] - start[0]) <= config.tremor_amp_max + 1.0
    assert abs(path[0][1] - start[1]) <= config.tremor_amp_max + 1.0
    assert path[-1][0] == end[0] and path[-1][1] == end[1]


def test_affine_coordinate_mapping() -> None:
    mapper = AffineCoordinateMapper(matrix_a=1.5, matrix_tx=100.0, matrix_d=1.5, matrix_ty=150.0)
    sx, sy = mapper.map_viewport_to_screen(10.0, 20.0)
    assert sx == 115.0
    assert sy == 180.0


def test_lorenz_attractor_chaos() -> None:
    lorenz = LorenzAttractorGenerator(sigma=10.0, rho=28.0, beta=2.6667, dt=0.001)
    x1, y1, _ = lorenz.x, lorenz.y, lorenz.z
    x2, y2, _ = lorenz.next_step()
    assert x1 != x2
    assert y1 != y2


def test_canvas_grid_mapping() -> None:
    canvas_box = {"x": 150.0, "y": 200.0, "width": 400.0, "height": 300.0}
    abs_x, abs_y = CanvasGridMappingDriver.map_canvas_coordinates(canvas_box, 0.5, 0.5)
    assert abs_x == 350.0
    assert abs_y == 350.0
