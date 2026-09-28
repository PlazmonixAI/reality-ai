"""1D quantum mechanics: bound states of wells (infinite, finite, harmonic) and tunnelling through a
rectangular barrier."""
import math

import numpy as np
from scipy.linalg import eigh_tridiagonal

from app.core.registry import tool

HBAR = 1.054571817e-34  # J s
ME = 9.1093837015e-31  # kg
QE = 1.602176634e-19  # J per eV
MASSES = {"electron": ME, "proton": 1.67262192369e-27, "neutron": 1.67492749804e-27}


def _mass(particle: str, mass: float | None) -> float:
    if mass is not None:
        if mass <= 0:
            raise ValueError("mass must be positive")
        return mass
    if particle not in MASSES:
        raise ValueError(f"particle must be one of {', '.join(MASSES)} (or give mass)")
    return MASSES[particle]


@tool(
    domain="physics",
    name="quantum_well",
    description=(
        "Bound states of a particle in a 1D well: 'infinite' square well (exact), 'finite' square well of depth_ev, "
        "or 'harmonic' oscillator with the given spring frequency omega (rad/s). Finite and harmonic wells are solved "
        "numerically (finite differences). Returns energies (eV), normalised wavefunctions and probability densities. "
        "width_nm is the well width. Example: well='infinite', width_nm=1, particle='electron'."
    ),
)
def quantum_well(
    well: str = "infinite",
    width_nm: float = 1.0,
    depth_ev: float = 5.0,
    omega: float = 2e15,
    particle: str = "electron",
    mass: float | None = None,
    n_levels: int = 5,
    n_grid: int = 1200,
) -> dict:
    m = _mass(particle, mass)
    if width_nm <= 0 or not 1 <= n_levels <= 30 or not 200 <= n_grid <= 8000:
        raise ValueError("width_nm must be positive, n_levels 1..30, n_grid 200..8000")
    a = width_nm * 1e-9
    if well == "infinite":
        x = np.linspace(0, a, n_grid)
        ns = np.arange(1, n_levels + 1)
        e = (ns * math.pi * HBAR / a) ** 2 / (2 * m)
        psi = [np.sqrt(2 / a) * np.sin(n * math.pi * x / a) for n in ns]
        v = np.zeros_like(x)
        bound = n_levels
    elif well in ("finite", "harmonic"):
        if well == "finite":
            if depth_ev <= 0:
                raise ValueError("depth_ev must be positive")
            v0 = depth_ev * QE
            # Extend the grid well past the walls so evanescent tails decay to ~0
            kappa_min = math.sqrt(2 * m * v0) / HBAR
            span = a / 2 + max(8 / kappa_min, a)
            x = np.linspace(-span, span, n_grid)
            v = np.where(np.abs(x) <= a / 2, 0.0, v0)
            ceiling = v0
        else:
            if omega <= 0:
                raise ValueError("omega must be positive (rad/s)")
            x0 = math.sqrt(HBAR / (m * omega))
            span = x0 * math.sqrt(2 * n_levels + 1) * 2.2 + 6 * x0
            x = np.linspace(-span, span, n_grid)
            v = 0.5 * m * omega**2 * x**2
            ceiling = np.inf
        dx = x[1] - x[0]
        t = HBAR**2 / (2 * m * dx**2)
        # Interior points only (ψ = 0 at the far edges of the box)
        vals, vecs = eigh_tridiagonal(2 * t + v[1:-1], -t * np.ones(len(x) - 3), select="i", select_range=(0, n_levels - 1))
        keep = vals < ceiling
        e, vecs = vals[keep], vecs[:, keep]
        bound = int(keep.sum())
        psi = []
        for j in range(bound):
            full = np.concatenate([[0], vecs[:, j], [0]])
            full /= math.sqrt(np.trapezoid(full**2, x))
            k = int(np.argmax(np.abs(full) > 1e-3 * np.max(np.abs(full))))
            psi.append(full * (1 if full[k] > 0 else -1))
    else:
        raise ValueError("well must be 'infinite', 'finite' or 'harmonic'")
    e_ev = np.asarray(e) / QE
    out = {
        "energies_ev": e_ev.tolist(),
        "bound_states": bound,
        "ground_state_ev": float(e_ev[0]) if bound else None,
        "transition_wavelengths_nm": [float(2 * math.pi * HBAR * 299792458 / ((e_ev[i] - e_ev[0]) * QE) * 1e9) for i in range(1, bound)],
    }
    if well == "finite":
        z0 = a / 2 * math.sqrt(2 * m * depth_ev * QE) / HBAR
        out["predicted_bound_states"] = int(math.ceil(2 * z0 / math.pi))
    if well == "harmonic":
        out["quantum_hbar_omega_ev"] = HBAR * omega / QE
    return {
        "result": out,
        "x_nm": (x * 1e9).tolist(),
        "potential_ev": (np.minimum(v, 1e30) / QE).tolist() if well != "infinite" else [0.0] * len(x),
        "wavefunctions": [(p / math.sqrt(1e9)).tolist() for p in psi],  # in nm^(-1/2)
        "densities": [(p**2 / 1e9).tolist() for p in psi],  # in 1/nm
        "units": "energies in eV, x in nm, ψ in nm^(-1/2), |ψ|² in 1/nm",
        "assumptions": ["Time-independent Schrödinger equation in 1D, non-relativistic",
                        "Finite/harmonic wells solved by second-order finite differences on a large box"],
    }


