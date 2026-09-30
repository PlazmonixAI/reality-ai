"""Real launch vehicles and satellites: the catalogue, launch azimuth and Earth-rotation assist from a real site,
and how much payload a vehicle can put into a given orbit (from its staged Δv)."""
import math

from app.core.registry import tool
from app.modules.physics.rocketry import BODIES, G0, _parse, _stages, burn_phases, stage_mass
from app.modules.physics.vehicle_data import SATELLITES, SITES, VEHICLE_PARTS, VEHICLES

MU_E = BODIES["earth"]["mu"]
R_E = BODIES["earth"]["radius"]
OMEGA_E = 7.2921159e-5
LEO_LOSSES = 1_750.0  # typical gravity + drag + steering losses on the way to low orbit, m/s


def azimuth(site_lat_deg: float, inc_deg: float, alt: float = 200e3) -> dict:
    """Launch azimuth for a target inclination from a site, the Earth-rotation help it gets, and the Δv penalty
    compared with launching due east. Inclinations below the site latitude need a plane change (dog-leg)."""
    lat, inc = math.radians(site_lat_deg), math.radians(inc_deg)
    v_orb = math.sqrt(MU_E / (R_E + alt))
    v_rot = OMEGA_E * R_E * math.cos(lat)
    reachable = abs(math.cos(inc)) <= math.cos(lat) + 1e-12
    if reachable:
        beta = math.asin(max(-1.0, min(1.0, math.cos(inc) / math.cos(lat))))  # inertial azimuth from north
        # correct for the rotating launch site: aim the relative velocity
        vx, vy = v_orb * math.sin(beta) - v_rot, v_orb * math.cos(beta)
        az = math.degrees(math.atan2(vx, vy))
        need = math.hypot(vx, vy)
        plane_change = 0.0
    else:
        az = 90.0
        need = v_orb - v_rot
        di = abs(inc) - abs(lat)
        plane_change = 2 * v_orb * math.sin(abs(math.radians(inc_deg) - lat) / 2) if di < 0 else 0.0
    east = v_orb - v_rot
    south = (180 - az) % 360 if reachable else 90.0  # the same inclination flown on the southbound pass
    return {"azimuth_deg": az % 360, "azimuth_south_deg": south, "rotation_assist": v_rot * (math.sin(math.radians(az)) if reachable else 1.0),
            "delta_v_vs_due_east": need - east + plane_change, "direct": reachable, "plane_change_delta_v": plane_change,
            "orbit_speed": v_orb}


@tool(
    domain="physics",
    name="launch_azimuth",
    description=(
        "Launch azimuth to reach an orbit inclination from a launch site latitude, the Earth-rotation speed the "
        "rocket gets for free and the extra Δv compared with launching due east (sun-synchronous and polar orbits "
        "cost more; inclinations below the site latitude need a dog-leg plane change). Example: "
        "site_latitude_deg=13.72 (Sriharikota), inclination_deg=97.5."
    ),
)
def launch_azimuth(site_latitude_deg: float, inclination_deg: float, orbit_altitude: float = 200e3) -> dict:
    if not -90 < site_latitude_deg < 90 or not 0 <= inclination_deg <= 180 or not 100e3 <= orbit_altitude <= 2_000e3:
        raise ValueError("site latitude in (-90, 90), inclination 0..180°, orbit altitude 100..2000 km (in m)")
    out = azimuth(site_latitude_deg, inclination_deg, orbit_altitude)
    return {"result": out, "units": "degrees, m/s",
            "assumptions": ["Spherical Earth; the azimuth accounts for the site's eastward speed",
                            "Plane change for too-low inclinations done at orbit speed (upper bound; real dog-legs "
                            "spread it through the ascent)"]}


def _target_dv(target: str, site_lat: float) -> tuple[float, str]:
    """Δv from the pad for a target orbit, including ascent losses and the site's rotation help."""
    r0 = R_E + 200e3
    vc = math.sqrt(MU_E / r0)
    v_rot = OMEGA_E * R_E * math.cos(math.radians(site_lat))
    leo = vc + LEO_LOSSES + 400.0 - v_rot
    if target == "leo":
        return leo, "200 km circular orbit launched due east"
    if target == "sso":
        r = R_E + 600e3
        at = (r0 + r) / 2
        climb = (math.sqrt(MU_E * (2 / r0 - 1 / at)) - vc) + (math.sqrt(MU_E / r) - math.sqrt(MU_E * (2 / r - 1 / at)))
        return leo + azimuth(site_lat, 97.8)["delta_v_vs_due_east"] + climb, "600 km sun-synchronous orbit (97.8°)"
    if target == "gto":
        at = (r0 + 42_164e3) / 2
        return leo + math.sqrt(MU_E * (2 / r0 - 1 / at)) - vc, "geostationary transfer orbit (200 km × 35,786 km)"
    if target == "tli":
        atl = (r0 + 384_400e3) / 2
        return leo + math.sqrt(MU_E * (2 / r0 - 1 / atl)) - vc, "trans-lunar injection from a 200 km parking orbit"
    if target == "mars":
        return leo + math.sqrt(2945.0**2 + 2 * MU_E / r0) - vc, "Hohmann trans-Mars injection from a 200 km parking orbit"
    raise ValueError("target must be leo, sso, gto, tli or mars")


def _vehicle(vehicle: str) -> dict:
    if vehicle not in VEHICLES:
        raise ValueError(f"unknown vehicle {vehicle!r}; choose from {', '.join(VEHICLES)}")
    return VEHICLES[vehicle]


