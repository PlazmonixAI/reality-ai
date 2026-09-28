"""Plane curves: parametric and polar curves (arc length, enclosed area) and conic sections from the
general quadratic Ax² + Bxy + Cy² + Dx + Ey + F = 0."""
import math

import numpy as np
import sympy as sp
from scipy.integrate import quad

from app.core.parsing import parse_expression, symbol
from app.core.registry import tool

MAX_POINTS = 10_000


def _compile(text: str, var: sp.Symbol, parameters: dict | None):
    expr = parse_expression(text).subs({symbol(k): float(v) for k, v in (parameters or {}).items()})
    extra = expr.free_symbols - {var}
    if extra:
        raise ValueError(f"Unknown symbols {sorted(map(str, extra))}; give them in parameters")
    f = sp.lambdify(var, expr, modules="numpy")
    df = sp.lambdify(var, sp.diff(expr, var), modules="numpy")
    return (lambda t: np.asarray(f(t), float) * np.ones_like(t)), (lambda t: np.asarray(df(t), float) * np.ones_like(t))


@tool(
    domain="mathematics",
    name="plane_curve",
    description=(
        "Parametric curve (x(t), y(t)) or polar curve r(θ): sampled points, exact-derivative arc length and "
        "enclosed (signed) area. kind='parametric' uses x_expression, y_expression in variable t; kind='polar' "
        "uses r_expression in variable theta. Example: kind='polar', r_expression='1 + cos(theta)', "
        "start=0, stop=2*pi -> area 3π/2, length 8."
    ),
)
def plane_curve(
    kind: str = "parametric",
    x_expression: str | None = None,
    y_expression: str | None = None,
    r_expression: str | None = None,
    start: float = 0.0,
    stop: float = 2 * math.pi,
    n_points: int = 800,
    parameters: dict[str, float] | None = None,
) -> dict:
    if not start < stop:
        raise ValueError("start must be less than stop")
    if not 2 <= n_points <= MAX_POINTS:
        raise ValueError(f"n_points must be between 2 and {MAX_POINTS}")
    if kind == "parametric":
        if not x_expression or not y_expression:
            raise ValueError("parametric curves need x_expression and y_expression (in t)")
        t = symbol("t")
        fx, dfx = _compile(x_expression, t, parameters)
        fy, dfy = _compile(y_expression, t, parameters)
        speed = lambda s: math.hypot(float(dfx(np.array(s))), float(dfy(np.array(s))))  # noqa: E731
        area_integrand = lambda s: 0.5 * (float(fx(np.array(s))) * float(dfy(np.array(s))) - float(fy(np.array(s))) * float(dfx(np.array(s))))  # noqa: E731
    elif kind == "polar":
        if not r_expression:
            raise ValueError("polar curves need r_expression (in theta)")
        th = symbol("theta")
        fr, dfr = _compile(r_expression, th, parameters)
        fx = lambda s: fr(s) * np.cos(s)  # noqa: E731
        fy = lambda s: fr(s) * np.sin(s)  # noqa: E731
        speed = lambda s: math.hypot(float(fr(np.array(s))), float(dfr(np.array(s))))  # noqa: E731
        area_integrand = lambda s: 0.5 * float(fr(np.array(s))) ** 2  # noqa: E731
    else:
        raise ValueError("kind must be 'parametric' or 'polar'")
    s = np.linspace(start, stop, n_points)
    with np.errstate(all="ignore"):
        x, y = fx(s), fy(s)
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise ValueError("the curve is undefined somewhere on [start, stop]")
    # Adaptive quadrature with breakpoints so oscillating integrands stay accurate
    pts = np.linspace(start, stop, 65)[1:-1]
    length = quad(speed, start, stop, points=pts, limit=400)[0]
    area = quad(area_integrand, start, stop, points=pts, limit=400)[0]
    closed = math.hypot(x[-1] - x[0], y[-1] - y[0]) <= 1e-9 * max(1.0, float(np.max(np.hypot(x, y))))
    return {
        "result": {
            "arc_length": length,
            "signed_area": area,
            "area": abs(area),
            "closed": bool(closed),
            "bounds": {"x": [float(x.min()), float(x.max())], "y": [float(y.min()), float(y.max())]},
        },
        "curve": {"s": s.tolist(), "x": x.tolist(), "y": y.tolist()},
        "units": "same length units as x and y (area in those units squared); parameter in radians for polar",
        "assumptions": [
            "Arc length ∫√(x'² + y'²) dt (or √(r² + r'²) dθ) with exact symbolic derivatives",
            "Area by Green's theorem ½∮(x dy − y dx) (or ½∫r² dθ); meaningful for closed, non-self-intersecting curves",
        ],
    }


