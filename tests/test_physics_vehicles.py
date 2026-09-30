"""Real launch vehicles, strap-on boosters (parallel staging) and launch azimuth."""
import math

import pytest

from app.modules.physics.rocketry import G0, rocket_design, rocket_flight, rocket_launch_state
from app.modules.physics.vehicle_data import VEHICLES
from app.modules.physics.vehicles import launch_azimuth, launch_vehicle_catalog, launch_vehicle_performance


def test_catalog_lists_real_vehicles():
    r = launch_vehicle_catalog()["result"]
    names = {v["name"] for v in r["vehicles"]}
    assert {"PSLV-XL", "GSLV Mk II", "LVM3", "Falcon 9 Block 5", "Saturn V (Apollo)"} <= names
    pslv = next(v for v in r["vehicles"] if v["id"] == "pslv_xl")
    assert pslv["liftoff_mass"] == pytest.approx(320_000, rel=0.05)  # PSLV-XL ≈ 320 t
    sv = next(v for v in r["vehicles"] if v["id"] == "saturn_v")
    assert sv["liftoff_mass"] == pytest.approx(2_950_000, rel=0.06)  # Saturn V ≈ 2,950 t
    assert any(s["id"] == "eos05" for s in r["satellites"])


@pytest.mark.parametrize("vid", list(VEHICLES))
def test_every_vehicle_designs_cleanly_and_lifts_off(vid):
    d = rocket_design(VEHICLES[vid]["parts"])["result"]
    assert d["stages"][0]["twr_surface"] > 1.05, vid
    assert not [w for w in d["warnings"] if "exposed" in w or "no engine" in w], d["warnings"]


@pytest.mark.parametrize("vid,target", [(v, t) for v in VEHICLES for t in ("leo", "gto", "sso", "tli")
                                         if VEHICLES[v].get({"leo": "payload_leo_kg", "gto": "payload_gto_kg",
                                                             "sso": "payload_sso_kg", "tli": "payload_tli_kg"}[t])])
def test_payload_close_to_published(vid, target):
    r = launch_vehicle_performance(vid, target)["result"]
    assert 0.6 < r["ratio_to_published"] < 1.7, (vid, target, r["max_payload_kg"])


def test_parallel_staging_matches_hand_calculation():
    # One core engine + two identical boosters that burn out first
    custom = {"custom_core": {"category": "engine", "mass": 1000, "height": 2, "width": 2, "thrust_sl": 900e3,
                              "thrust_vac": 1000e3, "isp_sl": 270, "isp_vac": 300}}
    parts = [{"part": "custom_core"}, {"part": "tank_l"}, {"part": "lvm3_s200", "count": 2}, {"part": "probe"}]
    d = rocket_design(parts, custom_parts=custom)["result"]["stages"][0]
    mb = 2 * (31_000 + 205_000)
    m0 = 1000 + 5000 + 70_000 + mb + 250
    mdot_c = 1000e3 / (300 * G0)
    mdot_b = 2 * 4312e3 / (274.5 * G0)
    tb = 2 * 205_000 / mdot_b
    used = mdot_c * tb + 2 * 205_000
    dv1 = (1000e3 + 2 * 4312e3) / (mdot_c + mdot_b) * math.log(m0 / (m0 - used))
    m1 = m0 - used - 2 * 31_000
    dv2 = 300 * G0 * math.log(m1 / (m1 - (70_000 - mdot_c * tb)))
    assert d["delta_v_vac"] == pytest.approx(dv1 + dv2, rel=1e-6)
    assert d["boosters"]["count"] == 2 and d["boosters"]["solid"]


def test_boosters_ignite_burn_out_and_separate_in_flight():
    parts = VEHICLES["pslv_xl"]["parts"]
    st = rocket_launch_state(parts)["result"]
    assert st["bprops"][0] == pytest.approx(6 * 12_200)
    events, t = [], 0
    s = st
    for _ in range(100):
        r = rocket_flight(s, parts, throttle=1.0, angle=math.pi / 2, dt=1.0, predict=False)["result"]
        events += r["events"]
        s = r["state"]
        if not s["boosters_on"][0]:
            break
    assert any("ignited" in e for e in events)
    assert any("separated" in e for e in events)
    assert 60 < s["t"] < 80  # PSOM-XL burn ≈ 70 s
    # solid boosters keep burning at zero throttle once lit
    s2 = rocket_launch_state(parts)["result"]
    s2 = rocket_flight(s2, parts, throttle=1.0, dt=5.0, predict=False)["result"]["state"]
    before = s2["bprops"][0]
    s3 = rocket_flight(s2, parts, throttle=0.0, dt=5.0, predict=False)["result"]
    assert s3["state"]["bprops"][0] < before
    assert s3["telemetry"]["thrust"] > 0


def test_orbit_start_uses_boosters_first():
    st = rocket_launch_state(VEHICLES["falcon_heavy"]["parts"], start="orbit")["result"]
    assert st["boosters_on"][0] is False and st["stage"] >= 1


def test_launch_azimuth():
    east = launch_azimuth(28.5, 28.5)["result"]
    assert east["azimuth_deg"] == pytest.approx(90, abs=0.5) and east["direct"]
    sso = launch_azimuth(13.72, 97.5)["result"]
    assert 340 < sso["azimuth_deg"] < 360 and 180 < sso["azimuth_south_deg"] < 200 and sso["delta_v_vs_due_east"] == pytest.approx(525, abs=15)
    low = launch_azimuth(45.96, 20.0)["result"]  # Baikonur can't launch directly into 20°
    assert not low["direct"] and low["plane_change_delta_v"] > 2000
