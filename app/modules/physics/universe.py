"""Beyond the Solar System: real stars, a model of the Milky Way, real galaxies and ΛCDM cosmology.

- Stars: the HYG v4.1 catalogue (Hipparcos + Yale + Gliese; app/data/space/stars.csv), naked-eye stars plus
  every star within 30 pc. Temperatures from B−V (Ballesteros 2012), colours by integrating a blackbody
  through the CIE 1931 colour-matching functions.
- Milky Way: a schematic structural model (exponential disc, bar, bulge, four logarithmic spiral arms and the
  local Orion spur) and a Bovy (2015)-style three-component rotation curve normalised to the measured
  circular speed at the Sun; real globular clusters from the Celestia catalogue.
- Galaxies: ~11,000 real galaxies with measured distances (Celestia catalogue from NED, RC3, Karachentsev+ 2004).
- Cosmology: Friedmann equation for a ΛCDM universe (Planck 2018 parameters by default).
"""
import csv
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy import integrate

from app.core.registry import tool
from app.modules.physics.ephemeris import OBLIQUITY

DATA = Path(__file__).resolve().parents[2] / "data" / "space"
C_KM_S = 299_792.458
PC_LY = 3.261563777
MPC_KM = 3.0856775814913673e19
GYR_S = 3.15576e16
G = 6.67430e-11
M_SUN = 1.98892e30
KPC_M = 3.0856775814913673e19
# ICRS/J2000 equatorial → galactic rotation matrix (Hipparcos, ESA 1997)
EQ_TO_GAL = np.array([[-0.0548755604, -0.8734370902, -0.4838350155],
                      [0.4941094279, -0.4448296300, 0.7469822445],
                      [-0.8676661490, -0.1980763734, 0.4559837762]])
_c, _s = math.cos(OBLIQUITY), math.sin(OBLIQUITY)
EQ_TO_ECL = np.array([[1, 0, 0], [0, _c, _s], [0, -_s, _c]])
GREEK = {"Alp": "α", "Bet": "β", "Gam": "γ", "Del": "δ", "Eps": "ε", "Zet": "ζ", "Eta": "η", "The": "θ", "Iot": "ι",
         "Kap": "κ", "Lam": "λ", "Mu": "μ", "Nu": "ν", "Xi": "ξ", "Omi": "ο", "Pi": "π", "Rho": "ρ", "Sig": "σ",
         "Tau": "τ", "Ups": "υ", "Phi": "φ", "Chi": "χ", "Psi": "ψ", "Ome": "ω"}
SPECTRAL_T = {"O": 35000, "B": 17000, "A": 8800, "F": 6700, "G": 5600, "K": 4400, "M": 3300}


def radec_unit(ra_h: np.ndarray, dec_deg: np.ndarray) -> np.ndarray:
    ra, dec = np.radians(np.asarray(ra_h, float) * 15), np.radians(np.asarray(dec_deg, float))
    return np.array([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)])


def _frame(name: str) -> np.ndarray:
    frames = {"ecliptic": EQ_TO_ECL, "galactic": EQ_TO_GAL, "equatorial": np.eye(3)}
    if name not in frames:
        raise ValueError(f"frame must be one of {sorted(frames)}")
    return frames[name]


# ---------- colour of a blackbody ----------
def _cie_xyz(lam_nm: np.ndarray) -> np.ndarray:
    """CIE 1931 2° colour-matching functions (Wyman, Sloan & Shirley 2013 multi-lobe fit)."""
    def g(mu, s1, s2):
        s = np.where(lam_nm < mu, s1, s2)
        return np.exp(-0.5 * ((lam_nm - mu) / s) ** 2)
    x = 1.056 * g(599.8, 37.9, 31.0) + 0.362 * g(442.0, 16.0, 26.7) - 0.065 * g(501.1, 20.4, 26.2)
    y = 0.821 * g(568.8, 46.9, 40.5) + 0.286 * g(530.9, 16.3, 31.1)
    z = 1.217 * g(437.0, 11.8, 36.0) + 0.681 * g(459.0, 26.0, 13.8)
    return np.array([x, y, z])


