"""Your own space company: satellites and probes that stay in orbit (or in flight) in real time.

Everything physical is computed by engine tools (satellite_track, satellite_manoeuvre, satellite_imaging,
orbit_from_parameters, interplanetary_mission, the vehicle catalogue); this layer stores the results per user
and applies the rules (a rocket can only lift what its Δv allows, burns spend real propellant)."""
from __future__ import annotations

import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.runner import ToolInputError
from app.modules.physics import fleet, interplanetary, vehicles
from app.modules.physics.vehicle_data import SATELLITES, SITES, VEHICLES
from app.platform import db
from app.platform.auth import current_user
from app.platform.history import save_run

router = APIRouter(prefix="/api/company", tags=["company"])
MAX_SPACECRAFT = 60
DAY = 86_400.0


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jd_to_ts(jd: float) -> float:
    return (jd - 2440587.5) * DAY


def engine(fn, **kw):
    """Call an engine function, turning bad input into a 422 with its message."""
    try:
        return fn(**kw)
    except (ValueError, ToolInputError) as e:
        raise HTTPException(422, str(e)) from None


# ---------------------------------------------------------------- helpers
def _company(conn, uid: str):
    return conn.execute("SELECT * FROM companies WHERE user_id = ?", (uid,)).fetchone()


def _require_company(conn, uid: str):
    row = _company(conn, uid)
    if row is None:
        raise HTTPException(409, "Found your space company first.")
    return row


def _craft(conn, uid: str, cid: str):
    row = conn.execute("SELECT * FROM spacecraft WHERE id = ? AND user_id = ?", (cid, uid)).fetchone()
    if row is None:
        raise HTTPException(404, "No such spacecraft in your fleet")
    return row


def _log(conn, row, message: str, extra: dict | None = None) -> None:
    log = db.loads(row["log"]) or []
    log.append({"t": time.time(), "event": message, **(extra or {})})
    conn.execute("UPDATE spacecraft SET log = ? WHERE id = ?", (db.dumps(log[-200:]), row["id"]))


def _spec_mass(spec: dict, propellant: float) -> float:
    return float(spec["dry_mass"]) + propellant


def live(row, detail: bool = False) -> dict[str, Any]:
    """Current state of a spacecraft, computed now."""
    spec, orbit = db.loads(row["spec"]), db.loads(row["orbit"])
    base = {"id": row["id"], "kind": row["kind"], "name": row["name"], "spec": spec, "propellant": row["propellant"],
            "created_at": row["created_at"], "epoch": row["epoch"], "status": row["status"]}
    if detail:
        base["log"] = db.loads(row["log"])
    now = time.time()
    if row["kind"] == "probe":
        m = engine(interplanetary.interplanetary_mission, depart=iso(orbit["depart_ts"]), origin=orbit["origin"], target=orbit["target"],
                   tof_days=orbit["tof_days"], at=iso(now), n_points=120 if detail else 20)["result"]
        base["mission"] = {k: m[k] for k in ("origin", "target", "depart", "arrive", "tof_days", "c3_km2s2", "departure_burn",
                                                "capture_burn", "vinf_arrival", "now")}
        base["mission"]["capture"] = orbit.get("capture", False)
        if detail:
            base["mission"].update({k: m[k] for k in ("path_au", "origin_orbit_au", "target_orbit_au", "origin_at_departure_au",
                                                      "target_at_arrival_au", "transfer_orbit")})
        phase = m["now"]["phase"]
        base["status"] = {"waiting for launch": "scheduled", "cruise": "in cruise"}.get(phase, "in orbit" if orbit.get("capture") else "flew by")
        return base
    if row["status"] == "re-entered":
        return base
    r = engine(fleet.satellite_track, orbit=orbit, epoch=iso(row["epoch"]), at=iso(now), mass=_spec_mass(spec, row["propellant"]),
               area_m2=spec.get("area_m2", 10.0), cd=spec.get("cd", 2.2), track_minutes=100 if detail else 0,
               track_points=121 if detail else 2, forecast=detail)["result"]
    base.update({k: r.get(k) for k in ("status", "lat", "lon", "altitude", "speed", "sunlit", "elements", "decay_m_per_day",
                                       "lifetime_days", "lifetime_beyond_years", "reentry_jd")})
    if detail:
        base["ground_track"] = r.get("ground_track", [])
        base["decay_history"] = r.get("decay_history", [])
        base["delta_v_available"] = spec.get("isp", 0) * 9.80665 * math.log(_spec_mass(spec, row["propellant"]) / spec["dry_mass"]) \
            if spec.get("isp") and row["propellant"] > 0 else 0.0
    return base


