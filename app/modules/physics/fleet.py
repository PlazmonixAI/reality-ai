"""Satellites that live in real time: mean-element propagation with Earth's oblateness (J2) and atmospheric
drag, so a low satellite slowly sinks and re-enters unless it boosts; impulsive thruster burns paid for with
propellant (rocket equation); and a camera model (ground sample distance, diffraction limit, swath, sun angle)
for taking pictures of the ground from orbit."""
from __future__ import annotations

import math

import numpy as np
from scipy.integrate import solve_ivp

from app.core.registry import tool
from app.modules.physics.ephemeris import J2000_JD, OBLIQUITY, ROTATION, heliocentric, julian_date
from app.modules.physics.perturbations import ATMOSPHERE, J2

MU = 3.986004418e14
RE = 6_378_137.0
J2E = J2["earth"]
DAY = 86_400.0
G0 = 9.80665
REENTRY_ALT = 100e3
DRAG_CEILING = 1_500e3  # above this the static atmosphere is negligible
_H0 = np.array([r[0] for r in ATMOSPHERE], float)
_RHO0 = np.array([r[1] for r in ATMOSPHERE], float)
_SCALE = np.array([r[2] for r in ATMOSPHERE], float)


def rho(alt_m) -> np.ndarray:
    """Static exponential atmosphere (Vallado table 8-4) for altitudes above 100 km; clamped below."""
    h = np.maximum(np.asarray(alt_m, float) / 1000.0, 100.0)
    i = np.clip(np.searchsorted(_H0, h, side="right") - 1, 0, len(_H0) - 1)
    return _RHO0[i] * np.exp(-(h - _H0[i]) / _SCALE[i])


# ---------------------------------------------------------------- element conversions
def coe_to_rv(a, e, i, raan, argp, m):
    """Classical elements (radians) → position (m) and velocity (m/s) in the equatorial inertial frame."""
    big = m
    for _ in range(60):
        big = big - (big - e * math.sin(big) - m) / (1 - e * math.cos(big))
    cos_e, sin_e = math.cos(big), math.sin(big)
    r = a * (1 - e * cos_e)
    xp, yp = a * (cos_e - e), a * math.sqrt(1 - e * e) * sin_e
    fac = math.sqrt(MU * a) / r
    vxp, vyp = -fac * sin_e, fac * math.sqrt(1 - e * e) * cos_e
    cw, sw, co, so, ci, si = math.cos(argp), math.sin(argp), math.cos(raan), math.sin(raan), math.cos(i), math.sin(i)
    rot = np.array([[cw * co - sw * so * ci, -sw * co - cw * so * ci],
                    [cw * so + sw * co * ci, -sw * so + cw * co * ci],
                    [sw * si, cw * si]])
    return rot @ np.array([xp, yp]), rot @ np.array([vxp, vyp])


def rv_to_coe(r, v) -> dict:
    """Position and velocity → classical elements (radians). Circular/equatorial cases use the usual conventions."""
    r, v = np.asarray(r, float), np.asarray(v, float)
    rn, vn = np.linalg.norm(r), np.linalg.norm(v)
    h = np.cross(r, v)
    hn = np.linalg.norm(h)
    nvec = np.cross([0.0, 0.0, 1.0], h)
    nn = np.linalg.norm(nvec)
    evec = ((vn * vn - MU / rn) * r - np.dot(r, v) * v) / MU
    e = float(np.linalg.norm(evec))
    energy = vn * vn / 2 - MU / rn
    if energy >= 0:
        raise ValueError("that burn puts the satellite on an escape trajectory")
    a = -MU / (2 * energy)
    i = math.acos(max(-1.0, min(1.0, h[2] / hn)))
    raan = math.atan2(nvec[1], nvec[0]) if nn > 1e-9 else 0.0
    if e > 1e-9:
        argp = math.atan2(np.dot(np.cross(nvec / nn, evec), h) / hn, np.dot(nvec / nn, evec)) if nn > 1e-9 else \
            math.atan2(evec[1], evec[0]) * (1 if h[2] >= 0 else -1)
        nu = math.atan2(np.dot(np.cross(evec, r), h) / hn, np.dot(evec, r))
    else:  # circular: measure from the node (or the x axis)
        argp = 0.0
        ref = nvec / nn if nn > 1e-9 else np.array([1.0, 0.0, 0.0])
        nu = math.atan2(np.dot(np.cross(ref, r), h) / hn, np.dot(ref, r))
    big = 2 * math.atan2(math.sqrt(1 - e) * math.sin(nu / 2), math.sqrt(1 + e) * math.cos(nu / 2))
    m = big - e * math.sin(big)
    return {"a": a, "e": e, "i": i, "raan": raan % (2 * math.pi), "argp": argp % (2 * math.pi), "m": m % (2 * math.pi)}


