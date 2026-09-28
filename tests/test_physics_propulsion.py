import math

import numpy as np
import pytest
from scipy.optimize import minimize

from app.modules.physics.propulsion import (
    G0, multi_stage_delta_v, optimize_staging, rocket_equation, thrust_parameters,
)


def test_delta_v_mass_ratio_e():
    # m0/mf = e  ->  dv = ve exactly
    r = rocket_equation(isp=450, initial_mass=math.e * 1000, final_mass=1000)
    assert r["result"] == pytest.approx(450 * G0)
    assert r["solved_for"] == "delta_v"


def test_textbook_example():
    # Curtis-style: ve = 3 km/s, mass ratio 10 -> dv = 3000 ln 10 = 6907.8 m/s
    r = rocket_equation(exhaust_velocity=3000, initial_mass=10_000, final_mass=1000)
    assert r["result"] == pytest.approx(6907.755, rel=1e-6)
    assert r["propellant_fraction"] == pytest.approx(0.9)


@pytest.mark.parametrize("unknown", ["delta_v", "exhaust_velocity", "initial_mass", "final_mass"])
def test_solve_for_each_variable(unknown):
    full = {"delta_v": 3000 * math.log(4), "exhaust_velocity": 3000.0, "initial_mass": 400.0, "final_mass": 100.0}
    args = {k: v for k, v in full.items() if k != unknown}
    r = rocket_equation(**args)
    assert r["solved_for"] == unknown
    assert r["result"] == pytest.approx(full[unknown])


def test_isp_solved_reports_seconds():
    r = rocket_equation(delta_v=4000, initial_mass=300, final_mass=100)
    assert r["isp"] == pytest.approx(4000 / math.log(3) / G0)


@pytest.mark.parametrize("kwargs", [
    {"isp": 300, "initial_mass": 100},                                   # two unknowns
    {"isp": 300, "exhaust_velocity": 3000, "initial_mass": 2, "final_mass": 1},
    {"isp": 300, "initial_mass": 100, "final_mass": 200},                # mf > m0
    {"isp": -1, "initial_mass": 100, "final_mass": 50},
])
def test_rocket_equation_validation(kwargs):
    with pytest.raises(ValueError):
        rocket_equation(**kwargs)


def test_single_stage_matches_rocket_equation():
    r = multi_stage_delta_v([{"isp": 300, "propellant_mass": 900, "dry_mass": 50}], payload_mass=50)
    assert r["result"] == pytest.approx(300 * G0 * math.log(1000 / 100))


def test_two_stage_by_hand():
    stages = [{"isp": 280, "propellant_mass": 80_000, "dry_mass": 8000},
              {"isp": 350, "propellant_mass": 15_000, "dry_mass": 1500}]
    r = multi_stage_delta_v(stages, payload_mass=1000)
    dv1 = 280 * G0 * math.log(105_500 / 25_500)
    dv2 = 350 * G0 * math.log(17_500 / 2_500)
    assert [s["delta_v"] for s in r["stages"]] == pytest.approx([dv1, dv2])
    assert r["result"] == pytest.approx(dv1 + dv2)
    assert r["liftoff_mass"] == pytest.approx(105_500)


def test_staging_beats_single_stage():
    # Same total propellant and dry mass split into two stages gives more delta-v.
    one = multi_stage_delta_v([{"isp": 300, "propellant_mass": 90_000, "dry_mass": 9000}], 1000)["result"]
    two = multi_stage_delta_v([{"isp": 300, "propellant_mass": 60_000, "dry_mass": 6000},
                               {"isp": 300, "propellant_mass": 30_000, "dry_mass": 3000}], 1000)["result"]
    assert two > one


def _brute_force_mass(c, eps, payload, dv_total):
    def mass(dv):
        up = payload
        for i in reversed(range(len(c))):
            n = math.exp(dv[i] / c[i])
            den = 1 - n * eps[i]
            if den <= 0:
                return 1e30
            up += up * (n - 1) / den
        return up

    k = len(c)
    x0 = np.full(k - 1, dv_total / k)
    res = minimize(lambda d: mass(np.append(d, dv_total - d.sum())), x0, method="Nelder-Mead",
                   options={"xatol": 1e-6, "fatol": 1e-6, "maxiter": 10_000})
    return res.fun


def test_optimal_staging_matches_brute_force():
    stages = [{"isp": 400, "structural_fraction": 0.10},
              {"isp": 350, "structural_fraction": 0.15},
              {"isp": 300, "structural_fraction": 0.20}]
    r = optimize_staging(delta_v=12_000, payload_mass=5000, stages=stages)
    c = [s["isp"] * G0 for s in stages]
    eps = [s["structural_fraction"] for s in stages]
    assert r["result"]["liftoff_mass"] == pytest.approx(_brute_force_mass(c, eps, 5000, 12_000), rel=1e-6)
    assert sum(s["delta_v"] for s in r["result"]["stages"]) == pytest.approx(12_000)


def test_identical_stages_split_delta_v_equally():
    r = optimize_staging(9000, 1000, [{"isp": 350, "structural_fraction": 0.1}] * 3)
    assert [s["delta_v"] for s in r["result"]["stages"]] == pytest.approx([3000] * 3)


def test_optimal_design_is_consistent():
    # Feeding the optimised masses back into multi_stage_delta_v reproduces the target delta-v.
    r = optimize_staging(9500, 2000, [{"isp": 290, "structural_fraction": 0.08},
                                      {"isp": 420, "structural_fraction": 0.12}])
    stages = [{"isp": isp, "propellant_mass": s["propellant_mass"], "dry_mass": s["dry_mass"]}
              for isp, s in zip((290, 420), r["result"]["stages"])]
    assert multi_stage_delta_v(stages, 2000)["result"] == pytest.approx(9500)


def test_unreachable_delta_v():
    with pytest.raises(ValueError, match="unreachable"):
        optimize_staging(20_000, 1000, [{"isp": 300, "structural_fraction": 0.2}])


def test_thrust_parameters():
    r = thrust_parameters(thrust=1_000_000, isp=300, mass=80_000, propellant_mass=60_000)["result"]
    assert r["mass_flow_rate"] == pytest.approx(1e6 / (300 * G0))
    assert r["thrust_to_weight"] == pytest.approx(1e6 / (80_000 * G0))
    assert r["can_lift_off"] is True
    assert r["burn_time"] == pytest.approx(60_000 / r["mass_flow_rate"])


def test_thrust_parameters_on_moon():
    r = thrust_parameters(thrust=45_000, isp=311, mass=15_000, gravity=1.62)["result"]
    assert r["thrust_to_weight"] == pytest.approx(45_000 / (15_000 * 1.62))
