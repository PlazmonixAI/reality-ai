"""Challenge mode: set missions with goals the server checks. Flights are checked from their signed state (the
signature proves the engine produced it for this user and rocket); fleet goals are checked against the stored
spacecraft, recomputed now."""
from __future__ import annotations

import math
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.modules.physics import fleet
from app.platform import db
from app.platform.auth import current_user
from app.platform.company import live
from app.platform.history import save_run

router = APIRouter(prefix="/api/challenges", tags=["challenges"])

CHALLENGES: list[dict[str, Any]] = [
    {"id": "karman", "title": "Touch space", "level": 1, "where": "lab", "template": "sounding",
     "goal": "Fly above 100 km, the Kármán line, and submit while you are up there.",
     "briefing": "Every space programme starts with a sounding rocket. Get above 100 km; you don't need orbital speed.",
     "hint": "Point straight up, full throttle. A single stage with a medium tank is enough."},
    {"id": "first_orbit", "title": "First orbit", "level": 1, "where": "lab", "template": "orbiter",
     "goal": "Reach a stable Earth orbit with the periapsis above 150 km.",
     "briefing": "Orbit is about going sideways fast enough: about 7.8 km/s at 200 km.",
     "hint": "Go up to about 10 km, then tilt east gradually. Burn at apoapsis to lift the periapsis (use Prograde hold)."},
    {"id": "splashdown", "title": "Round trip", "level": 2, "where": "lab", "template": "orbiter",
     "goal": "Reach orbit and come back to land safely on Earth, at least 90 minutes after lift-off.",
     "briefing": "Getting down is half the mission. Slow down enough, keep the capsule and open the parachute.",
     "hint": "After an orbit, burn retrograde until the periapsis is about 50 km, stage off the empty tanks, then deploy the chute below 10 km."},
    {"id": "sso_imager", "title": "Eyes on Earth", "level": 2, "where": "company", "template": None,
     "goal": "Put an imaging satellite into a sun-synchronous orbit between 400 and 900 km and take a picture with it.",
     "briefing": "Sun-synchronous orbits pass over each place at the same local time, so shadows match from day to day.",
     "hint": "From Sriharikota, PSLV-XL with Cartosat-3 at about 500 km and 97.4° is a classic. Then open the satellite and take a photo in daylight."},
    {"id": "geo_slot", "title": "Parking in the sky", "level": 2, "where": "company", "template": None,
     "goal": "Hold a satellite in geostationary orbit: 35,786 km, eccentricity below 0.01, inclination below 1°.",
     "briefing": "A geostationary satellite turns with the Earth, so a dish on the ground can stay pointed at it.",
     "hint": "Heavy rockets from low-latitude sites do this best. EOS-05 on GSLV Mk II or a comsat on Ariane 5 from Kourou."},
    {"id": "moonshot", "title": "Moonshot", "level": 3, "where": "lab", "template": "lunarOrbiter",
     "goal": "Enter lunar orbit (a closed orbit around the Moon).",
     "briefing": "Park in low orbit, wait for the trans-lunar injection window, coast about five days, then brake at the Moon.",
     "hint": "Start in low orbit, warp to the TLI window shown on the HUD, burn prograde about 3.1 km/s, then burn retrograde at the closest approach."},
    {"id": "moon_landing", "title": "The Eagle has landed", "level": 3, "where": "lab", "template": "moon",
     "goal": "Land gently on the Moon.",
     "briefing": "No air, so no parachute. Kill your speed with the engine and touch down below 16 m/s with legs.",
     "hint": "From lunar orbit, burn retrograde to drop, then point up and throttle to keep the descent slow near the ground."},
    {"id": "red_planet", "title": "Red Planet", "level": 3, "where": "company", "template": None,
     "goal": "Send a probe to Mars that will enter orbit there.",
     "briefing": "Earth and Mars line up for a cheap transfer every 26 months. Pick a date in the window and a rocket strong enough.",
     "hint": "Use the launch window finder: the 2026 window opens around November. A probe of about 1,500 kg dry with 1,600 kg of propellant on Falcon Heavy, or a lighter one on Falcon 9."},
    {"id": "jupiter", "title": "King of planets", "level": 3, "where": "company", "template": None,
     "goal": "Send a probe on its way to Jupiter.",
     "briefing": "Jupiter needs about eight times Mars's departure energy. Only big rockets and light probes make it.",
     "hint": "A flyby is fine for this one. Try Falcon Heavy or SLS with a probe under 5 t."},
    {"id": "still_flying", "title": "Still flying", "level": 2, "where": "company", "template": None,
     "goal": "Keep a satellite in orbit for 30 days (real time).",
     "briefing": "Low orbits sink because of drag. Boost with the thrusters before the orbit decays.",
     "hint": "Launch a satellite now, check on it in a few days and raise its orbit if it is getting low."},
]
BY_ID = {c["id"]: c for c in CHALLENGES}


