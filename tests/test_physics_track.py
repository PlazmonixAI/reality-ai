import math

import numpy as np
import pytest

from app.modules.physics.track import G0, skate_track

PARABOLA = [[x, 0.5 * x * x] for x in np.linspace(-3, 3, 25)]


def test_frictionless_energy_conserved_and_bottom_speed():
    r = skate_track(PARABOLA, mass=50, start=0.25, duration=6)
    tr = r["trajectory"]
    e = np.array(tr["kinetic"]) + np.array(tr["potential"])
    assert np.ptp(e) / e[0] < 1e-5
    y0 = tr["y"][0]
    assert r["result"]["max_speed"] == pytest.approx(math.sqrt(2 * G0 * y0), rel=1e-3)


def test_small_oscillation_period():
    # y = a x^2 -> omega = sqrt(2 g a)
    r = skate_track(PARABOLA, start=0.495, duration=6, n_points=6001)
    x, t = np.array(r["trajectory"]["x"]), np.array(r["trajectory"]["t"])
    idx = np.where(np.diff(np.sign(x)) != 0)[0]
    period = 2 * np.mean(np.diff(t[idx]))
    assert period == pytest.approx(2 * math.pi / math.sqrt(2 * G0 * 0.5), rel=5e-3)


def test_friction_dissipates_and_balances():
    r = skate_track(PARABOLA, start=0.2, friction=0.1, duration=20)
    tr = r["trajectory"]
    k, p, th = map(np.array, (tr["kinetic"], tr["potential"], tr["thermal"]))
    assert np.allclose(k + p + th, k[0] + p[0], rtol=1e-6)
    assert th[-1] > 0.9 * (k[0] + p[0] - min(p))            # nearly all usable energy lost
    assert np.all(np.diff(th) >= -1e-6)


def test_released_from_top_end_rolls_down():
    r = skate_track(PARABOLA, start=1.0, duration=2)
    assert r["trajectory"]["x"][-1] < 3


def test_track_validation():
    with pytest.raises(ValueError):
        skate_track([[0, 0], [1, 1]])
    with pytest.raises(ValueError):
        skate_track([[0, 0], [2, 1], [1, 3]])
