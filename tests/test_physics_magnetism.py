import math

import numpy as np
import pytest

from app.modules.physics.magnetism import MU0, coil_flux, magnet_coil_induction, magnet_field


def test_far_field_flux_matches_point_dipole():
    m, length, a = 2.0, 0.01, 0.05
    z = np.array([0.5, 1.0, -0.8])
    exact_dipole = MU0 * m * a**2 / (2 * (a**2 + z**2) ** 1.5)
    assert coil_flux(z, m / length, length / 2, a) == pytest.approx(exact_dipole, rel=1e-3)


def test_flux_continuous_through_the_coil():
    z = np.linspace(-0.2, 0.2, 40001)
    phi = coil_flux(z, 10, 0.04, 0.03)
    assert np.max(np.abs(np.diff(phi))) < 1e-3 * np.max(phi)
    assert phi == pytest.approx(phi[::-1])                  # symmetric about the coil


def test_emf_reverses_and_integrates_to_flux_change():
    r = magnet_coil_induction(moment=1, length=0.08, turns=200, radius=0.03, resistance=4, speed=2, n_points=20000)
    tr = r["trajectory"]
    t, emf, lam = map(np.array, (tr["t"], tr["emf"], tr["flux_linkage"]))
    assert emf[: len(emf) // 2].min() < 0 < emf[len(emf) // 2:].max()   # approaching vs leaving
    assert np.trapezoid(emf, t) == pytest.approx(-(lam[-1] - lam[0]), abs=1e-9)
    mid = len(t) // 2
    k = slice(mid - 2000, mid + 2000)
    assert np.gradient(lam, t)[k] == pytest.approx(-emf[k], rel=1e-3, abs=1e-6)


def test_emf_scales_with_speed_and_turns():
    base = magnet_coil_induction(1, 0.08, 100, 0.03, speed=1)["result"]["peak_emf"]
    assert magnet_coil_induction(1, 0.08, 100, 0.03, speed=3)["result"]["peak_emf"] == pytest.approx(3 * base)
    assert magnet_coil_induction(1, 0.08, 300, 0.03, speed=1)["result"]["peak_emf"] == pytest.approx(3 * base)


def test_flip_reverses_emf():
    a = np.array(magnet_coil_induction(1, 0.08, 50, 0.03, motion="oscillate", amplitude=0.05)["trajectory"]["emf"])
    b = np.array(magnet_coil_induction(1, 0.08, 50, 0.03, motion="oscillate", amplitude=0.05, flip=True)["trajectory"]["emf"])
    assert b == pytest.approx(-a)


def test_magnet_field_on_axis_and_lines():
    m, length = 1.0, 0.1
    r = magnet_field(m, length, [-0.5, 0.5], [-0.3, 0.3], grid=101)
    g = r["grid"]
    bx = np.array(g["bx"]); xs = np.array(g["x"]); j = len(g["y"]) // 2
    i = np.argmin(abs(xs - 0.4))
    qm, d1, d2 = m / length, xs[i] - 0.05, xs[i] + 0.05
    expected = MU0 / (4 * math.pi) * qm * (1 / d1**2 - 1 / d2**2)
    assert bx[j, i] == pytest.approx(expected, rel=1e-6)
    ends_at_s = sum(math.hypot(l[-1][0] + 0.05, l[-1][1]) < 0.02 for l in r["field_lines"])
    assert ends_at_s >= len(r["field_lines"]) // 2


def test_magnetism_validation():
    with pytest.raises(ValueError):
        magnet_coil_induction(1, 0.08, 0, 0.03)
    with pytest.raises(ValueError):
        magnet_coil_induction(1, 0.08, 10, 0.03, motion="spin")
