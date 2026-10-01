"""Space company: launch service rules, live fleet, burns, photos, probes, deploy from a flight, challenges."""
import math

import pytest

from app.modules.physics.vehicle_data import VEHICLES
from tests.helpers import new_client

pytestmark = pytest.mark.real_auth


def company():
    c, u = new_client()
    assert c.post("/api/company", json={"name": "Orbital Chai"}).status_code == 200
    return c


def test_company_needs_founding_first():
    c, _ = new_client()
    assert c.get("/api/company").json()["company"] is None
    assert c.get("/api/company/fleet").status_code == 409
    c.post("/api/company", json={"name": "Nova Works"})
    assert c.get("/api/company").json()["company"]["name"] == "Nova Works"


def test_launch_service_respects_rocket_capacity():
    c = company()
    # Electron can't lift Cartosat-3 (1.6 t)
    r = c.post("/api/company/launch", json={"vehicle": "electron", "satellite": "cartosat3",
                                            "orbit": {"perigee_alt": 509e3, "inclination_deg": 97.5}})
    assert r.status_code == 422 and "can lift about" in r.json()["detail"]
    ok = c.post("/api/company/launch", json={"vehicle": "pslv_xl", "satellite": "cartosat3",
                                             "orbit": {"perigee_alt": 509e3, "inclination_deg": 97.5}})
    assert ok.status_code == 201, ok.text
    sat = ok.json()
    assert sat["status"] == "orbiting" and sat["elements"]["i_deg"] == pytest.approx(97.5)
    assert sat["altitude"] == pytest.approx(509e3, abs=5e3)
    assert sat["lifetime_days"] and sat["ground_track"]
    fleet = c.get("/api/company/fleet").json()["fleet"]
    assert len(fleet) == 1 and -98 < fleet[0]["lat"] < 98
    hist = c.get("/api/history?kind=mission").json()["items"]
    assert hist and "Cartosat-3" in hist[0]["title"]


def test_geostationary_launch_and_burns():
    c = company()
    r = c.post("/api/company/launch", json={"vehicle": "gslv_mk2", "satellite": "eos05",
                                            "orbit": {"perigee_alt": 35_786e3, "inclination_deg": 0.0, "longitude_deg": 85.0}})
    # GSLV Mk II can't place 2.4 t directly into GEO from 13.7° N (needs the satellite's own engine in reality)
    assert r.status_code == 422
    r = c.post("/api/company/launch", json={"vehicle": "falcon_heavy", "satellite": "eos05",
                                            "orbit": {"perigee_alt": 35_786e3, "inclination_deg": 0.0, "longitude_deg": 85.0}})
    assert r.status_code == 201, r.text
    sat = r.json()
    assert sat["lon"] == pytest.approx(85.0, abs=0.2)
    burn = c.post(f"/api/company/spacecraft/{sat['id']}/burn", json={"burn": "prograde", "delta_v": 5.0})
    assert burn.status_code == 200
    b = burn.json()
    assert b["burn"]["propellant_used"] > 0 and b["spacecraft"]["propellant"] < sat["propellant"]
    assert b["spacecraft"]["elements"]["apogee_alt"] > 35_786e3 + 100e3
    too_much = c.post(f"/api/company/spacecraft/{sat['id']}/burn", json={"burn": "prograde", "delta_v": 4000})
    assert too_much.status_code == 422 and "propellant" in too_much.json()["detail"]
    photo = c.post(f"/api/company/spacecraft/{sat['id']}/photo", json={"target_lat": 20.0, "target_lon": 78.0})
    assert photo.status_code in (201, 422)  # depends on daylight over India right now
    if photo.status_code == 201:
        assert "gibs.earthdata.nasa.gov" in photo.json()["source"]["url"]
        assert photo.json()["imaging"]["resolution"] == pytest.approx(42, rel=0.15)


def test_satellite_without_camera_cant_photograph():
    c = company()
    sat = c.post("/api/company/launch", json={"vehicle": "falcon9", "satellite": "starlink_v2mini",
                                              "orbit": {"perigee_alt": 550e3, "inclination_deg": 53}}).json()
    assert c.post(f"/api/company/spacecraft/{sat['id']}/photo", json={}).status_code == 409


