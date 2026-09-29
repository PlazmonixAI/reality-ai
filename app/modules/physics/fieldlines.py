"""Shared RK4 field-line tracer for 2D vector fields (all lines advanced together with numpy). Not a tool module."""
from typing import Callable

import numpy as np


def trace_field_lines(
    field: Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]],
    seeds: np.ndarray,
    sinks: np.ndarray,
    x_range: list[float],
    y_range: list[float],
    direction_sign: float = 1.0,
    max_steps: int = 1200,
) -> list[list[list[float]]]:
    """Follow the field direction from each seed until it leaves the (slightly enlarged) box or reaches a sink."""
    if not len(seeds):
        return []
    span = max(x_range[1] - x_range[0], y_range[1] - y_range[0])
    h, r_stop = span / 250, span / 120
    P = np.array(seeds, dtype=float)
    paths = [[tuple(p)] for p in P]
    active = np.ones(len(P), dtype=bool)
    lo = np.array([x_range[0], y_range[0]]) - span * 0.1
    hi = np.array([x_range[1], y_range[1]]) + span * 0.1
    sinks = np.asarray(sinks, dtype=float).reshape(-1, 2)

    def direction(pts: np.ndarray) -> np.ndarray:
        fx, fy = field(pts[:, 0], pts[:, 1])
        n = np.hypot(fx, fy)
        n[n == 0] = np.inf
        return direction_sign * np.column_stack([fx / n, fy / n])

    for step in range(max_steps):
        if not active.any():
            break
        A = P[active]
        k1 = direction(A)
        k2 = direction(A + h / 2 * k1)
        k3 = direction(A + h / 2 * k2)
        k4 = direction(A + h * k3)
        A = A + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        P[active] = A
        ids = np.flatnonzero(active)
        done = np.any((A < lo) | (A > hi), axis=1)
        if len(sinks):
            d = np.min(np.hypot(A[:, None, 0] - sinks[None, :, 0], A[:, None, 1] - sinks[None, :, 1]), axis=1)
            done |= d < r_stop
        for j, i in enumerate(ids):
            if step % 2 == 0 or done[j]:
                paths[i].append((float(A[j, 0]), float(A[j, 1])))
        active[ids[done]] = False
    return [[[round(x, 6), round(y, 6)] for x, y in path] for path in paths]


def ring_seeds(cx: float, cy: float, radius: float, count: int) -> np.ndarray:
    a = 2 * np.pi * (np.arange(count) + 0.5) / count
    return np.column_stack([cx + radius * np.cos(a), cy + radius * np.sin(a)])
