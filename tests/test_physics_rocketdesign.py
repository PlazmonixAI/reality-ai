import math

import pytest

from app.modules.physics.rocketdesign import area_ratio, exit_mach, lunar_transfer, rocket_engine_design, satellite_design
from app.modules.physics.rocketry import (
    BODIES, MOON_RADIUS, MOON_SOI, PARTS, engine_class, moon_state, rocket_design, rocket_flight, rocket_launch_state,
    rocket_parts,
)


def test_isentropic_nozzle_relations():
    assert area_ratio(2.0, 1.4) == pytest.approx(1.6875)  # textbook compressible-flow table value
    assert exit_mach(1.6875, 1.4) == pytest.approx(2.0)


@pytest.mark.parametrize("args, isp_sl, isp_vac", [
    (("lox_rp1", "gas_generator", 97, 16, 914), 282, 311),       # Merlin 1D
    (("lox_rp1", "staged_combustion", 267, 36.9, 4150), 311, 338),  # RD-180
    (("lox_lh2", "staged_combustion", 206, 69, 2279), 366, 452),  # RS-25
    (("lox_ch4", "full_flow", 300, 34, 2400), 327, 350),         # Raptor 2
    (("lox_lh2", "expander", 44, 280, 110), None, 465),           # RL10B-2
    (("nto_mmh", "pressure_fed", 11, 84, 29.6), None, 324),        # Aestus
])
def test_engine_designer_matches_real_engines(args, isp_sl, isp_vac):
    r = rocket_engine_design(*args)["result"]
    assert r["isp_vac"] == pytest.approx(isp_vac, rel=0.03)
    if isp_sl:
        assert r["isp_sl"] == pytest.approx(isp_sl, rel=0.03)
    assert r["thrust_vac"] == pytest.approx(args[4] * 1e3)
    assert r["mass_flow"] == pytest.approx(r["thrust_vac"] / (r["isp_vac"] * 9.80665))
    assert r["thrust_sl"] == pytest.approx(r["mass_flow"] * r["isp_sl"] * 9.80665)
    assert r["exit_diameter"] == pytest.approx(r["throat_diameter"] * math.sqrt(args[3]))


def test_engine_designer_physics_and_part():
    low, high = (rocket_engine_design("lox_rp1", "staged_combustion", 150, e, 500)["result"] for e in (8, 60))
    assert high["isp_vac"] > low["isp_vac"]  # more expansion: more vacuum Isp
    assert high["sea_level_flow_separation"] and not low["sea_level_flow_separation"]
    assert any("vacuum stages" in w for w in high["warnings"])
    big = rocket_engine_design(thrust_vac_kn=2000)["result"]
    assert big["size_class"] == "heavy" and big["throat_diameter"] > low["throat_diameter"]
    part = big["part"]
    d = rocket_design([{"part": "custom_mine"}, {"part": "tank_xl"}, {"part": "probe"}], custom_parts={"custom_mine": part})["result"]
    assert d["stages"][0]["thrust_vac"] == pytest.approx(part["thrust_vac"]) and d["stages"][0]["isp_vac"] == pytest.approx(part["isp_vac"])
    with pytest.raises(ValueError):
        rocket_engine_design(propellant="unobtainium")


def test_satellite_power_eclipse_and_budget():
    r = satellite_design(bus="medium", payload_kg=300, solar_area_m2=10, battery_wh=3000, power_draw_w=1200,
                         propellant_kg=150, thruster="hydrazine", altitude_km=400)["result"]
    assert r["orbital_period"] / 60 == pytest.approx(92.4, abs=0.3)     # ISS-like orbit
    assert r["eclipse_fraction"] == pytest.approx(0.39, abs=0.01)
    assert r["power_in_sunlight"] == pytest.approx(1361 * 0.3 * 10 * 0.85)
    assert r["delta_v"] == pytest.approx(220 * 9.80665 * math.log(r["wet_mass"] / r["dry_mass"]))
    geo = satellite_design(altitude_km=35786, propellant_kg=0, thruster="none")["result"]
    assert geo["eclipse_duration"] / 60 == pytest.approx(69.5, abs=1.5)  # longest GEO eclipse ≈ 70 min
    starved = satellite_design(solar_area_m2=1, power_draw_w=3000)["result"]
    assert not starved["power_ok"] and starved["warnings"]
    part = r["part"]
    d = rocket_design([{"part": "engine_booster"}, {"part": "tank_m"}, {"part": "decoupler"}, {"part": "custom_sat"}, {"part": "fairing"}],
                      custom_parts={"custom_sat": part})["result"]
    assert d["stages"][1]["delta_v_vac"] > 0  # the satellite's own thruster counts as a stage


def test_lunar_transfer_patched_conics():
    r = lunar_transfer(200, 100)["result"]
    assert r["tli_delta_v"] == pytest.approx(3130, abs=30)          # classic LEO→Moon injection ≈ 3.1 km/s
    assert r["transfer_time_days"] == pytest.approx(4.98, abs=0.05)  # Hohmann half-period
    assert r["moon_lead_angle_deg"] == pytest.approx(114, abs=2)
    assert 700 < r["loi_delta_v"] < 1000 and r["lunar_orbit_period"] / 60 == pytest.approx(118, abs=2)
    assert 1600 < r["landing_delta_v_ideal"] < 1800