def to_public(el: dict) -> dict:
    a, e = el["a"], el["e"]
    return {"a": a, "e": e, "i_deg": math.degrees(el["i"]), "raan_deg": math.degrees(el["raan"]) % 360,
            "argp_deg": math.degrees(el["argp"]) % 360, "m_deg": math.degrees(el["m"]) % 360,
            "perigee_alt": a * (1 - e) - RE, "apogee_alt": a * (1 + e) - RE,
            "period": 2 * math.pi * math.sqrt(a**3 / MU)}


def from_public(orbit: dict) -> dict:
    try:
        el = {"a": float(orbit["a"]), "e": float(orbit["e"]), "i": math.radians(float(orbit["i_deg"])),
              "raan": math.radians(float(orbit.get("raan_deg", 0.0))), "argp": math.radians(float(orbit.get("argp_deg", 0.0))),
              "m": math.radians(float(orbit.get("m_deg", 0.0)))}
    except (KeyError, TypeError, ValueError):
        raise ValueError("orbit needs a (m), e, i_deg and optionally raan_deg, argp_deg, m_deg") from None
    if not 0 <= el["e"] < 0.97 or not 0 < el["a"] <= 2e9:
        raise ValueError("orbit must be elliptical (0 ≤ e < 0.97) and within 2 million km")
    if el["a"] * (1 - el["e"]) < RE:
        raise ValueError("that orbit's perigee is below the ground")
    return el


def jd_of(date: str | None) -> float:
    return julian_date(date)


def gmst_rad(jd: float) -> float:
    w0, rate = ROTATION["earth"][2:]
    return math.radians((w0 + rate * (jd - J2000_JD)) % 360.0)


def sun_dir(jd: float) -> np.ndarray:
    e = heliocentric("earth", np.array([jd]))[:, 0]
    c, s = math.cos(OBLIQUITY), math.sin(OBLIQUITY)
    v = -np.array([e[0], c * e[1] - s * e[2], s * e[1] + c * e[2]])
    return v / np.linalg.norm(v)


def geodetic(r: np.ndarray, jd: float) -> tuple[float, float, float]:
    """Latitude, longitude (degrees, geocentric on a sphere) and altitude (m) of an inertial position."""
    rn = float(np.linalg.norm(r))
    lat = math.degrees(math.asin(r[2] / rn))
    lon = math.degrees(math.atan2(r[1], r[0]) - gmst_rad(jd))
    return lat, (lon + 180) % 360 - 180, rn - RE


# ---------------------------------------------------------------- propagation
def mean_motion(a, e, i):
    n = math.sqrt(MU / a**3)
    p = a * (1 - e * e)
    return n * (1 + 1.5 * J2E * (RE / p) ** 2 * math.sqrt(1 - e * e) * (1 - 1.5 * math.sin(i) ** 2))


def j2_rates(a, e, i):
    n = math.sqrt(MU / a**3)
    p = a * (1 - e * e)
    k = n * J2E * (RE / p) ** 2
    return -1.5 * k * math.cos(i), 0.75 * k * (5 * math.cos(i) ** 2 - 1)


_EA = np.linspace(0, 2 * np.pi, 72, endpoint=False)


def drag_rates(a, e, bc):
    """Orbit-averaged da/dt and de/dt from drag (Gauss equations averaged over mean anomaly)."""
    e = max(e, 0.0)
    cos_e = np.cos(_EA)
    r = a * (1 - e * cos_e)
    v2 = MU * (2 / r - 1 / a)
    v = np.sqrt(v2)
    rh = rho(r - RE)
    w = (1 - e * cos_e) / len(_EA)  # dM = (1 − e cos E) dE
    cos_nu = (cos_e - e) / (1 - e * cos_e)
    dadt = -(a * a / (MU * bc)) * np.sum(rh * v2 * v * w)
    dedt = -(1 / bc) * np.sum(rh * v * (e + cos_nu) * w)
    return float(dadt), float(dedt)


