"""Bar magnet field (two-pole model) and Faraday induction in a coil as the magnet moves along its axis."""
import math

import numpy as np

from app.core.registry import tool
from app.modules.physics.fieldlines import ring_seeds, trace_field_lines

MU0 = 4e-7 * math.pi   # vacuum permeability, T m/A (to 1e-10)


def _pole_field(qm: float, half: float, x: np.ndarray, y: np.ndarray):
    """B of a bar magnet along x (N pole at +half) modelled as two magnetic poles, in the plane of its axis."""
    bx = np.zeros_like(x, dtype=float); by = np.zeros_like(x, dtype=float)
    for q, px in ((qm, half), (-qm, -half)):
        dx, dy = x - px, y
        r3 = np.maximum(dx * dx + dy * dy, 1e-18) ** 1.5
        bx += MU0 / (4 * math.pi) * q * dx / r3
        by += MU0 / (4 * math.pi) * q * dy / r3
    return bx, by


@tool(
    domain="physics",
    name="magnet_field",
    description=(
        "Magnetic field of a bar magnet (moment in A m^2, length in m) lying along the x-axis with its north "
        "pole at +x, in the plane through its axis. Returns B on a grid and field lines from N to S. "
        "Example: moment=1, length=0.1, x_range=[-0.3,0.3], y_range=[-0.2,0.2]."
    ),
)
def magnet_field(moment: float, length: float, x_range: list[float], y_range: list[float],
                 grid: int = 50, n_lines: int = 16) -> dict:
    if moment <= 0 or length <= 0:
        raise ValueError("moment and length must be positive")
    if x_range[0] >= x_range[1] or y_range[0] >= y_range[1]:
        raise ValueError("ranges must be [min, max]")
    if not 5 <= grid <= 200 or not 0 <= n_lines <= 60:
        raise ValueError("grid must be 5..200 and n_lines 0..60")
    qm, half = moment / length, length / 2
    xs = np.linspace(*x_range, grid)
    ys = np.linspace(*y_range, max(2, int(round(grid * (y_range[1] - y_range[0]) / (x_range[1] - x_range[0])))))
    X, Y = np.meshgrid(xs, ys)
    bx, by = _pole_field(qm, half, X, Y)
    span = max(x_range[1] - x_range[0], y_range[1] - y_range[0])
    lines = trace_field_lines(lambda x, y: _pole_field(qm, half, x, y), ring_seeds(half, 0, span / 120, n_lines),
                              np.array([[-half, 0.0]]), x_range, y_range)
    return {
        "result": {"pole_strength": qm, "field_on_axis_at_1m": MU0 * moment / (2 * math.pi)},
        "grid": {"x": xs.tolist(), "y": ys.tolist(), "bx": bx.tolist(), "by": by.tolist()},
        "field_lines": lines,
        "units": "field T, positions m, pole strength A m",
        "assumptions": ["Thin bar magnet modelled as two point poles (Gilbert model) outside the magnet"],
    }


def coil_flux(z: np.ndarray, qm: float, half: float, radius: float, orientation: int = 1) -> np.ndarray:
    """Flux (T m^2, one turn, +x direction) through a coil at x = 0 from a magnet centred at z on the axis.

    Each pole contributes mu0 q / 2 x (solid-angle fraction); when the magnet straddles the coil plane the
    magnetisation inside it adds mu0 q_m, which keeps the flux continuous as the magnet passes through.
    """
    def pole(q, zp):
        return MU0 * q / 2 * (-np.sign(zp) + zp / np.sqrt(zp * zp + radius * radius))
    zn, zs = z + orientation * half, z - orientation * half
    straddle = ((zn > 0) & (zs < 0)) | ((zn < 0) & (zs > 0))
    inside = MU0 * qm * np.where(straddle, np.sign(zn - zs), 0.0)
    return pole(qm, zn) + pole(-qm, zs) + inside


@tool(
    domain="physics",
    name="magnet_coil_induction",
    description=(
        "Faraday's law: a bar magnet moves along the axis of a coil (turns, radius in m, resistance in ohm). "
        "motion 'pass' = constant speed from -travel to +travel; 'oscillate' = centre + amplitude sin(2 pi f t). "
        "Returns flux linkage, EMF = -N dPhi/dt, current and power over time. flip=true points the north pole "
        "the other way. Example: moment=1, length=0.08, turns=100, radius=0.03, resistance=5, motion='pass', speed=1."
    ),
)
def magnet_coil_induction(
    moment: float,
    length: float,
    turns: int,
    radius: float,
    resistance: float = 1.0,
    motion: str = "pass",
    speed: float = 1.0,
    travel: float = 0.3,
    amplitude: float = 0.1,
    frequency: float = 1.0,
    centre: float = 0.0,
    flip: bool = False,
    duration: float | None = None,
    n_points: int = 801,
) -> dict:
    if moment <= 0 or length <= 0 or radius <= 0 or resistance <= 0 or turns < 1:
        raise ValueError("moment, length, radius, resistance must be positive and turns >= 1")
    if motion not in ("pass", "oscillate"):
        raise ValueError("motion must be 'pass' or 'oscillate'")
    if not 2 <= n_points <= 20_000:
        raise ValueError("n_points must be between 2 and 20000")
    qm, half, o = moment / length, length / 2, -1 if flip else 1
    if motion == "pass":
        if speed == 0 or travel <= 0:
            raise ValueError("speed must be non-zero and travel positive")
        duration = duration or 2 * travel / abs(speed)
        t = np.linspace(0, duration, n_points)
        z = -math.copysign(travel, speed) + speed * t
        zdot = np.full_like(t, speed)
    else:
        if amplitude <= 0 or frequency <= 0:
            raise ValueError("amplitude and frequency must be positive")
        duration = duration or 3 / frequency
        t = np.linspace(0, duration, n_points)
        w = 2 * math.pi * frequency
        z = centre + amplitude * np.sin(w * t)
        zdot = amplitude * w * np.cos(w * t)
    phi = coil_flux(z, qm, half, radius, o)
    # dPhi/dz is smooth: mu0 q a^2 / 2 [ (zN^2+a^2)^-3/2 - (zS^2+a^2)^-3/2 ]
    zn, zs = z + o * half, z - o * half
    dphi_dz = MU0 * qm * radius**2 / 2 * ((zn**2 + radius**2) ** -1.5 - (zs**2 + radius**2) ** -1.5)
    emf = -turns * dphi_dz * zdot
    current = emf / resistance
    return {
        "result": {"peak_emf": float(np.max(np.abs(emf))), "peak_current": float(np.max(np.abs(current))),
                   "max_flux_linkage": float(np.max(np.abs(turns * phi))),
                   "energy_dissipated": float(np.trapezoid(emf**2 / resistance, t))},
        "trajectory": {"t": t.tolist(), "position": z.tolist(), "flux_linkage": (turns * phi).tolist(),
                       "emf": emf.tolist(), "current": current.tolist(), "power": (emf**2 / resistance).tolist()},
        "units": "time s, position m (magnet centre, coil at 0), flux linkage Wb-turns, emf V, current A, power W",
        "assumptions": [
            "Thin bar magnet (two-pole model), coaxial circular coil of zero thickness",
            "Coil self-inductance neglected (current = emf / R), so no drag on the magnet is modelled",
        ],
    }