def blackbody_rgb(temperature_k: np.ndarray) -> np.ndarray:
    """sRGB colour (0..1, brightest channel = 1) of blackbodies at the given temperatures, shape (n, 3)."""
    t = np.atleast_1d(np.asarray(temperature_k, float))
    lam = np.linspace(380, 780, 81)
    cmf = _cie_xyz(lam)
    h, c, k = 6.62607015e-34, 2.99792458e8, 1.380649e-23
    lm = lam[None, :] * 1e-9
    planck = 1.0 / (lm ** 5 * np.expm1(np.minimum(h * c / (lm * k * t[:, None]), 700)))
    xyz = planck @ cmf.T
    m = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
    rgb = np.clip(xyz @ m.T, 0, None)
    rgb /= rgb.max(axis=1, keepdims=True)
    return np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * rgb ** (1 / 2.4) - 0.055)


def _hex(rgb: np.ndarray) -> list[str]:
    return ["#%02x%02x%02x" % tuple(int(round(255 * v)) for v in c) for c in rgb]


def bv_temperature(bv: np.ndarray) -> np.ndarray:
    """Effective temperature (K) from the B−V colour index (Ballesteros 2012, EPL 97, 34008)."""
    bv = np.asarray(bv, float)
    return 4600.0 * (1 / (0.92 * bv + 1.7) + 1 / (0.92 * bv + 0.62))


# ---------- stars ----------
@lru_cache(maxsize=None)
def star_table() -> dict:
    with (DATA / "stars.csv").open() as f:
        rows = list(csv.DictReader(f))
    names = []
    for r in rows:
        if r["name"]:
            names.append(r["name"])
        elif r["bayer"]:
            names.append(f"{GREEK.get(r['bayer'].rstrip('0123456789'), r['bayer'])} {r['con']}")
        elif r["flam"]:
            names.append(f"{r['flam']} {r['con']}")
        else:
            names.append(f"HIP {r['hip']}" if r["hip"] else "Gliese star")
    ci = np.array([float(r["ci"]) if r["ci"] else np.nan for r in rows])
    fallback = np.array([SPECTRAL_T.get(r["spect"][:1], 5600) for r in rows], float)
    temp = np.where(np.isfinite(ci), bv_temperature(np.clip(np.nan_to_num(ci), -0.4, 2.2)), fallback)
    return {
        "names": names, "proper": [bool(r["name"]) for r in rows], "con": [r["con"] for r in rows],
        "spect": [r["spect"] for r in rows],
        "unit": radec_unit([float(r["ra_h"]) for r in rows], [float(r["dec_deg"]) for r in rows]),
        "dist_ly": np.array([float(r["dist_pc"]) for r in rows]) * PC_LY,
        "mag": np.array([float(r["mag"]) for r in rows]), "abs_mag": np.array([float(r["abs_mag"]) for r in rows]),
        "temp": temp,
    }


@tool(
    domain="physics",
    name="star_catalog",
    description=(
        "Real stars from the HYG catalogue (Hipparcos/Yale/Gliese): 3D positions in light years (frame "
        "'ecliptic', 'galactic' or 'equatorial', Sun at the origin), distance, apparent and absolute magnitude, "
        "V-band luminosity, temperature from B−V, true blackbody colour and spectral type. Filters: stars "
        "brighter than max_magnitude, plus every catalogued star within nearby_ly; name= finds one star. "
        "Example: name='Sirius'."
    ),
)
def star_catalog(max_magnitude: float = 6.5, nearby_ly: float = 0.0, max_distance_ly: float = 1e6,
                 frame: str = "ecliptic", limit: int = 20000, name: str | None = None) -> dict:
    rot = _frame(frame)
    if not -2 <= max_magnitude <= 7.0:
        raise ValueError("max_magnitude must be between -2 and 7 (the catalogue stops at magnitude 7)")
    if not 0 <= nearby_ly <= 100 or max_distance_ly <= 0 or not 1 <= limit <= 20000:
        raise ValueError("nearby_ly must be 0..100 (catalogue completeness), max_distance_ly > 0, limit 1..20000")
    s = star_table()
    if name is not None:
        key = name.strip().lower()
        idx = [i for i, n in enumerate(s["names"]) if n.lower() == key] or \
              [i for i, n in enumerate(s["names"]) if s["proper"][i] and key in n.lower()]
        if not idx:
            raise ValueError(f"no star named {name!r} in the catalogue (try a proper name such as 'Vega')")
        sel = np.array(idx[:10])
    else:
        mask = ((s["mag"] <= max_magnitude) | (s["dist_ly"] <= nearby_ly)) & (s["dist_ly"] <= max_distance_ly)
        sel = np.flatnonzero(mask)
        sel = sel[np.argsort(s["mag"][sel])][:limit]
    xyz = (rot @ s["unit"][:, sel]) * s["dist_ly"][sel]
    temp = s["temp"][sel]
    lum = 10 ** (0.4 * (4.83 - s["abs_mag"][sel]))
    rgb = blackbody_rgb(temp)
    return {
        "result": {
            "count": int(sel.size), "frame": frame,
            "name": [s["names"][i] for i in sel], "proper_name": [s["proper"][i] for i in sel],
            "constellation": [s["con"][i] for i in sel], "spectral_type": [s["spect"][i] for i in sel],
            "x_ly": xyz[0].round(4).tolist(), "y_ly": xyz[1].round(4).tolist(), "z_ly": xyz[2].round(4).tolist(),
            "distance_ly": s["dist_ly"][sel].round(4).tolist(), "apparent_magnitude": s["mag"][sel].tolist(),
            "absolute_magnitude": s["abs_mag"][sel].tolist(), "luminosity_solar": lum.round(6).tolist(),
            "temperature_k": temp.round(0).tolist(), "color": _hex(rgb),
        },
        "units": "positions and distances in light years, luminosity in solar V-band luminosities, temperature in K",
        "assumptions": [
            "HYG v4.1 catalogue: all stars to magnitude 7 plus the Gliese stars within 30 pc; parallax distances",
            "Luminosity is V-band (no bolometric correction); temperature from B−V (Ballesteros 2012), "
            "or from the spectral class when B−V is missing",
            "Colours are blackbody colours in sRGB, normalised to the brightest channel",
        ],
    }