def propagate(el: dict, dt: float, bc: float | None) -> dict:
    """Mean elements after dt seconds (dt ≥ 0), with J2 secular drift and drag (bc = m / (Cd A), kg/m²).
    Returns the elements plus reentry information if the perigee sinks below 100 km."""
    a, e, i = el["a"], el["e"], el["i"]
    if dt <= 0:
        return {**el, "reentered": False, "reentry_after": None}
    drag = bc is not None and bc > 0 and a * (1 - e) - RE < DRAG_CEILING
    if not drag:
        rn, rw = j2_rates(a, e, i)
        return {**el, "raan": (el["raan"] + rn * dt) % (2 * math.pi), "argp": (el["argp"] + rw * dt) % (2 * math.pi),
                "m": (el["m"] + mean_motion(a, e, i) * dt) % (2 * math.pi), "reentered": False, "reentry_after": None}

    def rhs(_t, y):
        aa, ee = y[0], max(y[1], 0.0)
        da, de = drag_rates(aa, ee, bc)
        if ee <= 1e-7 and de < 0:
            de = 0.0
        rn, rw = j2_rates(aa, ee, i)
        return [da, de, rn, rw, mean_motion(aa, ee, i)]

    def low(_t, y):
        return y[0] * (1 - max(y[1], 0.0)) - RE - REENTRY_ALT
    low.terminal, low.direction = True, -1
    sol = solve_ivp(rhs, (0, dt), [a, e, el["raan"], el["argp"], el["m"]], method="LSODA", rtol=1e-10,
                    atol=[0.01, 1e-12, 1e-12, 1e-12, 1e-9], events=low, max_step=max(dt / 20, 600.0))
    y = sol.y[:, -1]
    out = {"a": float(y[0]), "e": max(float(y[1]), 0.0), "i": i, "raan": float(y[2]) % (2 * math.pi),
           "argp": float(y[3]) % (2 * math.pi), "m": float(y[4]) % (2 * math.pi), "reentered": False, "reentry_after": None}
    if len(sol.t_events[0]):
        out.update(reentered=True, reentry_after=float(sol.t_events[0][0]))
    return out


def lifetime(el: dict, bc: float | None, horizon_years: float = 100.0) -> dict:
    """Days until re-entry (None if longer than the horizon), and the perigee/apogee history on the way down."""
    if bc is None or bc <= 0 or el["a"] * (1 - el["e"]) - RE >= DRAG_CEILING:
        return {"days": None, "beyond_years": horizon_years, "history": []}
    horizon = horizon_years * 365.25 * DAY

    def rhs(_t, y):
        da, de = drag_rates(y[0], max(y[1], 0.0), bc)
        if y[1] <= 1e-7 and de < 0:
            de = 0.0
        return [da, de]

    def low(_t, y):
        return y[0] * (1 - max(y[1], 0.0)) - RE - REENTRY_ALT
    low.terminal, low.direction = True, -1
    sol = solve_ivp(rhs, (0, horizon), [el["a"], el["e"]], method="LSODA", rtol=1e-8, atol=[0.01, 1e-12],
                    events=low, dense_output=True)
    end = float(sol.t_events[0][0]) if len(sol.t_events[0]) else horizon
    ts = np.linspace(0, end, 60)
    ys = sol.sol(ts)
    hist = [{"t_days": float(t / DAY), "perigee_alt": float(aa * (1 - max(ee, 0)) - RE), "apogee_alt": float(aa * (1 + max(ee, 0)) - RE)}
            for t, aa, ee in zip(ts, ys[0], ys[1])]
    return {"days": end / DAY if len(sol.t_events[0]) else None, "beyond_years": None if len(sol.t_events[0]) else horizon_years,
            "history": hist}


