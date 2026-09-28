import math

import numpy as np
import pytest

from app.modules.physics.charged import ME, MP, QE, charged_particle
from app.modules.physics.doppler import doppler_effect
from app.modules.physics.oscillations import G0, coupled_oscillators, double_pendulum, driven_oscillator


# --- driven damped oscillator -----------------------------------------------------------------

def test_driven_steady_state_formulae():
    # m=1, k=100 (ω0=10), b=1: at ω = ω0 the amplitude is F0/(b ω0) and the phase lag is 90°
    r = driven_oscillator(1, 100, 1, 1, 10)["result"]
    assert r["natural_frequency"] == pytest.approx(10)
    assert r["steady_amplitude"] == pytest.approx(0.1)
    assert r["phase_lag_deg"] == pytest.approx(90)
    assert r["quality_factor"] == pytest.approx(10)
    assert r["amplification"] == pytest.approx(10)  # = Q at ω0
    assert r["resonance_frequency"] == pytest.approx(math.sqrt(100 - 0.5))


def test_driven_numerical_matches_steady_state():
    # After the transient dies (t >> 2m/b), the simulated amplitude equals the analytic one
    out = driven_oscillator(1, 100, 2, 3, 7, duration=30, n_points=6000)
    t, x = np.array(out["trajectory"]["t"]), np.array(out["trajectory"]["x"])
    late = t > 20
    assert np.max(np.abs(x[late])) == pytest.approx(out["result"]["steady_amplitude"], rel=2e-3)


def test_driven_response_peak_and_bandwidth():
    out = driven_oscillator(1, 100, 0.5, 1, 5)
    w = np.array(out["response"]["omega"]); a = np.array(out["response"]["amplitude"], float)
    assert w[np.nanargmax(a)] == pytest.approx(out["result"]["resonance_frequency"], abs=0.06)
    # Mean power peaks at ω0 and falls to half at ω = √(ω0² + γ²/4) ± γ/2 (γ = b/m): bandwidth = b/m exactly
    peak = driven_oscillator(1, 100, 0.5, 1, 10)["result"]["mean_power"]
    for sign in (-1, 1):
        g = 0.5  # b/m
        wh = math.sqrt(100 + g**2 / 4) + sign * g / 2
        assert driven_oscillator(1, 100, 0.5, 1, wh)["result"]["mean_power"] == pytest.approx(peak / 2)
    # Low-frequency limit: static displacement F0/k, phase 0; high frequency: phase → 180°
    assert a[1] == pytest.approx(0.01, rel=1e-3)
    assert out["response"]["phase_deg"][-1] > 170


def test_driven_validation():
    with pytest.raises(ValueError):
        driven_oscillator(1, 100, 0, 1, 10)  # undamped at resonance
    with pytest.raises(ValueError):
        driven_oscillator(0, 100, 1, 1, 10)


# --- coupled oscillators -------------------------------------------------------------------

def test_two_mass_normal_modes():
    # Equal masses, three equal springs: ω1 = √(k/m), ω2 = √(3k/m); shapes (1,1) and (1,-1)
    r = coupled_oscillators([2, 2], [8, 8, 8])["result"]
    assert r["frequencies"] == pytest.approx([2, math.sqrt(12)])
    s = r["mode_shapes"]
    assert s[0] == pytest.approx([1, 1]) and abs(s[1][0]) == pytest.approx(1) and s[1][0] == pytest.approx(-s[1][1])


def test_beats_transfer_energy_and_conserve_it():
    # Weak coupling: all the motion moves from mass 1 to mass 2 after half a beat period
    out = coupled_oscillators([1, 1], [10, 0.5, 10], [0.1, 0], duration=40, n_points=8001)
    w1, w2 = out["result"]["frequencies"]
    t = np.array(out["trajectory"]["t"]); x = np.array(out["trajectory"]["x"])
    half_beat = math.pi / (w2 - w1)
    window = np.abs(t - half_beat) < math.pi / w1
    assert np.max(np.abs(x[0][window])) < 0.01 and np.max(np.abs(x[1][window])) > 0.095
    # Total energy = k x0²/2 for the stretched springs (10 + 0.5) * 0.1² / 2
    assert out["result"]["total_energy"] == pytest.approx(0.5 * 10.5 * 0.01)


def test_three_mass_chain_and_free_mode():
    # Fixed-fixed chain of 3: ω_n = 2√(k/m) sin(nπ/8)
    r = coupled_oscillators([1, 1, 1], [1, 1, 1, 1])["result"]
    expect = [2 * math.sin(n * math.pi / 8) for n in (1, 2, 3)]
    assert r["frequencies"] == pytest.approx(expect)
    # Free-free two masses: one zero-frequency (translation) mode
    f = coupled_oscillators([1, 1], [0, 5, 0], velocities=[1, 1])["result"]
    assert f["frequencies"][0] == pytest.approx(0, abs=1e-7) and f["periods"][0] is None


def test_coupled_validation():
    with pytest.raises(ValueError):
        coupled_oscillators([1, 1], [1, 1])
    with pytest.raises(ValueError):
        coupled_oscillators([1, -1], [1, 1, 1])


# --- double pendulum ----------------------------------------------------------------------

def test_double_pendulum_small_angle_normal_mode():
    # m1 = m2, l1 = l2 = l: slow mode ω² = (2 − √2) g/l with θ2 = √2 θ1
    out = double_pendulum(1.0, math.sqrt(2), duration=20, n_points=4001, perturbation_deg=0)
    t = np.array(out["trajectory"]["t"]); th = np.array(out["trajectory"]["theta1_deg"])
    crossings = t[1:][np.diff(np.sign(th)) != 0]
    period = 2 * np.mean(np.diff(crossings))
    assert period == pytest.approx(2 * math.pi / math.sqrt((2 - math.sqrt(2)) * G0), rel=2e-3)
    ratio = np.array(out["trajectory"]["theta2_deg"]) / np.where(np.abs(th) > 0.3, th, np.nan)
    assert np.nanmedian(ratio) == pytest.approx(math.sqrt(2), rel=5e-3)