# ---------- Milky Way ----------
R0_KPC = 8.122      # Sun–Galactic-centre distance (GRAVITY 2018)
V0_KM_S = 229.0     # circular speed at the Sun (Eilers et al. 2019)
Z0_KPC = 0.0208     # Sun above the plane (Bennett & Bovy 2019)
PITCH_DEG = 12.0
ARMS = ["Sagittarius–Carina", "Scutum–Centaurus", "Norma–Outer", "Perseus"]


def _mn_shape(r):  # Miyamoto–Nagai disc (a = 3 kpc, b = 0.28 kpc), midplane v²
    return r ** 2 / (r ** 2 + 3.28 ** 2) ** 1.5


def _nfw_shape(r):  # NFW halo, scale radius 16 kpc
    x = r / 16.0
    return (np.log1p(x) - x / (1 + x)) / r


def _bulge_shape(r):  # power-law bulge ρ ∝ r^-1.8 exp(-(r/1.9)²): v² ∝ M(<r)/r
    r = np.atleast_1d(r)
    m = np.array([integrate.quad(lambda s: s ** 0.2 * math.exp(-(s / 1.9) ** 2), 0, ri)[0] for ri in r])
    return m / r


def circular_velocity(r_kpc: np.ndarray) -> np.ndarray:
    """Circular speed (km/s) of the three-component model; 5 %/60 %/35 % of the radial force at R0 comes
    from bulge/disc/halo (Bovy 2015, MWPotential2014 proportions), normalised to V0 at R0."""
    r = np.atleast_1d(np.asarray(r_kpc, float))
    v2 = 0.0
    for frac, shape in ((0.05, _bulge_shape), (0.60, _mn_shape), (0.35, _nfw_shape)):
        v2 = v2 + frac * V0_KM_S ** 2 * shape(r) / shape(np.array([R0_KPC]))
    return np.sqrt(v2)


def arm_radius(arm: int, phi: np.ndarray) -> np.ndarray:
    """Radius (kpc) of spiral arm `arm` at Galactocentric azimuth phi (radians, Sun at phi = π)."""
    return 6.6 * np.exp((phi - math.pi - arm * math.pi / 2) * math.tan(math.radians(PITCH_DEG)))


@lru_cache(maxsize=None)
def globular_table() -> list[dict]:
    with (DATA / "globulars.csv").open() as f:
        return list(csv.DictReader(f))


def galactocentric(unit_eq: np.ndarray, dist_kpc: np.ndarray) -> np.ndarray:
    """Equatorial unit vectors + distance → Galactocentric kpc (x toward the GC from the Sun, Sun at x = −R0)."""
    g = EQ_TO_GAL @ unit_eq * dist_kpc
    return np.array([g[0] - R0_KPC, g[1], g[2] + Z0_KPC])