def state_at(el: dict, jd: float) -> dict:
    r, v = coe_to_rv(el["a"], el["e"], el["i"], el["raan"], el["argp"], el["m"])
    lat, lon, alt = geodetic(r, jd)
    s = sun_dir(jd)
    rn = np.linalg.norm(r)
    along = float(np.dot(r, s))
    perp = float(np.linalg.norm(r - along * s))
    eclipse = along < 0 and perp < RE
    return {"r": r, "v": v, "lat": lat, "lon": lon, "alt": alt, "speed": float(np.linalg.norm(v)), "sunlit": not eclipse,
            "sun_elevation_below_deg": math.degrees(math.asin(float(np.dot(r / rn, s))))}


def ground_track(el: dict, jd: float, before: float, after: float, n: int) -> list:
    pts = []
    rn, rw = j2_rates(el["a"], el["e"], el["i"])
    nbar = mean_motion(el["a"], el["e"], el["i"])
    for dt in np.linspace(-before, after, n):
        e2 = {**el, "raan": el["raan"] + rn * dt, "argp": el["argp"] + rw * dt, "m": el["m"] + nbar * dt}
        r, _ = coe_to_rv(e2["a"], e2["e"], e2["i"], e2["raan"], e2["argp"], e2["m"])
        lat, lon, _ = geodetic(r, jd + dt / DAY)
        pts.append([round(lat, 4), round(lon, 4), round(float(dt), 1)])
    return pts


def _bc(mass: float, area_m2: float, cd: float) -> float | None:
    if mass <= 0 or area_m2 < 0 or cd < 0:
        raise ValueError("mass must be positive; area_m2 and cd not negative")
    return mass / (cd * area_m2) if area_m2 > 0 and cd > 0 else None


def _span(epoch: str, at: str | None) -> tuple[float, float, float]:
    jd0, jd1 = jd_of(epoch), jd_of(at)
    if not 2415020.5 <= jd0 <= 2488069.5:
        raise ValueError("epoch must be between 1900 and 2100")
    dt = (jd1 - jd0) * DAY
    if dt < -1.0:
        raise ValueError("'at' is before the orbit's epoch; propagate forward only")
    if dt > 200 * 365.25 * DAY:
        raise ValueError("at most 200 years after the epoch")
    return jd0, jd1, max(dt, 0.0)


@tool(
    domain="physics",
    name="satellite_track",
    description=(
        "Where a satellite is now (or at time 'at'): propagates its orbit from the epoch with J2 drift and "
        "atmospheric drag (static exponential atmosphere; ballistic coefficient from mass, area and Cd), so low "
        "orbits decay and re-enter. Returns latitude/longitude/altitude, speed, sunlight or eclipse, current "
        "elements, a ground track, and (forecast=True) the days until re-entry with the perigee/apogee history. "
        "orbit = {a (m), e, i_deg, raan_deg, argp_deg, m_deg} at epoch (ISO date-time, UTC)."
    ),
)
def satellite_track(orbit: dict, epoch: str, at: str | None = None, mass: float = 1000.0, area_m2: float = 10.0, cd: float = 2.2,
                    track_minutes: float = 120.0, track_points: int = 121, forecast: bool = False) -> dict:
    el0 = from_public(orbit)
    jd0, jd1, dt = _span(epoch, at)
    bc = _bc(mass, area_m2, cd)
    if not 0 <= track_minutes <= 3000 or not 2 <= track_points <= 2000:
        raise ValueError("track_minutes 0..3000 and track_points 2..2000")
    el = propagate(el0, dt, bc)
    result: dict = {"reentered": el["reentered"]}
    if el["reentered"]:
        result["reentry_jd"] = jd0 + el["reentry_after"] / DAY
        result["status"] = "re-entered"
        result["elements"] = to_public(el)
    else:
        st = state_at(el, jd1)
        period = 2 * math.pi * math.sqrt(el["a"] ** 3 / MU)
        result.update({"status": "orbiting", "lat": st["lat"], "lon": st["lon"], "altitude": st["alt"], "speed": st["speed"],
                       "sunlit": st["sunlit"], "elements": to_public(el), "position_eci": st["r"].tolist(),
                       "velocity_eci": st["v"].tolist(), "julian_date": jd1,
                       "ground_track": ground_track(el, jd1, min(track_minutes * 30, period / 2), track_minutes * 60, track_points)
                       if track_minutes > 0 else []})
        if bc is not None:
            da, _ = drag_rates(el["a"], el["e"], bc)
            result["decay_m_per_day"] = -da * DAY
        if forecast:
            lf = lifetime(el, bc)
            result["lifetime_days"] = lf["days"]
            result["lifetime_beyond_years"] = lf["beyond_years"]
            result["decay_history"] = lf["history"]
            if lf["days"] is not None and lf["days"] < 180:
                result["status"] = "decaying"
    return {"result": result, "units": "m, m/s, degrees, days, Julian dates",
            "assumptions": ["Mean elements with J2 secular drift of node, perigee and mean motion",
                            "Orbit-averaged drag in a static exponential atmosphere (real density changes 2 to 10 times "
                            "with solar activity, so real lifetimes can be shorter or longer)",
                            "Re-entry counted when the perigee falls below 100 km",
                            "Latitude and longitude on a spherical Earth (geocentric)"]}


