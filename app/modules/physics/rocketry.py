"""Rocket building and flight: a parts catalogue, staged-rocket design analysis (Δv, TWR, burn times) and a
2D flight integrator around Earth, the Moon or Mars with gravity, pressure-dependent thrust, drag in a
rotating atmosphere, staging, parachutes, landing and orbit prediction.

The flight tool is a pure step function: the caller passes the state and the pilot's controls and gets the
state dt seconds later, so an interactive simulator can call it repeatedly (with time warp)."""
import math
import re

import numpy as np
from scipy.integrate import solve_ivp

from app.core.registry import tool
from app.modules.physics.ephemeris import J2000_JD, OBLIQUITY, ROTATION, heliocentric, julian_date, moon_geocentric

G0 = 9.80665

# Part catalogue. Masses kg, propellant kg, thrust N, Isp s, sizes m. Engines can be clustered with "count".
# Engines carry a size class (small < 100 kN, medium < 500 kN, large < 1.5 MN, heavy above, by vacuum thrust);
# their numbers follow real engines of each kind (named generically).
PARTS: dict[str, dict] = {
    "capsule": {"name": "Crew capsule", "category": "command", "mass": 6000, "height": 3.6, "width": 3.2, "crew": 3},
    "probe": {"name": "Probe core", "category": "command", "mass": 250, "height": 1.0, "width": 1.4},
    "lander": {"name": "Lunar lander cabin", "category": "command", "mass": 2500, "height": 2.6, "width": 3.2, "crew": 2},
    # satellites (example payloads; users can design their own with satellite_design)
    "satellite": {"name": "Satellite (generic)", "category": "satellite", "mass": 1500, "height": 3.0, "width": 2.6},
    "sat_cubesat": {"name": "CubeSat 6U", "category": "satellite", "mass": 12, "height": 0.4, "width": 0.3},
    "sat_earthobs": {"name": "Earth-observation satellite", "category": "satellite", "mass": 1100, "height": 3.2, "width": 2.0},
    "sat_nav": {"name": "Navigation satellite", "category": "satellite", "mass": 2200, "height": 2.6, "width": 2.4},
    "sat_comms": {"name": "Geostationary comsat (apogee engine)", "category": "satellite", "mass": 2500, "prop": 3000, "height": 5.0,
                  "width": 3.0, "thrust_sl": 200.0, "thrust_vac": 450.0, "isp_sl": 140, "isp_vac": 318},
    "sat_telescope": {"name": "Space telescope", "category": "satellite", "mass": 11000, "height": 13.0, "width": 4.2},
    "sat_lunar": {"name": "Lunar orbiter (with engine)", "category": "satellite", "mass": 650, "prop": 900, "height": 2.4,
                  "width": 2.2, "thrust_sl": 200.0, "thrust_vac": 450.0, "isp_sl": 140, "isp_vac": 318},
    # tanks
    "tank_xs": {"name": "Fuel tank XS", "category": "tank", "mass": 400, "prop": 4000, "height": 2.2, "width": 1.3},
    "tank_s": {"name": "Fuel tank S", "category": "tank", "mass": 1200, "prop": 12000, "height": 3.0, "width": 3.2},
    "tank_m": {"name": "Fuel tank M", "category": "tank", "mass": 2500, "prop": 30000, "height": 6.0, "width": 3.2},
    "tank_l": {"name": "Fuel tank L", "category": "tank", "mass": 5000, "prop": 70000, "height": 12.0, "width": 3.2},
    "tank_xl": {"name": "Fuel tank XL", "category": "tank", "mass": 12000, "prop": 180000, "height": 24.0, "width": 3.7},
    # small engines
    "engine_micro": {"name": "Spark micro engine", "category": "engine", "class": "small", "mass": 35, "height": 0.9, "width": 0.6,
                     "thrust_sl": 24e3, "thrust_vac": 25.9e3, "isp_sl": 303, "isp_vac": 327},
    "engine_lander": {"name": "Hopper lander engine", "category": "engine", "class": "small", "mass": 150, "height": 1.2, "width": 1.0,
                      "thrust_sl": 40e3, "thrust_vac": 45e3, "isp_sl": 290, "isp_vac": 320},
    "engine_kick": {"name": "Nudge hypergolic vacuum engine", "category": "engine", "class": "small", "mass": 110, "height": 2.0,
                    "width": 1.3, "thrust_sl": 12e3, "thrust_vac": 29e3, "isp_sl": 134, "isp_vac": 324},
    # medium engines
    "engine_medium": {"name": "Sparrow kerolox engine", "category": "engine", "class": "medium", "mass": 350, "height": 2.2, "width": 1.2,
                      "thrust_sl": 270e3, "thrust_vac": 300e3, "isp_sl": 285, "isp_vac": 317},
    "engine_cryo_vac": {"name": "Cryo-V hydrolox vacuum engine", "category": "engine", "class": "medium", "mass": 300, "height": 4.2,
                        "width": 2.2, "thrust_sl": 30e3, "thrust_vac": 110e3, "isp_sl": 127, "isp_vac": 465},
    # large engines
    "engine_booster": {"name": "Kestrel booster engine", "category": "engine", "class": "large", "mass": 470, "height": 2.5, "width": 1.2,
                       "thrust_sl": 845e3, "thrust_vac": 914e3, "isp_sl": 282, "isp_vac": 311},
    "engine_vacuum": {"name": "Kestrel-V vacuum engine", "category": "engine", "class": "large", "mass": 490, "height": 3.6, "width": 2.0,
                      "thrust_sl": 420e3, "thrust_vac": 981e3, "isp_sl": 150, "isp_vac": 348},
    "engine_hydrolox": {"name": "Cryo-2 hydrolox engine", "category": "engine", "class": "large", "mass": 2100, "height": 3.4, "width": 2.1,
                        "thrust_sl": 960e3, "thrust_vac": 1310e3, "isp_sl": 318, "isp_vac": 434},
    # heavy engines
    "engine_methalox": {"name": "Condor methalox engine", "category": "engine", "class": "heavy", "mass": 1630, "height": 3.1, "width": 1.3,
                        "thrust_sl": 2256e3, "thrust_vac": 2394e3, "isp_sl": 327, "isp_vac": 347},
    "engine_heavy": {"name": "Titan heavy engine", "category": "engine", "class": "heavy", "mass": 5400, "height": 3.6, "width": 3.2,
                     "thrust_sl": 3830e3, "thrust_vac": 4150e3, "isp_sl": 311, "isp_vac": 338},
    "engine_f1": {"name": "Colossus heavy engine", "category": "engine", "class": "heavy", "mass": 8400, "height": 5.8, "width": 3.7,
                  "thrust_sl": 6770e3, "thrust_vac": 7825e3, "isp_sl": 263, "isp_vac": 304},
    # structure and aerodynamics
    "decoupler": {"name": "Stage decoupler", "category": "structural", "mass": 150, "height": 0.5, "width": 3.2},
    "interstage_s": {"name": "Interstage S", "category": "structural", "mass": 80, "height": 0.8, "width": 1.3},
    "interstage": {"name": "Interstage (covers the upper-stage engine)", "category": "structural", "mass": 600, "height": 1.5, "width": 3.7},
    "nose": {"name": "Nose cone", "category": "aero", "mass": 300, "height": 3.0, "width": 3.2},
    "fairing_s": {"name": "Payload fairing S", "category": "aero", "mass": 50, "height": 1.6, "width": 1.4},
    "fairing": {"name": "Payload fairing", "category": "aero", "mass": 1000, "height": 4.0, "width": 3.8},
    "fairing_xl": {"name": "Payload fairing XL", "category": "aero", "mass": 2000, "height": 6.0, "width": 5.2},
    "parachute": {"name": "Parachute", "category": "recovery", "mass": 120, "height": 0.6, "width": 1.6},
    "legs": {"name": "Landing legs", "category": "recovery", "mass": 250, "height": 0.6, "width": 3.6},
}
FAIRINGS = {"fairing_s", "fairing", "fairing_xl"}
ENGINE_CLASSES = (("small", 100e3), ("medium", 500e3), ("large", 1500e3), ("heavy", float("inf")))


