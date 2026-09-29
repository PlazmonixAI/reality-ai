import base64
import math

import numpy as np
import pytest

from app.modules.mathematics.curves import conic_section, plane_curve
from app.modules.mathematics.fitting import least_squares_fit
from app.modules.mathematics.fractals import fractal, in_mandelbrot
from app.modules.mathematics.graphs import minimum_spanning_tree, shortest_path
from app.modules.mathematics.monte_carlo import monte_carlo


# --- plane curves -----------------------------------------------------------------------------

def test_circle_parametric():
    r = plane_curve("parametric", x_expression="3*cos(t)", y_expression="3*sin(t)")["result"]
    assert r["arc_length"] == pytest.approx(6 * math.pi)
    assert r["signed_area"] == pytest.approx(9 * math.pi) and r["closed"]


def test_cardioid_and_astroid():
    c = plane_curve("polar", r_expression="1 + cos(theta)")["result"]
    assert c["area"] == pytest.approx(3 * math.pi / 2) and c["arc_length"] == pytest.approx(8)
    a = plane_curve("parametric", x_expression="cos(t)**3", y_expression="sin(t)**3")["result"]
    assert a["arc_length"] == pytest.approx(6) and a["area"] == pytest.approx(3 * math.pi / 8)


def test_rose_and_cycloid_and_parameters():
    # 3-petal rose r = cos 3θ over [0, π] has area π/4
    assert plane_curve("polar", r_expression="cos(3*theta)", stop=math.pi)["result"]["area"] == pytest.approx(math.pi / 4)
    # One arch of a cycloid of radius R has length 8R
    cyc = plane_curve("parametric", x_expression="R*(t - sin(t))", y_expression="R*(1 - cos(t))", parameters={"R": 2})
    assert cyc["result"]["arc_length"] == pytest.approx(16) and not cyc["result"]["closed"]


def test_curve_validation():
    with pytest.raises(ValueError):
        plane_curve("parametric", x_expression="t")
    with pytest.raises(ValueError):
        plane_curve("polar", r_expression="k*theta")  # k not given
    with pytest.raises(ValueError):
        plane_curve("spiral", r_expression="theta")


# --- conic sections ----------------------------------------------------------------------------

def test_ellipse():
    r = conic_section(a=1 / 9, c=1 / 4, f=-1)["result"]
    assert r["type"] == "ellipse" and r["semi_major"] == pytest.approx(3) and r["semi_minor"] == pytest.approx(2)
    assert r["eccentricity"] == pytest.approx(math.sqrt(5) / 3)
    assert sorted(p[0] for p in r["foci"]) == pytest.approx([-math.sqrt(5), math.sqrt(5)])
    assert r["area"] == pytest.approx(6 * math.pi)


def test_shifted_rotated_ellipse_points_satisfy_equation():
    coef = dict(a=5, b=4, c=5, d=-14, e=-14, f=5)  # rotated 45°, centred at (1, 1)
    out = conic_section(**coef)
    r = out["result"]
    assert r["type"] == "ellipse" and r["center"] == pytest.approx([1, 1]) and r["angle_deg"] in (pytest.approx(45), pytest.approx(135))
    br = out["branches"][0]
    x, y = np.array(br["x"]), np.array(br["y"])
    assert np.max(np.abs(5 * x**2 + 4 * x * y + 5 * y**2 - 14 * x - 14 * y + 5)) < 1e-9


def test_hyperbola_parabola_circle():
    h = conic_section(b=1, f=-1)["result"]  # xy = 1
    assert h["type"] == "hyperbola" and h["eccentricity"] == pytest.approx(math.sqrt(2))
    assert h["semi_transverse"] == pytest.approx(math.sqrt(2)) and h["angle_deg"] == pytest.approx(45)
    p = conic_section(a=1, e=-1)["result"]  # y = x²: focus (0, 1/4)
    assert p["type"] == "parabola" and p["focus"] == pytest.approx([0, 0.25]) and p["vertex"] == pytest.approx([0, 0])
    q = conic_section(c=1, d=-8)["result"]  # y² = 8x: focus (2, 0), opens +x
    assert q["focus"] == pytest.approx([2, 0]) and q["angle_deg"] == pytest.approx(0)
    c = conic_section(a=1, c=1, d=-2, f=-3)["result"]  # (x − 1)² + y² = 4
    assert c["type"] == "circle" and c["semi_major"] == pytest.approx(2) and c["center"] == pytest.approx([1, 0])


