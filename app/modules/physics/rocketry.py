"""Rocket building and flight: a parts catalogue, staged-rocket design analysis (Δv, TWR, burn times) and a
2D flight integrator around Earth, the Moon or Mars with gravity, pressure-dependent thrust, drag in a
rotating atmosphere, staging, parachutes, landing and orbit prediction.

The flight tool is a pure step function: the caller passes the state and the pilot's controls and gets the
state dt seconds later, so an interactive simulator can call it repeatedly (with time warp)."""
import math

import numpy as np
from scipy.integrate import solve_ivp

from app.core.registry import tool

G0 = 9.80665

# Part catalogue. Masses kg, propellant kg, thrust N, Isp s, sizes m. Engines can be clustered with "count".
PARTS: dict[str, dict] = {
    "capsule": {"name": "Crew capsule", "category": "command", "mass": 6000, "height": 3.6, "width": 3.2, "crew": 3},
    "probe": {"name": "Probe core", "category": "command", "mass": 250, "height": 1.0, "width": 1.4},
    "satellite": {"name": "Satellite payload", "category": "payload", "mass": 1500, "height": 3.0, "width": 2.6},
    "lander": {"name": "Lunar lander cabin", "category": "command", "mass": 2500, "height": 2.6, "width": 3.2, "crew": 2},
    "tank_s": {"name": "Fuel tank S", "category": "tank", "mass": 1200, "prop": 12000, "height": 3.0, "width": 3.2},
    "tank_m": {"name": "Fuel tank M", "category": "tank", "mass": 2500, "prop": 30000, "height": 6.0, "width": 3.2},
    "tank_l": {"name": "Fuel tank L", "category": "tank", "mass": 5000, "prop": 70000, "height": 12.0, "width": 3.2},
    "tank_xl": {"name": "Fuel tank XL", "category": "tank", "mass": 12000, "prop": 180000, "height": 24.0, "width": 3.7},
    "engine_booster": {"name": "Kestrel booster engine", "category": "engine", "mass": 470, "height": 2.5, "width": 1.2,
                       "thrust_sl": 845e3, "thrust_vac": 914e3, "isp_sl": 282, "isp_vac": 311},
    "engine_vacuum": {"name": "Kestrel-V vacuum engine", "category": "engine", "mass": 490, "height": 3.6, "width": 2.0,
                      "thrust_sl": 420e3, "thrust_vac": 981e3, "isp_sl": 150, "isp_vac": 348},
    "engine_heavy": {"name": "Titan heavy engine", "category": "engine", "mass": 5400, "height": 3.6, "width": 3.2,
                     "thrust_sl": 3830e3, "thrust_vac": 4150e3, "isp_sl": 311, "isp_vac": 338},
    "engine_lander": {"name": "Hopper lander engine", "category": "engine", "mass": 150, "height": 1.2, "width": 1.0,
                      "thrust_sl": 40e3, "thrust_vac": 45e3, "isp_sl": 290, "isp_vac": 320},
    "decoupler": {"name": "Stage decoupler", "category": "structural", "mass": 150, "height": 0.5, "width": 3.2},
    "nose": {"name": "Nose cone / fairing", "category": "aero", "mass": 300, "height": 3.0, "width": 3.2},
    "parachute": {"name": "Parachute", "category": "recovery", "mass": 120, "height": 0.6, "width": 1.6},
    "legs": {"name": "Landing legs", "category": "recovery", "mass": 250, "height": 0.6, "width": 3.6},
}

BODIES = {
    # radius m, μ m³/s², sidereal rotation rad/s (negative = surface moves toward +x, i.e. "east" is right),
    # sea-level density kg/m³, scale height m, top of atmosphere m
    "earth": {"name": "Earth", "radius": 6_371_000.0, "mu": 3.986004418e14, "omega": -7.2921159e-5, "rho0": 1.225, "H": 8_500.0, "top": 140_000.0, "sound": 340.0},
    "moon": {"name": "Moon", "radius": 1_737_400.0, "mu": 4.9048695e12, "omega": -2.6617e-6, "rho0": 0.0, "H": 1.0, "top": 0.0, "sound": 1.0},
    "mars": {"name": "Mars", "radius": 3_389_500.0, "mu": 4.282837e13, "omega": -7.088218e-5, "rho0": 0.020, "H": 11_100.0, "top": 120_000.0, "sound": 240.0},
}
SAFE_LANDING = 10.0  # m/s touchdown speed survivable without legs (capsule splashdown class)
SAFE_LANDING_LEGS = 16.0
CHUTE_CDA = 1500.0  # m², deployed parachute drag area × Cd (Apollo-class main chutes)


def _body(name: str) -> dict:
    if name not in BODIES:
        raise ValueError(f"body must be one of {', '.join(BODIES)}")
    return BODIES[name]