def engine_class(thrust_vac: float) -> str:
    return next(name for name, limit in ENGINE_CLASSES if thrust_vac < limit)


BODIES = {
    # radius m, μ m³/s², sidereal rotation rad/s (negative = surface moves toward +x, i.e. "east" is right),
    # sea-level density kg/m³, scale height m, top of atmosphere m
    "earth": {"name": "Earth", "radius": 6_371_000.0, "mu": 3.986004418e14, "omega": -7.2921159e-5, "rho0": 1.225, "H": 8_500.0, "top": 140_000.0, "sound": 340.0},
    "moon": {"name": "Moon", "radius": 1_737_400.0, "mu": 4.9048695e12, "omega": -2.6617e-6, "rho0": 0.0, "H": 1.0, "top": 0.0, "sound": 1.0},
    "mars": {"name": "Mars", "radius": 3_389_500.0, "mu": 4.282837e13, "omega": -7.088218e-5, "rho0": 0.020, "H": 11_100.0, "top": 120_000.0, "sound": 240.0},
}
# The Moon moves around the Earth on a circular orbit in the flight plane (Earth flights only)
MOON_DISTANCE = 384_400e3
MOON_RADIUS = BODIES["moon"]["radius"]
MU_MOON = BODIES["moon"]["mu"]
MOON_RATE = -math.sqrt((BODIES["earth"]["mu"] + MU_MOON) / MOON_DISTANCE**3)  # rad/s, same sense as Earth's spin
MOON_SOI = MOON_DISTANCE * (MU_MOON / BODIES["earth"]["mu"]) ** 0.4  # patched-conic sphere of influence (~66,000 km)
SAFE_LANDING = 10.0  # m/s touchdown speed survivable without legs (capsule splashdown class)
SAFE_LANDING_LEGS = 16.0
CHUTE_CDA = 1500.0  # m², deployed parachute drag area × Cd (Apollo-class main chutes)


def _body(name: str) -> dict:
    if name not in BODIES:
        raise ValueError(f"body must be one of {', '.join(BODIES)}")
    return BODIES[name]


def _custom(custom_parts: dict | None) -> dict[str, dict]:
    """Validate user-designed parts: {'custom_xxx': {'category': 'engine'|'satellite', 'name', 'mass', 'height',
    'width', engines: 'thrust_sl', 'thrust_vac', 'isp_sl', 'isp_vac'; satellites may add 'prop' and propulsion}}."""
    if not custom_parts:
        return {}
    if not isinstance(custom_parts, dict) or len(custom_parts) > 30:
        raise ValueError("custom_parts must be a dict of at most 30 designs")
    out = {}
    for cid, spec in custom_parts.items():
        if not re.fullmatch(r"custom_[a-z0-9_]{1,40}", str(cid)) or not isinstance(spec, dict):
            raise ValueError(f"custom part ids must look like 'custom_my_engine' (got {cid!r})")
        cat = spec.get("category")
        if cat not in ("engine", "satellite"):
            raise ValueError("custom parts must have category 'engine' or 'satellite'")
        keys = ["mass", "height", "width"] + (["thrust_sl", "thrust_vac", "isp_sl", "isp_vac"] if cat == "engine" else [])
        opt = ["prop", "thrust_sl", "thrust_vac", "isp_sl", "isp_vac"] if cat == "satellite" else []
        try:
            vals = {k: float(spec[k]) for k in keys}
            vals.update({k: float(spec[k]) for k in opt if spec.get(k) is not None})
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"custom part {cid} needs numeric {', '.join(keys)}") from None
        if not (0 < vals["mass"] <= 5e5 and 0.05 <= vals["height"] <= 80 and 0.05 <= vals["width"] <= 15):
            raise ValueError(f"custom part {cid}: mass 0..500 t, height 0.05..80 m, width 0.05..15 m")
        if "thrust_vac" in vals:
            if not (0 < vals.get("thrust_sl", 0) <= vals["thrust_vac"] <= 5e7 and 0 < vals.get("isp_sl", 0) <= vals["isp_vac"] <= 10000):
                raise ValueError(f"custom part {cid}: need 0 < thrust_sl ≤ thrust_vac ≤ 50 MN and 0 < isp_sl ≤ isp_vac ≤ 10000 s")
        if vals.get("prop", 0) < 0:
            raise ValueError(f"custom part {cid}: propellant cannot be negative")
        out[cid] = {"name": str(spec.get("name") or cid)[:48], "category": cat, "custom": True, **vals}
        if cat == "engine":
            out[cid]["class"] = engine_class(vals["thrust_vac"])
    return out


def _parse(parts: list, custom_parts: dict | None = None) -> list[dict]:
    if not isinstance(parts, list) or not parts:
        raise ValueError("parts must be a non-empty list, bottom to top, e.g. [{'part': 'engine_booster', 'count': 9}, {'part': 'tank_l'}]")
    if len(parts) > 60:
        raise ValueError("at most 60 parts")
    catalogue = {**PARTS, **_custom(custom_parts)}
    out = []
    for p in parts:
        pid = p.get("part") if isinstance(p, dict) else p
        count = int(p.get("count", 1)) if isinstance(p, dict) else 1
        if pid not in catalogue:
            raise ValueError(f"unknown part {pid!r}; choose from {', '.join(PARTS)} or a custom part")
        if not 1 <= count <= 9 or (count > 1 and catalogue[pid]["category"] != "engine"):
            raise ValueError("count must be 1..9 and only engines can be clustered")
        out.append({**catalogue[pid], "id": pid, "count": count})
    return out