def test_degenerate_conics():
    assert conic_section(a=1, c=-1)["result"]["type"] == "degenerate (two crossing lines)"
    assert conic_section(a=1, f=-1)["result"]["type"] == "degenerate (parallel lines)"
    assert conic_section(a=1, c=1, f=1)["result"]["type"] == "degenerate (no real points)"
    with pytest.raises(ValueError):
        conic_section(d=1, e=1)


# --- least squares ----------------------------------------------------------------------------

ANSCOMBE_X = [10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5]
ANSCOMBE_Y1 = [8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68]


def test_anscombe_linear():
    r = least_squares_fit(ANSCOMBE_X, ANSCOMBE_Y1)["result"]
    assert r["coefficients"]["a"] == pytest.approx(3.0001, abs=1e-3)
    assert r["coefficients"]["b"] == pytest.approx(0.5001, abs=1e-3)
    assert r["r_squared"] == pytest.approx(0.6665, abs=1e-3)
    assert r["standard_errors"]["b"] == pytest.approx(0.1179, abs=1e-3)


def test_exact_polynomial_and_exponential_recovery():
    x = np.linspace(-2, 3, 12)
    r = least_squares_fit(x.tolist(), (1 - 2 * x + 0.5 * x**3).tolist(), model="polynomial", degree=3)["result"]
    assert list(r["coefficients"].values()) == pytest.approx([1, -2, 0, 0.5], abs=1e-9)
    assert r["r_squared"] == pytest.approx(1)
    e = least_squares_fit(x.tolist(), (2.5 * np.exp(0.7 * x)).tolist(), model="exponential")["result"]
    assert e["coefficients"]["a"] == pytest.approx(2.5) and e["coefficients"]["b"] == pytest.approx(0.7)
    xp = np.linspace(1, 10, 10)
    p = least_squares_fit(xp.tolist(), (3 * xp**1.5).tolist(), model="power")["result"]
    assert p["coefficients"]["b"] == pytest.approx(1.5)
    lg = least_squares_fit(xp.tolist(), (1 + 2 * np.log(xp)).tolist(), model="logarithmic")["result"]
    assert lg["coefficients"]["b"] == pytest.approx(2)


def test_fit_validation():
    with pytest.raises(ValueError):
        least_squares_fit([1, 2], [1, 2, 3])
    with pytest.raises(ValueError):
        least_squares_fit([1, 1, 1], [1, 2, 3])
    with pytest.raises(ValueError):
        least_squares_fit([-1, 1, 2], [1, 2, 3], model="power")


# --- Monte Carlo -----------------------------------------------------------------------------

def test_monte_carlo_pi_within_error():
    r = monte_carlo("pi", 200_000, seed=7)["result"]
    assert abs(r["estimate"] - math.pi) < 4 * r["standard_error"]
    assert r["standard_error"] == pytest.approx(4 * math.sqrt(math.pi / 4 * (1 - math.pi / 4) / 200_000), rel=0.02)
    assert monte_carlo("pi", 1000, seed=3)["result"] == monte_carlo("pi", 1000, seed=3)["result"]  # reproducible


def test_monte_carlo_integral_and_convergence():
    r = monte_carlo("integral", 100_000, expression="x**2", a=0, b=1, seed=2)
    x = r["result"]
    assert x["exact"] == pytest.approx(1 / 3)
    assert abs(x["error"]) < 4 * x["standard_error"]
    # σ of x² on [0, 1] is √(1/5 − 1/9) = 0.298, so SE ≈ 0.298/√N
    assert x["standard_error"] == pytest.approx(math.sqrt(1 / 5 - 1 / 9) / math.sqrt(100_000), rel=0.02)
    g = monte_carlo("integral", 50_000, expression="sin(x)", a=0, b=math.pi, seed=4)["result"]
    assert abs(g["estimate"] - 2) < 4 * g["standard_error"]


def test_monte_carlo_validation():
    with pytest.raises(ValueError):
        monte_carlo("integral", 100)
    with pytest.raises(ValueError):
        monte_carlo("dice", 100)


# --- fractals --------------------------------------------------------------------------------