@tool(
    domain="physics",
    name="milky_way",
    description=(
        "Model of our Galaxy: Sun's position (8.12 kpc from the centre), the rotation curve from a bulge + disc + "
        "dark-halo mass model normalised to 229 km/s at the Sun, galactic year, enclosed mass, the spiral arms "
        "(logarithmic, 12° pitch) and bar, sample star positions with blackbody colours for rendering, and the "
        "real globular clusters. Positions in kpc, Galactocentric, Sun at (−8.12, 0, 0.02)."
    ),
)
def milky_way(n_points: int = 30000, seed: int = 7) -> dict:
    if not 100 <= n_points <= 200000:
        raise ValueError("n_points must be 100..200000")
    rng = np.random.default_rng(seed)
    tan_p = math.tan(math.radians(PITCH_DEG))
    n_arm, n_disc, n_bulge, n_bar, n_halo = (int(f * n_points) for f in (0.42, 0.30, 0.10, 0.12, 0.03))
    n_spur = n_points - n_arm - n_disc - n_bulge - n_bar - n_halo
    pts, temps, comp = [], [], []

    # Spiral arms: from the bar ends (~3.5 kpc) out to ~17 kpc along each log spiral
    arm = rng.integers(0, 4, n_arm)
    r_in, r_out = 3.3, 17.0
    phi0 = math.pi + arm * math.pi / 2 + np.log(r_in / 6.6) / tan_p
    phi1 = math.pi + arm * math.pi / 2 + np.log(r_out / 6.6) / tan_p
    u = rng.random(n_arm) ** 1.6  # denser toward the inner parts, like an exponential disc
    phi = phi0 + u * (phi1 - phi0)
    rad = arm_radius(arm, phi) + rng.normal(0, 0.35, n_arm)
    pts.append(np.array([rad * np.cos(phi), rad * np.sin(phi), rng.normal(0, 0.09, n_arm)]))
    young = rng.random(n_arm) < 0.55
    temps.append(np.where(young, rng.uniform(9000, 30000, n_arm), rng.uniform(4800, 7500, n_arm)))
    comp.append(np.where(young, 2, 3))
    # Local (Orion) spur: a short arm segment passing the Sun
    phi_s = math.pi + rng.uniform(-0.35, 0.35, n_spur)
    r_s = 8.3 * np.exp((phi_s - math.pi) * math.tan(math.radians(11))) + rng.normal(0, 0.25, n_spur)
    pts.append(np.array([r_s * np.cos(phi_s), r_s * np.sin(phi_s), rng.normal(0, 0.08, n_spur)]))
    temps.append(rng.uniform(6000, 25000, n_spur))
    comp.append(np.full(n_spur, 4))
    # Smooth exponential disc (scale length 2.6 kpc, scale height 0.3 kpc)
    rd = rng.gamma(2.0, 2.6, n_disc) + 1.0
    pd = rng.uniform(0, 2 * math.pi, n_disc)
    pts.append(np.array([rd * np.cos(pd), rd * np.sin(pd), rng.laplace(0, 0.3, n_disc)]))
    temps.append(rng.uniform(3500, 6500, n_disc))
    comp.append(np.full(n_disc, 1))
    # Bar: 5 kpc half length, 27° from the Sun–centre line, near end at positive longitude
    ang = math.radians(180 - 27)
    bx, by, bz = rng.normal(0, 1.7, n_bar), rng.normal(0, 0.55, n_bar), rng.normal(0, 0.3, n_bar)
    pts.append(np.array([bx * math.cos(ang) - by * math.sin(ang), bx * math.sin(ang) + by * math.cos(ang), bz]))
    temps.append(rng.uniform(3300, 5000, n_bar))
    comp.append(np.full(n_bar, 0))
    # Bulge: flattened spheroid
    rb = rng.exponential(0.6, n_bulge)
    v = rng.normal(size=(3, n_bulge))
    v /= np.linalg.norm(v, axis=0)
    pts.append(v * rb * np.array([[1], [1], [0.6]]))
    temps.append(rng.uniform(3300, 5200, n_bulge))
    comp.append(np.full(n_bulge, 0))
    # Stellar halo
    rh = rng.exponential(8.0, n_halo) + 2
    v = rng.normal(size=(3, n_halo))
    v /= np.linalg.norm(v, axis=0)
    pts.append(v * rh)
    temps.append(rng.uniform(3500, 6000, n_halo))
    comp.append(np.full(n_halo, 5))

    p = np.concatenate(pts, axis=1)
    t = np.concatenate(temps)
    r_curve = np.round(np.concatenate([np.linspace(0.25, 3, 12), np.linspace(3.5, 30, 54)]), 3)
    v_curve = circular_velocity(r_curve)
    v0 = float(circular_velocity(np.array([R0_KPC]))[0])
    year_myr = 2 * math.pi * R0_KPC * KPC_M / (v0 * 1000) / (GYR_S / 1000)
    m_enclosed = lambda r: float(circular_velocity(np.array([r]))[0] * 1000) ** 2 * r * KPC_M / G / M_SUN
    gc = globular_table()
    gcp = galactocentric(radec_unit([float(g["ra_h"]) for g in gc], [float(g["dec_deg"]) for g in gc]),
                         np.array([float(g["dist_ly"]) for g in gc]) / PC_LY / 1000)
    in_mw = np.linalg.norm(gcp, axis=0) < 150  # drop clusters that belong to the Magellanic Clouds
    arm_lines = []
    for k, nm in enumerate(ARMS):
        ph = np.linspace(math.pi + k * math.pi / 2 + math.log(r_in / 6.6) / tan_p,
                         math.pi + k * math.pi / 2 + math.log(r_out / 6.6) / tan_p, 120)
        rr = arm_radius(k, ph)
        arm_lines.append({"name": nm, "points_kpc": np.array([rr * np.cos(ph), rr * np.sin(ph), 0 * ph]).T.round(3).tolist()})
    return {
        "result": {
            "sun_position_kpc": [-R0_KPC, 0.0, Z0_KPC], "sun_distance_kpc": R0_KPC,
            "galactic_to_ecliptic": (EQ_TO_ECL @ EQ_TO_GAL.T).round(10).tolist(),
            "galactic_to_equatorial": EQ_TO_GAL.T.round(10).tolist(),
            "sun_distance_ly": R0_KPC * 1000 * PC_LY, "circular_speed_at_sun_km_s": v0,
            "galactic_year_myr": year_myr,
            "mass_within_sun_orbit_msun": m_enclosed(R0_KPC), "mass_within_50kpc_msun": m_enclosed(50.0),
            "disc_diameter_ly": 2 * r_out * 1000 * PC_LY,
            "rotation_curve": {"r_kpc": r_curve.tolist(), "v_km_s": v_curve.round(2).tolist()},
            "arms": arm_lines,
            "points": {"x_kpc": p[0].round(3).tolist(), "y_kpc": p[1].round(3).tolist(), "z_kpc": p[2].round(3).tolist(),
                       "color": _hex(blackbody_rgb(t)), "component": np.concatenate(comp).tolist(),
                       "component_names": ["bulge/bar", "thin disc", "arm (young stars)", "arm (older stars)",
                                           "Orion spur", "stellar halo"]},
            "globular_clusters": {
                "name": [g["name"] for g, keep in zip(gc, in_mw) if keep],
                "x_kpc": gcp[0][in_mw].round(3).tolist(), "y_kpc": gcp[1][in_mw].round(3).tolist(),
                "z_kpc": gcp[2][in_mw].round(3).tolist()},
        },
        "units": "positions in kpc (Galactocentric: x from the Sun toward the centre), speeds in km/s, masses in solar masses",
        "assumptions": [
            f"R0 = {R0_KPC} kpc (GRAVITY 2018), circular speed {V0_KM_S} km/s at the Sun (Eilers et al. 2019)",
            "Rotation curve: power-law bulge + Miyamoto–Nagai disc + NFW halo in MWPotential2014 proportions (Bovy 2015)",
            "Enclosed mass uses the spherical estimate M = v²R/G",
            "Arm geometry is schematic: four logarithmic arms with a 12° pitch placed through the observed arm "
            "tangencies; sample stars illustrate density, they are not individual real stars",
            "Globular clusters are real (Harris-type catalogue positions via Celestia)",
        ],
    }