def _stages(parts: list[dict]) -> list[dict]:
    """Split the stack (bottom → top) at decouplers; stage 0 fires first. The decoupler goes with the lower stage."""
    stages, cur = [], []
    for p in parts:
        cur.append(p)
        if p["id"] == "decoupler":
            stages.append(cur)
            cur = []
    if cur:
        stages.append(cur)
    out = []
    for i, s in enumerate(stages):
        engines = [p for p in s if p.get("thrust_vac")]
        thrust_vac = sum(p["thrust_vac"] * p["count"] for p in engines)
        thrust_sl = sum(p["thrust_sl"] * p["count"] for p in engines)
        flow = sum(p["thrust_vac"] * p["count"] / (p["isp_vac"] * G0) for p in engines)  # kg/s at full throttle
        out.append({
            "parts": [p["id"] for p in s],
            "dry": sum(p["mass"] * p["count"] for p in s),
            "prop": sum(p.get("prop", 0) for p in s),
            "thrust_vac": thrust_vac, "thrust_sl": thrust_sl, "mdot": flow,
            "isp_vac": thrust_vac / (flow * G0) if flow else 0.0,
            "isp_sl": thrust_sl / (flow * G0) if flow else 0.0,
            "height": sum(p["height"] for p in s),
            "width": max(p["width"] for p in s),
            "nose": any(p["id"] == "nose" for p in s),
            "fairing_mass": sum(p["mass"] for p in s if p["id"] in FAIRINGS),
            "interstage": any(p["id"].startswith("interstage") for p in s),
            "bottom_engine": i > 0 and bool(s[0].get("thrust_vac")),  # an upper-stage engine at the separation plane
            "satellites": [p["name"] for p in s if p["category"] == "satellite"],
            "chute": any(p["id"] == "parachute" for p in s),
            "legs": any(p["id"] == "legs" for p in s),
            "command": any(p["category"] in ("command", "satellite") for p in s),
        })
    for i in range(1, len(out)):
        # an engine at the bottom of an upper stage is shielded by an interstage below it or a fairing around it
        out[i]["exposed_engine"] = out[i]["bottom_engine"] and not out[i - 1]["interstage"] and not out[i]["fairing_mass"]
    if out:
        out[0]["exposed_engine"] = False
    return out


def mission_budget() -> dict:
    """Typical Δv from the ground (m/s): 9,400 to low Earth orbit (includes gravity and drag losses), plus
    patched-conic manoeuvres computed from a 200 km parking orbit."""
    mu, r0 = BODIES["earth"]["mu"], BODIES["earth"]["radius"] + 200e3
    vc = math.sqrt(mu / r0)
    r_geo = 42_164e3
    at = (r0 + r_geo) / 2
    gto = math.sqrt(mu * (2 / r0 - 1 / at)) - vc
    geo = math.sqrt(mu / r_geo) - math.sqrt(mu * (2 / r_geo - 1 / at))
    atl = (r0 + MOON_DISTANCE) / 2
    tli = math.sqrt(mu * (2 / r0 - 1 / atl)) - vc
    v_moon = math.sqrt((mu + MU_MOON) / MOON_DISTANCE)
    v_inf = v_moon - math.sqrt(mu * (2 / MOON_DISTANCE - 1 / atl))
    r_llo = MOON_RADIUS + 100e3
    loi = math.sqrt(v_inf**2 + 2 * MU_MOON / r_llo) - math.sqrt(MU_MOON / r_llo)
    landing = math.sqrt(MU_MOON / r_llo) * 1.05 + 100.0  # descent from 100 km with ~5 % gravity loss and hover margin
    mars_vinf = 2945.0  # Hohmann Earth→Mars departure excess speed
    tmi = math.sqrt(mars_vinf**2 + 2 * mu / r0) - vc
    leo = 9400.0
    return {"low Earth orbit": leo, "geostationary orbit": leo + gto + geo, "lunar orbit": leo + tli + loi,
            "Moon landing": leo + tli + loi + landing, "Mars transfer": leo + tmi}


@tool(
    domain="physics",
    name="rocket_design",
    description=(
        "Analyse a rocket built from catalogue or custom parts (bottom to top; decouplers split stages): per-stage "
        "mass, propellant, thrust, Isp, Δv (sea level and vacuum, Tsiolkovsky), thrust-to-weight on the chosen body, "
        "burn time, totals, a mission Δv budget (orbit, GEO, Moon, Mars) and design warnings (missing fairing or "
        "interstage, vacuum nozzle at sea level, TWR). Parts: " + ", ".join(PARTS) + ". custom_parts adds engines or "
        "satellites made with rocket_engine_design / satellite_design. Example: parts=[{'part':'engine_booster',"
        "'count':9},{'part':'tank_xl'},{'part':'interstage'},{'part':'decoupler'},{'part':'engine_vacuum'},"
        "{'part':'tank_l'},{'part':'decoupler'},{'part':'sat_comms'},{'part':'fairing'}]."
    ),
)
def rocket_design(parts: list, body: str = "earth", custom_parts: dict | None = None) -> dict:
    b = _body(body)
    ps = _parse(parts, custom_parts)
    stages = _stages(ps)
    g = b["mu"] / b["radius"] ** 2
    rows, warnings = [], []
    total_vac = total_sl = 0.0
    for k, s in enumerate(stages):
        m0 = sum(x["dry"] + x["prop"] for x in stages[k:])
        m1 = m0 - s["prop"]
        dv_vac = s["isp_vac"] * G0 * math.log(m0 / m1) if s["mdot"] and s["prop"] else 0.0
        dv_sl = s["isp_sl"] * G0 * math.log(m0 / m1) if s["mdot"] and s["prop"] else 0.0
        rows.append({
            "stage": k, "parts": s["parts"], "mass_start": m0, "mass_end": m1, "propellant": s["prop"],
            "thrust_sl": s["thrust_sl"], "thrust_vac": s["thrust_vac"], "isp_sl": s["isp_sl"], "isp_vac": s["isp_vac"],
            "delta_v_vac": dv_vac, "delta_v_sl": dv_sl,
            "twr_surface": s["thrust_sl"] / (m0 * g) if b["rho0"] > 0 else s["thrust_vac"] / (m0 * g),
            "twr_vac": s["thrust_vac"] / (m0 * g),
            "burn_time": s["prop"] / s["mdot"] if s["mdot"] else None,
            "has_fairing": s["fairing_mass"] > 0, "interstage": s["interstage"],
        })
        total_vac += dv_vac
        total_sl += dv_sl
        if s["prop"] and not s["mdot"]:
            warnings.append(f"stage {k + 1} carries propellant but has no engine")
        if s["mdot"] and not s["prop"]:
            warnings.append(f"stage {k + 1} has engines but no fuel tank")
        if s["exposed_engine"]:
            warnings.append(f"stage {k + 1}'s engine is exposed to the airflow: add an interstage below its decoupler")
        if s["satellites"] and not s["fairing_mass"] and b["rho0"] > 0:
            warnings.append(f"{', '.join(s['satellites'])} would fly unprotected through the air: add a payload fairing on top")
    if not any(s["command"] for s in stages):
        warnings.append("no capsule, probe or satellite on top")
    if rows and rows[0]["twr_surface"] <= 1:
        warnings.append(f"lift-off thrust-to-weight {rows[0]['twr_surface']:.2f} ≤ 1: the rocket cannot leave the pad on {b['name']}")
    if stages and b["rho0"] > 0 and stages[0]["mdot"] and stages[0]["isp_sl"] < 0.6 * stages[0]["isp_vac"]:
        warnings.append("the first stage uses vacuum-optimised nozzles: at sea level their flow separates and thrust is poor")
    orbit_v = math.sqrt(b["mu"] / (b["radius"] + (200e3 if body == "earth" else 50e3)))
    budget = mission_budget() if body == "earth" else {"low orbit": {"moon": 1870.0, "mars": 4100.0}[body]}
    return {
        "result": {
            "stages": rows,
            "total_mass": sum(s["dry"] + s["prop"] for s in stages),
            "total_delta_v_vac": total_vac, "total_delta_v_sl": total_sl,
            "height": sum(p["height"] for p in ps), "width": max(p["width"] for p in ps),
            "reference_orbit_speed": orbit_v,
            "delta_v_to_orbit_estimate": {"earth": 9400.0, "moon": 1870.0, "mars": 4100.0}[body],
            "mission_delta_v": budget,
            "reachable": [m for m, dv in budget.items() if total_vac >= dv],
            "warnings": warnings,
        },
        "units": "masses in kg, thrust in N, Isp in s, Δv and speeds in m/s, time in s, sizes in m",
        "assumptions": ["Tsiolkovsky Δv per stage with all upper stages as payload",
                        "Clustered engines of different types combine by thrust-weighted Isp",
                        "Δv to orbit estimates include typical gravity and drag losses; beyond orbit the budget is "
                        "patched-conic (Hohmann to GEO, Hohmann-like trans-lunar injection, 100 km lunar orbit)"],
    }


