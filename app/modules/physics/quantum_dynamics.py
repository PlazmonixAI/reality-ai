"""Quantum dynamics: an electron wave packet meeting a barrier or a well (time-dependent Schrödinger equation),
the quantum harmonic oscillator, and Rabi oscillations of a two-level system (a spin or a qubit).

All in SI units. The wave packet is solved with the split-step Fourier method, which is unitary, so the total
probability stays 1 to rounding error."""
from __future__ import annotations

import math

import numpy as np
from scipy.linalg import expm
from scipy.special import eval_hermite, factorial

from app.core.registry import tool

HBAR = 1.054571817e-34
ME = 9.1093837015e-31
EV = 1.602176634e-19
NM = 1e-9
FS = 1e-15

POTENTIALS = ("free", "barrier", "step", "well", "double_barrier", "harmonic")


def _potential(kind: str, x: np.ndarray, height_ev: float, width_nm: float) -> np.ndarray:
    V0, w = height_ev * EV, width_nm * NM
    if kind == "free":
        return np.zeros_like(x)
    if kind == "barrier":
        return np.where(np.abs(x) < w / 2, V0, 0.0)
    if kind == "step":
        return np.where(x > 0, V0, 0.0)
    if kind == "well":
        return np.where(np.abs(x) < w / 2, -V0, 0.0)
    if kind == "double_barrier":
        gap = 1.5 * w
        return np.where((np.abs(x - gap) < w / 2) | (np.abs(x + gap) < w / 2), V0, 0.0)
    if kind == "harmonic":  # V = ½ m ω² x² with ħω = height_ev
        omega = V0 / HBAR
        return 0.5 * ME * omega ** 2 * x ** 2
    raise ValueError(f"potential must be one of {', '.join(POTENTIALS)}")


@tool(domain="physics", name="wave_packet",
      description="An electron wave packet (Gaussian, energy in eV, width in nm) moving into a potential: free space, a "
                  "barrier, a step, a well, a double barrier or a harmonic trap. Solves the time-dependent Schrödinger "
                  "equation and returns frames of the probability density, plus transmitted and reflected probability.")