BURNS = ("prograde", "retrograde", "normal", "antinormal", "radial_out", "radial_in", "circularize", "change_altitude", "deorbit")


@tool(
    domain="physics",
    name="satellite_manoeuvre",
    description=(
        "Fire a satellite's thrusters at time 'at' (after propagating from the epoch with J2 and drag): a burn of "
        "delta_v m/s prograde/retrograde/normal/antinormal/radial_out/radial_in, or a planned manoeuvre: "
        "'circularize' (at the next apoapsis), 'change_altitude' (two-burn Hohmann to target_altitude, circular), "
        "'deorbit' (lower the perigee to 50 km). Propellant use from the rocket equation with the thruster's Isp; "
        "fails if the tanks can't pay for it. Returns the new orbit and its epoch."
    ),
)
def satellite_manoeuvre(orbit: dict, epoch: str, burn: str, at: str | None = None, delta_v: float = 0.0,
                        target_altitude: float | None = None, dry_mass: float = 1000.0, propellant: float = 50.0,
                        isp: float = 220.0, area_m2: float = 10.0, cd: float = 2.2) -> dict:
    if burn not in BURNS:
        raise ValueError(f"burn must be one of {', '.join(BURNS)}")
    if dry_mass <= 0 or propellant < 0 or isp < 0:
        raise ValueError("dry_mass must be positive, propellant and isp not negative")
    if not 0 <= delta_v <= 5000:
        raise ValueError("delta_v must be 0..5000 m/s")
    el0 = from_public(orbit)
    jd0, jd1, dt = _span(epoch, at)
    m_total = dry_mass + propellant
    el = propagate(el0, dt, _bc(m_total, area_m2, cd))
    if el["reentered"]:
        raise ValueError("this satellite has already re-entered the atmosphere")
    r, v = coe_to_rv(el["a"], el["e"], el["i"], el["raan"], el["argp"], el["m"])
    burns, t_after = [], 0.0  # t_after: seconds from 'at' to the end of the manoeuvre

    def unit(vec):
        return vec / np.linalg.norm(vec)

    def dv_vec(kind, mag, rr, vv):
        h = np.cross(rr, vv)
        return mag * {"prograde": unit(vv), "retrograde": -unit(vv), "normal": unit(h), "antinormal": -unit(h),
                      "radial_out": unit(rr), "radial_in": -unit(rr)}[kind]

    def coast(e_, seconds):
        nbar = mean_motion(e_["a"], e_["e"], e_["i"])
        rn, rw = j2_rates(e_["a"], e_["e"], e_["i"])
        return {**e_, "m": (e_["m"] + nbar * seconds) % (2 * math.pi), "raan": e_["raan"] + rn * seconds,
                "argp": e_["argp"] + rw * seconds}

    def time_to_true(e_, nu_target):
        ecc = e_["e"]
        big = 2 * math.atan2(math.sqrt(1 - ecc) * math.sin(nu_target / 2), math.sqrt(1 + ecc) * math.cos(nu_target / 2))
        m_t = big - ecc * math.sin(big)
        return ((m_t - e_["m"]) % (2 * math.pi)) / mean_motion(e_["a"], ecc, e_["i"])

    if burn in ("prograde", "retrograde", "normal", "antinormal", "radial_out", "radial_in"):
        if delta_v <= 0:
            raise ValueError("give delta_v (m/s) for a direct burn")
        v = v + dv_vec(burn, delta_v, r, v)
        burns.append({"at_s": 0.0, "delta_v": delta_v, "direction": burn})
        new = rv_to_coe(r, v)
    elif burn == "circularize":
        ap_wait = time_to_true(el, math.pi) if el["e"] > 1e-6 else 0.0
        e1 = coast(el, ap_wait)
        r1, v1 = coe_to_rv(e1["a"], e1["e"], e1["i"], e1["raan"], e1["argp"], e1["m"])
        need = math.sqrt(MU / np.linalg.norm(r1)) - np.linalg.norm(v1)
        v1 = v1 + unit(v1) * need
        burns.append({"at_s": ap_wait, "delta_v": abs(need), "direction": "prograde" if need >= 0 else "retrograde"})
        new, t_after = rv_to_coe(r1, v1), ap_wait
    elif burn == "change_altitude":
        if target_altitude is None or not 150e3 <= target_altitude <= 400_000e3:
            raise ValueError("change_altitude needs target_altitude between 150 km and 400,000 km (in m)")
        r1 = float(np.linalg.norm(r))
        r2 = RE + target_altitude
        at_ = (r1 + r2) / 2
        v_now = float(np.linalg.norm(v))
        v_tr1 = math.sqrt(MU * (2 / r1 - 1 / at_))
        dv1 = v_tr1 - v_now
        # first burn along the velocity (assumes a near-circular start), then coast half the transfer ellipse
        v = unit(v) * v_tr1
        mid = rv_to_coe(r, v)
        half = time_to_true(mid, math.pi) if mid["e"] > 1e-6 else math.pi * math.sqrt(at_**3 / MU)  # coast to apoapsis
        e2 = coast(mid, half)
        r2v, v2v = coe_to_rv(e2["a"], e2["e"], e2["i"], e2["raan"], e2["argp"], e2["m"])
        dv2 = math.sqrt(MU / np.linalg.norm(r2v)) - float(np.linalg.norm(v2v))
        v2v = v2v + unit(v2v) * dv2
        burns += [{"at_s": 0.0, "delta_v": abs(dv1), "direction": "prograde" if dv1 >= 0 else "retrograde"},
                  {"at_s": half, "delta_v": abs(dv2), "direction": "prograde" if dv2 >= 0 else "retrograde"}]
        new, t_after = rv_to_coe(r2v, v2v), half
    else:  # deorbit: at apoapsis, lower perigee to 50 km
        ap_wait = time_to_true(el, math.pi) if el["e"] > 1e-6 else 0.0
        e1 = coast(el, ap_wait)
        r1, v1 = coe_to_rv(e1["a"], e1["e"], e1["i"], e1["raan"], e1["argp"], e1["m"])
        ra, rp = float(np.linalg.norm(r1)), RE + 50e3
        need = math.sqrt(MU * (2 / ra - 2 / (ra + rp))) - float(np.linalg.norm(v1))
        v1 = v1 + unit(v1) * need
        burns.append({"at_s": ap_wait, "delta_v": abs(need), "direction": "retrograde"})
        new, t_after = rv_to_coe(r1, v1), ap_wait
    total = sum(b["delta_v"] for b in burns)
    if isp <= 0 and total > 0:
        raise ValueError("this satellite has no thrusters")
    used = m_total * (1 - math.exp(-total / (isp * G0))) if total > 0 else 0.0
    if used > propellant + 1e-9:
        dv_max = isp * G0 * math.log(m_total / dry_mass) if propellant > 0 else 0.0
        raise ValueError(f"not enough propellant: this manoeuvre needs {total:.1f} m/s ({used:.1f} kg) but the tanks hold "
                         f"{propellant:.1f} kg (≈ {dv_max:.1f} m/s)")
    new_epoch_jd = jd1 + t_after / DAY
    pub = to_public(new)
    reenters = pub["perigee_alt"] < REENTRY_ALT
    return {"result": {"orbit": pub, "epoch_jd": new_epoch_jd, "burns": burns, "delta_v_total": total,
                       "propellant_used": used, "propellant_left": propellant - used, "will_reenter": reenters,
                       "manoeuvre_seconds": t_after},
            "units": "m, m/s, kg, s; epoch as a Julian date",
            "assumptions": ["Impulsive burns", "Propellant from the rocket equation, Δm = m₀(1 − e^(−Δv / (Isp g₀)))",
                            "change_altitude assumes a near-circular starting orbit"]}


