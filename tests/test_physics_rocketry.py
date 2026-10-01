import math

import pytest

from app.modules.physics.rocketry import BODIES, G0, PARTS, rocket_design, rocket_flight, rocket_launch_state

TWO_STAGE = [{"part": "engine_booster", "count": 9}, {"part": "tank_xl"}, {"part": "interstage"}, {"part": "decoupler"},
             {"part": "engine_vacuum"}, {"part": "tank_l"}, {"part": "capsule"}, {"part": "nose"}]


def test_single_stage_tsiolkovsky():
    parts = [{"part": "engine_lander"}, {"part": "tank_s"}, {"part": "probe"}]
    r = rocket_design(parts, body="moon")["result"]
    s = r["stages"][0]
    m0 = 150 + 1200 + 12000 + 250
    assert s["mass_start"] == m0 and s["mass_end"] == m0 - 12000
    assert s["delta_v_vac"] == pytest.approx(320 * G0 * math.log(m0 / (m0 - 12000)))
    assert s["burn_time"] == pytest.approx(12000 / (45e3 / (320 * G0)))
    g_moon = BODIES["moon"]["mu"] / BODIES["moon"]["radius"] ** 2
    assert s["twr_surface"] == pytest.approx(45e3 / (m0 * g_moon))  # no air: vacuum thrust


def test_two_stage_design_and_warnings():
    r = rocket_design(TWO_STAGE)["result"]
    s0, s1 = r["stages"]
    assert s0["mass_start"] == pytest.approx(r["total_mass"])
    assert s1["mass_start"] == pytest.approx(r["total_mass"] - s0["mass_start"] + s1["mass_start"])
    assert r["total_delta_v_vac"] == pytest.approx(s0["delta_v_vac"] + s1["delta_v_vac"])
    assert s0["twr_surface"] > 1 and not r["warnings"]
    assert s0["isp_vac"] == pytest.approx(311)  # a cluster of identical engines keeps their Isp
    heavy = rocket_design([{"part": "engine_lander"}, {"part": "tank_xl"}, {"part": "capsule"}])["result"]
    assert any("cannot leave the pad" in w for w in heavy["warnings"])
    with pytest.raises(ValueError):
        rocket_design([{"part": "warp_drive"}])
    with pytest.raises(ValueError):
        rocket_design([{"part": "tank_s", "count": 3}])


def test_pad_state_rotates_with_earth():
    st = rocket_launch_state(TWO_STAGE)["result"]
    assert st["landed"] and st["y"] == BODIES["earth"]["radius"]
    assert st["vx"] == pytest.approx(7.2921159e-5 * 6_371_000)  # surface speed ωR ≈ 464.6 m/s
    out = rocket_flight(st, TWO_STAGE, throttle=0, dt=3600)["result"]
    assert out["state"]["landed"] and out["telemetry"]["altitude"] == pytest.approx(0, abs=1e-3)


def test_vacuum_vertical_burn_matches_rocket_equation_minus_gravity():
    parts = [{"part": "engine_lander"}, {"part": "tank_s"}, {"part": "probe"}]
    st = rocket_launch_state(parts, body="moon")["result"]
    t_burn = 60.0
    out = rocket_flight(st, parts, throttle=1, angle=math.pi / 2, dt=t_burn)["result"]
    m0 = 150 + 1200 + 12000 + 250
    m1 = m0 - 45e3 / (320 * G0) * t_burn
    g = BODIES["moon"]["mu"] / BODIES["moon"]["radius"] ** 2
    expect = 320 * G0 * math.log(m0 / m1) - g * t_burn  # g varies by <1 % over this climb
    assert out["telemetry"]["vertical_speed"] == pytest.approx(expect, rel=0.01)


def test_circular_orbit_elements_and_period():
    parts = [{"part": "probe"}]
    b = BODIES["earth"]
    r = b["radius"] + 300e3
    v = math.sqrt(b["mu"] / r)
    st = {"t": 0, "x": r, "y": 0, "vx": 0, "vy": v, "angle": 0, "stage": 0, "props": [0], "landed": False, "crashed": False, "body": "earth"}
    out = rocket_flight(st, parts, dt=1.0)["result"]
    tel = out["telemetry"]
    assert tel["apoapsis_alt"] == pytest.approx(300e3, abs=200) and tel["periapsis_alt"] == pytest.approx(300e3, abs=200)
    assert tel["status"] == "orbit" and tel["period"] == pytest.approx(2 * math.pi * math.sqrt(r**3 / b["mu"]))
    full = rocket_flight(st, parts, dt=tel["period"])["result"]["state"]
    assert math.hypot(full["x"] - r, full["y"]) < 1.0  # back where it started after one period
    assert len(rocket_flight(st, parts, dt=1)["trajectory"]) > 100


def test_terminal_velocity_in_air():
    parts = [{"part": "probe"}]
    b = BODIES["earth"]
    st = {"t": 0, "x": 0, "y": b["radius"] + 3000, "vx": -b["omega"] * (b["radius"] + 3000), "vy": 0, "angle": math.pi / 2,
          "stage": 0, "props": [0], "landed": False, "crashed": False, "body": "earth"}
    out = rocket_flight(st, parts, dt=40)["result"]
    tel = out["telemetry"]
    rho = b["rho0"] * math.exp(-tel["altitude"] / b["H"])
    cda = 0.75 * math.pi * (PARTS["probe"]["width"] / 2) ** 2
    vt = math.sqrt(2 * 250 * 9.80 / (rho * cda))
    assert -tel["vertical_speed"] == pytest.approx(vt, rel=0.03)


