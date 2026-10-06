"""The history of the universe from the Big Bang to today, for the Universe Map's Journey mode.

Two regimes:
  - the hot early universe (before ~1,000 s), where radiation dominates and time follows the temperature:
    t = 2.42 s · g*^(-1/2) · (kT / 1 MeV)^(-2)   (Kolb & Turner; g* = relativistic degrees of freedom);
  - everything later, from the Friedmann equation with matter, radiation and dark energy (the cosmology tool's
    ΛCDM, Planck 2018), with T = T0 (1 + z).
The size of the patch that is our observable universe today scales as a(t): R_then = R_now · a.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import integrate
from scipy.optimize import brentq

from app.core.registry import tool
from app.modules.physics.universe import C_KM_S, GYR_S, MPC_KM, PC_LY, _friedmann, _hex, blackbody_rgb

HBAR, G, C, KB = 1.054571817e-34, 6.67430e-11, 2.99792458e8, 1.380649e-23
T_CMB = 2.7255                 # K today (Fixsen 2009)
MEV_K = 1.160451812e10         # 1 MeV / k_B in kelvin
YEAR_S = 365.25 * 86400
GSTAR_NOW = 3.91               # entropy degrees of freedom today (photons + three neutrinos)


# (kT in MeV where a group of particles stops being relativistic, g* above it, g* below it)
_STEPS = ((5e4, 106.75, 61.75),    # top, W, Z, Higgs: around the electroweak scale
          (150.0, 61.75, 10.75),   # quark-hadron transition
          (0.2, 10.75, 3.36))      # electron-positron annihilation


def _gstar(t_mev: float) -> float:
    """Relativistic degrees of freedom of the Standard Model plasma at kT (MeV): the textbook steps, each smoothed
    over ~0.15 dex in temperature so the clock and the temperature stay continuous."""
    g = 3.36
    for tc, hi, lo in _STEPS:
        g += (hi - lo) * 0.5 * (1 + math.tanh((math.log10(t_mev) - math.log10(tc)) / 0.15))
    return g


def _t_of_mev(t_mev: float) -> float:
    return 2.42 / math.sqrt(_gstar(t_mev)) * t_mev ** -2


def _mev_of_t(t_s: float) -> float:
    """Invert t(T); t falls monotonically with T because g* only grows with temperature."""
    return 10 ** brentq(lambda lg: math.log(_t_of_mev(10 ** lg)) - math.log(t_s), -8, 12, xtol=1e-14)


def _scale_factor_hot(t_mev: float) -> float:
    """a = (T0/T) (g*s_now / g*s(T))^(1/3): entropy conservation, so a·T jumps when particles annihilate."""
    return (T_CMB / (t_mev * MEV_K)) * (GSTAR_NOW / _gstar(t_mev)) ** (1 / 3)


@tool(
    domain="physics",
    name="cosmic_history",
    description=(
        "The history of the universe from the Big Bang to today: the main epochs (Planck time, electroweak and "
        "quark-hadron transitions, neutrino decoupling, nucleosynthesis, matter-radiation equality, the CMB, the "
        "first stars, reionisation, the first galaxies seen, the Milky Way, accelerating expansion, the Sun, today) "
        "with time since the Big Bang, redshift, scale factor, temperature, the size then of today's observable "
        "universe and the colour of light at that temperature; plus n_frames samples for an animation."
    ),
)
def cosmic_history(h0: float = 67.66, omega_m: float = 0.3111, omega_r: float = 9.14e-5, n_frames: int = 120) -> dict:
    if not 50 <= h0 <= 90 or not 0.05 <= omega_m <= 1 or not 1e-5 <= omega_r <= 1e-3:
        raise ValueError("h0 must be 50..90, omega_m 0.05..1 and omega_r 1e-5..1e-3")
    if not 10 <= n_frames <= 400:
        raise ValueError("n_frames must be 10..400")
    ol = 1 - omega_m - omega_r
    e, _ = _friedmann(omega_m, omega_r, ol)
    t_hubble_s = MPC_KM / h0                         # 1/H0 in seconds
    age_s = lambda a: t_hubble_s * integrate.quad(lambda x: x / e(x), 0, a, limit=200, epsrel=1e-10)[0]  # noqa: E731
    now_s = age_s(1.0)
    chi_now = integrate.quad(lambda x: 1 / e(x), 0, 1, limit=400, epsrel=1e-10)[0]  # c dt / a = (c/H0) da / e(a)
    r_now_ly = chi_now * C_KM_S / h0 * PC_LY * 1e6  # comoving particle horizon today (ly)

    def a_of_age(t_s: float) -> float:
        return brentq(lambda a: age_s(a) - t_s, 1e-14, 1.0, xtol=1e-16, rtol=1e-12)

    def state(t_s: float, a: float | None = None, t_k: float | None = None) -> dict:
        if a is None:
            a = a_of_age(t_s)
        if t_k is None:
            t_k = T_CMB / a
        return {"time_s": t_s, "age_years": t_s / YEAR_S, "lookback_years": max(0.0, (now_s - t_s) / YEAR_S),
                "scale_factor": a, "redshift": 1 / a - 1, "temperature_k": t_k,
                "observable_patch_size_ly": 2 * r_now_ly * a,
                "colour": _hex(blackbody_rgb([min(t_k, 40_000.0)]))[0] if t_k >= 1000 else None}  # too cool to glow visibly

    def hot(t_mev: float) -> dict:
        t_s = _t_of_mev(t_mev)
        return state(t_s, _scale_factor_hot(t_mev), t_mev * MEV_K)

    def at_z(z: float) -> dict:
        a = 1 / (1 + z)
        return state(age_s(a), a)

    def ago(gyr: float) -> dict:
        return state(now_s - gyr * GYR_S)

    t_planck = math.sqrt(HBAR * G / C ** 5)
    temp_planck = math.sqrt(HBAR * C ** 5 / G) / KB
    a_eq = omega_r / omega_m
    a_acc = (omega_m / (2 * ol)) ** (1 / 3)          # deceleration parameter q = 0
    epochs = [
        ("planck", "The Big Bang: the Planck time", {"time_s": t_planck, "age_years": t_planck / YEAR_S, "lookback_years": now_s / YEAR_S,
                                                      "scale_factor": None, "redshift": None, "temperature_k": temp_planck,
                                                      "observable_patch_size_ly": None, "colour": _hex(blackbody_rgb([40_000.0]))[0]},
         "The earliest moment physics can describe. Gravity and quantum theory both matter; we have no tested theory for it."),
        ("electroweak", "Electromagnetism and the weak force separate", hot(1e5),
         "At 100 GeV the Higgs field switches on; W and Z particles become heavy."),
        ("quarks", "Quarks are bound into protons and neutrons", hot(150.0),
         "The quark-gluon plasma cools enough for quarks to stick together in threes and pairs."),
        ("neutrinos", "Neutrinos fly free", hot(1.0),
         "Neutrinos stop interacting and stream away; they still fill space today at 1.95 K."),
        ("nucleosynthesis", "The first nuclei: hydrogen and helium", hot(0.07),
         "Protons and neutrons fuse into helium-4 (about a quarter of the mass), deuterium and a trace of lithium."),
        ("equality", "Matter starts to outweigh light", state(age_s(a_eq), a_eq),
         "From here gravity can pull dark matter into clumps: the seeds of every galaxy."),
        ("cmb", "The universe turns transparent: the CMB", at_z(1089.8),
         "Electrons join nuclei to make atoms. The light released then is the cosmic microwave background we see today."),
        ("darkages", "The dark ages", at_z(50.0),
         "No stars yet. Hydrogen and helium gas cool and gather in dark-matter clumps."),
        ("firststars", "The first stars switch on", at_z(20.0),
         "Huge, hot, short-lived stars of pure hydrogen and helium (simulations put them near redshift 20)."),
        ("firstgalaxy", "The farthest galaxy seen: JADES-GS-z14-0", at_z(14.32),
         "Found by the James Webb Space Telescope in 2024; its light left it then."),
        ("reionisation", "Starlight reionises the universe", at_z(7.68),
         "Ultraviolet light from the first galaxies splits the hydrogen between them again (Planck 2018 midpoint)."),
        ("milkyway", "The Milky Way's oldest stars form", ago(13.5),
         "Ages of the oldest stars in our Galaxy's halo point to about 13.5 billion years ago."),
        ("acceleration", "Dark energy wins: expansion speeds up", state(age_s(a_acc), a_acc),
         "Dark energy now outweighs the pull of matter, and the expansion of space starts to accelerate."),
        ("sun", "The Sun and the planets form", ago(4.568),
         "The oldest grains in meteorites date the birth of the Solar System to 4.568 billion years ago."),
        ("today", "Today", state(now_s, 1.0),
         f"The CMB has cooled to {T_CMB} K. Our observable universe is about 93 billion light years across."),
    ]
    out = sorted(({"key": k, "name": n, **s, "what": w} for k, n, s, w in epochs), key=lambda x: x["time_s"])

    # animation frames: log-spaced in time from the electroweak era to today
    frames = []
    for t_s in np.geomspace(1e-11, now_s, n_frames):
        if t_s < 1000:
            mev = _mev_of_t(t_s)
            frames.append(state(t_s, _scale_factor_hot(mev), mev * MEV_K))
        else:
            frames.append(state(t_s))
    for f in frames:
        f.pop("lookback_years")
    return {
        "result": {"epochs": out, "frames": frames, "age_now_years": now_s / YEAR_S,
                   "observable_universe_diameter_ly": 2 * r_now_ly, "cmb_temperature_now_k": T_CMB,
                   "planck_time_s": t_planck, "planck_temperature_k": temp_planck},
        "units": "time in s and years, temperature in K, sizes in light years (proper size then)",
        "assumptions": [
            f"Flat ΛCDM, H0 = {h0} km/s/Mpc, Ωm = {omega_m}, Ωr = {omega_r}, ΩΛ = {ol:.4f} (Planck 2018)",
            "Before ~1,000 s: radiation era, t = 2.42 s · g*^(-1/2) (kT/MeV)^(-2), with the Standard Model g* (its steps smoothed over ~0.15 dex)",
            "Scale factor in the hot era from entropy conservation; afterwards from the Friedmann equation",
            "The Planck time is the limit of known physics, not a measured event; inflation (if it happened) came before 1e-32 s and is not modelled",
            "First stars (z ≈ 20) are a simulation estimate; JADES-GS-z14-0 (z = 14.32), reionisation (z = 7.68) and the 4.568 Gyr Solar System age are measurements; the Milky Way's 13.5 Gyr is the age of its oldest stars",
            "Colour is the blackbody colour of light at that temperature (capped at 40,000 K, where it looks blue-white; null below 1,000 K, too cool to glow visibly)",
        ],
    }