def _look(r_sat: np.ndarray, lat: float, lon: float, jd: float) -> dict:
    th = math.radians(lon) + gmst_rad(jd)
    la = math.radians(lat)
    g = RE * np.array([math.cos(la) * math.cos(th), math.cos(la) * math.sin(th), math.sin(la)])
    los = g - r_sat
    rng = float(np.linalg.norm(los))
    up = g / RE
    elev = math.degrees(math.asin(float(np.dot(-los / rng, up))))
    off = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(los / rng, -r_sat / np.linalg.norm(r_sat)))))))
    return {"range": rng, "elevation_deg": elev, "off_nadir_deg": off, "ground": g}


@tool(
    domain="physics",
    name="satellite_imaging",
    description=(
        "Take a picture from orbit: where the satellite is at 'at', whether a target (lat, lon; default the point "
        "straight below) is in view within the camera's off-nadir limit, the ground sample distance "
        "(IFOV × range, stretched off nadir), the diffraction limit of the aperture (1.22 λ/D × range), the effective "
        "resolution, swath, the footprint box and the Sun's elevation at the target (optical cameras need "
        "daylight; radar works day and night). camera = {type: optical, aperture_m, ifov_urad, pixels_across, "
        "max_off_nadir_deg} or {type: sar, resolution_m, swath_km, min_off_nadir_deg, max_off_nadir_deg}."
    ),
)
def satellite_imaging(orbit: dict, epoch: str, camera: dict, at: str | None = None, target_lat: float | None = None,
                      target_lon: float | None = None, mass: float = 1000.0, area_m2: float = 10.0, cd: float = 2.2) -> dict:
    el0 = from_public(orbit)
    jd0, jd1, dt = _span(epoch, at)
    el = propagate(el0, dt, _bc(mass, area_m2, cd))
    if el["reentered"]:
        raise ValueError("this satellite has re-entered the atmosphere")
    st = state_at(el, jd1)
    kind = camera.get("type", "optical")
    if kind not in ("optical", "sar"):
        raise ValueError("camera type must be optical or sar")
    if target_lat is None or target_lon is None:
        target_lat, target_lon = st["lat"], st["lon"]
    if not -90 <= target_lat <= 90 or not -180 <= target_lon <= 360:
        raise ValueError("target latitude -90..90 and longitude -180..360")
    look = _look(st["r"], target_lat, target_lon, jd1)
    alt = st["alt"]
    s = sun_dir(jd1)
    sun_el = math.degrees(math.asin(float(np.dot(look["ground"] / RE, s))))
    max_off = float(camera.get("max_off_nadir_deg", 30.0))
    min_off = float(camera.get("min_off_nadir_deg", 0.0))
    incidence = 90.0 - look["elevation_deg"]
    reasons = []
    if look["elevation_deg"] <= 0:
        reasons.append("the target is below the satellite's horizon")
    elif look["off_nadir_deg"] > max_off + 1e-6:
        reasons.append(f"the target is {look['off_nadir_deg']:.1f}° off nadir; this camera can point {max_off:g}° at most")
    if kind == "sar" and look["off_nadir_deg"] < min_off:
        reasons.append(f"radar looks sideways: the target must be at least {min_off:g}° off nadir")
    if kind == "optical" and sun_el < 5:
        reasons.append(f"the target is in darkness (Sun {sun_el:.0f}° above the horizon); optical cameras need daylight")
    cos_i = max(math.cos(math.radians(incidence)), 0.05)
    if kind == "optical":
        try:
            ifov = float(camera["ifov_urad"]) * 1e-6
            aperture = float(camera["aperture_m"])
            pixels = float(camera.get("pixels_across", 10_000))
        except (KeyError, TypeError, ValueError):
            raise ValueError("an optical camera needs ifov_urad, aperture_m and pixels_across") from None
        if ifov <= 0 or aperture <= 0 or pixels <= 0:
            raise ValueError("ifov_urad, aperture_m and pixels_across must be positive")
        gsd_nadir = ifov * alt
        gsd = ifov * look["range"] / math.sqrt(cos_i)  # geometric mean of along-track and stretched cross-track
        diffraction = 1.22 * 550e-9 / aperture * look["range"]
        resolution = max(gsd, diffraction)
        swath = pixels * ifov * look["range"] / cos_i
    else:
        try:
            resolution = float(camera["resolution_m"])
            swath = float(camera["swath_km"]) * 1000
        except (KeyError, TypeError, ValueError):
            raise ValueError("a radar camera needs resolution_m and swath_km") from None
        gsd_nadir = gsd = resolution
        diffraction = None
    half_lat = math.degrees(swath / 2 / RE)
    half_lon = half_lat / max(math.cos(math.radians(target_lat)), 0.05)
    tl = (target_lon + 180) % 360 - 180
    return {"result": {
        "possible": not reasons, "reasons": reasons, "camera_type": kind,
        "satellite": {"lat": st["lat"], "lon": st["lon"], "altitude": alt, "sunlit": st["sunlit"]},
        "target": {"lat": target_lat, "lon": tl}, "range": look["range"], "off_nadir_deg": look["off_nadir_deg"],
        "incidence_deg": incidence, "sun_elevation_deg": sun_el,
        "gsd_nadir": gsd_nadir, "gsd": gsd, "diffraction_limit": diffraction, "resolution": resolution, "swath": swath,
        "footprint": {"south": max(-90.0, target_lat - half_lat), "north": min(90.0, target_lat + half_lat),
                      "west": tl - half_lon, "east": tl + half_lon},
        "julian_date": jd1},
        "units": "m, degrees; resolution and swath in m",
        "assumptions": ["Diffraction limit at 550 nm (visible)", "Off-nadir ground pixels stretch as 1/cos(incidence) across track",
                        "Spherical Earth, no terrain or clouds; radar resolution taken from the instrument mode"]}


