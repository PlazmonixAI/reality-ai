"""Series RC / RL / RLC circuits: transients (DC step or AC drive) and frequency response."""
import math

import numpy as np
from scipy.integrate import solve_ivp

from app.core.registry import tool


def _check(resistance, inductance, capacitance):
    if resistance <= 0:
        raise ValueError("resistance must be positive")
    if inductance < 0:
        raise ValueError("inductance must be >= 0 (0 = no inductor)")
    if capacitance is not None and capacitance <= 0:
        raise ValueError("capacitance must be positive, or omitted for no capacitor")


@tool(
    domain="physics",
    name="rlc_circuit",
    description=(
        "Series R, L, C circuit driven by a source switched on at t = 0 (capacitor uncharged, no current). "
        "source 'dc' = constant voltage, 'ac' = voltage * sin(2 pi f t). inductance 0 means no inductor; omit "
        "capacitance for no capacitor (so RC, RL and RLC are all covered). Returns time constants, natural "
        "frequency, damping, Q and plot-ready current and voltages across R, L and C. "
        "Example: resistance=100, inductance=0.1, capacitance=1e-5, voltage=5, source='dc', duration=0.02."
    ),
)
def rlc_circuit(
    resistance: float,
    voltage: float,
    duration: float,
    inductance: float = 0.0,
    capacitance: float | None = None,
    source: str = "dc",
    frequency: float = 50.0,
    n_points: int = 1001,
) -> dict:
    _check(resistance, inductance, capacitance)
    if source not in ("dc", "ac"):
        raise ValueError("source must be 'dc' or 'ac'")
    if duration <= 0 or (source == "ac" and frequency <= 0):
        raise ValueError("duration (and frequency for ac) must be positive")
    if not 2 <= n_points <= 20_000:
        raise ValueError("n_points must be between 2 and 20000")
    R, L, C, V = resistance, inductance, capacitance, voltage
    w = 2 * math.pi * frequency

    def vs(t):
        return V if source == "dc" else V * np.sin(w * t)

    t = np.linspace(0, duration, n_points)
    kw = dict(t_eval=t, method="LSODA", rtol=1e-10, atol=1e-14)
    if L > 0 and C:
        sol = solve_ivp(lambda tt, z: [z[1], (vs(tt) - R * z[1] - z[0] / C) / L], (0, duration), [0.0, 0.0], **kw)
        q, i = sol.y
    elif L > 0:
        sol = solve_ivp(lambda tt, z: [(vs(tt) - R * z[0]) / L], (0, duration), [0.0], **kw)
        q, i = np.zeros_like(t), sol.y[0]
    elif C:
        sol = solve_ivp(lambda tt, z: [(vs(tt) - z[0] / C) / R], (0, duration), [0.0], **kw)
        q = sol.y[0]
        i = (vs(t) - q / C) / R
    else:
        q, i = np.zeros_like(t), vs(t) / R
    v_src = vs(t) * np.ones_like(t)
    v_r = i * R
    v_c = q / C if C else np.zeros_like(t)
    v_l = v_src - v_r - v_c

    summary: dict = {}
    if C and L == 0:
        summary["time_constant"] = R * C
    elif L > 0 and not C:
        summary["time_constant"] = L / R
    if L > 0 and C:
        w0 = 1 / math.sqrt(L * C)
        zeta = R / 2 * math.sqrt(C / L)
        summary.update({
            "natural_frequency_hz": w0 / (2 * math.pi),
            "damping_ratio": zeta,
            "quality_factor": 1 / R * math.sqrt(L / C),
            "regime": "underdamped" if zeta < 1 else "critically damped" if math.isclose(zeta, 1) else "overdamped",
            "damped_frequency_hz": w0 * math.sqrt(1 - zeta**2) / (2 * math.pi) if zeta < 1 else None,
        })
    return {
        "result": summary,
        "trajectory": {"t": t.tolist(), "current": i.tolist(), "v_source": v_src.tolist(), "v_resistor": v_r.tolist(),
                       "v_inductor": v_l.tolist(), "v_capacitor": v_c.tolist()},
        "units": "time s, current A, voltages V, frequency Hz, time constant s",
        "assumptions": ["Ideal lumped components in series", "Source switched on at t = 0 with no stored energy"],
    }


@tool(
    domain="physics",
    name="rlc_frequency_response",
    description=(
        "Steady-state AC response of a series RLC circuit: impedance magnitude and phase, current amplitude "
        "and voltage amplitudes vs frequency (log-spaced), plus resonance frequency, Q and half-power bandwidth. "
        "Example: resistance=10, inductance=0.01, capacitance=1e-6, voltage=1."
    ),
)
def rlc_frequency_response(
    resistance: float,
    inductance: float,
    capacitance: float,
    voltage: float = 1.0,
    f_min: float | None = None,
    f_max: float | None = None,
    n_points: int = 400,
) -> dict:
    if inductance <= 0:
        raise ValueError("inductance must be positive for a resonant circuit")
    _check(resistance, inductance, capacitance)
    R, L, C = resistance, inductance, capacitance
    f0 = 1 / (2 * math.pi * math.sqrt(L * C))
    f_min, f_max = f_min or f0 / 20, f_max or f0 * 20
    if not 0 < f_min < f_max:
        raise ValueError("Need 0 < f_min < f_max")
    f = np.geomspace(f_min, f_max, n_points)
    w = 2 * math.pi * f
    Z = R + 1j * (w * L - 1 / (w * C))
    I = voltage / np.abs(Z)
    return {
        "result": {
            "resonant_frequency_hz": f0,
            "quality_factor": math.sqrt(L / C) / R,
            "bandwidth_hz": R / (2 * math.pi * L),
            "peak_current": voltage / R,
        },
        "curve": {"frequency": f.tolist(), "impedance": np.abs(Z).tolist(), "phase_deg": np.degrees(np.angle(Z)).tolist(),
                  "current": I.tolist(), "v_resistor": (I * R).tolist(), "v_inductor": (I * w * L).tolist(),
                  "v_capacitor": (I / (w * C)).tolist()},
        "units": "frequency Hz, impedance ohm, phase degrees (voltage leads current when positive), current A, voltage V",
        "assumptions": ["Sinusoidal steady state (phasors)", "Ideal series R, L and C"],
    }