# ---------- galaxies ----------
@lru_cache(maxsize=None)
def galaxy_table() -> dict:
    with (DATA / "galaxies.csv").open() as f:
        rows = [r for r in csv.DictReader(f) if r["name"] != "Milky Way"]
    return {"name": [r["name"] for r in rows], "type": [r["type"] for r in rows],
            "unit": radec_unit([float(r["ra_h"]) for r in rows], [float(r["dec_deg"]) for r in rows]),
            "dist_ly": np.array([float(r["dist_ly"]) for r in rows]),
            "radius_ly": np.array([float(r["radius_ly"]) for r in rows]),
            "abs_mag": np.array([float(r["abs_mag"]) for r in rows])}


@tool(
    domain="physics",
    name="galaxy_catalog",
    description=(
        "Real galaxies with measured distances (~11,000: Local Group, Virgo cluster and beyond to ~2 billion "
        "light years): 3D positions in millions of light years (galactic frame, Sun at the origin), Hubble type, "
        "radius, absolute magnitude, and the Hubble-law recession speed and redshift. name= finds a galaxy, "
        "e.g. name='Andromeda Galaxy'."
    ),
)
def galaxy_catalog(max_distance_mly: float = 3000.0, limit: int = 12000, name: str | None = None,
                   h0: float = 67.66) -> dict:
    if max_distance_mly <= 0 or not 1 <= limit <= 12000 or not 40 <= h0 <= 100:
        raise ValueError("max_distance_mly must be > 0, limit 1..12000 and h0 40..100 km/s/Mpc")
    g = galaxy_table()
    if name is not None:
        key = name.strip().lower()
        sel = np.array([i for i, n in enumerate(g["name"]) if n.lower() == key or key in n.lower()][:10], int)
        if sel.size == 0:
            raise ValueError(f"no galaxy named {name!r} (try 'Andromeda Galaxy', 'M 87', 'LMC')")
    else:
        sel = np.flatnonzero(g["dist_ly"] <= max_distance_mly * 1e6)
        sel = sel[np.argsort(g["dist_ly"][sel])][:limit]
    d_mly = g["dist_ly"][sel] / 1e6
    xyz = (EQ_TO_GAL @ g["unit"][:, sel]) * d_mly
    v = h0 * d_mly / PC_LY  # km/s: H0 [km/s/Mpc] × d [Mpc], with d [Mpc] = d [Mly] / 3.2616
    z = np.sqrt((1 + v / C_KM_S) / (1 - np.minimum(v / C_KM_S, 0.99))) - 1
    return {
        "result": {
            "count": int(sel.size), "frame": "galactic",
            "name": [g["name"][i] for i in sel], "type": [g["type"][i] for i in sel],
            "x_mly": xyz[0].round(5).tolist(), "y_mly": xyz[1].round(5).tolist(), "z_mly": xyz[2].round(5).tolist(),
            "distance_mly": d_mly.round(5).tolist(), "radius_ly": g["radius_ly"][sel].round(0).tolist(),
            "absolute_magnitude": np.nan_to_num(g["abs_mag"][sel], nan=-18.0).tolist(),
            "hubble_velocity_km_s": [None if d < 30 else round(float(x), 1) for d, x in zip(d_mly, v)],
            "redshift": [None if d < 30 else round(float(x), 5) for d, x in zip(d_mly, z)],
        },
        "units": "positions and distances in millions of light years (Mly), radii in light years, velocities in km/s",
        "assumptions": [
            "Distances from the Celestia galaxy catalogue (NED-1D averages, RC3, Karachentsev+ 2004, CfA redshifts)",
            f"Recession speed from Hubble's law v = H0·d with H0 = {h0} km/s/Mpc (peculiar velocities ignored), "
            "redshift from the relativistic Doppler formula; left empty within 30 Mly, where gravity of the Local "
            "Group and nearby groups dominates (Andromeda is actually approaching us)",
        ],
    }


