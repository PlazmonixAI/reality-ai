import math

import numpy as np
import pytest

from app.modules.physics.waves import slit_interference, string_wave


def _peak_time_at(res, x_target):
    x = np.array(res["frames"]["x"]); t = np.array(res["frames"]["t"]); u = np.array(res["frames"]["u"])
    j = np.argmin(abs(x - x_target))
    return t[np.argmax(u[:, j])], u


def test_wave_speed_and_wavelength():
    r = string_wave(length=2, tension=10, linear_density=0.01, duration=0.1, frequency=10)["result"]
    assert r["wave_speed"] == pytest.approx(math.sqrt(1000))
    assert r["wavelength"] == pytest.approx(math.sqrt(1000) / 10)


def test_harmonics_fixed_and_loose():
    c = math.sqrt(1000)
    fixed = string_wave(length=2, tension=10, linear_density=0.01, duration=0.01, end="fixed")["result"]["harmonics"]
    loose = string_wave(length=2, tension=10, linear_density=0.01, duration=0.01, end="loose")["result"]["harmonics"]
    assert fixed[:3] == pytest.approx([c / 4, 2 * c / 4, 3 * c / 4])
    assert loose[:3] == pytest.approx([c / 8, 3 * c / 8, 5 * c / 8])


def test_pulse_travels_at_wave_speed():
    L, T, mu, w = 4.0, 16.0, 0.04, 0.02           # c = 20 m/s
    res = string_wave(length=L, tension=T, linear_density=mu, duration=0.25, driver="pulse", pulse_width=w,
                      amplitude=0.05, end="none", n_cells=400, n_frames=1000)
    t_peak, _ = _peak_time_at(res, 2.0)
    assert t_peak == pytest.approx(2 * w + 2.0 / 20, abs=2e-3)


def test_fixed_end_inverts_loose_end_does_not():
    common = dict(length=2.0, tension=4.0, linear_density=0.01, duration=0.25, driver="pulse", pulse_width=0.01,
                  amplitude=0.05, n_cells=400, n_frames=500)   # c = 20 m/s, round trip to x=1 after reflection
    for end, sign in (("fixed", -1), ("loose", 1)):
        res = string_wave(end=end, **common)
        x = np.array(res["frames"]["x"]); t = np.array(res["frames"]["t"]); u = np.array(res["frames"]["u"])
        # After reflecting (t ~ 0.02 + 0.1 + 0.05 = 0.17 s) the pulse is back near x = 1 m.
        k = np.argmin(abs(t - (0.02 + 0.1 + 0.05)))
        extreme = u[k][np.argmax(abs(u[k]))]
        assert np.sign(extreme) == sign
        assert abs(extreme) == pytest.approx(0.05, rel=0.05)


def test_absorbing_end_leaves_string_quiet():
    res = string_wave(length=1, tension=1, linear_density=0.01, duration=0.4, driver="pulse", pulse_width=0.01,
                      amplitude=0.05, end="none", n_cells=200)
    assert np.max(np.abs(res["frames"]["u"][-1])) < 1e-3


def test_damping_reduces_amplitude():
    common = dict(length=2, tension=10, linear_density=0.01, duration=0.5, frequency=12, amplitude=0.01, end="none")
    undamped = np.max(np.abs(string_wave(**common)["frames"]["u"][-1]))
    damped = np.max(np.abs(string_wave(damping=60, **common)["frames"]["u"][-1][100:]))
    assert damped < 0.5 * undamped


def test_resonance_builds_up():
    # Driving a fixed-fixed string at its 2nd harmonic grows far beyond the drive amplitude.
    c = math.sqrt(10 / 0.01)
    common = dict(length=2, tension=10, linear_density=0.01, duration=1.0, amplitude=0.001, end="fixed")
    on = np.max(np.abs(string_wave(frequency=c / 2, **common)["frames"]["u"]))
    off = np.max(np.abs(string_wave(frequency=0.73 * c / 2, **common)["frames"]["u"]))
    assert on > 10 * 0.001 and on > 3 * off


def test_string_validation():
    with pytest.raises(ValueError):
        string_wave(length=1, tension=1, linear_density=1, duration=1, end="bouncy")
    with pytest.raises(ValueError):
        string_wave(length=1, tension=-1, linear_density=1, duration=1)


def test_double_slit_maxima_and_spacing():
    lam, d, D = 650e-9, 100e-6, 1.0
    r = slit_interference(lam, d, D, n_slits=2, slit_width=0)
    assert r["result"]["fringe_spacing"] == pytest.approx(lam * D / d)
    m1 = D * math.tan(math.asin(lam / d))
    assert min(abs(y - m1) for y in r["result"]["maxima"]) < 1e-12
    y, I = np.array(r["pattern"]["y"]), np.array(r["pattern"]["intensity"])
    # cos^2 fringes: intensity at a dark fringe is ~0
    ym = D * math.tan(math.asin(0.5 * lam / d))
    assert np.interp(ym, y, I) < 1e-3
    assert np.interp(0, y, I) == pytest.approx(1)


def test_single_slit_first_minimum():
    lam, a, D = 500e-9, 50e-6, 2.0
    r = slit_interference(lam, 1.0, D, n_slits=1, slit_width=a)
    first = min(p for p in r["result"]["minima"] if p > 0)
    assert first == pytest.approx(D * math.tan(math.asin(lam / a)))
    assert r["result"]["central_width"] == pytest.approx(2 * lam * D / a)
    y, I = np.array(r["pattern"]["y"]), np.array(r["pattern"]["intensity"])
    assert np.interp(first, y, I) < 1e-4


def test_grating_principal_maxima_are_bright_and_sharp():
    lam, d = 600e-9, 2e-6
    r5 = slit_interference(lam, d, 1.0, n_slits=5, n_points=20001)
    y, I = np.array(r5["pattern"]["y"]), np.array(r5["pattern"]["intensity"])
    m1 = math.tan(math.asin(lam / d))
    assert np.interp(m1, y, I) == pytest.approx(1, abs=1e-3)
    # Between principal maxima the N=5 pattern is much dimmer than N=2
    r2 = slit_interference(lam, d, 1.0, n_slits=2, n_points=20001)
    mid = math.tan(math.asin(0.3 * lam / d))
    assert np.interp(mid, y, I) < 0.5 * np.interp(mid, np.array(r2["pattern"]["y"]), np.array(r2["pattern"]["intensity"]))


def test_near_field_shape():
    nf = slit_interference(650e-9, 100e-6, 1.0)["near_field"]
    assert len(nf["re"]) == len(nf["y"]) and len(nf["re"][0]) == len(nf["x"])
    assert nf["spacing_compressed"] is True           # 100 µm = 154 wavelengths: too wide to draw finely
    small = slit_interference(650e-9, 5e-6, 1.0)["near_field"]
    assert small["spacing_compressed"] is False and small["slits_y"] == pytest.approx([-2.5e-6, 2.5e-6])
    # at least ~5 samples per wavelength
    assert (small["y"][-1] - small["y"][0]) / (len(small["y"]) - 1) <= 650e-9 / 4.9


def test_slit_validation():
    with pytest.raises(ValueError):
        slit_interference(500e-9, 1e-6, 1, n_slits=2, slit_width=2e-6)
    with pytest.raises(ValueError):
        slit_interference(500e-9, 1e-6, 1, n_slits=1)