class FlightEvidence(BaseModel):
    state: dict[str, Any]
    signature: str
    parts: list[Any]
    custom_parts: dict[str, Any] | None = None


class SubmitIn(BaseModel):
    flight: FlightEvidence | None = None
    spacecraft_id: str | None = None


def _flight_telemetry(uid: str, ev: FlightEvidence) -> dict:
    from app.main import check_flight
    from app.modules.physics.rocketry import rocket_flight
    if not check_flight(uid, ev.state, {"parts": ev.parts, "custom_parts": ev.custom_parts}, ev.signature):
        raise HTTPException(403, "This flight can't be verified. Challenges only count flights flown in this app, unedited.")
    try:
        r = rocket_flight(state=ev.state, parts=ev.parts, custom_parts=ev.custom_parts, dt=0.01, predict=False)["result"]
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    return {**r["telemetry"], "state": r["state"]}


def check(uid: str, cid: str, body: SubmitIn) -> tuple[bool, str, dict]:
    if cid in ("karman", "first_orbit", "splashdown", "moonshot", "moon_landing"):
        if body.flight is None:
            raise HTTPException(422, "Submit this from the Spaceflight Lab during your flight.")
        tel = _flight_telemetry(uid, body.flight)
        st = tel["state"]
        ev = {"status": tel["status"], "altitude": tel["altitude"], "t": st["t"], "reference": tel["reference"],
              "periapsis_alt": tel["periapsis_alt"], "apoapsis_alt": tel["apoapsis_alt"]}
        if st.get("body", "earth") != "earth":
            return False, "Challenges start from Earth.", ev
        if cid == "karman":
            ok = tel["reference"] == "earth" and tel["altitude"] >= 100e3 and not st["crashed"]
            return ok, "Above the Kármán line!" if ok else f"You're at {tel['altitude'] / 1e3:.1f} km. Get above 100 km.", ev
        if cid == "first_orbit":
            ok = tel["status"] == "orbit" and tel["reference"] == "earth" and tel["periapsis_alt"] >= 150e3
            return ok, "Stable orbit confirmed." if ok else "Not in a stable orbit yet (periapsis must be above 150 km).", ev
        if cid == "splashdown":
            ok = st["landed"] and not st["crashed"] and st.get("landed_on") == "earth" and st["t"] >= 5400
            return ok, "Welcome home." if ok else "Land intact on Earth at least 90 minutes after lift-off.", ev
        if cid == "moonshot":
            ok = tel["status"] == "lunar orbit"
            return ok, "Lunar orbit confirmed." if ok else "You're not in a closed orbit around the Moon yet.", ev
        ok = st["landed"] and not st["crashed"] and st.get("landed_on") == "moon"
        return ok, "Touchdown on the Moon confirmed." if ok else "Land gently on the Moon first.", ev
    # fleet challenges
    with db.connect() as conn:
        if body.spacecraft_id:
            rows = conn.execute("SELECT * FROM spacecraft WHERE user_id = ? AND id = ?", (uid, body.spacecraft_id)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM spacecraft WHERE user_id = ?", (uid,)).fetchall()
        photo_ids = {r["spacecraft_id"] for r in conn.execute("SELECT spacecraft_id FROM photos WHERE user_id = ?", (uid,))}
    if not rows:
        return False, "You have no spacecraft that qualify yet.", {}
    for row in rows:
        try:
            s = live(row)
        except HTTPException:
            continue
        if cid in ("sso_imager", "geo_slot", "still_flying"):
            if row["kind"] != "satellite" or s.get("status") in ("re-entered", None) or "elements" not in s:
                continue
            el = s["elements"]
            if cid == "sso_imager":
                a = el["a"]
                need = _sso_inclination(a, el["e"])
                ok = 400e3 <= el["perigee_alt"] and el["apogee_alt"] <= 900e3 and need and abs(el["i_deg"] - need) <= 1.0 \
                    and row["id"] in photo_ids
                if ok:
                    return True, f"{row['name']} is sun-synchronous at {el['i_deg']:.2f}° and has taken a picture.", {"spacecraft": row["id"]}
            elif cid == "geo_slot":
                if abs(el["a"] - 42_166e3) <= 150e3 and el["e"] < 0.01 and el["i_deg"] < 1.0:
                    return True, f"{row['name']} holds a geostationary slot at {s['lon']:.1f}°.", {"spacecraft": row["id"]}
            elif time.time() - row["created_at"] >= 30 * 86400:
                return True, f"{row['name']} has flown for {(time.time() - row['created_at']) / 86400:.0f} days.", {"spacecraft": row["id"]}
        elif row["kind"] == "probe":
            m = s.get("mission", {})
            target = {"red_planet": "mars", "jupiter": "jupiter"}[cid]
            launched = m.get("now", {}).get("phase") in ("cruise", "arrived")
            if m.get("target") == target and launched and (cid == "jupiter" or m.get("capture")):
                return True, f"{row['name']} is on its way to {target.title()}.", {"spacecraft": row["id"]}
    msgs = {"sso_imager": "No satellite in a sun-synchronous orbit (400 to 900 km) that has taken a picture yet.",
            "geo_slot": "No satellite in a geostationary orbit yet.",
            "still_flying": "None of your satellites has been in orbit for 30 days yet.",
            "red_planet": "No probe on its way into Mars orbit yet (launched, with capture).",
            "jupiter": "No probe on its way to Jupiter yet (it must have launched)."}
    return False, msgs[cid], {}


def _sso_inclination(a: float, e: float) -> float | None:
    n = math.sqrt(fleet.MU / a**3)
    target = 2 * math.pi / (365.2422 * 86400)
    c = -target / (1.5 * n * fleet.J2E * (fleet.RE / (a * (1 - e * e))) ** 2)
    return math.degrees(math.acos(c)) if -1 <= c <= 1 else None


@router.get("")
def list_challenges(user=Depends(current_user)):
    with db.connect() as conn:
        done = {r["challenge_id"]: r["completed_at"] for r in conn.execute(
            "SELECT challenge_id, completed_at FROM challenge_progress WHERE user_id = ?", (user["id"],))}
    return {"challenges": [{**c, "completed_at": done.get(c["id"])} for c in CHALLENGES],
            "completed": len(done), "total": len(CHALLENGES)}


@router.post("/{cid}/submit")
def submit(cid: str, body: SubmitIn, user=Depends(current_user)):
    if cid not in BY_ID:
        raise HTTPException(404, "No such challenge")
    ok, message, evidence = check(user["id"], cid, body)
    ok = bool(ok)
    if ok:
        with db.connect() as conn:
            first = conn.execute("SELECT 1 FROM challenge_progress WHERE user_id = ? AND challenge_id = ?", (user["id"], cid)).fetchone() is None
            if first:
                conn.execute("INSERT INTO challenge_progress (user_id, challenge_id, completed_at, evidence) VALUES (?,?,?,?)",
                             (user["id"], cid, time.time(), db.dumps(evidence)))
        if first:
            save_run(user["id"], "challenge", f"Challenge complete: {BY_ID[cid]['title']}", {"challenge": cid, "evidence": evidence},
                     {"message": message}, sim_id="challenges")
    return {"passed": ok, "message": message, "evidence": evidence}
