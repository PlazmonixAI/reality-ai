import math

import pytest

from app.modules.chemistry.kinetics import arrhenius, reaction_kinetics


def test_first_order():
    r = reaction_kinetics(order=1, rate_constant=0.005, initial_concentration=1.0, time=200)["result"]
    assert r["half_life"] == pytest.approx(math.log(2) / 0.005)
    assert r["concentration"] == pytest.approx(math.exp(-1))


def test_first_order_time_to_reach():
    # Time to fall to 1/8 = three half-lives
    r = reaction_kinetics(order=1, rate_constant=0.1, initial_concentration=0.8, concentration=0.1)["result"]
    assert r["time"] == pytest.approx(3 * math.log(2) / 0.1)


def test_zero_order():
    r = reaction_kinetics(order=0, rate_constant=0.01, initial_concentration=1.0, time=30)["result"]
    assert r["concentration"] == pytest.approx(0.7)
    assert r["half_life"] == pytest.approx(50)
    # Runs out and stays at zero
    assert reaction_kinetics(order=0, rate_constant=0.01, initial_concentration=1.0,
                             time=500)["result"]["concentration"] == 0


def test_second_order():
    # 1/[A] = 1/[A]0 + kt: [A]0 = 0.5, k = 0.2, t = 10 -> 1/[A] = 4 -> [A] = 0.25 = half-life
    r = reaction_kinetics(order=2, rate_constant=0.2, initial_concentration=0.5, time=10)["result"]
    assert r["concentration"] == pytest.approx(0.25)
    assert r["half_life"] == pytest.approx(10)


def test_curve_is_plot_ready():
    r = reaction_kinetics(order=1, rate_constant=1.0, initial_concentration=2.0, n_points=11)
    assert len(r["curve"]["t"]) == len(r["curve"]["concentration"]) == 11
    assert r["curve"]["t"][-1] == pytest.approx(5 * math.log(2))
    assert r["curve"]["concentration"][-1] == pytest.approx(2.0 / 32)


@pytest.mark.parametrize("kwargs", [
    {"order": 3, "rate_constant": 1, "initial_concentration": 1},
    {"order": 1, "rate_constant": -1, "initial_concentration": 1},
    {"order": 1, "rate_constant": 1, "initial_concentration": 1, "concentration": 2},
    {"order": 1, "rate_constant": 1, "initial_concentration": 1, "time": 1, "concentration": 0.5},
])
def test_kinetics_validation(kwargs):
    with pytest.raises(ValueError):
        reaction_kinetics(**kwargs)


def test_arrhenius_single_point():
    r = arrhenius(pre_exponential=1e13, activation_energy=100_000, temperature=500)
    assert r["result"] == pytest.approx(1e13 * math.exp(-100_000 / (8.314462618 * 500)))


def test_arrhenius_rule_of_thumb():
    # Ea ~ 50 kJ/mol roughly doubles the rate from 25 C to 35 C
    r = arrhenius(k1=1.0, t1=298.15, t2=308.15, activation_energy=50_000)
    assert r["result"] == pytest.approx(1.9, abs=0.05)


def test_arrhenius_two_point_round_trip():
    ea = arrhenius(k1=2.0e-5, t1=300, k2=5.0e-4, t2=350)["result"]
    k2 = arrhenius(k1=2.0e-5, t1=300, t2=350, activation_energy=ea)["result"]
    t2 = arrhenius(k1=2.0e-5, t1=300, k2=5.0e-4, activation_energy=ea)["result"]
    assert k2 == pytest.approx(5.0e-4)
    assert t2 == pytest.approx(350)
    assert ea == pytest.approx(56_174, rel=1e-3)


def test_arrhenius_validation():
    with pytest.raises(ValueError):
        arrhenius(k1=1, t1=300, k2=0.5, t2=350)   # negative Ea
    with pytest.raises(ValueError):
        arrhenius(k1=1, t1=300)
    with pytest.raises(ValueError):
        arrhenius(pre_exponential=1e10, temperature=300)
