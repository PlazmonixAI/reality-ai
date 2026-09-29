import math

import numpy as np
import pytest

from app.modules.physics.fluids import buoyancy, pipe_flow
from app.modules.physics.heat import heat_conduction
from app.modules.physics.kepler import kepler_orbit, solve_kepler
from app.modules.physics.quantum import HBAR, ME, QE, quantum_tunnelling, quantum_well
from app.modules.physics.rotation import G0, rolling_race


# --- rolling --------------------------------------------------------------------------------

def test_rolling_accelerations_and_order():
    r = rolling_race(["hoop", "solid_sphere", "solid_cylinder", "hollow_sphere", "frictionless_block"], angle_deg=30)["result"]
    by = {x["shape"]: x for x in r["racers"]}
    g = G0 * 0.5
    assert by["solid_sphere"]["acceleration"] == pytest.approx(5 / 7 * g)
    assert by["solid_cylinder"]["acceleration"] == pytest.approx(2 / 3 * g)
    assert by["hollow_sphere"]["acceleration"] == pytest.approx(3 / 5 * g)
    assert by["hoop"]["acceleration"] == pytest.approx(g / 2)
    assert r["finish_order"] == ["frictionless_block", "solid_sphere", "solid_cylinder", "hollow_sphere", "hoop"]


def test_rolling_energy_split_and_speed():
    x = rolling_race(["solid_sphere"], angle_deg=20, length=2)["result"]["racers"][0]
    assert x["energy_fraction_rotational"] == pytest.approx(2 / 7)
    assert x["energy_fraction_translational"] == pytest.approx(5 / 7)
    h = 2 * math.sin(math.radians(20))
    assert x["final_speed"] == pytest.approx(math.sqrt(10 / 7 * G0 * h))
    assert x["final_spin"] == pytest.approx(x["final_speed"] / 0.1)


def test_slipping_when_friction_is_too_small():
    # Hoop on 45°: needs μ ≥ tan θ · k/(1+k) = 0.5; with μ = 0.2 it slides and loses energy
    x = rolling_race(["hoop"], angle_deg=45, mu=0.2)["result"]["racers"][0]
    assert x["friction_needed"] == pytest.approx(0.5)
    assert not x["rolling"] and x["acceleration"] == pytest.approx(G0 * math.sqrt(0.5) * 0.8)
    assert x["energy_fraction_lost"] > 0.05
    assert rolling_race(["hoop"], angle_deg=45, mu=0.5)["result"]["racers"][0]["rolling"]


# --- fluids --------------------------------------------------------------------------------

def test_iceberg_and_floating_fraction():
    r = buoyancy(917, 1.0, 1025)["result"]
    assert r["floats"] and r["fraction_submerged"] == pytest.approx(917 / 1025)  # ~89 % under water
    wood = buoyancy(500, 0.002, 1000)["result"]
    assert wood["fraction_submerged"] == pytest.approx(0.5) and wood["extra_load_capacity"] == pytest.approx(1.0)
    assert wood["apparent_weight"] == pytest.approx(0)


def test_sinking_block():
    r = buoyancy(7870, 1e-3, 1000)["result"]  # 1 L of iron
    assert not r["floats"]
    assert r["buoyant_force"] == pytest.approx(1000 * 1e-3 * G0)
    assert r["apparent_weight"] == pytest.approx(6.87 * G0)
    assert r["sinking_acceleration"] == pytest.approx(G0 * (1 - 1000 / 7870))


def test_venturi_and_height():
    q = 0.01
    r = pipe_flow([0.1, 0.05, 0.1], q, inlet_pressure=2e5)["result"]
    a1, a2 = math.pi * 0.05**2, math.pi * 0.025**2
    v1, v2 = q / a1, q / a2
    assert r["section_speeds"] == pytest.approx([v1, v2, v1])
    assert 2e5 - r["section_pressures"][1] == pytest.approx(0.5 * 998 * (v2**2 - v1**2))
    assert r["section_pressures"][2] == pytest.approx(2e5)  # recovered (no losses)
    # Rising 10 m at constant diameter costs ρ g h of pressure
    up = pipe_flow([0.1, 0.1], q, heights=[0, 10], inlet_pressure=2e5)["result"]
    assert 2e5 - up["section_pressures"][1] == pytest.approx(998 * G0 * 10)


# --- heat conduction -----------------------------------------------------------------------

def test_sine_mode_decays_exactly():
    # T = sin(πx/L) with both ends at 0 decays as exp(−α (π/L)² t)
    L, a, t = 1.0, 1e-4, 2000.0
    out = heat_conduction(length=L, duration=t, diffusivity=a, material=None, left_temperature=0, right_temperature=0,
                          initial="sine", initial_temperature=0, hot_temperature=1, n_nodes=201)
    mid = out["frames"]["temperature"][-1][100]
    assert mid == pytest.approx(math.exp(-a * (math.pi / L) ** 2 * t), rel=2e-4)


def test_steady_state_linear_and_insulated_conserves_heat():
    out = heat_conduction(length=0.2, duration=3000, material="copper", left_temperature=80, right_temperature=20)
    x, final = np.array(out["x"]), np.array(out["frames"]["temperature"][-1])
    assert np.max(np.abs(final - (80 - 300 * x))) < 0.01
    ins = heat_conduction(length=0.5, duration=500, material="aluminium", left_temperature=None, right_temperature=None,
                          initial="hot_middle", initial_temperature=20, hot_temperature=80)
    start_mean = np.trapezoid(ins["frames"]["temperature"][0], ins["x"]) / 0.5
    assert ins["result"]["final_mean_temperature"] == pytest.approx(start_mean, rel=1e-6)
    assert ins["steady_state"][0] == pytest.approx(start_mean)


