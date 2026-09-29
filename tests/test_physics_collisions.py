import math

import numpy as np
import pytest

from app.modules.physics.collisions import collision_1d, collisions_2d


def test_elastic_equal_masses_swap():
    r = collision_1d(1, 3, 1, -1)["result"]
    assert (r["v1_final"], r["v2_final"]) == pytest.approx((-1, 3))


def test_perfectly_inelastic_common_velocity():
    r = collision_1d(2, 3, 1, 0, restitution=0)
    assert r["result"]["v1_final"] == pytest.approx(2) and r["result"]["v2_final"] == pytest.approx(2)
    assert r["kinetic_energy"]["lost"] == pytest.approx(9 - 6)


def test_heavy_hits_light_elastic():
    # Textbook limit: m1 >> m2 at rest -> light ball leaves at ~2 v1
    r = collision_1d(1000, 1, 0.001, 0)["result"]
    assert r["v2_final"] == pytest.approx(2, rel=1e-5)


@pytest.mark.parametrize("e", [0, 0.5, 1])
def test_momentum_conserved_1d(e):
    r = collision_1d(3, 2, 5, -4, restitution=e)
    assert r["momentum"]["after"] == pytest.approx(r["momentum"]["before"])
    rel_before, rel_after = 2 - (-4), r["result"]["v1_final"] - r["result"]["v2_final"]
    assert rel_after == pytest.approx(-e * rel_before)


def test_2d_head_on_matches_1d():
    r = collisions_2d([{"mass": 2, "radius": 0.1, "x": 0.5, "y": 0.5, "vx": 1, "vy": 0},
                       {"mass": 1, "radius": 0.1, "x": 1.5, "y": 0.5, "vx": 0, "vy": 0}],
                      duration=1.5, width=10, height=1)
    exp = collision_1d(2, 1, 1, 0)["result"]
    assert r["result"]["final_velocities"][0] == pytest.approx([exp["v1_final"], 0])
    assert r["result"]["final_velocities"][1] == pytest.approx([exp["v2_final"], 0])


def test_glancing_equal_masses_right_angle():
    r = collisions_2d([{"mass": 1, "radius": 0.1, "x": 0.3, "y": 0.5, "vx": 1, "vy": 0},
                       {"mass": 1, "radius": 0.1, "x": 1.0, "y": 0.62, "vx": 0, "vy": 0}],
                      duration=1.0, width=10, height=10, reflecting_walls=False)
    va, vb = map(np.array, r["result"]["final_velocities"])
    assert r["result"]["ball_collisions"] == 1
    assert va @ vb == pytest.approx(0, abs=1e-12)          # 90° apart for elastic equal masses
    assert np.hypot(*va) ** 2 + np.hypot(*vb) ** 2 == pytest.approx(1)


def test_many_balls_conserve_energy_and_momentum_without_walls():
    rng = np.random.default_rng(1)
    balls = [{"mass": float(m), "radius": 0.05, "x": 0.2 + 0.3 * i, "y": 0.5 + 0.2 * (i % 2),
              "vx": float(vx), "vy": float(vy)}
             for i, (m, vx, vy) in enumerate(zip(rng.uniform(0.5, 2, 6), rng.normal(0, 1, 6), rng.normal(0, 1, 6)))]
    r = collisions_2d(balls, duration=3, reflecting_walls=False)
    ke = r["kinetic_energy"]
    assert max(ke) - min(ke) < 1e-9 * ke[0]
    assert np.ptp(r["momentum"]["px"]) < 1e-9 and np.ptp(r["momentum"]["py"]) < 1e-9


def test_inelastic_loses_energy_walls_keep_balls_inside():
    balls = [{"mass": 1, "radius": 0.1, "x": 0.3, "y": 0.3, "vx": 2, "vy": 1.3},
             {"mass": 1, "radius": 0.1, "x": 1.5, "y": 0.7, "vx": -1.5, "vy": 0.4}]
    r = collisions_2d(balls, duration=5, restitution=0.5)
    assert r["kinetic_energy"][-1] < r["kinetic_energy"][0]
    for xs, ys in zip(r["frames"]["x"], r["frames"]["y"]):
        assert min(xs) >= 0.1 - 1e-9 and max(xs) <= 1.9 + 1e-9
        assert min(ys) >= 0.1 - 1e-9 and max(ys) <= 0.9 + 1e-9


def test_collisions_validation():
    with pytest.raises(ValueError, match="overlap"):
        collisions_2d([{"mass": 1, "radius": 0.2, "x": 0.5, "y": 0.5}, {"mass": 1, "radius": 0.2, "x": 0.6, "y": 0.5}], 1)
    with pytest.raises(ValueError, match="inside"):
        collisions_2d([{"mass": 1, "radius": 0.2, "x": 0.1, "y": 0.5}], 1)
    with pytest.raises(ValueError):
        collision_1d(0, 1, 1, 1)