@tool(
    domain="physics",
    name="orbit_from_parameters",
    description=(
        "Build orbital elements for a satellite from simple parameters at an epoch: perigee and apogee altitude (m), "
        "inclination, and optionally the right ascension of the node, argument of perigee and mean anomaly, or "
        "for a geostationary satellite the longitude it should sit over. Also returns the period and speed."
    ),
)
def orbit_from_parameters(perigee_alt: float, epoch: str, apogee_alt: float | None = None, inclination_deg: float = 0.0,
                          raan_deg: float = 0.0, argp_deg: float = 0.0, m_deg: float = 0.0, longitude_deg: float | None = None) -> dict:
    apogee_alt = perigee_alt if apogee_alt is None else apogee_alt
    if not 100e3 <= perigee_alt <= apogee_alt <= 1e9:
        raise ValueError("need 100 km ≤ perigee_alt ≤ apogee_alt (in m)")
    if not 0 <= inclination_deg <= 180:
        raise ValueError("inclination_deg must be 0..180")
    rp, ra = RE + perigee_alt, RE + apogee_alt
    a, e = (rp + ra) / 2, (ra - rp) / (ra + rp)
    jd = jd_of(epoch)
    if longitude_deg is not None:  # place the satellite over a longitude at the epoch (argument of latitude = RA − Ω)
        if e < 1e-6 and inclination_deg < 5:
            # geostationary: pick the radius whose J2-perturbed angular rate matches Earth's rotation exactly
            w_earth = math.radians(ROTATION["earth"][3]) / DAY
            inc = math.radians(inclination_deg)
            for _ in range(30):
                rn, rw = j2_rates(a, 0.0, inc)
                rate = mean_motion(a, 0.0, inc) + rn + rw
                a *= (rate / w_earth) ** (2 / 3)
        ra_sat = math.radians(longitude_deg) + gmst_rad(jd)
        raan_deg, argp_deg = 0.0, 0.0
        m_deg = math.degrees(ra_sat) % 360
    el = {"a": a, "e": e, "i": math.radians(inclination_deg), "raan": math.radians(raan_deg) % (2 * math.pi),
          "argp": math.radians(argp_deg) % (2 * math.pi), "m": math.radians(m_deg) % (2 * math.pi)}
    pub = to_public(el)
    return {"result": {"orbit": pub, "epoch_jd": jd, "speed_at_perigee": math.sqrt(MU * (2 / rp - 1 / a))},
            "units": "m, degrees, s", "assumptions": ["Two-body elements in Earth's equatorial frame (J2000 axes)"]}
