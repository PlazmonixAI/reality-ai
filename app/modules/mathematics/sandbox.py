"""Maths sandbox: analyse a list of typed entries (like a graphing notebook) over a viewing window.

Each entry is one line a student types:
  y = x^2 - 2      x = 3        sin(x)/x        r = 1 + cos(theta)      (cos(3t), sin(2t))
  x^2 + y^2 = 9    y < 2x + 1   A = (1, 2)      a = 1.5 (a slider)      f(x) = x^3 - x     f(2) + 1
Every curve, region, root, turning point, intersection and value is computed here with numpy, scipy and sympy;
the browser only draws what comes back.
"""
from __future__ import annotations

import math
import re

import numpy as np
import sympy as sp
from scipy.optimize import brentq, minimize_scalar

from app.core.parsing import parse_expression
from app.core.registry import tool

X, Y, T, R, TH = sp.symbols("x y t r theta")
RESERVED = {"x", "y", "t", "r", "theta", "e", "E", "pi", "I"}
MAX_ENTRIES = 30
N_SAMPLES = 1200
GRID = 220           # implicit curves: grid cells along the longer side
REGION = 200         # inequality shading: cells along the longer side
_NAME = r"[A-Za-z][A-Za-z0-9_]*"
_DEF_FN = re.compile(rf"^\s*({_NAME})\s*\(\s*([a-z])\s*\)\s*=\s*(.+)$")
_DEF_PARAM = re.compile(rf"^\s*({_NAME})\s*=\s*(.+)$")
_INEQ = re.compile(r"(<=|>=|≤|≥|<|>)")


def _numeric(f, arg):
    with np.errstate(all="ignore"):
        v = np.asarray(f(arg), dtype=complex) * np.ones(np.shape(arg))
    ok = np.isfinite(v) & (np.abs(v.imag) <= 1e-9 * np.maximum(1.0, np.abs(v.real)))
    out = np.where(ok, v.real, np.nan)
    return out


def _lam(expr, *vars_):
    return sp.lambdify(vars_, expr, modules=["numpy", {"Heaviside": lambda z: np.heaviside(z, 0.5)}])


def _split_tuple(text: str) -> list[str] | None:
    s = text.strip()
    if not (s.startswith("(") and s.endswith(")")):
        return None
    depth, parts, cur = 0, [], ""
    for ch in s[1:-1]:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts if len(parts) == 2 and depth == 0 else None


def _rows(arr: np.ndarray, nd: int = 5) -> list:
    return [None if not np.isfinite(v) else round(float(v), nd) for v in arr]


class _Context:
    def __init__(self) -> None:
        self.params: dict[str, float] = {}
        self.funcs: dict[str, tuple[sp.Symbol, sp.Expr]] = {}

    def parse(self, text: str) -> sp.Expr:
        lams = {k: sp.Lambda(v, body) for k, (v, body) in self.funcs.items()}
        e = parse_expression(text, functions=lams)
        for f in e.atoms(sp.core.function.AppliedUndef):
            raise ValueError(f"unknown function {f.func.__name__}(); define it first, e.g. {f.func.__name__}(x) = x^2")
        e = e.subs({sp.Symbol(k): v for k, v in self.params.items()})
        return e.subs({sp.Symbol("e"): sp.E})


def _free(e: sp.Expr) -> set[str]:
    return {str(s) for s in e.free_symbols}


def _check(e: sp.Expr, allowed: set[str], what: str) -> None:
    bad = _free(e) - allowed
    if bad:
        raise ValueError(f"{what}: unknown {', '.join(sorted(bad))}; make a slider with e.g. {sorted(bad)[0]} = 1")


def _breaks(y: np.ndarray, span: float) -> np.ndarray:
    """Cut the line at jumps through an asymptote (tan x, 1/x) so they are not drawn as vertical strokes."""
    y = y.copy()
    dy = np.abs(np.diff(y))
    jump = np.flatnonzero(dy > 3 * span)
    for i in jump:
        y[i if abs(y[i]) > abs(y[i + 1]) else i + 1] = np.nan
    return y