def test_mandelbrot_membership():
    assert in_mandelbrot(0) and in_mandelbrot(-1) and in_mandelbrot(-2) and in_mandelbrot(0.25)
    assert not in_mandelbrot(1) and not in_mandelbrot(0.26) and not in_mandelbrot(1j + 0.5)


def test_mandelbrot_area_and_encoding():
    out = fractal("mandelbrot", -0.75, 0, 2.6, 400, 400, 300)
    r = out["result"]
    assert r["area_inside"] == pytest.approx(1.5066, abs=0.03)  # true area ≈ 1.50659
    img = np.frombuffer(base64.b64decode(out["image"]["data"]), dtype="<u2").reshape(400, 400)
    assert np.mean(img == 65535) == pytest.approx(r["fraction_inside"])
    # The set is symmetric about the real axis
    assert np.mean((img == 65535) == (img[::-1] == 65535)) > 0.995


def test_julia_connectedness():
    assert fractal("julia", 0, 0, 3.2, 64, 64, 100, c_re=-1, c_im=0)["result"]["julia"]["connected"]
    dust = fractal("julia", 0, 0, 3.2, 64, 64, 100, c_re=0.4, c_im=0.4)["result"]
    assert not dust["julia"]["connected"]
    # c = 0: the Julia set is the unit circle, so the filled set is the unit disk (area π)
    disk = fractal("julia", 0, 0, 2.4, 300, 300, 200, c_re=0, c_im=0)["result"]
    assert disk["area_inside"] == pytest.approx(math.pi, rel=0.01)


# --- graphs ----------------------------------------------------------------------------------

CLRS_DIJKSTRA = [["s", "t", 10], ["s", "y", 5], ["t", "x", 1], ["t", "y", 2], ["y", "t", 3], ["y", "x", 9],
                 ["y", "z", 2], ["x", "z", 4], ["z", "x", 6], ["z", "s", 7]]


def test_dijkstra_clrs():
    r = shortest_path(CLRS_DIJKSTRA, "s", "x", directed=True)
    x = r["result"]
    assert x["algorithm"] == "dijkstra"
    assert x["distances"] == {"s": 0, "t": 8, "x": 9, "y": 5, "z": 7}
    assert x["path"] == ["s", "y", "t", "x"] and x["distance"] == 9
    assert [o["node"] for o in r["order"]] == ["s", "y", "z", "t", "x"]


def test_bellman_ford_clrs_and_negative_cycle():
    edges = [["s", "t", 6], ["s", "y", 7], ["t", "x", 5], ["t", "y", 8], ["t", "z", -4], ["x", "t", -2],
             ["y", "x", -3], ["y", "z", 9], ["z", "s", 2], ["z", "x", 7]]
    x = shortest_path(edges, "s", "z", directed=True)["result"]
    assert x["algorithm"] == "bellman-ford"
    assert x["distances"] == {"s": 0, "t": 2, "x": 4, "y": 7, "z": -2}
    assert x["path"] == ["s", "y", "x", "t", "z"]
    with pytest.raises(ValueError):
        shortest_path([["a", "b", 1], ["b", "a", -2]], "a", directed=True)


def test_unreachable_and_undirected():
    x = shortest_path([["a", "b", 1], ["c", "d", 1]], "a", "d")["result"]
    assert x["path"] is None and not x["reachable"] and x["distances"]["d"] is None
    u = shortest_path([["a", "b", 4], ["a", "c", 2], ["c", "b", 1], ["b", "d", 5]], "d", "a")["result"]
    assert u["distance"] == 8 and u["path"] == ["d", "b", "c", "a"]


def test_kruskal_mst():
    # CLRS MST example: total weight 37
    edges = [["a", "b", 4], ["a", "h", 8], ["b", "c", 8], ["b", "h", 11], ["c", "d", 7], ["c", "f", 4], ["c", "i", 2],
             ["d", "e", 9], ["d", "f", 14], ["e", "f", 10], ["f", "g", 2], ["g", "h", 1], ["g", "i", 6], ["h", "i", 7]]
    r = minimum_spanning_tree(edges)["result"]
    assert r["total_weight"] == 37 and len(r["edges"]) == 8 and r["spanning_tree"]
    f = minimum_spanning_tree([["a", "b", 1], ["c", "d", 2]])["result"]
    assert f["components"] == 2 and not f["spanning_tree"]