def _refresh(conn, row) -> None:
    """Mark re-entries and move the stored epoch forward now and then so propagation stays short."""
    if row["kind"] != "satellite" or row["status"] == "re-entered":
        return
    now = time.time()
    if now - row["epoch"] < 2 * DAY:
        return
    spec, orbit = db.loads(row["spec"]), db.loads(row["orbit"])
    el = fleet.propagate(fleet.from_public(orbit), now - row["epoch"],
                         fleet._bc(_spec_mass(spec, row["propellant"]), spec.get("area_m2", 10.0), spec.get("cd", 2.2)))
    if el["reentered"]:
        when = row["epoch"] + el["reentry_after"]
        conn.execute("UPDATE spacecraft SET status = 're-entered' WHERE id = ?", (row["id"],))
        _log(conn, row, f"Re-entered the atmosphere and burned up ({iso(when)[:10]})", {"at": when})
    else:
        conn.execute("UPDATE spacecraft SET orbit = ?, epoch = ? WHERE id = ?", (db.dumps(fleet.to_public(el)), now, row["id"]))


def _insert(conn, uid: str, kind: str, name: str, spec: dict, orbit: dict, epoch: float, propellant: float, first_log: str) -> str:
    (n,) = conn.execute("SELECT COUNT(*) FROM spacecraft WHERE user_id = ? AND status != 're-entered'", (uid,)).fetchone()
    if n >= MAX_SPACECRAFT:
        raise HTTPException(409, f"Your fleet is full ({MAX_SPACECRAFT} active spacecraft). Retire some first.")
    cid = db.new_id("sc")
    conn.execute("INSERT INTO spacecraft (id, user_id, kind, name, spec, orbit, epoch, propellant, status, log, created_at) "
                 "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                 (cid, uid, kind, name, db.dumps(spec), db.dumps(orbit), epoch, propellant,
                  "orbiting" if kind == "satellite" else "scheduled", db.dumps([{"t": time.time(), "event": first_log}]), time.time()))
    return cid


def satellite_spec(sat_id: str | None, custom: dict | None) -> tuple[str, dict, float]:
    """(name, spec, propellant) for a catalogue satellite or a user-designed one."""
    if sat_id:
        if sat_id not in SATELLITES:
            raise HTTPException(422, f"Unknown satellite {sat_id!r}")
        s = SATELLITES[sat_id]
        f = s["fleet"]
        spec = {"catalog": sat_id, "agency": s["agency"], "purpose": s["purpose"], "dry_mass": s["mass"] - f["propellant_kg"],
                "area_m2": f["area_m2"], "cd": f["cd"], "isp": f["isp"], "thrust": f["thrust"], "camera": f["camera"]}
        return s["name"], spec, float(f["propellant_kg"])
    if not isinstance(custom, dict):
        raise HTTPException(422, "Choose a satellite from the catalogue or describe your own")
    try:
        dry = float(custom["dry_mass"])
        prop = float(custom.get("propellant", 0))
        spec = {"dry_mass": dry, "area_m2": float(custom.get("area_m2", 4.0)), "cd": 2.2, "isp": float(custom.get("isp", 220)),
                "thrust": float(custom.get("thrust", 1.0)), "camera": custom.get("camera"), "purpose": str(custom.get("purpose", ""))[:120]}
    except (KeyError, TypeError, ValueError):
        raise HTTPException(422, "A custom satellite needs dry_mass (kg), and optionally propellant, area_m2, isp, thrust, camera") from None
    if not 1 <= dry <= 50_000 or not 0 <= prop <= 20_000 or not 0.01 <= spec["area_m2"] <= 500 or not 0 <= spec["isp"] <= 10_000:
        raise HTTPException(422, "dry_mass 1..50,000 kg, propellant 0..20,000 kg, area 0.01..500 m², Isp 0..10,000 s")
    cam = spec["camera"]
    if cam is not None:
        if not isinstance(cam, dict) or cam.get("type") not in ("optical", "sar"):
            raise HTTPException(422, "camera must be an object with type optical or sar")
    return str(custom.get("name") or "My satellite")[:48], spec, prop