def test_other_users_cant_touch_my_fleet():
    a = company()
    sat = a.post("/api/company/launch", json={"vehicle": "falcon9", "satellite": "landsat9",
                                              "orbit": {"perigee_alt": 705e3, "inclination_deg": 98.2}}).json()
    b = company()
    assert b.get(f"/api/company/spacecraft/{sat['id']}").status_code == 404
    assert b.post(f"/api/company/spacecraft/{sat['id']}/burn", json={"burn": "prograde", "delta_v": 1}).status_code == 404
    assert b.delete(f"/api/company/spacecraft/{sat['id']}").status_code == 404


def test_mars_probe_rules():
    c = company()
    heavy = {"name": "Mangal-2", "vehicle": "electron", "target": "mars", "depart": "2026-11-01", "tof_days": 310,
             "probe_dry_mass": 1500, "probe_propellant": 1600, "probe_isp": 320, "capture": True}
    assert c.post("/api/company/probes", json=heavy).status_code == 422  # Electron is far too small
    no_fuel = {**heavy, "vehicle": "falcon_heavy", "probe_propellant": 10}
    r = c.post("/api/company/probes", json=no_fuel)
    assert r.status_code == 422 and "orbit at Mars" in r.json()["detail"]
    ok = c.post("/api/company/probes", json={**heavy, "vehicle": "falcon_heavy"})
    assert ok.status_code == 201, ok.text
    p = ok.json()
    assert p["kind"] == "probe" and p["mission"]["target"] == "mars" and p["mission"]["path_au"]


def test_deploy_from_flight_and_challenges():
    c = company()
    parts = VEHICLES["falcon9"]["parts"]
    r = c.post("/simulate", json={"domain": "physics", "name": "rocket_launch_state",
                                  "args": {"parts": parts, "start": "orbit", "date": "2026-10-01T00:00:00Z",
                                           "site_longitude_deg": -80.6}}).json()
    state, sig = r["result"], r["signature"]
    step = c.post("/simulate", json={"domain": "physics", "name": "rocket_flight", "signature": sig,
                                     "args": {"state": state, "parts": parts, "dt": 60.0, "predict": False}}).json()
    assert step["verified"]
    ev = {"state": step["result"]["state"], "signature": step["signature"], "parts": parts}
    res = c.post("/api/challenges/first_orbit/submit", json={"flight": ev}).json()
    assert res["passed"], res
    assert c.post("/api/challenges/moonshot/submit", json={"flight": ev}).json()["passed"] is False
    forged = {**ev, "state": {**ev["state"], "t": 99999.0}}
    assert c.post("/api/challenges/splashdown/submit", json={"flight": forged}).status_code == 403
    listing = c.get("/api/challenges").json()
    assert listing["completed"] == 1 and next(x for x in listing["challenges"] if x["id"] == "first_orbit")["completed_at"]
    # deploy the Starlink batch from that orbit into the fleet at the site's latitude
    dep = c.post("/api/company/deploy", json={**ev, "name": "Batch 1", "satellite": "starlink_v2mini", "inclination_deg": 28.5})
    assert dep.status_code == 201, dep.text
    assert dep.json()["elements"]["i_deg"] == pytest.approx(28.5)
    # a polar orbit costs more Δv than the upper stage has left after reaching orbit this way? (it may or may not)
    polar = c.post("/api/company/deploy", json={**ev, "name": "Batch 2", "satellite": "starlink_v2mini", "inclination_deg": 90})
    assert polar.status_code in (201, 422)
    assert c.post("/api/company/deploy", json={**ev, "signature": "0" * 64, "name": "x", "inclination_deg": 30}).status_code == 403


def test_sso_challenge_via_fleet():
    c = company()
    sat = c.post("/api/company/launch", json={"vehicle": "pslv_xl", "satellite": "cartosat3",
                                              "orbit": {"perigee_alt": 500e3, "inclination_deg": 97.4}}).json()
    first = c.post("/api/challenges/sso_imager/submit", json={}).json()
    assert first["passed"] is False  # no photo yet
    for lat in range(-80, 81, 20):  # try targets until one is in daylight and in view
        for lon in range(-180, 180, 30):
            r = c.post(f"/api/company/spacecraft/{sat['id']}/photo", json={"target_lat": lat, "target_lon": lon})
            if r.status_code == 201:
                break
        else:
            continue
        break
    if r.status_code == 201:  # the satellite may be over the night side right now
        assert c.post("/api/challenges/sso_imager/submit", json={}).json()["passed"]