# ------------------------------------------------------------------------------------------------
def _density(b: dict, alt: float) -> float:
    if b["rho0"] <= 0 or alt >= b["top"]:
        return 0.0
    return b["rho0"] * math.exp(-max(alt, 0.0) / b["H"])


def _elements(b: dict, x, y, vx, vy) -> dict:
    mu, R = b["mu"], b["radius"]
    r, v2 = math.hypot(x, y), vx * vx + vy * vy
    h = x * vy - y * vx
    energy = v2 / 2 - mu / r
    ex = (vy * h) / mu - x / r
    ey = (-vx * h) / mu - y / r
    e = math.hypot(ex, ey)
    out = {"eccentricity": e, "specific_energy": energy, "angular_momentum": h}
    if energy < 0:
        a = -mu / (2 * energy)
        out.update({"semi_major_axis": a, "apoapsis_alt": a * (1 + e) - R, "periapsis_alt": a * (1 - e) - R,
                    "period": 2 * math.pi * math.sqrt(a**3 / mu)})
    else:
        p = h * h / mu
        out.update({"semi_major_axis": None, "apoapsis_alt": None, "periapsis_alt": p / (1 + e) - R, "period": None})
    out["arg_periapsis"] = math.atan2(ey, ex)
    return out


def _predict(b: dict, x, y, vx, vy, n=240) -> list:
    """Points of the current conic ahead of the craft (ellipse or hyperbola arc) for the map view,
    stopping where it meets the surface."""
    el = _elements(b, x, y, vx, vy)
    mu, R, e, h = b["mu"], b["radius"], el["eccentricity"], el["angular_momentum"]
    if abs(h) < 1e-3:  # purely radial motion
        return [[x, y], [x * R / math.hypot(x, y), y * R / math.hypot(x, y)]]
    p, w, sign = h * h / mu, el["arg_periapsis"], (1 if h > 0 else -1)
    nu0 = (math.atan2(y, x) - w + math.pi) % (2 * math.pi) - math.pi
    if e < 1:
        span = 2 * math.pi
    else:
        span = max(0.0, math.acos(-1 / e) * 0.98 - sign * nu0)
    pts = []
    for d in np.linspace(0, span, n):
        nu = nu0 + sign * d
        r = p / (1 + e * math.cos(nu))
        if r <= 0 or r > 80 * R:
            break
        pts.append([r * math.cos(nu + w), r * math.sin(nu + w)])
        if r < R and len(pts) > 1:
            break
    return pts


def _earth_rotation_deg(jd: float) -> float:
    """Earth's prime-meridian angle W (IAU): the right ascension of Greenwich, degrees."""
    w0, rate = ROTATION["earth"][2:]
    return (w0 + rate * (jd - J2000_JD)) % 360.0


def _ecl_to_eq(v) -> np.ndarray:
    c, s_ = math.cos(OBLIQUITY), math.sin(OBLIQUITY)
    return np.array([v[0], c * v[1] - s_ * v[2], s_ * v[1] + c * v[2]])


def view3d(state: dict, x: float, y: float, angle: float, moon_xy, traj: list) -> dict:
    """Map the planar flight onto the real sky (equatorial J2000, metres) for a 3D view: craft, pointing, Moon,
    trajectory, Earth's rotation angle and the Sun's direction at the current mission time."""
    c0 = float(state["site_ra"]) + math.pi / 2
    cc, ss = math.cos(c0), math.sin(c0)
    to_eq = lambda px, py: [cc * px + ss * py, ss * px - cc * py, 0.0]
    jd = float(state["epoch_jd"]) + float(state["t"]) / 86400.0
    sun = -_ecl_to_eq(heliocentric("earth", np.array([jd]))[:, 0])
    return {
        "julian_date": jd, "earth_rotation_deg": _earth_rotation_deg(jd),
        "sun_direction": (sun / np.linalg.norm(sun)).tolist(),
        "craft": to_eq(x, y), "pointing": to_eq(math.cos(angle), math.sin(angle)),
        "moon": to_eq(*moon_xy) if moon_xy else None,
        "trajectory": [to_eq(px, py) for px, py in traj],
        "frame": "equatorial J2000, Earth-centred, metres",
    }


def moon_state(theta0: float, t: float) -> tuple[float, float, float, float]:
    """Position and velocity of the Moon (Earth-centred, m and m/s) at mission time t."""
    th = theta0 + MOON_RATE * t
    c, s = math.cos(th), math.sin(th)
    return MOON_DISTANCE * c, MOON_DISTANCE * s, -MOON_DISTANCE * MOON_RATE * s, MOON_DISTANCE * MOON_RATE * c


def _on_moon(theta0: float, t: float, phi: float) -> list[float]:
    """A point fixed on the (tidally locked) Moon's surface at Moon-fixed longitude phi."""
    mx, my, mvx, mvy = moon_state(theta0, t)
    a = phi + theta0 + MOON_RATE * t
    ox, oy = MOON_RADIUS * math.cos(a), MOON_RADIUS * math.sin(a)
    return [mx + ox, my + oy, mvx - MOON_RATE * oy, mvy + MOON_RATE * ox]