def orbit_delta_v(site_lat: float, perigee_alt: float, apogee_alt: float, inclination: float) -> float:
    """Δv from the pad to an orbit: to 200 km (with losses and the site's rotation), the plane penalty for the
    inclination, then a Hohmann-style climb; low inclinations from high latitudes add a plane change at apogee."""
    mu, re = fleet.MU, fleet.RE
    leo, _ = vehicles._target_dv("leo", site_lat)
    az = vehicles.azimuth(site_lat, max(inclination, abs(site_lat)) if inclination < abs(site_lat) else inclination)
    r0, rp, ra = re + 200e3, re + perigee_alt, re + apogee_alt
    vc0 = math.sqrt(mu / r0)
    # raise apogee from 200 km, then raise perigee at apogee
    a1 = (r0 + ra) / 2
    dv1 = math.sqrt(mu * (2 / r0 - 1 / a1)) - vc0
    v_ap_transfer = math.sqrt(mu * (2 / ra - 1 / a1))
    v_ap_final = math.sqrt(mu * (2 / ra - 2 / (rp + ra)))
    di = math.radians(abs(site_lat) - inclination) if inclination < abs(site_lat) else 0.0
    dv2 = math.sqrt(v_ap_transfer**2 + v_ap_final**2 - 2 * v_ap_transfer * v_ap_final * math.cos(di))
    return leo + az["delta_v_vs_due_east"] + max(dv1, 0.0) + (dv2 if (rp > r0 + 1e3 or di) else 0.0)


# ---------------------------------------------------------------- models
class CompanyIn(BaseModel):
    name: str = Field(min_length=2, max_length=48)


class OrbitIn(BaseModel):
    perigee_alt: float = Field(ge=150e3, le=400_000e3)
    apogee_alt: float | None = Field(default=None, ge=150e3, le=400_000e3)
    inclination_deg: float = Field(ge=0, le=180)
    longitude_deg: float | None = Field(default=None, ge=-180, le=360)  # geostationary slot


class LaunchIn(BaseModel):
    vehicle: str
    site: str | None = None
    satellite: str | None = None
    custom_satellite: dict[str, Any] | None = None
    name: str | None = Field(default=None, max_length=48)
    orbit: OrbitIn


class DeployIn(BaseModel):
    state: dict[str, Any]
    signature: str
    parts: list[Any]
    custom_parts: dict[str, Any] | None = None
    name: str = Field(min_length=1, max_length=48)
    satellite: str | None = None  # catalogue id if the payload is a real satellite
    custom_satellite: dict[str, Any] | None = None
    inclination_deg: float = Field(ge=0, le=180)


class BurnIn(BaseModel):
    burn: str
    delta_v: float = Field(default=0.0, ge=0, le=5000)
    target_altitude: float | None = None


class PhotoIn(BaseModel):
    target_lat: float | None = Field(default=None, ge=-90, le=90)
    target_lon: float | None = Field(default=None, ge=-180, le=360)


class ProbeIn(BaseModel):
    name: str = Field(min_length=1, max_length=48)
    vehicle: str
    target: str
    depart: str
    tof_days: float = Field(ge=20, le=6000)
    probe_dry_mass: float = Field(ge=10, le=100_000)
    probe_propellant: float = Field(default=0.0, ge=0, le=100_000)
    probe_isp: float = Field(default=320.0, ge=0, le=10_000)
    capture: bool = True