@tool(
    domain="physics",
    name="quantum_tunnelling",
    description=(
        "Transmission of a particle with energy_ev through a rectangular barrier of height barrier_ev and width "
        "width_nm (exact result, for E below or above the barrier), with the reflection coefficient, a plot of T vs E, "
        "and |ψ|² across the barrier from the transfer-matrix solution. Example: energy_ev=1, barrier_ev=2, width_nm=0.5."
    ),
)
def quantum_tunnelling(
    energy_ev: float,
    barrier_ev: float,
    width_nm: float,
    particle: str = "electron",
    mass: float | None = None,
    n_points: int = 600,
) -> dict:
    m = _mass(particle, mass)
    if energy_ev <= 0 or barrier_ev < 0 or width_nm <= 0:
        raise ValueError("energy_ev must be positive, barrier_ev >= 0, width_nm positive")
    if not 50 <= n_points <= 5000:
        raise ValueError("n_points must be between 50 and 5000")
    a = width_nm * 1e-9
    v0 = barrier_ev * QE

    def transmission(e_j):
        k = math.sqrt(2 * m * e_j) / HBAR
        if abs(e_j - v0) < 1e-12 * max(v0, e_j):
            return 1 / (1 + m * v0 * a * a / (2 * HBAR**2))
        if e_j < v0:
            kap = math.sqrt(2 * m * (v0 - e_j)) / HBAR
            return 1 / (1 + (v0**2 * math.sinh(kap * a) ** 2) / (4 * e_j * (v0 - e_j)))
        q = math.sqrt(2 * m * (e_j - v0)) / HBAR
        return 1 / (1 + (v0**2 * math.sin(q * a) ** 2) / (4 * e_j * (e_j - v0))) if v0 > 0 else 1.0

    e = energy_ev * QE
    t = transmission(e)
    # Wavefunction via piecewise solution: ψ = e^{ikx} + r e^{-ikx} (x<0); A e^{iqx} + B e^{-iqx} (0<x<a); τ e^{ikx} (x>a)
    k = math.sqrt(2 * m * e) / HBAR
    q = np.sqrt(complex(2 * m * (e - v0))) / HBAR  # imaginary below the barrier
    if abs(q) < 1e-20:
        q = 1e-6 * k + 0j
    # Match at x = a (from the right), then at x = 0
    tau = 1.0 + 0j
    ea = np.exp(1j * k * a)
    A = tau * ea * (q + k) / (2 * q) * np.exp(-1j * q * a)
    B = tau * ea * (q - k) / (2 * q) * np.exp(1j * q * a)
    inc = (A * (q + k) + B * (k - q)) / (2 * k)  # coefficient of e^{ikx} on the left
    refl = (A * (k - q) + B * (k + q)) / (2 * k)
    A, B, tau, refl = A / inc, B / inc, tau / inc, refl / inc
    xs = np.linspace(-1.5 * a - 2 * math.pi / k, 2.5 * a + 2 * math.pi / k, n_points)
    psi = np.where(xs < 0, np.exp(1j * k * xs) + refl * np.exp(-1j * k * xs),
                   np.where(xs <= a, A * np.exp(1j * q * xs) + B * np.exp(-1j * q * xs), tau * np.exp(1j * k * xs)))
    es = np.linspace(max(1e-4, 0.01 * max(barrier_ev, energy_ev)), 3 * max(barrier_ev, energy_ev), 400)
    decay = None
    if e < v0:
        decay = 1 / (math.sqrt(2 * m * (v0 - e)) / HBAR) * 1e9
    return {
        "result": {
            "transmission": t,
            "reflection": 1 - t,
            "transmission_from_wavefunction": float(abs(tau) ** 2),
            "above_barrier": e > v0,
            "decay_length_nm": decay,
            "wkb_estimate": math.exp(-2 * a / (decay * 1e-9)) if decay else None,
            "wavelength_nm": 2 * math.pi / k * 1e9,
        },
        "curve": {"energy_ev": es.tolist(), "transmission": [transmission(x * QE) for x in es]},
        "wavefunction": {"x_nm": (xs * 1e9).tolist(), "density": (np.abs(psi) ** 2).tolist(), "real": psi.real.tolist()},
        "units": "energies in eV, lengths in nm; T and R dimensionless; |ψ|² relative to the incoming wave",
        "assumptions": ["Rectangular barrier, plane-wave particle (steady state), non-relativistic",
                        "WKB estimate e^(−2κa) is only valid for thick, high barriers"],
    }
