import math

import pytest

from app.modules.mathematics.vectors_prob import probability_distribution, sample_means, vector_operations


def test_vectors_2d():
    r = vector_operations([3, 1], [1, 2])["result"]
    assert r["dot"] == 5 and r["cross"] == [0, 0, 5]
    assert r["angle_deg"] == pytest.approx(45)
    assert r["projection_a_on_b"][:2] == pytest.approx([1, 2])


def test_vectors_3d_orthogonal():
    r = vector_operations([1, 0, 0], [0, 1, 0])["result"]
    assert r["cross"] == [0, 0, 1] and r["angle_deg"] == pytest.approx(90)


def test_binomial():
    r = probability_distribution("binomial", {"n": 20, "p": 0.3}, [4, 8])["result"]
    assert r["mean"] == pytest.approx(6) and r["variance"] == pytest.approx(4.2)
    exact = sum(math.comb(20, k) * 0.3**k * 0.7 ** (20 - k) for k in range(4, 9))
    assert r["probability"] == pytest.approx(exact)


def test_normal_68_95():
    r = probability_distribution("normal", {"mean": 10, "sd": 2}, [8, 12])["result"]
    assert r["probability"] == pytest.approx(0.682689, abs=1e-6)


def test_poisson_and_exponential_moments():
    assert probability_distribution("poisson", {"rate": 3.5})["result"]["variance"] == pytest.approx(3.5)
    assert probability_distribution("exponential", {"rate": 2})["result"]["mean"] == pytest.approx(0.5)


def test_clt_spread_shrinks_like_sqrt_n():
    r = sample_means("exponential", 25, 20000, {"rate": 1}, seed=1)["result"]
    assert r["mean_of_means"] == pytest.approx(1, abs=0.01)
    assert r["sd_of_means"] == pytest.approx(1 / 5, rel=0.03)
    big = sample_means("exponential", 400, 5000, {"rate": 1}, seed=2)["result"]
    assert abs(big["skewness"]) < abs(r["skewness"])


def test_prob_validation():
    with pytest.raises(ValueError):
        probability_distribution("gamma")
    with pytest.raises(ValueError):
        probability_distribution("normal", {"sd": -1})
    with pytest.raises(ValueError):
        vector_operations([1], [1, 2])