def _parse(parts: list) -> list[dict]:
    if not isinstance(parts, list) or not parts:
        raise ValueError("parts must be a non-empty list, bottom to top, e.g. [{'part': 'engine_booster', 'count': 9}, {'part': 'tank_l'}]")
    if len(parts) > 60:
        raise ValueError("at most 60 parts")
    out = []
    for p in parts:
        pid = p.get("part") if isinstance(p, dict) else p
        count = int(p.get("count", 1)) if isinstance(p, dict) else 1
        if pid not in PARTS:
            raise ValueError(f"unknown part {pid!r}; choose from {', '.join(PARTS)}")
        if not 1 <= count <= 9 or (count > 1 and PARTS[pid]["category"] != "engine"):
            raise ValueError("count must be 1..9 and only engines can be clustered")
        out.append({**PARTS[pid], "id": pid, "count": count})
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
    for s in stages:
        engines = [p for p in s if p["category"] == "engine"]
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
            "chute": any(p["id"] == "parachute" for p in s),
            "legs": any(p["id"] == "legs" for p in s),
            "command": any(p["category"] == "command" for p in s),
        })
    return out


@tool(
    domain="physics",
    name="rocket_design",
    description=(
        "Analyse a rocket built from catalogue parts (bottom to top; decouplers split stages): per-stage mass, "
        "propellant, thrust, Isp, Δv (sea level and vacuum, Tsiolkovsky), thrust-to-weight on the chosen body, burn "
        "time, plus totals and design warnings. Parts: " + ", ".join(PARTS) + ". Example: parts=[{'part':'engine_booster',"
        "'count':9},{'part':'tank_xl'},{'part':'decoupler'},{'part':'engine_vacuum'},{'part':'tank_m'},{'part':'capsule'}]."
    ),
)
def rocket_design(parts: list, body: str = "earth") -> dict:
    b = _body(body)
    ps = _parse(parts)
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
        })
        total_vac += dv_vac
        total_sl += dv_sl
        if s["prop"] and not s["mdot"]:
            warnings.append(f"stage {k} carries propellant but has no engine")
        if s["mdot"] and not s["prop"]:
            warnings.append(f"stage {k} has engines but no fuel tank")
    if not any(s["command"] for s in stages) and not any(p["category"] == "payload" for p in ps):
        warnings.append("no capsule, probe or payload on top")
    if rows and rows[0]["twr_surface"] <= 1:
        warnings.append(f"lift-off thrust-to-weight {rows[0]['twr_surface']:.2f} ≤ 1: the rocket cannot leave the pad on {b['name']}")
    orbit_v = math.sqrt(b["mu"] / (b["radius"] + (200e3 if body == "earth" else 50e3)))
    return {
        "result": {
            "stages": rows,
            "total_mass": sum(s["dry"] + s["prop"] for s in stages),
            "total_delta_v_vac": total_vac, "total_delta_v_sl": total_sl,
            "height": sum(p["height"] for p in ps), "width": max(p["width"] for p in ps),
            "reference_orbit_speed": orbit_v,
            "delta_v_to_orbit_estimate": {"earth": 9400.0, "moon": 1870.0, "mars": 4100.0}[body],
            "warnings": warnings,
        },
        "units": "masses in kg, thrust in N, Isp in s, Δv and speeds in m/s, time in s, sizes in m",
        "assumptions": ["Tsiolkovsky Δv per stage with all upper stages as payload",
                        "Clustered engines of different types combine by thrust-weighted Isp",
                        "Δv to orbit estimates include typical gravity and drag losses"],
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


@tool(
    domain="physics",
    name="rocket_launch_state",
    description="Initial flight state of a rocket standing on the launch pad of a body (earth, moon or mars), for rocket_flight.",
)
def rocket_launch_state(parts: list, body: str = "earth") -> dict:
    b = _body(body)
    stages = _stages(_parse(parts))
    R = b["radius"]
    state = {"t": 0.0, "x": 0.0, "y": R, "vx": -b["omega"] * R, "vy": 0.0, "angle": math.pi / 2, "stage": 0,
             "props": [s["prop"] for s in stages], "landed": True, "crashed": False, "chute": False, "body": body}
    return {"result": state, "units": "SI (m, m/s, kg, rad, s); planet-centred inertial frame, pad at (0, R)",
            "assumptions": ["The pad rotates with the planet, so the rocket starts with the surface speed"]}


@tool(
    domain="physics",
    name="rocket_flight",
    description=(
        "Advance a rocket's 2D flight by dt seconds (use with time warp): gravity, thrust with pressure-dependent Isp, "
        "drag in a rotating exponential atmosphere, propellant use, staging (stage=True drops the lowest stage), "
        "parachute, touchdown (landed or crashed) and orbit elements. state comes from rocket_launch_state or a "
        "previous call; throttle 0..1; angle is the rocket's pointing direction in radians (inertial, from +x). "
        "Returns the new state, telemetry, events and the predicted trajectory for a map view."
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
) -> dict:
    b = _body(str(state.get("body", "earth")))
    stages = _stages(_parse(parts))
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
    ang = float(state.get("angle", math.pi / 2)) if angle is None else float(angle)
    landed, crashed, chute = bool(state.get("landed")), bool(state.get("crashed")), bool(state.get("chute"))
    events: list[str] = []
    R, mu, om = b["radius"], b["mu"], b["omega"]
    if crashed:
        throttle = 0.0
    if stage and k < len(stages) - 1:
        events.append(f"stage {k} separated")
        k += 1
    upper = stages[k:]
    if deploy_chute and not chute and any(s["chute"] for s in upper):
        chute = True
        events.append("parachute deployed")
    st = stages[k]
    dry = sum(s["dry"] for s in upper) + sum(props[j] for j in range(k + 1, len(stages)))
    width = max(s["width"] for s in upper)
    cd = 0.3 if any(s["nose"] for s in upper) else 0.75
    cda = cd * math.pi * (width / 2) ** 2 + (CHUTE_CDA if chute else 0.0)
    legs = any(s["legs"] for s in upper)
    burning = throttle > 0 and st["mdot"] > 0 and props[k] > 0 and not crashed

    def accel(xx, yy, vxx, vyy, mprop, on):
        r = math.hypot(xx, yy)
        m = dry + mprop
        ax, ay = -mu * xx / r**3, -mu * yy / r**3
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

    # On the ground: stay put (co-rotating) unless thrust beats weight
    if landed and not crashed:
        g = mu / (x * x + y * y)
        m = dry + props[k]
        frac = _density(b, 0) / b["rho0"] if b["rho0"] > 0 else 0.0
        f = throttle * (st["thrust_vac"] - (st["thrust_vac"] - st["thrust_sl"]) * frac) if burning else 0.0
        radial = f * ((x * math.cos(ang) + y * math.sin(ang)) / math.hypot(x, y))
        if radial <= m * g:
            th = om * dt
            c, s_ = math.cos(th), math.sin(th)
            x, y = x * c - y * s_, x * s_ + y * c
            vx, vy = -om * y, om * x
            if burning:
                used = min(props[k], throttle * st["mdot"] * dt)
                props[k] -= used
            t += dt
            return _result(b, stages, t, x, y, vx, vy, ang, k, props, True, False, chute, events, throttle, dry, st, cda, predict)
        landed = False
        events.append("lift-off")

    def rhs(_t, s):
        on = burning
        ax, ay = accel(s[0], s[1], s[2], s[3], s[4], on)
        dm = -throttle * st["mdot"] if on and s[4] > 0 else 0.0
        return [s[2], s[3], ax, ay, dm]

    def ground(_t, s):
        return math.hypot(s[0], s[1]) - R
    ground.terminal, ground.direction = True, -1

    def empty(_t, s):
        return s[4]
    empty.terminal, empty.direction = True, -1

    y0 = [x, y, vx, vy, props[k]]
    remaining, tt = dt, 0.0
    alt0 = math.hypot(x, y) - R
    fine = burning or (b["top"] > 0 and alt0 < b["top"] * 1.2) or alt0 < 5_000
    max_step = 0.25 if fine else max(1.0, dt / 200)
    while remaining > 1e-9:
        evs = [ground] + ([empty] if burning else [])
        sol = solve_ivp(rhs, (0, remaining), y0, method="DOP853" if not fine else "RK45", rtol=1e-9, atol=1e-6,
                        max_step=max_step, events=evs)
        y0 = list(sol.y[:, -1])
        tt += sol.t[-1]
        remaining -= sol.t[-1]
        if sol.status == 1 and len(sol.t_events[0]):  # touched the ground
            gx, gy, gvx, gvy = y0[:4]
            rvx, rvy = gvx - (-om * gy), gvy - (om * gx)
            impact = math.hypot(rvx, rvy)
            r = math.hypot(gx, gy)
            y0[0], y0[1] = gx * R / r, gy * R / r
            if impact <= (SAFE_LANDING_LEGS if legs else SAFE_LANDING):
                landed = True
                y0[2], y0[3] = -om * y0[1], om * y0[0]
                events.append(f"touchdown at {impact:.1f} m/s")
            else:
                crashed = True
                y0[2], y0[3] = -om * y0[1], om * y0[0]
                events.append(f"crashed at {impact:.0f} m/s")
            # remaining time is spent sitting on the surface
            th = om * remaining
            c, s_ = math.cos(th), math.sin(th)
            y0[0], y0[1] = y0[0] * c - y0[1] * s_, y0[0] * s_ + y0[1] * c
            y0[2], y0[3] = -om * y0[1], om * y0[0]
            tt += remaining
            remaining = 0
            break
        if sol.status == 1 and burning and len(sol.t_events) > 1 and len(sol.t_events[1]):
            y0[4] = 0.0
            burning = False
            events.append(f"stage {k} out of fuel")
    x, y, vx, vy, props[k] = y0
    props[k] = max(0.0, props[k])
    t += tt
    return _result(b, stages, t, x, y, vx, vy, ang, k, props, landed, crashed, chute, events, throttle, dry, st, cda, predict)


def _result(b, stages, t, x, y, vx, vy, ang, k, props, landed, crashed, chute, events, throttle, dry, st, cda, predict):
    R, mu, om = b["radius"], b["mu"], b["omega"]
    r = math.hypot(x, y)
    alt = r - R
    ux, uy = x / r, y / r
    rvx, rvy = vx - (-om * y), vy - (om * x)
    m = dry + props[k]
    rho = _density(b, alt)
    frac = rho / b["rho0"] if b["rho0"] > 0 else 0.0
    thrust = throttle * (st["thrust_vac"] - (st["thrust_vac"] - st["thrust_sl"]) * frac) if props[k] > 0 and st["mdot"] > 0 and not crashed else 0.0
    el = _elements(b, x, y, vx, vy)
    if crashed:
        status = "crashed"
    elif landed:
        status = "landed"
    elif el["specific_energy"] >= 0:
        status = "escape trajectory"
    elif el["periapsis_alt"] > max(b["top"], 10_000.0):
        status = "orbit"
    else:
        status = "suborbital"
    # Δv left (vacuum) from the current stage upward, with the propellant actually remaining
    dv_left, mass_above = 0.0, 0.0
    for j in range(len(stages) - 1, k - 1, -1):
        s = stages[j]
        m_start = mass_above + s["dry"] + props[j]
        if s["mdot"] and props[j] > 0:
            dv_left += s["isp_vac"] * G0 * math.log(m_start / (m_start - props[j]))
        mass_above = m_start
    q = 0.5 * rho * (rvx * rvx + rvy * rvy)
    state = {"t": t, "x": x, "y": y, "vx": vx, "vy": vy, "angle": ang, "stage": k, "props": props,
             "landed": landed, "crashed": crashed, "chute": chute, "body": [n for n, v in BODIES.items() if v is b][0]}
    speed_surface = math.hypot(rvx, rvy)
    telemetry = {
        "altitude": alt, "speed": math.hypot(vx, vy), "surface_speed": speed_surface,
        "vertical_speed": vx * ux + vy * uy, "horizontal_speed": vx * uy - vy * ux,  # + = east (direction of rotation)
        "downrange_angle_deg": math.degrees(math.atan2(x, y)),
        "mass": m, "thrust": thrust, "twr": thrust / (m * mu / r**2),
        "acceleration_g": (thrust + 0.5 * rho * speed_surface**2 * cda) / m / G0,
        "dynamic_pressure": q, "mach": speed_surface / b["sound"] if rho > 0 else None, "air_density": rho,
        "stage_fuel_fraction": props[k] / stages[k]["prop"] if stages[k]["prop"] else 0.0,
        "delta_v_remaining": dv_left, "status": status,
        "apoapsis_alt": el["apoapsis_alt"], "periapsis_alt": el["periapsis_alt"], "eccentricity": el["eccentricity"],
        "period": el["period"], "stages_left": len(stages) - k,
    }
    return {
        "result": {"state": state, "telemetry": telemetry, "events": events},
        "trajectory": _predict(b, x, y, vx, vy) if predict and not landed and not crashed else [],
        "planet": {"radius": R, "atmosphere_top": b["top"], "name": b["name"]},
        "units": "SI: m, m/s, kg, N, s, Pa, kg/m³; angles in radians unless noted",
        "assumptions": ["2D point-mass flight in the planet's equatorial plane; attitude is set by the pilot",
                        "Exponential atmosphere co-rotating with the planet; Cd 0.3 with a nose cone, 0.75 without",
                        "Thrust interpolates between sea-level and vacuum values with ambient pressure"],
    }


@tool(
    domain="physics",
    name="rocket_parts",
    description="The rocket parts catalogue (ids, names, categories, masses, propellant, thrust, Isp, sizes) and the flyable bodies.",
)
def rocket_parts() -> dict:
    return {
        "result": {"parts": [{"id": k, **v} for k, v in PARTS.items()],
                   "bodies": {k: {"name": v["name"], "radius": v["radius"], "atmosphere_top": v["top"],
                                  "surface_gravity": v["mu"] / v["radius"] ** 2} for k, v in BODIES.items()}},
        "units": "masses in kg, thrust in N, Isp in s, sizes in m, gravity in m/s²",
        "assumptions": ["Generic parts with values typical of real kerosene/oxygen hardware"],
    }