@tool(
    domain="mathematics",
    name="conic_section",
    description=(
        "Classify and analyse the conic Ax² + Bxy + Cy² + Dx + Ey + F = 0: type (ellipse, circle, parabola, "
        "hyperbola or degenerate), centre/vertex, rotation angle, semi-axes, eccentricity, foci, asymptotes and "
        "plot-ready branches. Example: a=1/9, c=1/4, f=-1 (x²/9 + y²/4 = 1)."
    ),
)
def conic_section(a: float = 0.0, b: float = 0.0, c: float = 0.0, d: float = 0.0, e: float = 0.0, f: float = 0.0,
                  n_points: int = 400, extent: float = 10.0) -> dict:
    if a == b == c == 0:
        raise ValueError("A, B and C cannot all be zero (that is a line, not a conic)")
    if not 10 <= n_points <= MAX_POINTS or extent <= 0:
        raise ValueError("n_points must be 10..10000 and extent positive")
    m = np.array([[a, b / 2], [b / 2, c]], float)
    disc = b * b - 4 * a * c
    scale = max(abs(a), abs(b), abs(c))
    lam, vec = np.linalg.eigh(m)
    out: dict = {"discriminant": disc}
    branches: list[dict] = []
    tol = 1e-12 * scale**2
    if abs(disc) > tol:  # central conic
        ctr = np.linalg.solve(2 * m, [-d, -e])
        fp = f + (d * ctr[0] + e * ctr[1]) / 2
        out["center"] = ctr.tolist()
        rhs = -fp  # λ1 u² + λ2 v² = rhs
        if disc < 0:
            if abs(rhs) <= 1e-12 * max(1.0, abs(f)) or rhs / lam[0] < 0:
                out["type"] = "degenerate (single point)" if abs(rhs) <= 1e-12 * max(1.0, abs(f)) else "degenerate (no real points)"
            else:
                ax = np.sqrt(rhs / lam)  # semi-axes along each eigenvector
                i_major = int(np.argmax(ax))
                big, small = float(ax[i_major]), float(ax[1 - i_major])
                u = vec[:, i_major]
                ecc = math.sqrt(max(0.0, 1 - (small / big) ** 2))
                fc = big * ecc
                circle = abs(big - small) <= 1e-9 * big
                out |= {
                    "type": "circle" if circle else "ellipse",
                    "semi_major": big, "semi_minor": small, "eccentricity": 0.0 if circle else ecc,
                    "angle_deg": 0.0 if circle else math.degrees(math.atan2(u[1], u[0])) % 180,
                    "foci": [(ctr + fc * u).tolist(), (ctr - fc * u).tolist()],
                    "vertices": [(ctr + big * u).tolist(), (ctr - big * u).tolist()],
                    "area": math.pi * big * small,
                }
                th = np.linspace(0, 2 * math.pi, n_points)
                v2 = vec[:, 1 - i_major]
                pts = ctr[:, None] + big * np.outer(u, np.cos(th)) + small * np.outer(v2, np.sin(th))
                branches.append({"x": pts[0].tolist(), "y": pts[1].tolist()})
        else:
            if abs(rhs) <= 1e-12 * max(1.0, abs(f)):
                out["type"] = "degenerate (two crossing lines)"
                for i, sgn in ((0, 1), (0, -1)):
                    # λ1 u² + λ2 v² = 0 → v = ±√(−λ1/λ2) u
                    k = math.sqrt(-lam[0] / lam[1])
                    dirv = vec[:, 0] + sgn * k * vec[:, 1]
                    tt = np.linspace(-extent, extent, 2)
                    branches.append({"x": (ctr[0] + tt * dirv[0]).tolist(), "y": (ctr[1] + tt * dirv[1]).tolist()})
            else:
                i_t = 0 if rhs / lam[0] > 0 else 1  # transverse axis: the eigen-direction with a real intercept
                at = math.sqrt(rhs / lam[i_t])
                bc = math.sqrt(-rhs / lam[1 - i_t])
                u, v2 = vec[:, i_t], vec[:, 1 - i_t]
                ecc = math.sqrt(1 + (bc / at) ** 2)
                fc = at * ecc
                slopes_local = bc / at
                asym = []
                for sgn in (1, -1):
                    dirv = u + sgn * slopes_local * v2
                    asym.append({"point": ctr.tolist(), "direction": (dirv / np.linalg.norm(dirv)).tolist()})
                out |= {
                    "type": "hyperbola",
                    "semi_transverse": at, "semi_conjugate": bc, "eccentricity": ecc,
                    "angle_deg": math.degrees(math.atan2(u[1], u[0])) % 180,
                    "foci": [(ctr + fc * u).tolist(), (ctr - fc * u).tolist()],
                    "vertices": [(ctr + at * u).tolist(), (ctr - at * u).tolist()],
                    "asymptotes": asym,
                }
                tmax = math.acosh(max(2.0, extent / at + 1))
                tt = np.linspace(-tmax, tmax, n_points // 2)
                for sgn in (1, -1):
                    pts = ctr[:, None] + sgn * at * np.outer(u, np.cosh(tt)) + bc * np.outer(v2, np.sinh(tt))
                    branches.append({"x": pts[0].tolist(), "y": pts[1].tolist()})
    else:  # parabolic family: one eigenvalue is zero
        i0 = int(np.argmin(np.abs(lam)))
        e1, e2, lm = vec[:, i0], vec[:, 1 - i0], lam[1 - i0]
        g1, g2 = d * e1[0] + e * e1[1], d * e2[0] + e * e2[1]
        if abs(g1) <= 1e-12 * max(1.0, abs(d) + abs(e)):
            # λ q² + g2 q + F = 0: two parallel lines, one line or nothing
            disc_q = g2 * g2 - 4 * lm * f
            out["type"] = "degenerate (parallel lines)" if disc_q > 0 else "degenerate (one line)" if disc_q == 0 else "degenerate (no real points)"
            if disc_q >= 0:
                for q in {(-g2 + sgn * math.sqrt(disc_q)) / (2 * lm) for sgn in (1, -1)}:
                    tt = np.linspace(-extent, extent, 2)
                    branches.append({"x": (q * e2[0] + tt * e1[0]).tolist(), "y": (q * e2[1] + tt * e1[1]).tolist()})
        else:
            # p = −(λ q² + g2 q + F)/g1 → p − p0 = k (q − q0)²
            q0 = -g2 / (2 * lm)
            p0 = -(lm * q0**2 + g2 * q0 + f) / g1
            k = -lm / g1
            focal = float(1 / (4 * abs(k)))
            vertex = p0 * e1 + q0 * e2
            axis = e1 * math.copysign(1, k)  # opening direction
            out |= {
                "type": "parabola", "eccentricity": 1.0,
                "vertex": vertex.tolist(),
                "focus": (vertex + focal * axis).tolist(),
                "focal_length": focal,
                "directrix": {"point": (vertex - focal * axis).tolist(), "direction": e2.tolist()},
                "angle_deg": math.degrees(math.atan2(axis[1], axis[0])) % 360,
            }
            half = math.sqrt(extent / abs(k)) if k else extent
            qs = np.linspace(q0 - half, q0 + half, n_points)
            ps = p0 + k * (qs - q0) ** 2
            branches.append({"x": (ps * e1[0] + qs * e2[0]).tolist(), "y": (ps * e1[1] + qs * e2[1]).tolist()})
    return {
        "result": out,
        "branches": branches,
        "units": "same length units as x and y; angles in degrees",
        "assumptions": ["Classification by the discriminant B² − 4AC and the eigen-decomposition of the quadratic form"],
    }