@tool(
    domain="physics",
    name="rocket_launch_state",
    description=(
        "Initial flight state of a rocket standing on the launch pad of a body (earth, moon or mars), for "
        "rocket_flight. On Earth the Moon is included as a moving body (moon_phase_deg sets where it is at launch, "
        "measured from the pad direction), so trans-lunar flights, lunar orbits and landings can be flown."
    ),
)
def rocket_launch_state(parts: list, body: str = "earth", custom_parts: dict | None = None, moon_phase_deg: float = -30.0,
                        start: str = "pad", date: str | None = None, site_longitude_deg: float = -52.77) -> dict:
    b = _body(body)
    if start not in ("pad", "orbit"):
        raise ValueError("start must be 'pad' or 'orbit'")
    if not -180 <= site_longitude_deg <= 360:
        raise ValueError("site_longitude_deg must be between -180 and 360")
    ps = _parse(parts, custom_parts)
    stages = _stages(ps)
    R = b["radius"]
    state = {"t": 0.0, "x": 0.0, "y": R, "vx": -b["omega"] * R, "vy": 0.0, "angle": math.pi / 2, "stage": 0,
             "props": [s["prop"] for s in stages], "landed": True, "crashed": False, "chute": False, "body": body,
             "landed_on": body, "fairing": any(p["id"] in FAIRINGS for p in ps),
             "moon_theta0": math.pi / 2 + math.radians(moon_phase_deg) if body == "earth" else None}
    assumptions = ["The pad rotates with the planet, so the rocket starts with the surface speed",
                   "Earth flights include the Moon on a circular 384,400 km orbit in the flight plane"]
    if date is not None and body == "earth":
        # Tie the flight to the real sky: the flight plane is Earth's equator, the pad sits at the site's longitude
        # and the model Moon starts at the real Moon's right ascension on that date (JPL/IAU ephemeris).
        jd = julian_date(date)
        if not 2378496.5 <= jd <= 2469807.5:
            raise ValueError("date must be between 1800 and 2050")
        site_ra = math.radians(_earth_rotation_deg(jd) + site_longitude_deg)
        m = _ecl_to_eq(moon_geocentric(np.array([jd]))[:, 0])
        moon_ra = math.atan2(m[1], m[0])
        state.update(epoch_jd=jd, site_ra=site_ra, site_longitude_deg=site_longitude_deg,
                     moon_theta0=math.pi / 2 - (moon_ra - site_ra))  # the flight frame is the equator seen from the south
        assumptions.append(f"Real sky for {date}: launch site at longitude {site_longitude_deg}°, Moon placed at its real right "
                           "ascension (its ±28° declination is flattened into the equatorial flight plane)")
    if start == "orbit":
        # Spend the ascent Δv budget (with typical losses) from the bottom stage up, then place what is left in a
        # circular prograde parking orbit. The fairing is gone by then.
        alt = 200e3 if body == "earth" else 50e3
        need = {"earth": 9400.0, "moon": 1870.0, "mars": 4100.0}[body]
        props, k = list(state["props"]), 0
        for j, st_ in enumerate(stages):
            if need <= 0:
                break
            m0 = sum(s_["dry"] for s_ in stages[j:]) + sum(props[j:])  # the fairing rides along during the ascent
            if not st_["mdot"] or props[j] <= 0:
                k = j + 1
                continue
            ve = st_["isp_vac"] * G0
            used = m0 * (1 - math.exp(-need / ve))
            if used >= props[j]:
                need -= ve * math.log(m0 / (m0 - props[j]))
                props[j] = 0.0
                k = j + 1
            else:
                props[j] -= used
                need, k = 0.0, j
        if need > 0 or k >= len(stages):
            raise ValueError("this rocket does not have the Δv to reach orbit, so it cannot start there")
        r = R + alt
        v = math.sqrt(b["mu"] / r)
        state.update(x=0.0, y=r, vx=v, vy=0.0, angle=0.0, stage=k, props=props, landed=False, landed_on=None, fairing=False)
        assumptions.append(f"Started in a circular {alt / 1e3:.0f} km orbit after spending {({'earth': 9400, 'moon': 1870, 'mars': 4100})[body]} m/s "
                           "(ascent including gravity and drag losses) from the lowest stages")
    return {"result": state, "units": "SI (m, m/s, kg, rad, s); planet-centred inertial frame, pad at (0, R)",
            "assumptions": assumptions}


def _ref_frame(b, moon_on, theta0, t, x, y, vx, vy, landed_on):
    """Which body the craft is 'at' (Moon inside its sphere of influence) and the craft's state relative to it."""
    if moon_on:
        mx, my, mvx, mvy = moon_state(theta0, t)
        if landed_on == "moon" or math.hypot(x - mx, y - my) < MOON_SOI:
            moon = {**BODIES["moon"], "omega": MOON_RATE}
            return "moon", moon, (x - mx, y - my, vx - mvx, vy - mvy)
    return "earth" if b is BODIES["earth"] else [n for n, v in BODIES.items() if v is b][0], b, (x, y, vx, vy)


def _nbody_rhs(theta0, t_start, mu):
    def rhs(tt, s):
        x, y = s[0], s[1]
        r3 = math.hypot(x, y) ** 3
        mx, my, _, _ = moon_state(theta0, t_start + tt)
        dx, dy = x - mx, y - my
        d3 = math.hypot(dx, dy) ** 3
        return [s[2], s[3], -mu * x / r3 - MU_MOON * (dx / d3 + mx / MOON_DISTANCE**3),
                -mu * y / r3 - MU_MOON * (dy / d3 + my / MOON_DISTANCE**3)]
    return rhs


def _predict_nbody(b, theta0, t0, x, y, vx, vy, horizon, n=400):
    """Coast trajectory with the Moon's gravity: points (Earth frame and Moon-relative) and the closest lunar pass."""
    R, mu = b["radius"], b["mu"]
    rhs = _nbody_rhs(theta0, t0, mu)

    def hit_earth(_t, s):
        return math.hypot(s[0], s[1]) - R
    hit_earth.terminal, hit_earth.direction = True, -1

    def hit_moon(tt, s):
        mx, my, _, _ = moon_state(theta0, t0 + tt)
        return math.hypot(s[0] - mx, s[1] - my) - MOON_RADIUS
    hit_moon.terminal, hit_moon.direction = True, -1

    def periselene(tt, s):  # d/dt |r − r_moon| crosses zero from below at the closest approach
        mx, my, mvx, mvy = moon_state(theta0, t0 + tt)
        return (s[0] - mx) * (s[2] - mvx) + (s[1] - my) * (s[3] - mvy)
    periselene.direction = 1

    sol = solve_ivp(rhs, (0, horizon), [x, y, vx, vy], method="DOP853", rtol=1e-9, atol=1.0,
                    t_eval=np.linspace(0, horizon, n), events=[hit_earth, hit_moon, periselene], max_step=horizon / 150)
    pts, rel = [], []
    for tt, px, py in zip(sol.t, sol.y[0], sol.y[1]):
        mx, my, _, _ = moon_state(theta0, t0 + tt)
        pts.append([px, py])
        rel.append([px - mx, py - my])
    encounter = None
    for tt, st in zip(sol.t_events[2], sol.y_events[2]):
        mx, my, _, _ = moon_state(theta0, t0 + tt)
        d = math.hypot(st[0] - mx, st[1] - my)
        if d < MOON_SOI and (encounter is None or d < encounter["closest_distance"]):
            encounter = {"time_from_now": float(tt), "closest_distance": d, "periselene_alt": d - MOON_RADIUS,
                         "moon_position": [mx, my], "craft_position": [float(st[0]), float(st[1])]}
    if len(sol.t_events[1]):
        tt = float(sol.t_events[1][0])
        st = sol.y_events[1][0]
        mx, my, _, _ = moon_state(theta0, t0 + tt)
        encounter = {"time_from_now": tt, "closest_distance": MOON_RADIUS, "periselene_alt": 0.0, "impact": True,
                     "moon_position": [mx, my], "craft_position": [float(st[0]), float(st[1])]}
        pts.append([st[0], st[1]])
        rel.append([st[0] - mx, st[1] - my])
    return pts, rel, encounter