# ---------- cosmology ----------
def _friedmann(omega_m: float, omega_r: float, omega_l: float):
    omega_k = 1 - omega_m - omega_r - omega_l
    # (a·H/H0)² = Ωr/a² + Ωm/a + Ωk + ΩΛ a²
    return lambda a: math.sqrt(omega_r + omega_m * a + omega_k * a * a + omega_l * a ** 4), omega_k


@tool(
    domain="physics",
    name="cosmology",
    description=(
        "ΛCDM cosmology from the Friedmann equation (Planck 2018 defaults: H0 = 67.66 km/s/Mpc, Ωm = 0.3111, "
        "flat): age of the universe, and for redshift z the lookback time, age then, comoving, luminosity and "
        "angular-diameter distances; also the radius of the observable universe (particle horizon), the Hubble "
        "radius, the event horizon, the CMB distance and the critical density. Example: z=1."
    ),
)
def cosmology(z: float = 1.0, h0: float = 67.66, omega_m: float = 0.3111, omega_lambda: float | None = None,
              omega_r: float = 9.14e-5) -> dict:
    if not 0 <= z <= 1e4:
        raise ValueError("z must be between 0 and 10000")
    if not 20 <= h0 <= 150 or not 0 < omega_m <= 2 or not 0 <= omega_r < 0.01:
        raise ValueError("h0 must be 20..150, omega_m in (0, 2], omega_r in [0, 0.01)")
    ol = 1 - omega_m - omega_r if omega_lambda is None else omega_lambda
    if not -1 <= ol <= 2:
        raise ValueError("omega_lambda must be between -1 and 2")
    e, ok = _friedmann(omega_m, omega_r, ol)
    if min(e(a) for a in np.linspace(1e-6, 1, 400)) <= 0:
        raise ValueError("these parameters give a universe that recollapses or never had a big bang")
    hubble_time_gyr = MPC_KM / h0 / GYR_S
    hubble_radius_gly = C_KM_S / h0 * PC_LY / 1000  # c/H0 in Mpc → Mly → Gly
    quad = lambda f, lo, hi: integrate.quad(f, lo, hi, limit=200, epsabs=0, epsrel=1e-10)[0]
    age = lambda a: hubble_time_gyr * quad(lambda x: x / e(x), 0, a)  # dt = da / (a H)
    chi = lambda a0, a1: quad(lambda x: 1 / e(x), a0, a1)  # comoving distance in c/H0 units
    a_z = 1 / (1 + z)

    def transverse(x):
        if abs(ok) < 1e-9:
            return x
        s = math.sqrt(abs(ok))
        return math.sinh(s * x) / s if ok > 0 else math.sin(s * x) / s

    dc = chi(a_z, 1) * hubble_radius_gly
    dm = transverse(chi(a_z, 1)) * hubble_radius_gly
    age_now, age_then = age(1), age(a_z)
    horizon = chi(0, 1) * hubble_radius_gly
    event = quad(lambda x: 1 / e(x), 1, np.inf) * hubble_radius_gly if ol > 0 else float("inf")
    z_cmb = 1089.8
    d_cmb = chi(1 / (1 + z_cmb), 1) * hubble_radius_gly
    rho_c = 3 * (h0 / MPC_KM) ** 2 / (8 * math.pi * G)
    ly_m = 9.4607304725808e15
    r_m = horizon * 1e9 * ly_m
    shells = []
    for zs in (0.01, 0.1, 0.5, 1, 2, 3, 6, 10, 20, 100, z_cmb):
        a_s = 1 / (1 + zs)
        shells.append({"z": zs, "comoving_distance_gly": chi(a_s, 1) * hubble_radius_gly,
                       "lookback_time_gyr": age_now - age(a_s), "age_then_gyr": age(a_s)})
    gly_to_mpc = 1000 / PC_LY
    return {
        "result": {
            "z": z, "scale_factor": a_z, "hubble_parameter_km_s_mpc": h0 * e(a_z) / a_z ** 2,
            "age_now_gyr": age_now, "age_then_gyr": age_then, "lookback_time_gyr": age_now - age_then,
            "comoving_distance_gly": dc, "comoving_distance_mpc": dc * gly_to_mpc,
            "luminosity_distance_gly": dm * (1 + z), "angular_diameter_distance_gly": dm / (1 + z),
            "light_travel_distance_gly": age_now - age_then,
            "observable_universe_radius_gly": horizon, "observable_universe_diameter_gly": 2 * horizon,
            "hubble_radius_gly": hubble_radius_gly, "event_horizon_gly": event,
            "cmb_redshift": z_cmb, "cmb_comoving_distance_gly": d_cmb,
            "critical_density_kg_m3": rho_c,
            "matter_mass_in_observable_universe_kg": omega_m * rho_c * 4 / 3 * math.pi * r_m ** 3,
            "omega_lambda": ol, "omega_k": ok, "shells": shells,
        },
        "units": "distances in billions of light years (Gly) unless marked Mpc, times in Gyr, density in kg/m³",
        "assumptions": [
            "Homogeneous ΛCDM universe (Friedmann equation) with constant dark-energy density",
            f"H0 = {h0} km/s/Mpc, Ωm = {omega_m}, Ωr = {omega_r} (photons + massless neutrinos), ΩΛ = {ol:.4f}",
            "The observable universe's radius is the comoving particle horizon; the CMB was emitted at z = 1089.8",
        ],
    }
