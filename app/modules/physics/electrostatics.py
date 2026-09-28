"""Electrostatics of point charges: Coulomb force, field and potential maps, field lines."""
import math
from typing import Any

import numpy as np

from app.core.registry import tool

K_E = 8.9875517923e9  # Coulomb constant, N m^2 / C^2


@tool(
    domain="physics",
    name="coulomb_force",
    description=(
        "Coulomb force between two point charges: F = k q1 q2 / r^2 (positive = repulsive). Charges in C, "
        "distance in m. Example: q1=1e-6, q2=-2e-6, distance=0.05."
    ),
)
def coulomb_force(q1: float, q2: float, distance: float) -> dict:
    if distance <= 0:
        raise ValueError("distance must be positive")
    f = K_E * q1 * q2 / distance**2
    return {
        "result": f,
        "magnitude": abs(f),
        "nature": "repulsive" if f > 0 else "attractive" if f < 0 else "none",
        "potential_energy": K_E * q1 * q2 / distance,
        "units": "force N (positive = repulsive), energy J",
        "assumptions": ["Point charges in vacuum", f"k = {K_E} N m^2/C^2"],
    }


def _field(charges: np.ndarray, px: np.ndarray, py: np.ndarray):
    ex = np.zeros_like(px, dtype=float); ey = np.zeros_like(px, dtype=float); v = np.zeros_like(px, dtype=float)
    for q, cx, cy in charges:
        dx, dy = px - cx, py - cy
        r2 = np.maximum(dx * dx + dy * dy, 1e-18)
        r = np.sqrt(r2)
        ex += K_E * q * dx / (r2 * r)
        ey += K_E * q * dy / (r2 * r)
        v += K_E * q / r
    return ex, ey, v


@tool(
    domain="physics",
    name="electric_field",
    description=(
        "Electric field and potential of point charges in a plane (charges in C, positions in m). Returns field "
        "and potential on a grid, traced field lines (polylines) and, if given, E and V at probe points. "
        "Example: charges=[{q:1e-9,x:-0.5,y:0},{q:-1e-9,x:0.5,y:0}], x_range=[-2,2], y_range=[-1.5,1.5]."
    ),
)
def electric_field(
    charges: list[dict[str, Any]],
    x_range: list[float],
    y_range: list[float],
    grid: int = 60,
    lines_per_charge: int = 12,
    points: list[list[float]] | None = None,
) -> dict:
    if not 1 <= len(charges) <= 30:
        raise ValueError("Give between 1 and 30 charges")
    q = np.array([[float(c["q"]), float(c["x"]), float(c["y"])] for c in charges])
    if len(x_range) != 2 or len(y_range) != 2 or x_range[0] >= x_range[1] or y_range[0] >= y_range[1]:
        raise ValueError("x_range and y_range must be [min, max] with min < max")
    if not 5 <= grid <= 200 or not 0 <= lines_per_charge <= 48:
        raise ValueError("grid must be 5..200 and lines_per_charge 0..48")

    xs = np.linspace(*x_range, grid)
    ys = np.linspace(*y_range, int(round(grid * (y_range[1] - y_range[0]) / (x_range[1] - x_range[0]))) or 2)
    X, Y = np.meshgrid(xs, ys)
    ex, ey, v = _field(q, X, Y)

    # Field lines: start around each charge of the dominant sign, follow E (or -E), RK4 with fixed arc step.
    span = max(x_range[1] - x_range[0], y_range[1] - y_range[0])
    h, r_stop = span / 250, span / 120
    total = q[:, 0].sum()
    start_sign = 1 if total >= 0 else -1
    qmax = np.max(np.abs(q[:, 0])) or 1
    sinks = q[q[:, 0] * start_sign < 0][:, 1:]
    seeds = []
    for qq, cx, cy in q:
        if qq == 0 or np.sign(qq) != start_sign:
            continue
        count = max(4, int(round(lines_per_charge * abs(qq) / qmax)))
        a = 2 * np.pi * (np.arange(count) + 0.5) / count
        seeds.append(np.column_stack([cx + r_stop * np.cos(a), cy + r_stop * np.sin(a)]))
    lines = []
    if seeds:
        P = np.vstack(seeds)
        paths = [[tuple(p)] for p in P]
        active = np.ones(len(P), dtype=bool)
        lo = np.array([x_range[0], y_range[0]]) - span * 0.1
        hi = np.array([x_range[1], y_range[1]]) + span * 0.1

        def direction(pts):
            fx, fy, _ = _field(q, pts[:, 0], pts[:, 1])
            n = np.hypot(fx, fy)
            n[n == 0] = np.inf
            return start_sign * np.column_stack([fx / n, fy / n])

        for step in range(1200):
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
        lines = [[[round(x, 6), round(y, 6)] for x, y in path] for path in paths]

    probes = []
    for pt in points or []:
        fx, fy, pv = _field(q, np.array([float(pt[0])]), np.array([float(pt[1])]))
        probes.append({"x": pt[0], "y": pt[1], "ex": float(fx[0]), "ey": float(fy[0]),
                       "magnitude": float(math.hypot(fx[0], fy[0])), "potential": float(pv[0])})
    return {
        "result": {"net_charge": float(total), "probes": probes},
        "grid": {"x": xs.tolist(), "y": ys.tolist(), "ex": ex.tolist(), "ey": ey.tolist(), "potential": v.tolist()},
        "field_lines": lines,
        "units": "field N/C (= V/m), potential V, positions m, charge C",
        "assumptions": ["Point charges in vacuum, superposition of Coulomb fields",
                        "Field lines traced with RK4 along the field direction; start density ∝ |q|"],
    }
