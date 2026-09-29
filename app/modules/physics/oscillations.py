"""Oscillations beyond the single spring: driven damped resonance, coupled normal modes and the
chaotic double pendulum."""
import math

import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import eigh

from app.core.registry import tool

G0 = 9.80665
MAX_POINTS = 20_000


def _points(n_points: int) -> None:
    if not 2 <= n_points <= MAX_POINTS:
        raise ValueError(f"n_points must be between 2 and {MAX_POINTS}")


@tool(
    domain="physics",
    name="driven_oscillator",
    description=(
        "Driven damped mass-spring oscillator m x'' + b x' + k x = F0 cos(ω t): steady-state amplitude and phase, "
        "resonance frequency, quality factor Q, the full amplitude/phase response curve, and the time trajectory "
        "(transient + steady state) from x0, v0. SI units: mass kg, stiffness N/m, damping kg/s, drive_force N, "
        "drive_frequency rad/s. Example: mass=1, stiffness=100, damping=1, drive_force=1, drive_frequency=10."
    ),
)
def driven_oscillator(
    mass: float,
    stiffness: float,
    damping: float,
    drive_force: float,
    drive_frequency: float,
    x0: float = 0.0,
    v0: float = 0.0,
    duration: float | None = None,
    n_points: int = 1500,
) -> dict:
    if mass <= 0 or stiffness <= 0 or damping < 0:
        raise ValueError("mass and stiffness must be positive, damping >= 0")
    if drive_frequency < 0:
        raise ValueError("drive_frequency must be >= 0 (rad/s)")
    _points(n_points)
    w0 = math.sqrt(stiffness / mass)
    g = damping / mass  # b/m
    f0m = drive_force / mass
    denom = math.hypot(w0**2 - drive_frequency**2, g * drive_frequency)
    if denom == 0:
        raise ValueError("undamped drive exactly at resonance has no steady state (amplitude grows without limit)")
    amp = abs(f0m) / denom
    phase = math.atan2(g * drive_frequency, w0**2 - drive_frequency**2)  # lag of x behind the drive, 0..π
    w_res = math.sqrt(w0**2 - g**2 / 2) if g**2 < 2 * w0**2 else None
    q = w0 / g if g > 0 else math.inf
    if duration is None:
        tau = 2 / g if g > 0 else 20 * 2 * math.pi / w0
        duration = min(max(4 * tau, 10 * 2 * math.pi / w0), 400 * 2 * math.pi / w0)
    if duration <= 0:
        raise ValueError("duration must be positive")

    def rhs(t, s):
        return [s[1], f0m * math.cos(drive_frequency * t) - g * s[1] - w0**2 * s[0]]

    t = np.linspace(0, duration, n_points)
    sol = solve_ivp(rhs, (0, duration), [x0, v0], t_eval=t, method="DOP853", rtol=1e-9, atol=1e-12,
                    max_step=2 * math.pi / max(w0, drive_frequency, 1e-9) / 20)
    if not sol.success:
        raise ValueError(f"Integration failed: {sol.message}")
    x, v = sol.y
    ws = np.linspace(0, 3 * w0, 600)
    a_curve = abs(f0m) / np.hypot(w0**2 - ws**2, g * ws)
    a_curve[~np.isfinite(a_curve)] = np.nan
    p_curve = np.arctan2(g * ws, w0**2 - ws**2)
    # Mean power absorbed in steady state: <P> = b ω² A² / 2
    return {
        "result": {
            "natural_frequency": w0,
            "resonance_frequency": w_res,
            "quality_factor": q,
            "steady_amplitude": amp,
            "phase_lag": phase,
            "phase_lag_deg": math.degrees(phase),
            "static_displacement": drive_force / stiffness,
            "amplification": amp / (abs(drive_force) / stiffness) if drive_force else None,
            "mean_power": 0.5 * damping * drive_frequency**2 * amp**2,
            "bandwidth": g,
            "regime": "undamped" if g == 0 else "underdamped" if g < 2 * w0 else "critically damped" if g == 2 * w0 else "overdamped",
        },
        "trajectory": {
            "t": t.tolist(), "x": x.tolist(), "v": v.tolist(),
            "drive": (drive_force * np.cos(drive_frequency * t)).tolist(),
        },
        "response": {
            "omega": ws.tolist(),
            "amplitude": [None if not np.isfinite(a) else float(a) for a in a_curve],
            "phase_deg": np.degrees(p_curve).tolist(),
        },
        "units": "frequencies in rad/s, displacement in m, phase in rad (and deg), power in W",
        "assumptions": ["Linear spring and viscous damping", "Sinusoidal drive F0 cos(ω t)",
                        "Bandwidth (FWHM of the power curve) ≈ b/m for light damping"],
    }