def _explicit(e: sp.Expr, xs: np.ndarray, span: float, var=X) -> dict:
    f = _lam(e, var)
    y = _numeric(f, xs)
    ys = _breaks(y, span)
    # roots: sign changes of a continuous stretch, refined with Brent's method
    g = lambda v: float(np.real(complex(f(v))))  # noqa: E731
    roots, ext = [], []
    for i in range(len(xs) - 1):
        a, b = y[i], y[i + 1]
        if not (np.isfinite(a) and np.isfinite(b)):
            continue
        if a == 0:
            roots.append(float(xs[i]))
        elif a * b < 0 and abs(a - b) < 3 * span:
            try:
                roots.append(brentq(g, xs[i], xs[i + 1], xtol=1e-12))
            except (ValueError, ZeroDivisionError, TypeError):
                pass
    # turning points: where the slope changes sign, refined by a bounded 1-D search
    d = np.diff(y)
    for i in range(1, len(d)):
        a, b = d[i - 1], d[i]
        if not (np.isfinite(a) and np.isfinite(b)) or abs(a) >= span or abs(b) >= span:
            continue
        if (a > 0 >= b) or (a < 0 <= b):  # the slope changes sign (a flat step counts once)
            lo, hi = xs[i - 1], xs[min(i + 2, len(xs) - 1)]
            kind = "maximum" if a > 0 else "minimum"
            sgn = -1 if kind == "maximum" else 1
            try:
                r = minimize_scalar(lambda v: sgn * g(v), bounds=(lo, hi), method="bounded", options={"xatol": 1e-10})
                ext.append({"x": float(r.x), "y": g(r.x), "kind": kind})
            except (ValueError, ZeroDivisionError, TypeError):
                pass
    y0 = None
    if xs[0] <= 0 <= xs[-1]:
        try:
            v = complex(f(0.0))
            y0 = v.real if math.isfinite(v.real) and abs(v.imag) < 1e-9 else None
        except (ZeroDivisionError, ValueError, TypeError, OverflowError):
            y0 = None
    ext = _dedupe_pts(ext)
    wx = float(xs[-1] - xs[0])
    snap = lambda v, size: 0.0 if abs(v) < 1e-9 * size else v  # noqa: E731  (1e-10 is zero at this zoom)
    roots = [snap(r, wx) for r in roots]
    ext = [{"x": snap(p["x"], wx), "y": snap(p["y"], span), "kind": p["kind"]} for p in ext]
    pts = [{"x": r, "y": 0.0, "kind": "root"} for r in _dedupe(roots)][:25] + ext[:25]
    if y0 is not None:
        pts.append({"x": 0.0, "y": y0, "kind": "y-intercept"})
    return {"x": _rows(xs), "y": _rows(ys), "points": pts, "fn": f}


def _dedupe_pts(ps: list[dict]) -> list[dict]:
    out: list[dict] = []
    for p in sorted(ps, key=lambda q: q["x"]):
        if not out or abs(p["x"] - out[-1]["x"]) > 1e-6 * max(1.0, abs(p["x"])):
            out.append(p)
    return out


def _dedupe(vals: list[float], tol: float = 1e-7) -> list[float]:
    out: list[float] = []
    for v in sorted(vals):
        if not out or abs(v - out[-1]) > tol * max(1.0, abs(v)):
            out.append(v)
    return out