class RenameIn(BaseModel):
    name: str = Field(min_length=1, max_length=48)


# ---------------------------------------------------------------- routes
@router.get("")
def get_company(user=Depends(current_user)):
    with db.connect() as conn:
        row = _company(conn, user["id"])
        if row is None:
            return {"company": None}
        counts = {r["status"]: r["n"] for r in conn.execute(
            "SELECT status, COUNT(*) AS n FROM spacecraft WHERE user_id = ? GROUP BY status", (user["id"],))}
        (photos,) = conn.execute("SELECT COUNT(*) FROM photos WHERE user_id = ?", (user["id"],)).fetchone()
    return {"company": {"name": row["name"], "founded_at": row["founded_at"], "counts": counts, "photos": photos}}


@router.post("")
def found_company(body: CompanyIn, user=Depends(current_user)):
    name = " ".join(body.name.split())
    with db.connect() as conn:
        if _company(conn, user["id"]):
            conn.execute("UPDATE companies SET name = ? WHERE user_id = ?", (name, user["id"]))
        else:
            conn.execute("INSERT INTO companies (user_id, name, founded_at) VALUES (?,?,?)", (user["id"], name, time.time()))
    return get_company(user)


@router.get("/catalog")
def catalog(user=Depends(current_user)):
    out = vehicles.launch_vehicle_catalog()["result"]
    return {"vehicles": [{k: v[k] for k in ("id", "name", "agency", "country", "site", "site_info", "liftoff_mass", "payload_leo_kg")
                          if k in v} | {"payload_gto_kg": v.get("payload_gto_kg"), "payload_sso_kg": v.get("payload_sso_kg")}
                         for v in out["vehicles"]],
            "satellites": out["satellites"], "sites": SITES}


@router.get("/fleet")
def get_fleet(user=Depends(current_user)):
    with db.connect() as conn:
        _require_company(conn, user["id"])
        rows = conn.execute("SELECT * FROM spacecraft WHERE user_id = ? ORDER BY created_at", (user["id"],)).fetchall()
        for r in rows:
            _refresh(conn, r)
        rows = conn.execute("SELECT * FROM spacecraft WHERE user_id = ? ORDER BY created_at", (user["id"],)).fetchall()
    out = []
    for r in rows:
        try:
            out.append(live(r))
        except HTTPException as e:
            out.append({"id": r["id"], "name": r["name"], "kind": r["kind"], "status": "error", "error": e.detail})
    lat, lon = fleet.subsolar(fleet.jd_of(iso(time.time())))
    return {"now": time.time(), "fleet": out, "subsolar": {"lat": lat, "lon": lon}}


@router.get("/spacecraft/{cid}")
def get_spacecraft(cid: str, user=Depends(current_user)):
    with db.connect() as conn:
        row = _craft(conn, user["id"], cid)
        _refresh(conn, row)
        row = _craft(conn, user["id"], cid)
        photos = [{"id": p["id"], "taken_at": p["taken_at"], **db.loads(p["data"])} for p in conn.execute(
            "SELECT * FROM photos WHERE spacecraft_id = ? ORDER BY taken_at DESC LIMIT 50", (cid,))]
    return {**live(row, detail=True), "photos": photos, "now": time.time()}


@router.patch("/spacecraft/{cid}")
def rename_spacecraft(cid: str, body: RenameIn, user=Depends(current_user)):
    with db.connect() as conn:
        _craft(conn, user["id"], cid)
        conn.execute("UPDATE spacecraft SET name = ? WHERE id = ?", (body.name.strip(), cid))
    return {"ok": True}


@router.delete("/spacecraft/{cid}")
def retire_spacecraft(cid: str, user=Depends(current_user)):
    with db.connect() as conn:
        _craft(conn, user["id"], cid)
        conn.execute("DELETE FROM spacecraft WHERE id = ?", (cid,))
    return {"ok": True}