def test_engine_classes_fairings_interstage_and_satellites():
    classes = {v["class"] for v in PARTS.values() if v["category"] == "engine"}
    assert classes == {"small", "medium", "large", "heavy"}
    assert all(engine_class(v["thrust_vac"]) == v["class"] for v in PARTS.values() if v["category"] == "engine")
    bare = [{"part": "engine_booster", "count": 9}, {"part": "tank_xl"}, {"part": "decoupler"}, {"part": "engine_vacuum"},
            {"part": "tank_l"}, {"part": "decoupler"}, {"part": "sat_comms"}]
    w = rocket_design(bare)["result"]["warnings"]
    assert any("interstage" in x for x in w) and any("fairing" in x for x in w)
    good = bare[:2] + [{"part": "interstage"}] + bare[2:] + [{"part": "fairing"}]
    d = rocket_design(good)["result"]
    assert not d["warnings"] and "geostationary orbit" in d["mission_delta_v"]
    # Jettisoning the fairing drops its mass; flying without it in thick air is flagged
    st = rocket_launch_state(good)["result"]
    assert st["fairing"]
    o = rocket_flight(st, good, dt=0.1, jettison_fairing=True)["result"]
    assert not o["state"]["fairing"] and o["telemetry"]["mass"] == pytest.approx(d["total_mass"] - PARTS["fairing"]["mass"])
    assert rocket_parts()["result"]["mission_delta_v"]["Moon landing"] > 15000


def _moon_rocket():
    parts = [{"part": "engine_vacuum"}, {"part": "tank_m"}, {"part": "probe"}]
    b = BODIES["earth"]
    r0 = b["radius"] + 200e3
    st = rocket_launch_state(parts)["result"]
    st.update(x=0.0, y=r0, vx=math.sqrt(b["mu"] / r0), vy=0.0, landed=False, landed_on=None)
    return parts, st


def test_moon_moves_and_tli_window():
    parts, st = _moon_rocket()
    tel = rocket_flight(st, parts, dt=1)["result"]["telemetry"]
    assert tel["tli"]["delta_v"] == pytest.approx(3133, abs=5) and tel["tli"]["phase_required_deg"] == pytest.approx(114.3, abs=0.5)
    m0 = moon_state(st["moon_theta0"], 0)
    m1 = moon_state(st["moon_theta0"], 27.321661 * 86400)
    assert math.hypot(m0[0] - m1[0], m0[1] - m1[1]) < 0.01 * 384_400e3  # one sidereal month later it is back
    assert math.hypot(m0[2], m0[3]) == pytest.approx(1022, abs=5)      # orbital speed ≈ 1.02 km/s


def test_full_scale_trip_to_lunar_orbit():
    """Coast to the TLI window, burn prograde, coast ~2.5 days in the Earth–Moon field and capture at the Moon."""
    parts, st = _moon_rocket()
    b = BODIES["earth"]
    tel = rocket_flight(st, parts, dt=1)["result"]["telemetry"]
    burn = tel["mass"] * (1 - math.exp(-tel["tli"]["delta_v"] / (348 * 9.80665))) / (981e3 / (348 * 9.80665))
    st = rocket_flight(st, parts, dt=tel["tli"]["time_to_window"] - burn / 2 - 320, predict=False)["result"]["state"]
    target = -b["mu"] / (b["radius"] + 200e3 + 384_400e3)
    while (st["vx"] ** 2 + st["vy"] ** 2) / 2 - b["mu"] / math.hypot(st["x"], st["y"]) < target:
        st = rocket_flight(st, parts, throttle=1, angle=math.atan2(st["vy"], st["vx"]), dt=1, predict=False)["result"]["state"]
    enc = rocket_flight(st, parts, dt=1)["result"]["telemetry"]["encounter"]
    assert enc and 0 < enc["periselene_alt"] < MOON_SOI and 1.5 < enc["time_from_now"] / 86400 < 5
    st = rocket_flight(st, parts, dt=enc["time_from_now"] - 120, predict=False)["result"]["state"]
    for _ in range(400):
        loc = rocket_flight(st, parts, dt=0.1, predict=False)["local"]
        o = rocket_flight(st, parts, throttle=1, angle=math.atan2(-loc["vy"], -loc["vx"]), dt=1, predict=False)["result"]
        st, tel = o["state"], o["telemetry"]
        if tel["status"] == "lunar orbit" and tel["apoapsis_alt"] < 5000e3:
            break
    assert tel["reference"] == "moon" and tel["status"] == "lunar orbit" and tel["delta_v_remaining"] > 1000