def _contour(F: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> list[list[float]]:
    """Marching squares on F(x, y) = 0: a list of segments [x1, y1, x2, y2]. Cells that straddle a pole are skipped."""
    segs = []
    finite = np.isfinite(F)
    scale = np.nanmedian(np.abs(F[finite])) if finite.any() else 1.0
    ny, nx = F.shape
    for j in range(ny - 1):
        for i in range(nx - 1):
            c = (F[j, i], F[j, i + 1], F[j + 1, i + 1], F[j + 1, i])
            if not all(np.isfinite(c)):
                continue
            s = [v > 0 for v in c]
            if all(s) or not any(s):
                continue
            if max(abs(v) for v in c) > 1e4 * max(scale, 1e-12):  # a pole, not a curve
                continue
            corners = ((xs[i], ys[j]), (xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1]))
            cross = []
            for k in range(4):
                a, b = c[k], c[(k + 1) % 4]
                if (a > 0) != (b > 0):
                    tt = a / (a - b)
                    (x1, y1), (x2, y2) = corners[k], corners[(k + 1) % 4]
                    cross.append((x1 + tt * (x2 - x1), y1 + tt * (y2 - y1)))
            if len(cross) == 2:
                segs.append([round(cross[0][0], 5), round(cross[0][1], 5), round(cross[1][0], 5), round(cross[1][1], 5)])
            elif len(cross) == 4:  # saddle: pair by the centre value
                centre = sum(c) / 4
                pairs = ((0, 1), (2, 3)) if (centre > 0) == s[0] else ((0, 3), (1, 2))
                for p, q in pairs:
                    segs.append([round(cross[p][0], 5), round(cross[p][1], 5), round(cross[q][0], 5), round(cross[q][1], 5)])
    return segs


def _grid(x_min, x_max, y_min, y_max, n):
    w, h = x_max - x_min, y_max - y_min
    nx, ny = (n, max(8, int(n * h / w))) if w >= h else (max(8, int(n * w / h)), n)
    return np.linspace(x_min, x_max, nx + 1), np.linspace(y_min, y_max, ny + 1)