@tool(
    domain="physics",
    name="coupled_oscillators",
    description=(
        "Chain of masses joined by springs between two walls: normal-mode frequencies and shapes (K v = ω² M v), "
        "and the exact motion from initial displacements and velocities by modal superposition. masses: list (kg); "
        "springs: list of len(masses)+1 stiffnesses (N/m), wall-mass-...-mass-wall (use 0 for a free end). "
        "Example: masses=[1,1], springs=[10,2,10], displacements=[0.1,0]  (beats)."
    ),
)
def coupled_oscillators(
    masses: list[float],
    springs: list[float],
    displacements: list[float] | None = None,
    velocities: list[float] | None = None,
    duration: float | None = None,
    n_points: int = 1200,
) -> dict:
    n = len(masses)
    if not 1 <= n <= 20:
        raise ValueError("between 1 and 20 masses")
    if len(springs) != n + 1:
        raise ValueError("springs needs len(masses) + 1 values (wall, between masses, wall)")
    if any(m <= 0 for m in masses) or any(k < 0 for k in springs):
        raise ValueError("masses must be positive and spring constants >= 0")
    x0 = np.array(displacements if displacements is not None else [0.0] * n, float)
    v0 = np.array(velocities if velocities is not None else [0.0] * n, float)
    if x0.shape != (n,) or v0.shape != (n,):
        raise ValueError("displacements and velocities need one value per mass")
    _points(n_points)
    m = np.diag(masses)
    k = np.zeros((n, n))
    for i in range(n):
        k[i, i] = springs[i] + springs[i + 1]
        if i + 1 < n:
            k[i, i + 1] = k[i + 1, i] = -springs[i + 1]
    w2, modes = eigh(k, m)  # modes are M-orthonormal: modesᵀ M modes = I
    w2 = np.clip(w2, 0, None)
    w = np.sqrt(w2)
    if duration is None:
        wpos = w[w > 1e-9]
        duration = 6 * 2 * math.pi / wpos.min() if len(wpos) else 10.0
        if len(wpos) >= 2:  # show at least one full beat
            beat = 2 * math.pi / max(1e-9, np.min(np.diff(np.sort(wpos))))
            duration = min(max(duration, 1.2 * beat), 200 * 2 * math.pi / wpos.min())
    if duration <= 0:
        raise ValueError("duration must be positive")
    q0, qd0 = modes.T @ m @ x0, modes.T @ m @ v0
    t = np.linspace(0, duration, n_points)
    q, qd = np.empty((n, n_points)), np.empty((n, n_points))
    for j in range(n):
        if w[j] > 1e-12:
            c, s = np.cos(w[j] * t), np.sin(w[j] * t)
            q[j] = q0[j] * c + qd0[j] / w[j] * s
            qd[j] = -q0[j] * w[j] * s + qd0[j] * c
        else:  # zero mode: free translation
            q[j] = q0[j] + qd0[j] * t
            qd[j] = qd0[j]
    x, v = modes @ q, modes @ qd
    # Per-mass energy (kinetic + half of each attached spring) to show energy flowing between masses
    ke = 0.5 * np.array(masses)[:, None] * v**2
    mode_energy = 0.5 * (qd0**2 + w2 * q0**2)
    # Normalise mode shapes so the largest component is +1 for display
    shapes = []
    for j in range(n):
        s = modes[:, j] / np.max(np.abs(modes[:, j]))
        if s[np.argmax(np.abs(s))] < 0:
            s = -s
        shapes.append(s.tolist())
    return {
        "result": {
            "frequencies": w.tolist(),
            "frequencies_hz": (w / (2 * math.pi)).tolist(),
            "periods": [2 * math.pi / x if x > 1e-12 else None for x in w],
            "mode_shapes": shapes,
            "mode_energies": mode_energy.tolist(),
            "total_energy": float(mode_energy.sum()),
        },
        "trajectory": {"t": t.tolist(), "x": x.tolist(), "kinetic": ke.tolist()},
        "units": "frequencies in rad/s (and Hz), displacement in m, energy in J",
        "assumptions": ["Ideal massless linear springs, no damping, motion along the chain only",
                        "Exact solution by superposing normal modes"],
    }