def wave_packet(potential: str = "barrier", energy_ev: float = 0.5, height_ev: float = 0.6, width_nm: float = 0.6,
                packet_width_nm: float = 2.0, duration_fs: float = 60.0, frames: int = 60) -> dict:
    if potential not in POTENTIALS:
        raise ValueError(f"potential must be one of {', '.join(POTENTIALS)}")
    if not (0.01 <= energy_ev <= 20 and 0 <= height_ev <= 20 and 0.05 <= width_nm <= 10 and 0.3 <= packet_width_nm <= 10):
        raise ValueError("energy 0.01 to 20 eV, height 0 to 20 eV, width 0.05 to 10 nm, packet width 0.3 to 10 nm")
    if not (1 <= duration_fs <= 500 and 2 <= frames <= 200):
        raise ValueError("duration 1 to 500 fs and 2 to 200 frames")
    L = 120 * NM
    n = 4096
    x = np.linspace(-L / 2, L / 2, n, endpoint=False)
    dx = x[1] - x[0]
    k = 2 * np.pi * np.fft.fftfreq(n, dx)
    k0 = math.sqrt(2 * ME * energy_ev * EV) / HBAR
    s0 = packet_width_nm * NM
    x0 = -20 * NM if potential != "harmonic" else -min(15 * NM, 4 * s0 + 5 * NM)
    if potential == "harmonic":
        k0 = 0.0  # start at rest, displaced: a coherent-like state oscillates
        s0 = math.sqrt(HBAR / (2 * ME * (height_ev * EV / HBAR)))  # ground-state width
    psi = (2 * np.pi * s0 ** 2) ** -0.25 * np.exp(-(x - x0) ** 2 / (4 * s0 ** 2) + 1j * k0 * x)
    V = _potential(potential, x, height_ev, width_nm)
    T = duration_fs * FS
    dt = 0.01 * FS if potential != "harmonic" else min(0.01 * FS, 0.02 / (height_ev * EV / HBAR))
    steps = int(math.ceil(T / dt))
    dt = T / steps
    half_v = np.exp(-1j * V * dt / (2 * HBAR))
    kin = np.exp(-1j * HBAR * k ** 2 * dt / (2 * ME))
    # absorbing edges so the packet does not wrap round the periodic box
    edge = np.clip((np.abs(x) - 0.42 * L) / (0.08 * L), 0, 1)
    absorb = np.exp(-0.02 * edge ** 2)
    keep_every = max(1, steps // (frames - 1))
    out_x = slice(None, None, 8)
    dens_frames, re_frames, times, mean_x = [], [], [], []
    trans = []
    for i in range(steps + 1):
        if i % keep_every == 0 or i == steps:
            p = np.abs(psi) ** 2
            dens_frames.append((p[out_x] * NM).round(8).tolist())  # per nm
            re_frames.append((psi.real[out_x] * math.sqrt(NM)).round(6).tolist())
            times.append(i * dt / FS)
            norm = p.sum() * dx
            mean_x.append(float((x * p).sum() * dx / max(norm, 1e-30) / NM))
            trans.append(float(p[x > (width_nm * NM if potential == "double_barrier" else width_nm * NM / 2)].sum() * dx))
        if i == steps:
            break
        psi = half_v * psi
        psi = np.fft.ifft(kin * np.fft.fft(psi))
        psi = half_v * psi * absorb
    p = np.abs(psi) ** 2
    total = float(p.sum() * dx)
    right = float(p[x > 0].sum() * dx)
    # plane-wave transmission for a rectangular barrier, for comparison (exact for a single energy)
    T_plane = None
    if potential == "barrier" and height_ev > 0:
        E, V0, a = energy_ev * EV, height_ev * EV, width_nm * NM
        if abs(E - V0) < 1e-6 * V0:
            T_plane = 1 / (1 + ME * V0 * a ** 2 / (2 * HBAR ** 2))
        elif E < V0:
            kap = math.sqrt(2 * ME * (V0 - E)) / HBAR
            T_plane = 1 / (1 + V0 ** 2 * math.sinh(kap * a) ** 2 / (4 * E * (V0 - E)))
        else:
            kk = math.sqrt(2 * ME * (E - V0)) / HBAR
            T_plane = 1 / (1 + V0 ** 2 * math.sin(kk * a) ** 2 / (4 * E * (E - V0)))
    return {
        "result": {
            "x_nm": (x[out_x] / NM).round(5).tolist(), "potential_ev": (V[out_x] / EV).round(6).tolist(),
            "times_fs": times, "density_per_nm": dens_frames, "real_part": re_frames, "mean_x_nm": mean_x,
            "probability_right": trans, "final_right": right, "final_total": total,
            "group_velocity_nm_per_fs": HBAR * k0 / ME / NM * FS, "wavelength_nm": (2 * math.pi / k0 / NM) if k0 else None,
            "plane_wave_transmission": T_plane,
        },
        "units": {"x": "nm", "potential": "eV", "time": "fs", "density": "1/nm", "velocity": "nm/fs"},
        "assumptions": ["One electron in one dimension; no spin and no other particles.",
                        "Split-step Fourier solution of iħ∂ψ/∂t = −ħ²/2m ∂²ψ/∂x² + Vψ on a 120 nm grid.",
                        "The edges of the box absorb the packet so nothing wraps round; total probability falls only "
                        "when part of the packet leaves the screen.",
                        "A packet spans a range of energies, so its transmission differs a little from the single-energy formula."],
    }


@tool(domain="physics", name="quantum_oscillator",
      description="Quantum harmonic oscillator: energy levels (n + ½)ħω, the eigenfunctions ψ_n(x), and the probability "
                  "density of an equal superposition of two levels as it sloshes back and forth over one period.")
def quantum_oscillator(hbar_omega_ev: float = 0.2, n_max: int = 5, superpose_a: int = 0, superpose_b: int = 1,
                       frames: int = 48) -> dict:
    if not (0.001 <= hbar_omega_ev <= 10):
        raise ValueError("hbar_omega_ev must be between 0.001 and 10 eV")
    if not (0 <= n_max <= 12 and 0 <= superpose_a <= 12 and 0 <= superpose_b <= 12 and superpose_a != superpose_b):
        raise ValueError("levels are 0 to 12 and the two superposed levels must differ")
    if not (2 <= frames <= 120):
        raise ValueError("frames must be between 2 and 120")
    omega = hbar_omega_ev * EV / HBAR
    x0 = math.sqrt(HBAR / (ME * omega))  # oscillator length
    span = math.sqrt(2 * max(n_max, superpose_a, superpose_b) + 1) * x0 * 1.6
    x = np.linspace(-span, span, 401)
    xi = x / x0

    def psi(n):
        return (1 / math.sqrt(2.0 ** n * float(factorial(n)))) * (1 / (math.pi * x0 ** 2)) ** 0.25 * \
            np.exp(-xi ** 2 / 2) * eval_hermite(n, xi)
    levels = [{"n": n, "energy_ev": (n + 0.5) * hbar_omega_ev, "psi": (psi(n) * math.sqrt(NM)).round(6).tolist()}
              for n in range(n_max + 1)]
    a, b = superpose_a, superpose_b
    pa, pb = psi(a), psi(b)
    period = 2 * math.pi / (abs(a - b) * omega)
    ts = np.linspace(0, period, frames)
    dens = []
    mean = []
    for t in ts:
        ps = (pa * np.exp(-1j * (a + 0.5) * omega * t) + pb * np.exp(-1j * (b + 0.5) * omega * t)) / math.sqrt(2)
        d = np.abs(ps) ** 2
        dens.append((d * NM).round(7).tolist())
        mean.append(float(np.trapezoid(x * d, x) / NM))
    V = 0.5 * ME * omega ** 2 * x ** 2 / EV
    return {"result": {"x_nm": (x / NM).round(5).tolist(), "potential_ev": V.round(6).tolist(), "levels": levels,
                       "oscillator_length_nm": x0 / NM, "period_fs": period / FS, "times_fs": (ts / FS).tolist(),
                       "superposition_density": dens, "mean_x_nm": mean, "zero_point_energy_ev": 0.5 * hbar_omega_ev},
            "units": {"x": "nm", "energy": "eV", "psi": "1/sqrt(nm)", "density": "1/nm", "time": "fs"},
            "assumptions": ["An electron in a parabolic potential V = ½mω²x².",
                            "ψ_n(x) = (2ⁿ n!)^-½ (mω/πħ)^¼ e^(−ξ²/2) H_n(ξ), ξ = x/√(ħ/mω)."]}


@tool(domain="physics", name="rabi_oscillation",
      description="A two-level quantum system (a spin in a magnetic field or a qubit) driven at Rabi frequency Ω with "
                  "detuning Δ: excited-state probability against time and the Bloch vector's path on the sphere.")
def rabi_oscillation(rabi_mhz: float = 1.0, detuning_mhz: float = 0.0, duration_us: float = 3.0, points: int = 300) -> dict:
    if not (0.001 <= rabi_mhz <= 1000 and -1000 <= detuning_mhz <= 1000):
        raise ValueError("rabi_mhz 0.001 to 1000, detuning_mhz −1000 to 1000")
    if not (0.001 <= duration_us <= 1000 and 10 <= points <= 2000):
        raise ValueError("duration 0.001 to 1000 µs and 10 to 2000 points")
    Om, De = 2 * math.pi * rabi_mhz * 1e6, 2 * math.pi * detuning_mhz * 1e6
    H = 0.5 * np.array([[-De, Om], [Om, De]], dtype=complex)  # rotating frame, units of ħ (rad/s)
    ts = np.linspace(0, duration_us * 1e-6, points)
    U1 = expm(-1j * H * (ts[1] - ts[0]))
    state = np.array([1, 0], dtype=complex)  # start in the ground state
    pe, bloch = [], []
    for _ in ts:
        g, e = state
        pe.append(float(abs(e) ** 2))
        rho01 = g * np.conj(e)
        bloch.append([float(2 * rho01.real), float(-2 * rho01.imag), float(abs(g) ** 2 - abs(e) ** 2)])
        state = U1 @ state
    Om_eff = math.sqrt(Om ** 2 + De ** 2)
    return {"result": {"t_us": (ts * 1e6).tolist(), "excited_probability": pe, "bloch": bloch,
                       "max_excitation": Om ** 2 / Om_eff ** 2, "rabi_period_us": 2 * math.pi / Om_eff * 1e6,
                       "pi_pulse_us": math.pi / Om * 1e6},
            "units": {"time": "µs", "probability": "dimensionless", "bloch": "dimensionless (unit sphere)"},
            "assumptions": ["Rotating-wave approximation; no decay or dephasing.",
                            "The Bloch vector's z component is +1 in the ground state and −1 in the excited state."]}