@tool(
    domain="mathematics",
    name="sandbox",
    description=(
        "Maths sandbox (a graphing notebook): analyse a list of typed entries over a viewing window. Entries can be "
        "functions 'y = x^2 - 2' or just 'sin(x)', 'x = 3', implicit curves 'x^2 + y^2 = 9', inequalities 'y < 2x + 1', "
        "points 'A = (1, 2)', parametric curves '(cos(3t), sin(2t))', polar curves 'r = 1 + cos(theta)', sliders 'a = 1.5' "
        "(used by other entries), named functions 'f(x) = x^3 - x', and calculations 'f(2) + sqrt(2)'. Returns sampled "
        "curves, contour segments, shaded regions, roots, maxima, minima, y-intercepts and intersections."
    ),
)
def sandbox(entries: list[str], x_min: float = -10.0, x_max: float = 10.0, y_min: float = -7.0, y_max: float = 7.0,
            t_min: float = 0.0, t_max: float = 2 * math.pi) -> dict:
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        raise ValueError(f"entries must be a list of at most {MAX_ENTRIES} lines")
    if not (x_min < x_max and y_min < y_max):
        raise ValueError("the window needs x_min < x_max and y_min < y_max")
    if max(abs(x_min), abs(x_max), abs(y_min), abs(y_max)) > 1e9 or (x_max - x_min) < 1e-9 or (y_max - y_min) < 1e-9:
        raise ValueError("the window must be between 1e-9 and 1e9 wide")
    if not t_min < t_max or t_max - t_min > 2000:
        raise ValueError("t_min must be below t_max (range at most 2000)")
    ctx = _Context()
    span = y_max - y_min
    xs = np.linspace(x_min, x_max, N_SAMPLES)
    items: list[dict] = []

    # pass 1: sliders and named functions, in order (later lines may use earlier ones)
    kinds: list[str | None] = []
    for text in entries:
        s = (text or "").strip()
        kinds.append(None)
        if not s:
            continue
        m = _DEF_FN.match(s)
        if m and m.group(1) not in RESERVED and m.group(1) != "y":
            kinds[-1] = "function_def"
            continue
        m = _DEF_PARAM.match(s)
        if m and m.group(1) not in RESERVED and not _INEQ.search(s) and _split_tuple(m.group(2)) is None:
            kinds[-1] = "param"

    for idx, text in enumerate(entries):
        s = (text or "").strip()
        item: dict = {"index": idx, "text": s}
        try:
            if not s:
                item["kind"] = "empty"
            elif kinds[idx] == "function_def":
                name, var, body = _DEF_FN.match(s).groups()
                e = ctx.parse(body)
                _check(e, {var}, f"{name}({var})")
                ctx.funcs[name] = (sp.Symbol(var), e)
                item.update(kind="function", name=name, expression=str(e))
                if var == "x":
                    item.update(_strip(_explicit(e, xs, span)))
            elif kinds[idx] == "param":
                name, rhs = _DEF_PARAM.match(s).groups()
                e = ctx.parse(rhs)
                _check(e, set(), name)
                v = complex(sp.N(e))
                if abs(v.imag) > 1e-12 or not math.isfinite(v.real):
                    raise ValueError(f"{name} must be a real number")
                ctx.params[name] = v.real
                item.update(kind="slider", name=name, value=v.real)
            else:
                item.update(_entry(s, ctx, xs, span, x_min, x_max, y_min, y_max, t_min, t_max))
        except ValueError as err:
            item.update(kind="error", error=str(err))
        except (TypeError, ZeroDivisionError, OverflowError, AttributeError, sp.SympifyError, RecursionError) as err:
            item.update(kind="error", error=f"could not work this out: {err}")
        items.append(item)

    # intersections between pairs of plotted y = f(x) curves
    fns = [(it["index"], it.pop("_fn")) for it in items if "_fn" in it]
    for it in items:
        it.pop("_fn", None)
    crossings = []
    for a in range(len(fns)):
        for b in range(a + 1, min(len(fns), 8)):
            (ia, fa), (ib, fb) = fns[a], fns[b]
            da = _numeric(fa, xs) - _numeric(fb, xs)
            for i in range(len(xs) - 1):
                p, q = da[i], da[i + 1]
                if np.isfinite(p) and np.isfinite(q) and p * q < 0 and abs(p - q) < 3 * span:
                    try:
                        xr = brentq(lambda v: float(np.real(complex(fa(v)) - complex(fb(v)))), xs[i], xs[i + 1], xtol=1e-12)
                        crossings.append({"x": xr, "y": float(np.real(complex(fa(xr)))), "between": [ia, ib]})
                    except (ValueError, ZeroDivisionError, TypeError):
                        pass
                elif p == 0:
                    crossings.append({"x": float(xs[i]), "y": float(np.real(complex(fa(xs[i])))), "between": [ia, ib]})
    return {
        "result": {"items": items, "intersections": crossings[:60], "window": [x_min, x_max, y_min, y_max], "parameters": ctx.params},
        "units": "dimensionless (x and y are pure numbers)",
        "assumptions": [
            f"Curves y = f(x) sampled at {N_SAMPLES} points; roots refined with Brent's method, turning points with a bounded search",
            f"Implicit curves and regions found on a grid (~{GRID} and ~{REGION} cells across), so very thin features can be missed",
            "Jumps larger than three window heights are treated as asymptotes and left undrawn",
            "Only real values are drawn",
        ],
    }


def _strip(d: dict) -> dict:
    out = {k: v for k, v in d.items() if k != "fn"}
    out["_fn"] = d["fn"]
    out["kind"] = "curve"
    return out


