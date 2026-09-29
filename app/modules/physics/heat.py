"""Heat conduction in a 1D rod: the heat equation ∂T/∂t = α ∂²T/∂x² solved by Crank-Nicolson."""
import math

import numpy as np
from scipy.linalg import solve_banded

from app.core.registry import tool

# Thermal diffusivity α = k / (ρ c) in m²/s for a few materials (typical room-temperature values).
MATERIALS = {"copper": 1.11e-4, "aluminium": 9.7e-5, "iron": 2.3e-5, "stainless_steel": 4.2e-6, "glass": 3.4e-7,
             "water": 1.43e-7, "wood": 1.0e-7}


@tool(
    domain="physics",
    name="heat_conduction",
    description=(
        "1D heat equation in a rod of given length (m) and thermal diffusivity (m²/s, or a material: "
        f"{', '.join(MATERIALS)}), solved with the unconditionally stable Crank-Nicolson scheme. Ends are fixed at "
        "left_temperature/right_temperature or insulated. initial: 'uniform' (initial_temperature), 'hot_middle' "
        "(a hot central third at hot_temperature) or 'sine' (one half-wave of amplitude hot_temperature). Returns "
        "temperature snapshots, heat flux and the steady state. Example: material='copper', length=0.5, duration=600."
    ),
)
def heat_conduction(
    length: float = 0.5,
    duration: float = 600.0,
    diffusivity: float | None = None,
    material: str | None = "copper",
    left_temperature: float | None = 100.0,
    right_temperature: float | None = 0.0,
    initial: str = "uniform",
    initial_temperature: float = 20.0,
    hot_temperature: float = 100.0,
    n_nodes: int = 101,
    n_frames: int = 61,
) -> dict:
    if diffusivity is None:
        if material not in MATERIALS:
            raise ValueError(f"give diffusivity or a material from {', '.join(MATERIALS)}")
        diffusivity = MATERIALS[material]
    if diffusivity <= 0 or length <= 0 or duration <= 0:
        raise ValueError("diffusivity, length and duration must be positive")
    if not 11 <= n_nodes <= 2001 or not 2 <= n_frames <= 500:
        raise ValueError("n_nodes must be 11..2001 and n_frames 2..500")
    if initial not in ("uniform", "hot_middle", "sine"):
        raise ValueError("initial must be 'uniform', 'hot_middle' or 'sine'")
    x = np.linspace(0, length, n_nodes)
    dx = x[1] - x[0]
    if initial == "uniform":
        u = np.full(n_nodes, float(initial_temperature))
    elif initial == "hot_middle":
        u = np.where((x > length / 3) & (x < 2 * length / 3), hot_temperature, initial_temperature).astype(float)
    else:
        u = initial_temperature + hot_temperature * np.sin(math.pi * x / length)
    fixed_l, fixed_r = left_temperature is not None, right_temperature is not None
    if fixed_l:
        u[0] = left_temperature
    if fixed_r:
        u[-1] = right_temperature
    # Time step: several hundred steps per run, capped so fine grids stay accurate
    tau = dx * dx / diffusivity
    n_steps = int(min(20000, max(400, math.ceil(duration / (5 * tau)))))
    dt = duration / n_steps
    r = diffusivity * dt / dx**2
    n = n_nodes
    # Banded matrices for (I − r/2 L) u_new = (I + r/2 L) u_old, with Dirichlet or Neumann (ghost-node) ends
    ab = np.zeros((3, n))
    ab[0, 1:] = -r / 2
    ab[1, :] = 1 + r
    ab[2, :-1] = -r / 2
    if fixed_l:
        ab[1, 0], ab[0, 1] = 1, 0
    else:
        ab[0, 1] = -r  # ghost node u[-1] = u[1]
    if fixed_r:
        ab[1, -1], ab[2, -2] = 1, 0
    else:
        ab[2, -2] = -r

    def rhs(v):
        b = np.empty_like(v)
        b[1:-1] = r / 2 * v[:-2] + (1 - r) * v[1:-1] + r / 2 * v[2:]
        b[0] = v[0] if fixed_l else (1 - r) * v[0] + r * v[1]
        b[-1] = v[-1] if fixed_r else (1 - r) * v[-1] + r * v[-2]
        return b

    frame_steps = np.unique(np.linspace(0, n_steps, n_frames).round().astype(int))
    frames, times = [u.copy()], [0.0]
    step = 0
    for target in frame_steps[1:]:
        while step < target:
            u = solve_banded((1, 1), ab, rhs(u))
            step += 1
        frames.append(u.copy())
        times.append(step * dt)
    # Steady state: linear between fixed ends; insulated rod → the (conserved) mean
    if fixed_l and fixed_r:
        steady = left_temperature + (right_temperature - left_temperature) * x / length
    elif fixed_l or fixed_r:
        steady = np.full(n, left_temperature if fixed_l else right_temperature)
    else:
        steady = np.full(n, float(np.trapezoid(frames[0], x) / length))
    grad = np.gradient(u, x)
    return {
        "result": {
            "diffusivity": diffusivity,
            "time_constant": length**2 / (math.pi**2 * diffusivity),
            "final_mean_temperature": float(np.trapezoid(u, x) / length),
            "max_deviation_from_steady": float(np.max(np.abs(u - steady))),
            "flux_per_conductivity_left": float(-grad[0]),
            "flux_per_conductivity_right": float(-grad[-1]),
            "steps": n_steps,
        },
        "x": x.tolist(),
        "frames": {"t": times, "temperature": [f.tolist() for f in frames]},
        "steady_state": steady.tolist(),
        "units": "temperature in °C (any linear scale), x in m, t in s, α in m²/s; flux/k in K/m",
        "assumptions": ["Constant diffusivity, no internal heat sources, 1D conduction (sides insulated)",
                        "Time constant L²/(π² α) is the decay time of the slowest mode"],
    }