def test_double_pendulum_chaos_and_energy():
    r = double_pendulum(120, -20, duration=20)["result"]
    assert r["max_energy_drift"] < 1e-6
    assert r["chaotic"] and r["lyapunov_exponent"] > 0.3
    assert r["final_separation"] > 0.1
    calm = double_pendulum(5, 5, duration=20)["result"]
    assert not calm["chaotic"] and calm["final_separation"] < 1e-6


# --- charged particles -----------------------------------------------------------------------

def test_cyclotron_proton():
    # Proton, 1 T: ω = eB/m = 9.58e7 rad/s, radius = m v / (e B)
    out = charged_particle([1e5, 0, 0], magnetic_field=[0, 0, 1], particle="proton")
    r = out["result"]
    assert r["cyclotron_frequency"] == pytest.approx(QE / MP)
    assert r["cyclotron_frequency_hz"] / 1e6 == pytest.approx(15.25, abs=0.01)
    assert r["larmor_radius"] == pytest.approx(MP * 1e5 / QE)
    x, y = np.array(out["trajectory"]["x"]), np.array(out["trajectory"]["y"])
    # Circle centred at (0, -R) for a positive charge moving +x in +z field
    rr = np.hypot(x - 0, y + r["larmor_radius"])
    assert np.allclose(rr, r["larmor_radius"], rtol=1e-6)
    assert abs(r["kinetic_energy_change"]) / (0.5 * MP * 1e10) < 1e-8  # B does no work


def test_electron_helix_pitch_and_sense():
    out = charged_particle([1e6, 0, 2e5], magnetic_field=[0, 0, 0.01], particle="electron")
    r = out["result"]
    assert r["pitch"] == pytest.approx(2e5 * 2 * math.pi * ME / (QE * 0.01))
    z = np.array(out["trajectory"]["z"]); t = np.array(out["trajectory"]["t"])
    assert z[-1] == pytest.approx(2e5 * t[-1], rel=1e-6)
    # Electron gyrates the other way: starts moving +x, curves toward +y
    assert out["trajectory"]["y"][5] > 0


def test_e_cross_b_drift():
    out = charged_particle([0, 0, 0], magnetic_field=[0, 0, 0.1], electric_field=[0, 1000, 0], particle="proton",
                           n_points=4001)
    r = out["result"]
    assert r["drift_velocity"] == pytest.approx([1e4, 0, 0])
    t, x = np.array(out["trajectory"]["t"]), np.array(out["trajectory"]["x"])
    # Over whole gyro-periods the guiding centre moves at E/B
    assert x[-1] / t[-1] == pytest.approx(1e4, rel=1e-5)


def test_charged_validation():
    with pytest.raises(ValueError):
        charged_particle([1, 0], magnetic_field=[0, 0, 1])
    with pytest.raises(ValueError):
        charged_particle([1e8, 0, 0], magnetic_field=[0, 0, 1])
    with pytest.raises(ValueError):
        charged_particle([1, 0, 0], particle="muon")


# --- Doppler -----------------------------------------------------------------------------

def test_doppler_textbook():
    r = doppler_effect(440, 34.3)["result"]
    assert r["approaching_frequency"] == pytest.approx(440 / 0.9)
    assert r["receding_frequency"] == pytest.approx(400)
    o = doppler_effect(440, 0, observer_speed=34.3)["result"]
    assert o["approaching_frequency"] == pytest.approx(484) and o["receding_frequency"] == pytest.approx(396)


def test_mach_cone():
    r = doppler_effect(100, 686)["result"]
    assert r["mach_number"] == pytest.approx(2) and r["supersonic"]
    assert r["mach_cone_half_angle_deg"] == pytest.approx(30)
    assert r["approaching_frequency"] is None


def test_drive_by_limits():
    out = doppler_effect(500, 30, pass_distance=5, track_half_length=2000, n_points=20000)
    d, r = out["drive_by"], out["result"]
    heard = np.array(d["heard_frequency"])
    assert heard[0] == pytest.approx(r["approaching_frequency"], rel=1e-4)
    assert heard[-1] == pytest.approx(r["receding_frequency"], rel=1e-4)
    # Sound emitted at closest approach is heard at the true pitch, pass_distance/c later
    assert np.interp(0, d["source_x"], heard) == pytest.approx(500, rel=1e-5)
    t0 = np.interp(0, d["source_x"], d["emission_time"])
    assert np.interp(0, d["source_x"], d["arrival_time"]) - t0 == pytest.approx(5 / 343, rel=1e-3)
    assert np.all(np.diff(d["arrival_time"]) > 0)  # subsonic: sounds arrive in order


def test_supersonic_drive_by_boom():
    c, v, d = 343.0, 686.0, 50.0
    out = doppler_effect(100, v, pass_distance=d, track_half_length=1000, n_points=20000)["drive_by"]
    # The boom is the earliest arrival: d(t_arrive)/dt_emit = 1 − v cos φ / c = 0, so the sound was emitted
    # when the line to the listener made φ = acos(c/v) = 60° with the path, i.e. |x| = d / tan φ before it
    phi = math.acos(c / v)
    x_emit = -d / math.tan(phi)
    t_emit = (x_emit + 1000) / v
    expect = t_emit + math.hypot(x_emit, d) / c
    assert out["boom_time"] == pytest.approx(expect, rel=1e-4)
    assert np.all(np.array(out["heard_frequency"]) > 0)