@router.post("/launch", status_code=201)
def launch(body: LaunchIn, user=Depends(current_user)):
    """Launch service: fly a real vehicle from a real site and put a satellite into the requested orbit."""
    if body.vehicle not in VEHICLES:
        raise HTTPException(422, f"Unknown vehicle {body.vehicle!r}")
    v = VEHICLES[body.vehicle]
    site_id = body.site or v["site"]
    if site_id not in SITES:
        raise HTTPException(422, f"Unknown launch site {site_id!r}")
    site = SITES[site_id]
    name, spec, prop = satellite_spec(body.satellite, body.custom_satellite)
    o = body.orbit
    apogee = o.apogee_alt if o.apogee_alt is not None else o.perigee_alt
    if apogee < o.perigee_alt:
        raise HTTPException(422, "apogee must be at or above perigee")
    need = orbit_delta_v(site["latitude"], o.perigee_alt, apogee, o.inclination_deg)
    mass = spec["dry_mass"] + prop
    have = vehicles.total_dv(*vehicles.with_payload(body.vehicle, mass))
    if have < need:
        lo, hi = 0.0, 200_000.0
        for _ in range(40):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if vehicles.total_dv(*vehicles.with_payload(body.vehicle, mid)) >= need else (lo, mid)
        raise HTTPException(422, f"{v['name']} can't reach that orbit with {mass:,.0f} kg: it needs {need:,.0f} m/s from "
                                 f"{site['name']} but has {have:,.0f} m/s. It can lift about {lo:,.0f} kg there. Try a bigger "
                                 f"rocket, a lower orbit or an inclination closer to {abs(site['latitude']):.0f}°.")
    now = time.time()
    orbit = engine(fleet.orbit_from_parameters, perigee_alt=o.perigee_alt, apogee_alt=apogee, epoch=iso(now),
                   inclination_deg=o.inclination_deg,
                   raan_deg=(math.degrees(fleet.gmst_rad(fleet.jd_of(iso(now)))) + site["longitude"] - 90) % 360,
                   longitude_deg=o.longitude_deg)["result"]["orbit"]
    name = (body.name or name).strip()[:48]
    with db.connect() as conn:
        _require_company(conn, user["id"])
        cid = _insert(conn, user["id"], "satellite", name, {**spec, "launch": {"vehicle": v["name"], "site": site["name"]}},
                      orbit, now, prop, f"Launched on {v['name']} from {site['name']} into {o.perigee_alt / 1e3:,.0f} × "
                                        f"{apogee / 1e3:,.0f} km at {o.inclination_deg:g}°")
    save_run(user["id"], "mission", f"{name} on {v['name']}", {"spacecraft_id": cid, "vehicle": body.vehicle, "site": site_id,
                                                                  "orbit": o.model_dump(), "satellite": body.satellite},
             {"delta_v_needed": need, "delta_v_available": have, "mass": mass}, sim_id="company")
    with db.connect() as conn:
        return live(_craft(conn, user["id"], cid), detail=True)