def _entry(s, ctx, xs, span, x_min, x_max, y_min, y_max, t_min, t_max) -> dict:
    # A = (1, 2) or (1, 2) or (cos(t), sin(t))
    label = None
    m = re.match(rf"^\s*({_NAME})\s*=\s*(\(.*\))\s*$", s)
    if m and m.group(1) not in RESERVED:
        label, s = m.group(1), m.group(2)
    tup = _split_tuple(s)
    if tup is not None:
        ex, ey = ctx.parse(tup[0]), ctx.parse(tup[1])
        free = _free(ex) | _free(ey)
        if free <= {"t"} and free:
            ts = np.linspace(t_min, t_max, N_SAMPLES)
            px, py = _numeric(_lam(ex, T), ts), _numeric(_lam(ey, T), ts)
            return {"kind": "parametric", "label": label, "x": _rows(px), "y": _rows(py)}
        _check(ex, set(), "point x"), _check(ey, set(), "point y")
        return {"kind": "point", "label": label, "x": float(sp.N(ex)), "y": float(sp.N(ey))}
    # inequalities: shade the region and draw its boundary
    if _INEQ.search(s):
        parts = _INEQ.split(s)
        if len(parts) != 3:
            raise ValueError("write one inequality at a time, e.g. y < 2x + 1")
        lhs, op, rhs = parts
        g = ctx.parse(lhs) - ctx.parse(rhs)
        _check(g, {"x", "y"}, "inequality")
        gx, gy = _grid(x_min, x_max, y_min, y_max, REGION)
        cx, cy = (gx[:-1] + gx[1:]) / 2, (gy[:-1] + gy[1:]) / 2
        Xg, Yg = np.meshgrid(cx, cy)
        G = _grid_eval(g, Xg, Yg)
        inside = (G < 0) if op in ("<", "<=", "≤") else (G > 0)
        if op in ("<=", ">=", "≤", "≥"):
            inside |= np.isclose(G, 0)
        bx, by = _grid(x_min, x_max, y_min, y_max, GRID)
        Bx, By = np.meshgrid(bx, by)
        boundary = _contour(_grid_eval(g, Bx, By), bx, by)
        rows = ["".join("1" if v else "0" for v in row) for row in inside]
        return {"kind": "region", "cells": rows, "nx": len(cx), "ny": len(cy), "strict": op in ("<", ">"), "segments": boundary,
                "area_fraction": round(float(inside.mean()), 4)}
    if "=" in s:
        lhs, rhs = s.split("=", 1)
        L, Rr = lhs.strip(), rhs.strip()
        if L == "y":
            e = ctx.parse(Rr)
            if "y" not in _free(e):
                _check(e, {"x"}, "y =")
                return _strip(_explicit(e, xs, span))
        if L == "x":
            e = ctx.parse(Rr)
            if "x" not in _free(e):
                _check(e, {"y"}, "x =")
                ys = np.linspace(y_min, y_max, N_SAMPLES)
                px = _numeric(_lam(e, Y), ys)
                return {"kind": "curve_y", "x": _rows(_breaks(px, x_max - x_min)), "y": _rows(ys)}
        if L == "r":
            e = ctx.parse(Rr).subs(T, TH)
            _check(e, {"theta"}, "r =")
            th = np.linspace(t_min, t_max, N_SAMPLES * 2)
            rr = _numeric(_lam(e, TH), th)
            return {"kind": "parametric", "polar": True, "x": _rows(rr * np.cos(th)), "y": _rows(rr * np.sin(th))}
        g = ctx.parse(L) - ctx.parse(Rr)
        _check(g, {"x", "y"}, "equation")
        bx, by = _grid(x_min, x_max, y_min, y_max, GRID)
        Bx, By = np.meshgrid(bx, by)
        return {"kind": "implicit", "segments": _contour(_grid_eval(g, Bx, By), bx, by)}
    e = ctx.parse(s)
    free = _free(e)
    if not free:
        v = complex(sp.N(e, 15))
        exact = sp.nsimplify(e) if e.is_number else e
        return {"kind": "value", "value": v.real if abs(v.imag) < 1e-12 else None,
                "imag": v.imag if abs(v.imag) >= 1e-12 else 0.0, "exact": str(sp.simplify(exact))[:200]}
    if free <= {"x"}:
        return _strip(_explicit(e, xs, span))
    _check(e, {"x"}, "expression")
    return {}


def _grid_eval(g: sp.Expr, Xg: np.ndarray, Yg: np.ndarray) -> np.ndarray:
    f = _lam(g, X, Y)
    with np.errstate(all="ignore"):
        v = np.asarray(f(Xg.astype(complex), Yg.astype(complex)), dtype=complex) * np.ones_like(Xg)
    ok = np.isfinite(v) & (np.abs(v.imag) <= 1e-9 * np.maximum(1.0, np.abs(v.real)))
    return np.where(ok, v.real, np.nan)