def test_landing_on_and_lifting_off_the_moon():
    parts = [{"part": "legs"}, {"part": "engine_lander"}, {"part": "tank_s"}, {"part": "lander"}]
    st = rocket_launch_state(parts)["result"]
    mx, my, mvx, mvy = moon_state(st["moon_theta0"], 0.0)
    ux, uy = -mx / 384_400e3, -my / 384_400e3  # hover over the near side, 30 m up, sinking at 4 m/s
    st.update(x=mx + ux * (MOON_RADIUS + 30), y=my + uy * (MOON_RADIUS + 30), vx=mvx - 4 * ux, vy=mvy - 4 * uy,
              landed=False, landed_on=None, t=0.0)
    o = rocket_flight(st, parts, dt=200, angle=math.atan2(uy, ux))["result"]
    assert o["state"]["landed"] and o["state"]["landed_on"] == "moon" and any("on the Moon" in e for e in o["events"])
    later = rocket_flight(o["state"], parts, dt=3600)
    assert later["result"]["telemetry"]["reference"] == "moon" and later["result"]["telemetry"]["altitude"] == pytest.approx(0, abs=1)
    up = math.atan2(later["local"]["y"], later["local"]["x"])
    lift = rocket_flight(later["result"]["state"], parts, throttle=1, angle=up, dt=20)["result"]
    assert "lift-off from the Moon" in lift["events"] and lift["telemetry"]["altitude"] > 100


def test_custom_part_validation():
    with pytest.raises(ValueError):
        rocket_design([{"part": "custom_x"}], custom_parts={"custom_x": {"category": "engine", "mass": 1}})
    with pytest.raises(ValueError):
        rocket_design([{"part": "probe"}], custom_parts={"bad id": {"category": "satellite", "mass": 1, "height": 1, "width": 1}})


def test_start_in_parking_orbit_spends_the_ascent_budget():
    parts = [P for P in ([{"part": "engine_methalox", "count": 5}, {"part": "tank_xl"}, {"part": "tank_xl"}, {"part": "tank_xl"},
                          {"part": "interstage"}, {"part": "decoupler"}, {"part": "engine_vacuum"}, {"part": "tank_l"}, {"part": "tank_l"},
                          {"part": "decoupler"}, {"part": "sat_lunar"}, {"part": "fairing"}])]
    d = rocket_design(parts)["result"]
    st = rocket_launch_state(parts, start="orbit")["result"]
    assert st["stage"] == 1 and not st["fairing"] and not st["landed"]
    tel = rocket_flight(st, parts, dt=1)["result"]["telemetry"]
    assert tel["status"] == "orbit" and tel["periapsis_alt"] == pytest.approx(200e3, abs=500)
    # stage 2 keeps what the ascent did not use; the satellite then flies without the 1 t fairing around it
    g0, sat = 9.80665, 650 + 900
    upper = 490 + 150 + 2 * 5000 + sat
    stage2 = 348 * g0 * math.log((upper + st["props"][1]) / upper)
    with_fairing = 348 * g0 * math.log((upper + 1000 + st["props"][1]) / (upper + 1000))  # during the ascent it was still on
    assert d["stages"][0]["delta_v_vac"] + d["stages"][1]["delta_v_vac"] - with_fairing == pytest.approx(9400, rel=1e-6)
    assert tel["delta_v_remaining"] == pytest.approx(stage2 + 318 * g0 * math.log(sat / 650), rel=1e-3)
    with pytest.raises(ValueError):
        rocket_launch_state([{"part": "engine_lander"}, {"part": "tank_s"}, {"part": "probe"}], start="orbit")


def test_real_sky_launch_and_3d_view():
    """With a date, the pad sits at the site's real longitude, the model Moon at the real Moon's right ascension,
    and the 3D view turns with the Earth exactly as the flight model's pad does."""
    import numpy as np
    from app.modules.physics.ephemeris import julian_date, moon_geocentric
    from app.modules.physics.rocketry import _ecl_to_eq, _earth_rotation_deg
    parts = [{"part": "engine_booster"}, {"part": "tank_m"}, {"part": "probe"}]
    st = rocket_launch_state(parts, date="2026-09-29T12:00:00Z", site_longitude_deg=-80.6)["result"]
    v = rocket_flight(st, parts, dt=0.1)["view3d"]
    jd = julian_date("2026-09-29T12:00:00Z")
    pad_ra = math.degrees(math.atan2(v["craft"][1], v["craft"][0]))
    assert (pad_ra - (_earth_rotation_deg(jd) - 80.6) + 180) % 360 - 180 == pytest.approx(0, abs=0.01)
    m = _ecl_to_eq(moon_geocentric(np.array([jd]))[:, 0])
    real_ra = math.degrees(math.atan2(m[1], m[0]))
    model_ra = math.degrees(math.atan2(v["moon"][1], v["moon"][0]))
    assert (model_ra - real_ra + 180) % 360 - 180 == pytest.approx(0, abs=0.01)
    assert np.linalg.norm(v["sun_direction"]) == pytest.approx(1)
    # six hours on the pad: the pad and Greenwich both turn by the same angle in the 3D frame
    later = rocket_flight(st, parts, dt=6 * 3600)["view3d"]
    turn = lambda a, b: (math.degrees(math.atan2(b[1], b[0]) - math.atan2(a[1], a[0])) + 180) % 360 - 180
    assert turn(v["craft"], later["craft"]) == pytest.approx((later["earth_rotation_deg"] - v["earth_rotation_deg"] + 180) % 360 - 180, abs=0.01)