def test_parachute_landing_and_crash():
    parts = [{"part": "parachute"}, {"part": "capsule"}]
    b = BODIES["earth"]
    st = {"t": 0, "x": 0, "y": b["radius"] + 2000, "vx": -b["omega"] * (b["radius"] + 2000), "vy": 0, "angle": math.pi / 2,
          "stage": 0, "props": [0], "landed": False, "crashed": False, "body": "earth"}
    safe = rocket_flight(st, parts, dt=600, deploy_chute=True)["result"]
    assert safe["state"]["landed"] and any("touchdown" in e for e in safe["events"])
    hard = rocket_flight(st, parts, dt=600)["result"]
    assert hard["state"]["crashed"] and hard["telemetry"]["status"] == "crashed"


def test_staging_and_burnout_events():
    st = rocket_launch_state(TWO_STAGE)["result"]
    out = rocket_flight(st, TWO_STAGE, throttle=1, angle=math.pi / 2, dt=80)["result"]
    assert "lift-off" in out["events"] and "stage 1 out of fuel" in out["events"]
    staged = rocket_flight(out["state"], TWO_STAGE, dt=0.1, stage=True)["result"]
    dry0 = rocket_design(TWO_STAGE)["result"]["stages"][0]["mass_end"] - rocket_design(TWO_STAGE)["result"]["stages"][1]["mass_start"]
    assert staged["state"]["stage"] == 1 and staged["telemetry"]["mass"] == pytest.approx(out["telemetry"]["mass"] - dry0)


def test_scripted_launch_reaches_orbit():
    """A simple gravity turn plus closed-loop upper-stage guidance puts the two-stage rocket in orbit."""
    st, tel, stage = rocket_launch_state(TWO_STAGE)["result"], None, False
    for _ in range(1000):
        r = math.hypot(st["x"], st["y"])
        ux, uy = st["x"] / r, st["y"] / r
        alt = r - BODIES["earth"]["radius"]
        if st["stage"] == 0:
            pitch = min(70, 90 * max(0, (alt - 500) / 60000) ** 0.6)
        else:
            vs_d = max(-50, min(300, (180e3 - alt) / 60))
            pitch = 90 - max(-20, min(60, (vs_d - tel["vertical_speed"]) * 0.3))
        p = math.radians(pitch)
        ang = math.atan2(uy * math.cos(p) - ux * math.sin(p), ux * math.cos(p) + uy * math.sin(p))
        out = rocket_flight(st, TWO_STAGE, throttle=1, angle=ang, dt=1.0, stage=stage, predict=False)["result"]
        st, tel, stage = out["state"], out["telemetry"], False
        if st["stage"] == 0 and st["props"][0] == 0:
            stage = True
        if tel["periapsis_alt"] and tel["periapsis_alt"] > 150e3:
            break
        assert not st["crashed"]
    assert tel["status"] == "orbit" and tel["periapsis_alt"] > 150e3


def test_flight_validation():
    st = rocket_launch_state(TWO_STAGE)["result"]
    with pytest.raises(ValueError):
        rocket_flight(st, TWO_STAGE, throttle=2)
    with pytest.raises(ValueError):
        rocket_flight(st, [{"part": "probe"}])  # state has two stages
    with pytest.raises(ValueError):
        rocket_launch_state(TWO_STAGE, body="venus")


def test_parts_catalogue():
    from app.modules.physics.rocketry import rocket_parts
    r = rocket_parts()["result"]
    ids = {p["id"] for p in r["parts"]}
    assert {"capsule", "tank_l", "engine_booster", "decoupler"} <= ids
    assert r["bodies"]["earth"]["surface_gravity"] == pytest.approx(9.82, abs=0.01)
    assert r["bodies"]["moon"]["surface_gravity"] == pytest.approx(1.62, abs=0.01)


def test_time_to_apsides():
    import math
    from app.modules.physics.rocketry import _elements, BODIES
    b = BODIES["earth"]
    mu, R = b["mu"], b["radius"]
    rp, ra = R + 200e3, R + 2000e3
    a = (rp + ra) / 2
    v = math.sqrt(mu * (2 / rp - 1 / a))
    el = _elements(b, 0.0, rp, -v, 0.0)  # at periapsis, moving prograde (counter-clockwise here: h > 0)
    period = 2 * math.pi * math.sqrt(a**3 / mu)
    assert el["time_to_apoapsis"] == pytest.approx(period / 2, rel=1e-6)
    assert el["time_to_periapsis"] == pytest.approx(0.0, abs=1e-3) or el["time_to_periapsis"] == pytest.approx(period, rel=1e-6)
    el2 = _elements(b, 0.0, -rp, v, 0.0)  # the same orbit flown clockwise
    assert el2["time_to_apoapsis"] == pytest.approx(period / 2, rel=1e-6)
