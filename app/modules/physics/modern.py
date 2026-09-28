"""Modern physics: blackbody radiation, photoelectric effect, hydrogen spectrum, radioactive decay, relativity."""
import math

import numpy as np
from scipy.integrate import quad
from scipy.linalg import expm

from app.core.registry import tool

H = 6.62607015e-34        # Planck constant, J s (exact)
C = 299_792_458.0         # speed of light, m/s (exact)
KB = 1.380649e-23         # Boltzmann constant, J/K (exact)
QE = 1.602176634e-19      # elementary charge, C (exact)
SIGMA = 2 * math.pi**5 * KB**4 / (15 * H**3 * C**2)   # Stefan-Boltzmann constant from the exact constants
WIEN_B = 2.897771955e-3   # Wien displacement constant, m K
RYDBERG_INF = 10_973_731.568160   # m^-1
ME_OVER_MP = 1 / 1836.15267343
RY_EV = 13.605693122994   # Rydberg energy, eV


def planck(wl: np.ndarray, t: float) -> np.ndarray:
    """Spectral radiance B_lambda(T) in W sr^-1 m^-3."""
    x = H * C / (wl * KB * t)
    with np.errstate(over="ignore"):
        return 2 * H * C**2 / wl**5 / np.expm1(x)


@tool(
    domain="physics",
    name="blackbody",
    description=(
        "Blackbody (Planck) spectrum at temperature T (K): spectral radiance vs wavelength, the peak wavelength "
        "(Wien's law), total emitted power per area (Stefan-Boltzmann) and the fraction emitted as visible light. "
        "Example: temperature=5778 (the Sun)."
    ),
)
def blackbody(temperature: float, wl_min_nm: float = 100.0, wl_max_nm: float = 3000.0, n_points: int = 600) -> dict:
    if not 1 <= temperature <= 1e6:
        raise ValueError("temperature must be between 1 and 1e6 K")
    if not 0 < wl_min_nm < wl_max_nm or not 10 <= n_points <= 10_000:
        raise ValueError("Need 0 < wl_min < wl_max and 10..10000 points")
    wl = np.linspace(wl_min_nm, wl_max_nm, n_points) * 1e-9
    b = planck(wl, temperature)
    total = SIGMA * temperature**4
    vis, _ = quad(lambda l: float(planck(np.array(l), temperature)), 380e-9, 750e-9)
    return {
        "result": {
            "peak_wavelength_nm": WIEN_B / temperature * 1e9,
            "total_power_per_area": total,
            "visible_fraction": math.pi * vis / total,
        },
        "spectrum": {"wavelength_nm": (wl * 1e9).tolist(), "radiance": b.tolist()},
        "units": "radiance W sr^-1 m^-3 (per metre of wavelength), power W/m^2, wavelengths nm",
        "assumptions": ["Ideal blackbody (emissivity 1)", "Planck's law; Wien and Stefan-Boltzmann follow from it"],
    }


@tool(
    domain="physics",
    name="photoelectric",
    description=(
        "Photoelectric effect for light of a given wavelength (nm) on a metal with work function (eV): photon "
        "energy, maximum kinetic energy of ejected electrons, stopping voltage, threshold wavelength, and the "
        "photocurrent vs applied voltage for the given light power (W) and quantum efficiency. "
        "Example: wavelength_nm=400, work_function_ev=2.28, power=1e-3."
    ),
)
def photoelectric(wavelength_nm: float, work_function_ev: float, power: float = 1e-3, quantum_efficiency: float = 0.1,
                  v_min: float = -5.0, v_max: float = 5.0) -> dict:
    if wavelength_nm <= 0 or work_function_ev <= 0 or power < 0 or not 0 <= quantum_efficiency <= 1 or v_min >= v_max:
        raise ValueError("wavelength, work function positive; power >= 0; efficiency 0..1; v_min < v_max")
    e_photon = H * C / (wavelength_nm * 1e-9) / QE          # eV
    k_max = e_photon - work_function_ev
    emits = k_max > 0
    photon_rate = power / (e_photon * QE)
    i_sat = quantum_efficiency * photon_rate * QE if emits else 0.0
    v = np.linspace(v_min, v_max, 201)
    # Retarding voltage V < 0 stops electrons with K < e|V|; K uniform on [0, K_max] (simple model).
    frac = np.clip(1 + v / k_max, 0, 1) if emits else np.zeros_like(v)
    return {
        "result": {
            "photon_energy_ev": e_photon,
            "max_kinetic_energy_ev": max(k_max, 0.0),
            "stopping_voltage": max(k_max, 0.0),
            "threshold_wavelength_nm": H * C / (work_function_ev * QE) * 1e9,
            "threshold_frequency": work_function_ev * QE / H,
            "electrons_emitted": emits,
            "saturation_current": i_sat,
            "max_electron_speed": math.sqrt(2 * k_max * QE / 9.1093837015e-31) if emits else 0.0,
        },
        "iv_curve": {"voltage": v.tolist(), "current": (i_sat * frac).tolist()},
        "units": "energies eV, voltages V, current A, wavelength nm, frequency Hz, speed m/s",
        "assumptions": ["Einstein's relation K_max = hf - phi", "Current vs voltage uses a uniform spread of electron energies up to K_max"],
    }