@router.post("/deploy", status_code=201)
def deploy_from_flight(body: DeployIn, user=Depends(current_user)):
    """Put the payload of a verified Spaceflight Lab flight into the fleet (from its current orbit)."""
    from app.main import check_flight
    from app.modules.physics.rocketry import rocket_flight
    args = {"parts": body.parts, "custom_parts": body.custom_parts or {}}
    if not check_flight(user["id"], body.state, {"parts": body.parts, "custom_parts": body.custom_parts}, body.signature):
        raise HTTPException(403, "This flight can't be verified (it was edited or comes from another session). Fly it again.")
    step = engine(rocket_flight, state=body.state, parts=body.parts, custom_parts=body.custom_parts, dt=0.01, predict=False)
    tel = step["result"]["telemetry"]
    if tel["reference"] != "earth" or tel["status"] != "orbit":
        raise HTTPException(422, "Deploy satellites from a stable Earth orbit (periapsis above the atmosphere).")
    if tel["periapsis_alt"] < 150e3:
        raise HTTPException(422, "The periapsis is too low; raise it above 150 km before deploying.")
    st = body.state
    site_lon = float(st.get("site_longitude_deg", -52.77))
    lat = next((s["latitude"] for s in SITES.values() if abs(s["longitude"] - site_lon) < 0.5), 0.0)
    az = vehicles.azimuth(lat, body.inclination_deg)
    penalty = az["delta_v_vs_due_east"]  # includes the plane change when the inclination is below the site latitude
    if penalty > tel["delta_v_remaining"] + 1e-6:
        raise HTTPException(422, f"Reaching {body.inclination_deg:g}° from this site costs about {penalty:,.0f} m/s more than the "
                                 f"equatorial flight you flew, and the rocket has {tel['delta_v_remaining']:,.0f} m/s left.")
    name, spec, prop = satellite_spec(body.satellite, body.custom_satellite)
    # planar flight → 3D orbit: keep the shape and the position along it; the plane is set by the inclination,
    # with the ascending node at the launch site's right ascension
    x, y, vx, vy = (float(st[k]) for k in ("x", "y", "vx", "vy"))
    r, v2 = math.hypot(x, y), vx * vx + vy * vy
    mu = fleet.MU
    energy = v2 / 2 - mu / r
    a = -mu / (2 * energy)
    h = x * vy - y * vx
    ex = (v2 - mu / r) * x / mu - (x * vx + y * vy) * vx / mu
    ey = (v2 - mu / r) * y / mu - (x * vx + y * vy) * vy / mu
    e = math.hypot(ex, ey)
    sign = 1 if h >= 0 else -1
    theta = math.atan2(y, x) * sign
    peri = math.atan2(ey, ex) * sign if e > 1e-9 else theta
    nu = theta - peri
    big = 2 * math.atan2(math.sqrt(1 - e) * math.sin(nu / 2), math.sqrt(1 + e) * math.cos(nu / 2))
    m_anom = big - e * math.sin(big)
    downrange = math.radians(tel["downrange_angle_deg"])
    now = time.time()
    raan = (math.degrees(float(st.get("site_ra", 0.0)))) % 360
    orbit = fleet.to_public({"a": a, "e": e, "i": math.radians(body.inclination_deg), "raan": math.radians(raan),
                             "argp": (downrange - nu) % (2 * math.pi), "m": m_anom % (2 * math.pi)})
    with db.connect() as conn:
        _require_company(conn, user["id"])
        cid = _insert(conn, user["id"], "satellite", body.name.strip() or name, {**spec, "launch": {"vehicle": "Spaceflight Lab flight"}},
                      orbit, now, prop, f"Deployed from your own rocket into {tel['periapsis_alt'] / 1e3:,.0f} × "
                                        f"{tel['apoapsis_alt'] / 1e3:,.0f} km at {body.inclination_deg:g}°")
        return live(_craft(conn, user["id"], cid), detail=True)


@router.post("/spacecraft/{cid}/burn")
def burn(cid: str, body: BurnIn, user=Depends(current_user)):
    with db.connect() as conn:
        row = _craft(conn, user["id"], cid)
        if row["kind"] != "satellite" or row["status"] == "re-entered":
            raise HTTPException(409, "Only satellites still in orbit can fire their thrusters")
        spec, orbit = db.loads(row["spec"]), db.loads(row["orbit"])
        r = engine(fleet.satellite_manoeuvre, orbit=orbit, epoch=iso(row["epoch"]), at=iso(time.time()), burn=body.burn,
                   delta_v=body.delta_v, target_altitude=body.target_altitude, dry_mass=spec["dry_mass"], propellant=row["propellant"],
                   isp=spec.get("isp", 0.0), area_m2=spec.get("area_m2", 10.0), cd=spec.get("cd", 2.2))["result"]
        new_epoch = jd_to_ts(r["epoch_jd"])
        conn.execute("UPDATE spacecraft SET orbit = ?, epoch = ?, propellant = ? WHERE id = ?",
                     (db.dumps(r["orbit"]), new_epoch, r["propellant_left"], cid))
        label = body.burn.replace("_", " ")
        _log(conn, row, f"Burn: {label}, {r['delta_v_total']:.1f} m/s, {r['propellant_used']:.2f} kg propellant. New orbit "
                        f"{r['orbit']['perigee_alt'] / 1e3:,.0f} × {r['orbit']['apogee_alt'] / 1e3:,.0f} km")
        row = _craft(conn, user["id"], cid)
    return {"burn": r, "spacecraft": live(row, detail=True)}