def with_payload(vehicle: str, payload_kg: float) -> tuple[list, dict]:
    """The vehicle's stack with its example payload replaced by a plain payload of the given mass."""
    from app.modules.physics.rocketry import PARTS
    v = _vehicle(vehicle)
    out = []
    for p in v["parts"]:
        cat = {**PARTS, **VEHICLE_PARTS}[p["part"]]["category"]
        if p["part"].startswith("fairing") or p["part"] == "nose":
            continue  # jettisoned early in the ascent, so it costs little Δv
        if cat in ("satellite", "command"):
            if not any(q["part"] == "custom_payload" for q in out):
                out.append({"part": "custom_payload"})
        else:
            out.append(p)
    return out, {"custom_payload": {"category": "satellite", "name": "Payload", "mass": max(1.0, payload_kg), "height": 3.0, "width": 2.0}}


def total_dv(parts: list, custom: dict | None = None) -> float:
    stages = _stages(_parse(parts, custom))
    dv = 0.0
    for k, s in enumerate(stages):
        m0 = sum(stage_mass(x) for x in stages[k:])
        dv += burn_phases(s, m0, s["prop"], s["boosters"]["prop"] if s["boosters"] else 0.0)["delta_v_vac"]
    return dv


@tool(
    domain="physics",
    name="launch_vehicle_performance",
    description=(
        "How much payload a real launch vehicle (PSLV-XL, GSLV Mk II, LVM3, SSLV, Falcon 9, Falcon Heavy, Starship, "
        "Saturn V, SLS, Ariane 5, Soyuz-2.1b, Long March 5, Electron) can put into leo, sso, gto, tli or mars from its "
        "usual launch site: the payload whose staged vacuum Δv equals the orbit's Δv budget (with typical ascent "
        "losses and the site's Earth-rotation help), compared with the published figure."
    ),
)
def launch_vehicle_performance(vehicle: str, target: str = "leo") -> dict:
    v = _vehicle(vehicle)
    site = SITES[v["site"]]
    need, what = _target_dv(target, site["latitude"])
    lo, hi = 0.0, 400_000.0
    if total_dv(*with_payload(vehicle, 1.0)) < need:
        best = 0.0
    else:
        for _ in range(60):
            mid = (lo + hi) / 2
            (lo, hi) = (mid, hi) if total_dv(*with_payload(vehicle, mid)) >= need else (lo, mid)
        best = lo
    published = v.get({"leo": "payload_leo_kg", "sso": "payload_sso_kg", "gto": "payload_gto_kg", "tli": "payload_tli_kg"}.get(target, ""))
    return {
        "result": {"vehicle": v["name"], "target": what, "delta_v_needed": need, "max_payload_kg": best,
                   "published_payload_kg": published, "ratio_to_published": best / published if published else None,
                   "site": site["name"], "liftoff_mass": sum(stage_mass(s) for s in _stages(_parse(*with_payload(vehicle, best))))},
        "units": "kg, m/s",
        "assumptions": [f"Ascent losses of about {LEO_LOSSES:.0f} m/s plus 400 m/s for steering and margins",
                        "Staged vacuum Δv with parallel strap-on boosters; the fairing and escape tower are left out (dropped early); crew "
                        "spacecraft count as payload; published payloads use optimised "
                        "trajectories, reserves and sometimes different launch sites, so expect differences of 10 to 30 %",
                        "Stage figures are rounded public numbers"],
    }


@tool(
    domain="physics",
    name="launch_vehicle_catalog",
    description=(
        "Real launch vehicles (ISRO, NASA, SpaceX, ESA, Roscosmos, CNSA, Rocket Lab) as flyable stacks of real stages "
        "and strap-on boosters, their launch sites and published payloads, plus real satellites (Cartosat-3, "
        "EOS-05/GISAT-1A, EOS-04/RISAT-1A, Landsat 9, Sentinel-2A, WorldView-3, INSAT-3DS, Starlink, GPS III, Hubble) "
        "with their instruments and usual orbits."
    ),
)
def launch_vehicle_catalog() -> dict:
    vehicles = []
    for vid, v in VEHICLES.items():
        stages = _stages(_parse(v["parts"]))
        vehicles.append({"id": vid, **{k: v[k] for k in v if k != "parts"}, "parts": v["parts"],
                         "site_info": SITES[v["site"]], "stages": len(stages),
                         "liftoff_mass": sum(stage_mass(s) for s in stages),
                         "liftoff_thrust": stages[0]["thrust_sl"] + (stages[0]["boosters"]["thrust_sl"] if stages[0]["boosters"] else 0.0),
                         "height": sum(VEHICLE_PARTS.get(p["part"], {}).get("height", 0) for p in v["parts"]
                                       if VEHICLE_PARTS.get(p["part"], {}).get("category") != "booster")})
    return {
        "result": {"vehicles": vehicles, "parts": [{"id": k, **p} for k, p in VEHICLE_PARTS.items()],
                   "satellites": [{"id": k, **s} for k, s in SATELLITES.items()], "sites": SITES},
        "units": "kg, N, s, m, degrees",
        "assumptions": ["Rounded public figures (agency fact sheets, press kits and standard references); some thrusts "
                        "are derived from propellant mass, burn time and Isp"],
    }


__all__ = ["azimuth", "launch_azimuth", "launch_vehicle_catalog", "launch_vehicle_performance", "G0"]