@tool(
    domain="physics",
    name="hydrogen_spectrum",
    description=(
        "Hydrogen atom (Bohr model with reduced-mass Rydberg constant): energy levels up to n_max and every "
        "emission line between them, grouped by series (Lyman, Balmer, Paschen, ...), plus the chosen transition. "
        "Example: n_upper=3, n_lower=2 (H-alpha)."
    ),
)
def hydrogen_spectrum(n_upper: int = 3, n_lower: int = 2, n_max: int = 7) -> dict:
    if not 1 <= n_lower < n_upper <= n_max <= 20:
        raise ValueError("Need 1 <= n_lower < n_upper <= n_max <= 20")
    r_h = RYDBERG_INF / (1 + ME_OVER_MP)
    ry_h = RY_EV / (1 + ME_OVER_MP)
    series = {1: "Lyman", 2: "Balmer", 3: "Paschen", 4: "Brackett", 5: "Pfund", 6: "Humphreys"}

    def line(nu: int, nl: int) -> dict:
        inv = r_h * (1 / nl**2 - 1 / nu**2)
        return {"n_upper": nu, "n_lower": nl, "wavelength_nm": 1e9 / inv, "energy_ev": ry_h * (1 / nl**2 - 1 / nu**2),
                "series": series.get(nl, f"n={nl}")}
    levels = [{"n": n, "energy_ev": -ry_h / n**2, "orbit_radius_nm": 0.0529177210903 * n * n * (1 + ME_OVER_MP)} for n in range(1, n_max + 1)]
    lines = [line(u, l) for l in range(1, n_max) for u in range(l + 1, n_max + 1)]
    chosen = line(n_upper, n_lower)
    return {
        "result": {**chosen, "frequency_hz": C / (chosen["wavelength_nm"] * 1e-9), "ionisation_energy_ev": ry_h},
        "levels": levels,
        "lines": lines,
        "units": "energies eV, wavelengths nm (vacuum), radii nm",
        "assumptions": ["Bohr model / Rydberg formula with the reduced-mass correction; fine structure ignored",
                        "Vacuum wavelengths (air wavelengths are about 0.03% shorter)"],
    }


@tool(
    domain="physics",
    name="radioactive_decay",
    description=(
        "Radioactive decay chain A -> B -> C -> ... solved exactly (Bateman equations via a matrix exponential). "
        "half_lives in seconds for each member (use null for a stable end member); initial amounts (atoms or "
        "moles). Returns amounts and activities vs time. Example: half_lives=[3.82*86400, null], initial=[1000, 0], "
        "duration=20*86400."
    ),
)
def radioactive_decay(half_lives: list[float | None], initial: list[float], duration: float, n_points: int = 301) -> dict:
    n = len(half_lives)
    if not 1 <= n <= 8 or len(initial) != n:
        raise ValueError("1..8 chain members, with one initial amount each")
    if duration <= 0 or not 2 <= n_points <= 5000:
        raise ValueError("duration must be positive and 2..5000 points")
    lam = []
    for h in half_lives:
        if h is None:
            lam.append(0.0)
        elif h <= 0:
            raise ValueError("half-lives must be positive (or null for stable)")
        else:
            lam.append(math.log(2) / h)
    if any(v < 0 for v in initial):
        raise ValueError("initial amounts must be >= 0")
    A = np.zeros((n, n))
    for i, l in enumerate(lam):
        A[i, i] = -l
        if i + 1 < n:
            A[i + 1, i] = l
    t = np.linspace(0, duration, n_points)
    n0 = np.array(initial, dtype=float)
    N = np.array([expm(A * tt) @ n0 for tt in t]).T
    act = N * np.array(lam)[:, None]
    return {
        "result": {"final_amounts": N[:, -1].tolist(), "decay_constants": lam,
                   "mean_lives": [1 / l if l else None for l in lam]},
        "curves": {"t": t.tolist(), "amounts": N.tolist(), "activities": act.tolist()},
        "units": "time s, amounts in the units given, activity = amount per second (Bq if amounts are atoms)",
        "assumptions": ["Each member decays only to the next (no branching)", "Exact solution via matrix exponential"],
    }


@tool(
    domain="physics",
    name="special_relativity",
    description=(
        "Special relativity at speed beta = v/c: Lorentz factor, time dilation and length contraction, "
        "relativistic energy and momentum for a rest mass, and a twin-paradox trip of distance_ly light-years "
        "(one way) and back. Example: beta=0.8, distance_ly=4, rest_mass=1."
    ),
)
def special_relativity(beta: float, proper_time: float = 1.0, proper_length: float = 1.0, rest_mass: float = 1.0,
                       distance_ly: float | None = None) -> dict:
    if not 0 <= beta < 1:
        raise ValueError("beta must be in [0, 1)")
    if proper_time < 0 or proper_length < 0 or rest_mass < 0:
        raise ValueError("proper time, length and rest mass must be >= 0")
    g = 1 / math.sqrt(1 - beta * beta)
    e0 = rest_mass * C * C
    out = {
        "gamma": g, "rapidity": math.atanh(beta),
        "dilated_time": g * proper_time, "contracted_length": proper_length / g,
        "rest_energy": e0, "total_energy": g * e0, "kinetic_energy": (g - 1) * e0,
        "momentum": g * rest_mass * beta * C, "newtonian_kinetic_energy": 0.5 * rest_mass * (beta * C) ** 2,
    }
    if distance_ly is not None:
        if distance_ly <= 0 or beta == 0:
            raise ValueError("distance_ly must be positive and beta > 0 for a trip")
        earth = 2 * distance_ly / beta
        out["trip"] = {"earth_years": earth, "traveller_years": earth / g, "age_difference_years": earth - earth / g,
                       "distance_seen_by_traveller_ly": distance_ly / g}
    b = np.linspace(0, 0.995, 200)
    return {
        "result": out,
        "gamma_curve": {"beta": b.tolist(), "gamma": (1 / np.sqrt(1 - b * b)).tolist()},
        "units": "times in the units of proper_time (trip in years), lengths in the units of proper_length, energy J, momentum kg m/s",
        "assumptions": ["Inertial frames, constant speed; the twin turnaround is instantaneous"],
    }