@tool(
    domain="physics",
    name="rocket_flight",
    description=(
        "Advance a rocket's 2D flight by dt seconds (use with time warp): gravity (Earth flights also feel the moving "
        "Moon), thrust with pressure-dependent Isp, drag in a rotating exponential atmosphere (lower with a nose cone or "
        "fairing, higher with exposed upper-stage engines), propellant use, staging (stage=True drops the lowest "
        "stage), fairing jettison, parachute, touchdown on Earth or the Moon (landed or crashed), orbit elements "
        "relative to the body whose sphere of influence the craft is in, a trans-lunar-injection window planner, and "
        "the predicted trajectory (numerical with the Moon's gravity when it matters). state comes from "
        "rocket_launch_state or a previous call; throttle 0..1; angle is the pointing direction (radians, inertial)."
    ),
)
def rocket_flight(
    state: dict,
    parts: list,
    throttle: float = 0.0,
    angle: float | None = None,
    dt: float = 0.1,
    stage: bool = False,
    deploy_chute: bool = False,
    predict: bool = True,
    jettison_fairing: bool = False,
    custom_parts: dict | None = None,
) -> dict:
    b = _body(str(state.get("body", "earth")))
    stages = _stages(_parse(parts, custom_parts))
    if not 0 <= throttle <= 1:
        raise ValueError("throttle must be between 0 and 1")
    if not 0 < dt <= 86_400 * 30:
        raise ValueError("dt must be between 0 and 30 days (in seconds)")
    try:
        t, x, y, vx, vy = (float(state[k]) for k in ("t", "x", "y", "vx", "vy"))
        k = int(state["stage"])
        props = [float(v) for v in state["props"]]
    except (KeyError, TypeError, ValueError):
        raise ValueError("state is missing fields; start from rocket_launch_state") from None
    if len(props) != len(stages) or not 0 <= k < len(stages):
        raise ValueError("state does not match this rocket (different number of stages)")
    body_name = [n for n, v in BODIES.items() if v is b][0]
    moon_on = body_name == "earth" and state.get("moon_theta0") is not None
    theta0 = float(state["moon_theta0"]) if moon_on else 0.0
    ang = float(state.get("angle", math.pi / 2)) if angle is None else float(angle)
    landed, crashed, chute = bool(state.get("landed")), bool(state.get("crashed")), bool(state.get("chute"))
    landed_on = state.get("landed_on") or (body_name if landed else None)
    phi = float(state.get("surface_angle") or 0.0)
    fairing = bool(state.get("fairing", False))
    events: list[str] = []
    R, mu, om = b["radius"], b["mu"], b["omega"]
    if crashed:
        throttle = 0.0
    if stage and k < len(stages) - 1:
        events.append(f"stage {k + 1} separated")
        k += 1
    upper = stages[k:]
    if jettison_fairing and fairing and any(s["fairing_mass"] for s in upper):
        fairing = False
        rho_now = _density(b, math.hypot(x, y) - R)
        q_now = 0.5 * rho_now * ((vx + om * y) ** 2 + (vy - om * x) ** 2)
        events.append("fairing jettisoned" + (f" at {q_now / 1000:.1f} kPa — the payload is exposed to heating" if q_now > 1000 else ""))
    if deploy_chute and not chute and any(s["chute"] for s in upper):
        chute = True
        events.append("parachute deployed")
    st = stages[k]
    fairing_mass = sum(s["fairing_mass"] for s in upper)
    dry = sum(s["dry"] for s in upper) + sum(props[j] for j in range(k + 1, len(stages))) - (0.0 if fairing else fairing_mass)
    width = max(s["width"] for s in upper)
    pointy = any(s["nose"] for s in upper) or (fairing and fairing_mass > 0)
    exposed = sum(1 for s in upper[1:] if s["exposed_engine"])
    cd = (0.3 if pointy else 0.75) + 0.15 * exposed
    cda = cd * math.pi * (width / 2) ** 2 + (CHUTE_CDA if chute else 0.0)
    legs = any(s["legs"] for s in upper)
    burning = throttle > 0 and st["mdot"] > 0 and props[k] > 0 and not crashed

    def accel(tt, xx, yy, vxx, vyy, mprop, on):
        r = math.hypot(xx, yy)
        m = dry + mprop
        ax, ay = -mu * xx / r**3, -mu * yy / r**3
        if moon_on:
            mx, my, _, _ = moon_state(theta0, tt)
            dx, dy = xx - mx, yy - my
            d3 = math.hypot(dx, dy) ** 3
            ax -= MU_MOON * (dx / d3 + mx / MOON_DISTANCE**3)  # direct pull + the Earth's own fall toward the Moon
            ay -= MU_MOON * (dy / d3 + my / MOON_DISTANCE**3)
        alt = r - R
        rho = _density(b, alt)
        if on and mprop > 0:
            frac = rho / b["rho0"] if b["rho0"] > 0 else 0.0
            f = throttle * (st["thrust_vac"] - (st["thrust_vac"] - st["thrust_sl"]) * frac)
            ax += f / m * math.cos(ang)
            ay += f / m * math.sin(ang)
        if rho > 0:
            # velocity relative to the co-rotating air: v_air = ω × r
            rvx, rvy = vxx - (-om * yy), vyy - (om * xx)
            vrel = math.hypot(rvx, rvy)
            dmag = 0.5 * rho * vrel * cda / m
            ax -= dmag * rvx
            ay -= dmag * rvy
        return ax, ay

    def finish(tt, xx, yy, vxx, vyy, landed_, crashed_, lo, ph):
        return _result(b, stages, tt, xx, yy, vxx, vyy, ang, k, props, landed_, crashed_, chute, events, throttle, dry, st,
                       cda, predict, moon_on, theta0, lo, ph, fairing,
                       {k_: state[k_] for k_ in ("epoch_jd", "site_ra", "site_longitude_deg") if state.get(k_) is not None})

    # On the ground: stay put (moving with the surface) unless thrust beats weight
    if landed and not crashed:
        on_moon = landed_on == "moon" and moon_on
        if on_moon:
            mx, my, _, _ = moon_state(theta0, t)
            cx_, cy_, g, mu_ref = x - mx, y - my, MU_MOON / MOON_RADIUS**2, MU_MOON
        else:
            cx_, cy_, g = x, y, mu / (x * x + y * y)
        m = dry + props[k]
        frac = _density(b, 0) / b["rho0"] if b["rho0"] > 0 and not on_moon else 0.0
        f = throttle * (st["thrust_vac"] - (st["thrust_vac"] - st["thrust_sl"]) * frac) if burning else 0.0
        radial = f * ((cx_ * math.cos(ang) + cy_ * math.sin(ang)) / math.hypot(cx_, cy_))
        if radial <= m * g:
            if on_moon:
                x, y, vx, vy = _on_moon(theta0, t + dt, phi)
            else:
                th = om * dt
                c, s_ = math.cos(th), math.sin(th)
                x, y = x * c - y * s_, x * s_ + y * c
                vx, vy = -om * y, om * x
            if burning:
                props[k] -= min(props[k], throttle * st["mdot"] * dt)
            return finish(t + dt, x, y, vx, vy, True, False, landed_on, phi)
        landed = False
        events.append("lift-off" + (" from the Moon" if on_moon else ""))

    def rhs(tt, s):
        ax, ay = accel(t + tt, s[0], s[1], s[2], s[3], s[4], burning)
        dm = -throttle * st["mdot"] if burning and s[4] > 0 else 0.0
        return [s[2], s[3], ax, ay, dm]

    def ground(_t, s):
        return math.hypot(s[0], s[1]) - R
    ground.terminal, ground.direction = True, -1

    seg = [0.0]  # time already integrated in this step (events see solver-local time)

    def moon_ground(a, s):
        mx, my, _, _ = moon_state(theta0, t + seg[0] + a)
        return math.hypot(s[0] - mx, s[1] - my) - MOON_RADIUS
    moon_ground.terminal, moon_ground.direction = True, -1

    def empty(_t, s):
        return s[4]
    empty.terminal, empty.direction = True, -1

    y0 = [x, y, vx, vy, props[k]]
    remaining, tt = dt, 0.0
    alt0 = math.hypot(x, y) - R
    near_moon = moon_on and math.hypot(x - moon_state(theta0, t)[0], y - moon_state(theta0, t)[1]) < MOON_SOI
    fine = burning or (b["top"] > 0 and alt0 < b["top"] * 1.2) or alt0 < 5_000
    max_step = 0.25 if fine else max(1.0, dt / 200)
    if near_moon and not burning:
        max_step = min(max_step, 60.0)
    while remaining > 1e-9:
        evs = [ground] + ([moon_ground] if moon_on else []) + ([empty] if burning else [])
        seg[0] = tt
        sol = solve_ivp(lambda a, s_: rhs(seg[0] + a, s_), (0, remaining), y0, method="DOP853" if not fine else "RK45",
                        rtol=1e-9, atol=1e-6, max_step=max_step, events=evs)
        y0 = list(sol.y[:, -1])
        tt += sol.t[-1]
        remaining -= sol.t[-1]
        hit_earth = sol.status == 1 and len(sol.t_events[0])
        hit_moon = sol.status == 1 and moon_on and len(sol.t_events[1])
        if hit_earth or hit_moon:
            gx, gy, gvx, gvy = y0[:4]
            if hit_earth:
                rvx, rvy = gvx - (-om * gy), gvy - (om * gx)
                r = math.hypot(gx, gy)
                y0[0], y0[1] = gx * R / r, gy * R / r
                lo, ph = body_name, 0.0
            else:
                mx, my, mvx, mvy = moon_state(theta0, t + tt)
                ox, oy = gx - mx, gy - my
                rvx, rvy = gvx - mvx + MOON_RATE * oy, gvy - mvy - MOON_RATE * ox
                lo, ph = "moon", math.atan2(oy, ox) - theta0 - MOON_RATE * (t + tt)
            impact = math.hypot(rvx, rvy)
            where = " on the Moon" if hit_moon else ""
            if impact <= (SAFE_LANDING_LEGS if legs else SAFE_LANDING):
                landed = True
                events.append(f"touchdown{where} at {impact:.1f} m/s")
            else:
                crashed = True
                events.append(f"crashed{where} at {impact:.0f} m/s")
            landed_on, phi = lo, ph
            tt += remaining  # the rest of the step is spent sitting on the surface
            if lo == "moon":
                y0[:4] = _on_moon(theta0, t + tt, phi)
            else:
                th = om * remaining
                c, s_ = math.cos(th), math.sin(th)
                y0[0], y0[1] = y0[0] * c - y0[1] * s_, y0[0] * s_ + y0[1] * c
                y0[2], y0[3] = -om * y0[1], om * y0[0]
            remaining = 0
            break
        if sol.status == 1 and burning and len(sol.t_events[-1]):
            y0[4] = 0.0
            burning = False
            events.append(f"stage {k + 1} out of fuel")
    x, y, vx, vy, props[k] = y0
    props[k] = max(0.0, props[k])
    return finish(t + tt, x, y, vx, vy, landed, crashed, landed_on if landed or crashed else None, phi)