def imagery(result: dict, when: float) -> dict:
    """Where the picture comes from: NASA GIBS true-colour imagery of that day for the footprint (loaded by the
    browser), with the app's own Blue Marble map as the fallback."""
    fp = result["footprint"]
    day = (datetime.fromtimestamp(when, tz=timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    res = result["resolution"]
    span_m = max(result["swath"], 2_000.0)
    px = int(max(256, min(1024, span_m / max(res, 250.0))))
    if result["camera_type"] == "sar":
        layer, time_q = "BlueMarble_ShadedRelief", ""
    else:
        layer, time_q = "MODIS_Terra_CorrectedReflectance_TrueColor", f"&TIME={day}"
    url = ("https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0"
           f"&LAYERS={layer}&STYLES=&FORMAT=image/jpeg&CRS=EPSG:4326"
           f"&BBOX={fp['south']:.5f},{fp['west']:.5f},{fp['north']:.5f},{fp['east']:.5f}&WIDTH={px}&HEIGHT={px}{time_q}")
    return {"url": url, "layer": layer, "date": day if time_q else None, "pixels": px, "source_resolution_m": 250.0,
            "credit": "NASA EOSDIS GIBS" + (f", MODIS Terra true colour, {day}" if time_q else ", Blue Marble relief")}


@router.post("/spacecraft/{cid}/photo", status_code=201)
def take_photo(cid: str, body: PhotoIn, user=Depends(current_user)):
    with db.connect() as conn:
        row = _craft(conn, user["id"], cid)
        spec, orbit = db.loads(row["spec"]), db.loads(row["orbit"])
        if row["kind"] != "satellite" or row["status"] == "re-entered":
            raise HTTPException(409, "Only satellites in orbit can take pictures")
        if not spec.get("camera"):
            raise HTTPException(409, "This satellite has no camera")
        now = time.time()
        r = engine(fleet.satellite_imaging, orbit=orbit, epoch=iso(row["epoch"]), camera=spec["camera"], at=iso(now),
                   target_lat=body.target_lat, target_lon=body.target_lon, mass=_spec_mass(spec, row["propellant"]),
                   area_m2=spec.get("area_m2", 10.0), cd=spec.get("cd", 2.2))["result"]
        if not r["possible"]:
            raise HTTPException(422, "Can't take that picture: " + "; ".join(r["reasons"]))
        data = {"imaging": r, "source": imagery(r, now), "satellite": row["name"]}
        pid = db.new_id("ph")
        conn.execute("INSERT INTO photos (id, user_id, spacecraft_id, taken_at, data) VALUES (?,?,?,?,?)",
                     (pid, user["id"], cid, now, db.dumps(data)))
        _log(conn, row, f"Photo of {r['target']['lat']:.2f}°, {r['target']['lon']:.2f}° at {r['resolution']:.1f} m resolution")
    save_run(user["id"], "photo", f"{row['name']}: {r['target']['lat']:.1f}°, {r['target']['lon']:.1f}°",
             {"photo_id": pid, "spacecraft_id": cid}, {"resolution": r["resolution"], "swath": r["swath"]}, sim_id="company")
    return {"id": pid, "taken_at": now, **data}


@router.get("/photos")
def photos(spacecraft: str | None = None, limit: int = 60, user=Depends(current_user)):
    limit = max(1, min(200, limit))
    sql, args = "SELECT p.*, s.name AS sname FROM photos p JOIN spacecraft s ON s.id = p.spacecraft_id WHERE p.user_id = ?", [user["id"]]
    if spacecraft:
        sql += " AND p.spacecraft_id = ?"
        args.append(spacecraft)
    sql += " ORDER BY p.taken_at DESC LIMIT ?"
    args.append(limit)
    with db.connect() as conn:
        rows = conn.execute(sql, args).fetchall()
    return {"photos": [{"id": p["id"], "spacecraft_id": p["spacecraft_id"], "taken_at": p["taken_at"], **db.loads(p["data"])} for p in rows]}


@router.delete("/photos/{pid}")
def delete_photo(pid: str, user=Depends(current_user)):
    with db.connect() as conn:
        if conn.execute("DELETE FROM photos WHERE id = ? AND user_id = ?", (pid, user["id"])).rowcount == 0:
            raise HTTPException(404, "No such photo")
    return {"ok": True}


@router.post("/probes", status_code=201)
def launch_probe(body: ProbeIn, user=Depends(current_user)):
    """A deep-space mission: the vehicle must give the probe the departure energy, and the probe's own engine must
    pay for the capture burn if it is to stay in orbit at the target."""
    if body.vehicle not in VEHICLES:
        raise HTTPException(422, f"Unknown vehicle {body.vehicle!r}")
    v = VEHICLES[body.vehicle]
    m = engine(interplanetary.interplanetary_mission, depart=body.depart, origin="earth", target=body.target,
               tof_days=body.tof_days, n_points=30)["result"]
    depart_ts = jd_to_ts(m["depart_jd"])
    if depart_ts < time.time() - DAY:
        raise HTTPException(422, "Pick a departure date from today onward.")
    site = SITES[v["site"]]
    leo, _ = vehicles._target_dv("leo", site["latitude"])
    need = leo + m["departure_burn"]
    mass = body.probe_dry_mass + body.probe_propellant
    have = vehicles.total_dv(*vehicles.with_payload(body.vehicle, mass))
    if have < need:
        raise HTTPException(422, f"{v['name']} gives a {mass:,.0f} kg probe {have:,.0f} m/s, but this departure needs {need:,.0f} m/s "
                                 f"(C3 {m['c3_km2s2']:.1f} km²/s²). Use a bigger rocket, a lighter probe or a better launch window.")
    probe_dv = body.probe_isp * 9.80665 * math.log(mass / body.probe_dry_mass) if body.probe_propellant > 0 else 0.0
    if body.capture and probe_dv < m["capture_burn"]:
        raise HTTPException(422, f"Entering orbit at {body.target.title()} needs a {m['capture_burn']:,.0f} m/s burn but the probe only "
                                 f"carries {probe_dv:,.0f} m/s. Add propellant or choose a flyby.")
    spec = {"dry_mass": body.probe_dry_mass, "isp": body.probe_isp, "launch": {"vehicle": v["name"], "site": site["name"]}}
    orbit = {"origin": "earth", "target": body.target, "depart_ts": depart_ts, "tof_days": body.tof_days, "capture": body.capture}
    prop_left = body.probe_propellant
    if body.capture:
        prop_left = mass * math.exp(-m["capture_burn"] / (body.probe_isp * 9.80665)) - body.probe_dry_mass
    with db.connect() as conn:
        _require_company(conn, user["id"])
        cid = _insert(conn, user["id"], "probe", body.name.strip(), spec, orbit, depart_ts, max(prop_left, 0.0),
                      f"{'Scheduled' if depart_ts > time.time() + 3600 else 'Launched'} on {v['name']} for {body.target.title()}: "
                      f"departs {m['depart'][:10]}, arrives {m['arrive'][:10]} ({body.tof_days:.0f} days)")
    save_run(user["id"], "mission", f"{body.name.strip()} to {body.target.title()}",
             {"spacecraft_id": cid, **body.model_dump()}, {"c3": m["c3_km2s2"], "departure_burn": m["departure_burn"],
                                                           "capture_burn": m["capture_burn"]}, sim_id="company")
    with db.connect() as conn:
        return live(_craft(conn, user["id"], cid), detail=True)
