import math

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from app.modules.physics.classical import harmonic_oscillator, projectile_motion

G = 9.80665


def test_vacuum_range_45_deg():
    r = projectile_motion(speed=50, angle_deg=45)["result"]
    assert r["range"] == pytest.approx(50**2 / G)
    assert r["max_height"] == pytest.approx(50**2 / (4 * G))
    assert r["flight_time"] == pytest.approx(2 * 50 * math.sin(math.pi / 4) / G)
    assert r["impact_speed"] == pytest.approx(50)


def test_vacuum_from_height():
    # Horizontal launch from 20 m at 10 m/s: t = sqrt(2h/g), range = v t
    r = projectile_motion(speed=10, angle_deg=0, height=20)["result"]
    t = math.sqrt(2 * 20 / G)
    assert r["flight_time"] == pytest.approx(t)
    assert r["range"] == pytest.approx(10 * t)
    assert r["impact_speed"] == pytest.approx(math.sqrt(10**2 + 2 * G * 20))


def test_complementary_angles_same_range():
    assert projectile_motion(speed=30, angle_deg=30)["result"]["range"] == pytest.approx(
        projectile_motion(speed=30, angle_deg=60)["result"]["range"])


def test_trajectory_is_plot_ready():
    r = projectile_motion(speed=20, angle_deg=60, n_points=11)
    traj = r["trajectory"]
    assert len(traj["t"]) == len(traj["x"]) == len(traj["y"]) == 11
    assert traj["y"][0] == 0 and traj["y"][-1] == 0


def test_tiny_drag_approaches_vacuum():
    vac = projectile_motion(speed=40, angle_deg=35)["result"]
    drag = projectile_motion(speed=40, angle_deg=35, mass=1000, drag_coefficient=1e-6, area=1e-6)["result"]
    assert drag["range"] == pytest.approx(vac["range"], rel=1e-6)


def test_drag_reduces_range_and_speed():
    vac = projectile_motion(speed=50, angle_deg=45)["result"]
    ball = projectile_motion(speed=50, angle_deg=45, mass=0.145, drag_coefficient=0.3, area=0.0042)["result"]
    assert ball["range"] < vac["range"]
    assert ball["impact_speed"] < 50
    assert ball["impact_angle_deg"] > 45  # descends more steeply


def test_vertical_launch_with_drag_max_height():
    # Analytic: h_max = ln(1 + k v0^2 / g) / (2k) for quadratic drag
    m, cd, a, rho, v0 = 0.5, 0.47, 0.01, 1.225, 40.0
    k = 0.5 * rho * cd * a / m
    r = projectile_motion(speed=v0, angle_deg=90, mass=m, drag_coefficient=cd, area=a)["result"]
    assert r["max_height"] == pytest.approx(math.log(1 + k * v0**2 / G) / (2 * k), rel=1e-5)


def test_drop_reaches_terminal_velocity():
    # Skydiver-like: m=80, Cd*A = 0.7 -> v_t = sqrt(2 m g / (rho Cd A)) ~ 42.7 m/s
    r = projectile_motion(speed=0, angle_deg=0, height=3000, mass=80, drag_coefficient=1.0, area=0.7)["result"]
    v_t = math.sqrt(2 * 80 * G / (1.225 * 0.7))
    assert r["terminal_velocity"] == pytest.approx(v_t)
    assert r["impact_speed"] == pytest.approx(v_t, rel=1e-6)


@pytest.mark.parametrize("kwargs", [
    {"speed": -1, "angle_deg": 10},
    {"speed": 10, "angle_deg": 120},
    {"speed": 10, "angle_deg": 30, "mass": 1},               # partial drag args
    {"speed": 0, "angle_deg": 0},                            # nothing moves
])
def test_projectile_validation(kwargs):
    with pytest.raises(ValueError):
        projectile_motion(**kwargs)


def test_simple_harmonic_period_and_energy():
    r = harmonic_oscillator(mass=2, stiffness=50, initial_displacement=0.3, initial_velocity=1.0)
    res = r["result"]
    assert res["natural_frequency"] == pytest.approx(5)
    assert res["period"] == pytest.approx(2 * math.pi / 5)
    assert res["regime"] == "undamped"
    assert res["amplitude"] == pytest.approx(math.hypot(0.3, 1.0 / 5))
    energy = np.array(r["trajectory"]["energy"])
    assert np.allclose(energy, 0.5 * 50 * 0.3**2 + 0.5 * 2 * 1.0**2)


def test_underdamped_q_factor():
    res = harmonic_oscillator(mass=1, stiffness=100, damping=2)["result"]
    assert res["damping_ratio"] == pytest.approx(0.1)
    assert res["quality_factor"] == pytest.approx(5)
    assert res["damped_frequency"] == pytest.approx(10 * math.sqrt(1 - 0.01))


@pytest.mark.parametrize("damping, regime", [(0, "undamped"), (4, "underdamped"),
                                             (20, "critically damped"), (60, "overdamped")])
def test_all_regimes_match_numerical_ode(damping, regime):
    m, k, x0, v0 = 1.0, 100.0, 0.2, -1.5
    r = harmonic_oscillator(mass=m, stiffness=k, damping=damping, initial_displacement=x0,
                            initial_velocity=v0, duration=2.0, n_points=41)
    assert r["result"]["regime"] == regime
    t = r["trajectory"]["t"]
    sol = solve_ivp(lambda _t, s: [s[1], -(damping * s[1] + k * s[0]) / m], (0, 2), [x0, v0],
                    t_eval=t, rtol=1e-11, atol=1e-13)
    assert r["trajectory"]["x"] == pytest.approx(sol.y[0].tolist(), abs=1e-8)
    assert r["trajectory"]["v"] == pytest.approx(sol.y[1].tolist(), abs=1e-7)


def test_oscillator_validation():
    with pytest.raises(ValueError):
        harmonic_oscillator(mass=0, stiffness=1)
    with pytest.raises(ValueError):
        harmonic_oscillator(mass=1, stiffness=1, damping=-1)