def _tli_window(mu, t_x, t_y, t_vx, t_vy, theta0, t):
    """Hohmann-like trans-lunar injection from a near-circular prograde Earth orbit: Δv, transfer time, the Moon
    lead angle it needs, the lead angle now and the wait until it comes round."""
    r = math.hypot(t_x, t_y)
    h = t_x * t_vy - t_y * t_vx
    if h >= 0:  # orbiting against the Moon's direction
        return None
    at = (r + MOON_DISTANCE) / 2
    t_tr = math.pi * math.sqrt(at**3 / mu)
    need = math.pi - abs(MOON_RATE) * t_tr
    mx, my, _, _ = moon_state(theta0, t)
    lead = (math.atan2(t_y, t_x) - math.atan2(my, mx)) % (2 * math.pi)  # both move clockwise
    w = math.sqrt(mu / r**3) - abs(MOON_RATE)
    return {"delta_v": math.sqrt(mu * (2 / r - 1 / at)) - math.sqrt(mu / r), "transfer_time": t_tr,
            "phase_required_deg": math.degrees(need), "phase_now_deg": math.degrees(lead),
            "time_to_window": ((lead - need) % (2 * math.pi)) / w}


def _result(b, stages, t, x, y, vx, vy, ang, k, props, landed, crashed, chute, events, throttle, dry, st, cda, predict,
            moon_on=False, theta0=0.0, landed_on=None, phi=0.0, fairing=False, extra=None):
    extra = extra or {}
    ref, rb, (lx, ly, lvx, lvy) = _ref_frame(b, moon_on, theta0, t, x, y, vx, vy, landed_on)
    R, mu, om = rb["radius"], rb["mu"], rb["omega"]
    r = math.hypot(lx, ly)
    alt = r - R
    ux, uy = lx / r, ly / r
    rvx, rvy = lvx - (-om * ly), lvy - (om * lx)
    m = dry + props[k]
    rho = _density(rb, alt)
    frac = rho / rb["rho0"] if rb["rho0"] > 0 else 0.0
    thrust = throttle * (st["thrust_vac"] - (st["thrust_vac"] - st["thrust_sl"]) * frac) if props[k] > 0 and st["mdot"] > 0 and not crashed else 0.0
    el = _elements(rb, lx, ly, lvx, lvy)
    top = rb["top"] if ref != "moon" else 0.0
    if crashed:
        status = "crashed"
    elif landed:
        status = "landed"
    elif el["specific_energy"] >= 0:
        status = "lunar flyby" if ref == "moon" else "escape trajectory"
    elif el["periapsis_alt"] > max(top, 10_000.0 if ref != "moon" else 1_000.0):
        status = "lunar orbit" if ref == "moon" else "orbit"
    else:
        status = "suborbital"
    # Δv left (vacuum) from the current stage upward, with the propellant actually remaining
    dv_left, mass_above = 0.0, 0.0
    for j in range(len(stages) - 1, k - 1, -1):
        s = stages[j]
        m_start = mass_above + s["dry"] + props[j] - (0.0 if fairing else s["fairing_mass"])
        if s["mdot"] and props[j] > 0:
            dv_left += s["isp_vac"] * G0 * math.log(m_start / (m_start - props[j]))
        mass_above = m_start
    q = 0.5 * rho * (rvx * rvx + rvy * rvy)
    state = {"t": t, "x": x, "y": y, "vx": vx, "vy": vy, "angle": ang, "stage": k, "props": props,
             "landed": landed, "crashed": crashed, "chute": chute, "body": [n for n, v in BODIES.items() if v is b][0],
             "landed_on": landed_on, "surface_angle": phi, "fairing": fairing,
             "moon_theta0": theta0 if moon_on else None}
    for key in ("epoch_jd", "site_ra", "site_longitude_deg"):
        if key in extra:
            state[key] = extra[key]
    speed_surface = math.hypot(rvx, rvy)
    telemetry = {
        "reference": ref, "altitude": alt, "speed": math.hypot(lvx, lvy), "surface_speed": speed_surface,
        "vertical_speed": lvx * ux + lvy * uy, "horizontal_speed": lvx * uy - lvy * ux,  # + = east (direction of rotation)
        "downrange_angle_deg": math.degrees(math.atan2(lx, ly)),
        "mass": m, "thrust": thrust, "twr": thrust / (m * mu / r**2),
        "acceleration_g": (thrust + 0.5 * rho * speed_surface**2 * cda) / m / G0,
        "dynamic_pressure": q, "mach": speed_surface / rb["sound"] if rho > 0 else None, "air_density": rho,
        "stage_fuel_fraction": props[k] / stages[k]["prop"] if stages[k]["prop"] else 0.0,
        "delta_v_remaining": dv_left, "status": status, "fairing_attached": fairing,
        "apoapsis_alt": el["apoapsis_alt"], "periapsis_alt": el["periapsis_alt"], "eccentricity": el["eccentricity"],
        "period": el["period"], "stages_left": len(stages) - k,
    }
    out = {"result": {"state": state, "telemetry": telemetry, "events": events}, "trajectory": [],
           "local": {"x": lx, "y": ly, "vx": lvx, "vy": lvy, "radius": R, "atmosphere_top": top, "body": ref},
           "planet": {"radius": b["radius"], "atmosphere_top": b["top"], "name": b["name"]}}
    if moon_on:
        mx, my, _, _ = moon_state(theta0, t)
        telemetry["moon_altitude"] = math.hypot(x - mx, y - my) - MOON_RADIUS
        out["moon"] = {"x": mx, "y": my, "radius": MOON_RADIUS, "soi": MOON_SOI, "orbit_radius": MOON_DISTANCE}
        if ref == "earth" and not landed and not crashed and el["specific_energy"] < 0 and el["eccentricity"] < 0.05 \
                and el["apoapsis_alt"] < 3_000e3:
            telemetry["tli"] = _tli_window(mu, x, y, vx, vy, theta0, t)
    if predict and not landed and not crashed:
        bound = el["specific_energy"] < 0
        if moon_on and (ref == "moon" or not bound or el["apoapsis_alt"] > 60_000e3):
            if ref == "moon":
                horizon = min(12 * 86400.0, el["period"] * 1.05) if bound and el["period"] else 4 * 86400.0
            else:
                horizon = min(12 * 86400.0, el["period"] * 1.02) if bound else 8 * 86400.0
            horizon = max(horizon, 600.0)
            pts, rel, enc = _predict_nbody(b, theta0, t, x, y, vx, vy, horizon)
            out["trajectory"], out["trajectory_moon"], out["trajectory_dt"] = pts, rel, horizon / 399
            if enc:
                telemetry["encounter"] = enc
        else:
            out["trajectory"] = _predict(b, x, y, vx, vy)
    if "epoch_jd" in state and "site_ra" in state:
        out["view3d"] = view3d(state, x, y, ang, (out["moon"]["x"], out["moon"]["y"]) if moon_on else None, out["trajectory"])
        enc = telemetry.get("encounter")
        if enc:
            v0 = view3d(state, enc["craft_position"][0], enc["craft_position"][1], 0.0, enc["moon_position"], [])
            out["view3d"]["encounter"] = {"craft": v0["craft"], "moon": v0["moon"], "periselene_alt": enc["periselene_alt"],
                                          "impact": bool(enc.get("impact")), "time_from_now": enc["time_from_now"]}
    out["units"] = "SI: m, m/s, kg, N, s, Pa, kg/m³; angles in radians unless noted"
    out["assumptions"] = ["2D point-mass flight in the planet's equatorial plane; attitude is set by the pilot",
                          "Exponential atmosphere co-rotating with the planet; Cd 0.3 with a nose cone or fairing, 0.75 "
                          "without, +0.15 for each exposed upper-stage engine",
                          "Thrust interpolates between sea-level and vacuum values with ambient pressure",
                          "Earth flights: the Moon moves on a circular coplanar orbit (restricted three-body problem in "
                          "the Earth-centred frame); orbit elements refer to the Moon inside its sphere of influence"]
    return out


@tool(
    domain="physics",
    name="rocket_parts",
    description="The rocket parts catalogue (ids, names, categories, engine size classes, masses, propellant, thrust, Isp, sizes), the flyable bodies and a mission Δv budget.",
)
def rocket_parts() -> dict:
    return {
        "result": {"parts": [{"id": k, **v} for k, v in PARTS.items()],
                   "engine_classes": [{"class": c, "max_thrust_vac": None if lim == float("inf") else lim} for c, lim in ENGINE_CLASSES],
                   "bodies": {k: {"name": v["name"], "radius": v["radius"], "atmosphere_top": v["top"],
                                  "surface_gravity": v["mu"] / v["radius"] ** 2} for k, v in BODIES.items()},
                   "mission_delta_v": mission_budget()},
        "units": "masses in kg, thrust in N, Isp in s, sizes in m, gravity in m/s², Δv in m/s",
        "assumptions": ["Generic parts with values typical of real hardware of each kind (kerolox, hydrolox, "
                        "methalox and hypergolic engines; example satellites)"],
    }