def test_heat_validation():
    with pytest.raises(ValueError):
        heat_conduction(material="unobtainium")
    with pytest.raises(ValueError):
        heat_conduction(initial="spiky")


# --- quantum ----------------------------------------------------------------------------------

def test_infinite_well_electron_1nm():
    r = quantum_well("infinite", 1.0)
    e = r["result"]["energies_ev"]
    assert e[0] == pytest.approx(0.376, abs=1e-3)  # textbook value for an electron in a 1 nm box
    assert e[1] / e[0] == pytest.approx(4) and e[2] / e[0] == pytest.approx(9)
    x = np.array(r["x_nm"])
    assert np.trapezoid(r["densities"][0], x) == pytest.approx(1, rel=1e-5)


def test_harmonic_oscillator_ladder():
    w = 2e15
    r = quantum_well("harmonic", omega=w, n_levels=5, n_grid=3000)["result"]
    hw = HBAR * w / QE
    assert r["energies_ev"] == pytest.approx([hw * (n + 0.5) for n in range(5)], rel=1e-4)


def test_finite_well_below_infinite_and_counts():
    fin = quantum_well("finite", 1.0, depth_ev=5, n_levels=10, n_grid=4000)["result"]
    inf = quantum_well("infinite", 1.0, n_levels=4)["result"]
    assert fin["bound_states"] == fin["predicted_bound_states"] == 4
    assert all(f < i for f, i in zip(fin["energies_ev"], inf["energies_ev"]))
    # Exact: with z = k a/2 and z0 = (a/2)√(2mV0)/ħ, even states satisfy z tan z = √(z0² − z²),
    # odd states −z cot z = √(z0² − z²)
    from scipy.optimize import brentq
    z0 = 0.5e-9 * math.sqrt(2 * ME * 5 * QE) / HBAR
    even = lambda z: z * math.tan(z) - math.sqrt(z0**2 - z**2)  # noqa: E731
    odd = lambda z: -z / math.tan(z) - math.sqrt(z0**2 - z**2)  # noqa: E731
    zs = sorted([brentq(even, 1e-9, min(math.pi / 2 - 1e-9, z0)), brentq(odd, math.pi / 2 + 1e-9, min(math.pi - 1e-9, z0)),
                 brentq(even, math.pi + 1e-9, min(3 * math.pi / 2 - 1e-9, z0)), brentq(odd, 3 * math.pi / 2 + 1e-9, z0 - 1e-12)])
    exact = [(HBAR * 2 * z / 1e-9) ** 2 / (2 * ME) / QE for z in zs]
    assert fin["energies_ev"] == pytest.approx(exact, rel=2e-3)


def test_tunnelling_exact_and_consistency():
    r = quantum_tunnelling(1.0, 2.0, 0.5)["result"]
    kap = math.sqrt(2 * ME * QE) / HBAR
    expect = 1 / (1 + 4 * math.sinh(kap * 0.5e-9) ** 2 / (4 * 1 * 1))
    assert r["transmission"] == pytest.approx(expect)
    assert r["transmission_from_wavefunction"] == pytest.approx(r["transmission"], rel=1e-9)
    assert r["transmission"] + r["reflection"] == pytest.approx(1)
    # Thicker barrier: exponentially smaller, approaching the WKB-style estimate within a prefactor
    thick = quantum_tunnelling(1.0, 2.0, 2.0)["result"]
    assert thick["transmission"] < 1e-5 and 0.1 < thick["transmission"] / thick["wkb_estimate"] < 10


def test_resonant_transmission_above_barrier():
    # Above the barrier, T = 1 when q a = n π
    v0, a = 1.0, 1.0
    q = math.pi / 1e-9  # n = 1 for a = 1 nm
    e = v0 + (HBAR * q) ** 2 / (2 * ME) / QE
    r = quantum_tunnelling(e, v0, a)["result"]
    assert r["transmission"] == pytest.approx(1, abs=1e-9)
    assert r["transmission_from_wavefunction"] == pytest.approx(1, abs=1e-9)


# --- Kepler ----------------------------------------------------------------------------------

def test_earth_and_halley():
    earth = kepler_orbit(1.0, 0.0167)["result"]
    assert earth["period_years"] == pytest.approx(1.0, abs=1e-4)
    assert earth["perihelion_speed"] / 1000 == pytest.approx(30.29, abs=0.05)
    assert earth["aphelion_speed"] / 1000 == pytest.approx(29.29, abs=0.05)
    halley = kepler_orbit(17.8, 0.967)["result"]
    assert halley["period_years"] == pytest.approx(75.1, abs=0.1)
    assert halley["perihelion_au"] == pytest.approx(0.587, abs=1e-3)


def test_equal_areas_and_third_law():
    r = kepler_orbit(5.2, 0.5, n_sectors=10)["result"]
    areas = np.array(r["sector_areas_au2"])
    assert np.allclose(areas, areas[0], rtol=1e-10)
    assert areas.sum() == pytest.approx(math.pi * 5.2 * r["semi_minor_axis_au"])
    for a in (0.387, 1.524, 30.07):  # Mercury, Mars, Neptune
        assert kepler_orbit(a, 0.1)["result"]["t2_over_a3"] == pytest.approx(1.0, rel=1e-4)
    assert kepler_orbit(1, 0, star_mass_solar=4)["result"]["period_years"] == pytest.approx(0.5, rel=1e-4)


def test_kepler_equation_solver():
    for e in (0, 0.3, 0.9, 0.99):
        m = np.linspace(0, 2 * math.pi, 50)
        big = solve_kepler(m, e)
        assert np.allclose(big - e * np.sin(big), m, atol=1e-12)
    with pytest.raises(ValueError):
        kepler_orbit(1, 1.0)