@tool(
    domain="physics",
    name="double_pendulum",
    description=(
        "Double pendulum (two point masses on rigid massless rods), integrated with a tight-tolerance Runge-Kutta "
        "method, plus a twin run started perturbation_deg away to show chaos: separation over time, a Lyapunov "
        "exponent estimate and energy drift. Angles in degrees from straight down; lengths m, masses kg. "
        "Example: theta1=120, theta2=-20."
    ),
)
def double_pendulum(
    theta1: float,
    theta2: float,
    omega1: float = 0.0,
    omega2: float = 0.0,
    mass1: float = 1.0,
    mass2: float = 1.0,
    length1: float = 1.0,
    length2: float = 1.0,
    gravity: float = G0,
    duration: float = 20.0,
    n_points: int = 2001,
    perturbation_deg: float = 1e-6,
) -> dict:
    if min(mass1, mass2, length1, length2, gravity) <= 0:
        raise ValueError("masses, lengths and gravity must be positive")
    if not 0 < duration <= 200:
        raise ValueError("duration must be between 0 and 200 s")
    _points(n_points)
    m1, m2, l1, l2, g = mass1, mass2, length1, length2, gravity

    def rhs(_t, s):
        a1, a2, w1, w2 = s
        d = a1 - a2
        den = 2 * m1 + m2 - m2 * math.cos(2 * d)
        dw1 = (-g * (2 * m1 + m2) * math.sin(a1) - m2 * g * math.sin(a1 - 2 * a2)
               - 2 * math.sin(d) * m2 * (w2**2 * l2 + w1**2 * l1 * math.cos(d))) / (l1 * den)
        dw2 = (2 * math.sin(d) * (w1**2 * l1 * (m1 + m2) + g * (m1 + m2) * math.cos(a1)
               + w2**2 * l2 * m2 * math.cos(d))) / (l2 * den)
        return [w1, w2, dw1, dw2]

    def energy(a1, a2, w1, w2):
        ke = 0.5 * m1 * (l1 * w1) ** 2 + 0.5 * m2 * ((l1 * w1) ** 2 + (l2 * w2) ** 2 + 2 * l1 * l2 * w1 * w2 * np.cos(a1 - a2))
        pe = -(m1 + m2) * g * l1 * np.cos(a1) - m2 * g * l2 * np.cos(a2)
        return ke + pe

    t = np.linspace(0, duration, n_points)
    s0 = [math.radians(theta1), math.radians(theta2), omega1, omega2]
    s1 = [s0[0] + math.radians(perturbation_deg), s0[1], omega1, omega2]
    runs = []
    for s in (s0, s1):
        sol = solve_ivp(rhs, (0, duration), s, t_eval=t, method="DOP853", rtol=1e-11, atol=1e-12)
        if not sol.success:
            raise ValueError(f"Integration failed: {sol.message}")
        runs.append(sol.y)
    a1, a2, w1, w2 = runs[0]
    e = energy(a1, a2, w1, w2)
    # Phase-space separation between the twins (angles wrapped)
    da = [np.angle(np.exp(1j * (runs[1][i] - runs[0][i]))) for i in (0, 1)]
    sep = np.sqrt(da[0] ** 2 + da[1] ** 2 + ((runs[1][2] - w1) ** 2 + (runs[1][3] - w2) ** 2) * (l1 / g))
    sep = np.maximum(sep, 1e-300)
    grow = (sep > 10 * sep[0]) & (sep < 1e-2)  # exponential-growth window before saturation
    lyap = float(np.polyfit(t[grow], np.log(sep[grow]), 1)[0]) if grow.sum() > 10 else None
    x1, y1 = l1 * np.sin(a1), -l1 * np.cos(a1)
    x2, y2 = x1 + l2 * np.sin(a2), y1 - l2 * np.cos(a2)
    tx1, ty1 = l1 * np.sin(runs[1][0]), -l1 * np.cos(runs[1][0])
    tx2, ty2 = tx1 + l2 * np.sin(runs[1][1]), ty1 - l2 * np.cos(runs[1][1])
    return {
        "result": {
            "energy": float(e[0]),
            "max_energy_drift": float(np.max(np.abs(e - e[0])) / max(abs(e[0]), 1e-12)),
            "lyapunov_exponent": lyap,
            "chaotic": lyap is not None and lyap > 0.05,
            "final_separation": float(sep[-1]),
            "flips": int(np.sum(np.abs(np.diff(np.floor((a2 + math.pi) / (2 * math.pi)))) > 0)),
        },
        "trajectory": {
            "t": t.tolist(), "theta1_deg": np.degrees(a1).tolist(), "theta2_deg": np.degrees(a2).tolist(),
            "x1": x1.tolist(), "y1": y1.tolist(), "x2": x2.tolist(), "y2": y2.tolist(),
        },
        "twin": {"x1": tx1.tolist(), "y1": ty1.tolist(), "x2": tx2.tolist(), "y2": ty2.tolist(), "separation": sep.tolist()},
        "units": "angles in degrees, positions in m, energy in J, Lyapunov exponent in 1/s",
        "assumptions": ["Point masses on rigid massless rods, frictionless pivots",
                        "Lyapunov exponent from the exponential growth of the twin separation (rough estimate)"],
    }
