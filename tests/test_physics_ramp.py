import math

import numpy as np
import pytest

from app.modules.physics.ramp import G0, ramp_motion


def test_frictionless_acceleration():
    r = ramp_motion(mass=2, angle_deg=30, position=4, duration=0.5)
    assert r["result"]["initial_acceleration"] == pytest.approx(-G0 * 0.5)
    t, x = np.array(r["trajectory"]["t"]), np.array(r["trajectory"]["position"])
    assert x[-1] == pytest.approx(4 - 0.5 * G0 * 0.5 * 0.25)


def test_static_friction_holds():
    # tan 20° = 0.364 < mu_s = 0.5: no motion
    r = ramp_motion(mass=5, angle_deg=20, mu_static=0.5, mu_kinetic=0.4, position=3)
    assert r["result"]["moves"] is False
    assert r["forces"]["friction"] == pytest.approx(5 * G0 * math.sin(math.radians(20)))
    assert np.ptp(r["trajectory"]["position"]) == 0


def test_kinetic_friction_sliding_down():
    r = ramp_motion(mass=10, angle_deg=40, mu_static=0.6, mu_kinetic=0.3, position=4.9, duration=0.3)
    th = math.radians(40)
    assert r["result"]["initial_acceleration"] == pytest.approx(-G0 * (math.sin(th) - 0.3 * math.cos(th)))


def test_pushed_up_the_ramp():
    m, th, mu = 4, math.radians(25), 0.2
    F = 40
    r = ramp_motion(mass=m, angle_deg=25, mu_static=0.3, mu_kinetic=mu, applied_force=F, position=0.5)
    assert r["result"]["initial_acceleration"] == pytest.approx((F - m * G0 * (math.sin(th) + mu * math.cos(th))) / m)


def test_launched_up_then_sticks():
    # Up at 3 m/s on 15° with mu_s=0.4 (> tan 15°): decelerates, stops, stays.
    th = math.radians(15)
    r = ramp_motion(mass=1, angle_deg=15, mu_static=0.4, mu_kinetic=0.3, velocity=3, position=0.5, length=10, duration=3)
    a = G0 * (math.sin(th) + 0.3 * math.cos(th))
    x = np.array(r["trajectory"]["position"]); v = np.array(r["trajectory"]["velocity"])
    assert x.max() == pytest.approx(0.5 + 9 / (2 * a), rel=1e-6)
    assert v[-1] == 0 and x[-1] == pytest.approx(x.max())


def test_launched_up_then_slides_back():
    th = math.radians(35)
    r = ramp_motion(mass=1, angle_deg=35, mu_static=0.3, mu_kinetic=0.2, velocity=2, position=5, length=10, duration=1.6)
    v = np.array(r["trajectory"]["velocity"]); t = np.array(r["trajectory"]["t"])
    t_stop = 2 / (G0 * (math.sin(th) + 0.2 * math.cos(th)))
    later = v[t > t_stop + 0.2]
    assert np.all(later < 0)
    assert (later[-1] - later[0]) / (t[t > t_stop + 0.2][-1] - t[t > t_stop + 0.2][0]) == pytest.approx(
        -G0 * (math.sin(th) - 0.2 * math.cos(th)), rel=1e-6)


def test_energy_bookkeeping():
    r = ramp_motion(mass=3, angle_deg=30, mu_static=0.2, mu_kinetic=0.1, position=4, duration=1)["trajectory"]
    k, p, th = np.array(r["kinetic"]), np.array(r["potential"]), np.array(r["thermal"])
    assert np.allclose(k + p + th, k[0] + p[0] + th[0])
    assert th[-1] > 0


def test_stops_at_bottom():
    r = ramp_motion(mass=1, angle_deg=45, position=1, duration=3)
    assert r["result"]["stopped_at_end"] == "bottom"
    assert r["trajectory"]["position"][-1] == 0 and r["trajectory"]["velocity"][-1] == 0


def test_ramp_validation():
    with pytest.raises(ValueError):
        ramp_motion(mass=1, angle_deg=30, mu_static=0.1, mu_kinetic=0.2)
    with pytest.raises(ValueError):
        ramp_motion(mass=1, angle_deg=90)
