"""ASM Teach Equation Lab: build whatever equation the teacher writes, from the mathematics itself.

Nothing here is looked up. The equation is parsed and then worked on symbolically and numerically:

* an identity (sin²x + cos²x = 1) is proved by a chain of algebraic rewrites and checked at random points;
* a statement that can never hold (sin²x + cos²x = 2, 2 + 2 = 5) is caught, with the reason;
* an equation in one unknown is solved exactly over the reals (general solutions for trigonometric equations),
  or the engine explains why no real solution exists (sin x = 2 lies outside the range of sin);
* y = f(x) gets its graph, derivative, zeros, turning points, period and domain;
* a relation in x and y is drawn as an implicit curve (and named when it is a conic); z = f(x, y) as contour lines;
* a physics formula (T = 2π√(L/g), PV = nRT) is checked for dimensional consistency and becomes a live formula
  with a slider for every input; an equation whose two sides have different dimensions is reported as wrong;
* a chemical equation (H2 + O2 -> H2O) is balanced by conservation of atoms and charge, or reported as impossible.
"""
from __future__ import annotations

import itertools
import math
import re
from fractions import Fraction
from typing import Any

import numpy as np
import sympy as sp

from app.core.registry import tool
from app.modules.teach.core import parse, pretty, split_teacher_text, sym_name

# ---------------------------------------------------------------- text helpers
_TRIG = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc)


def _txt(e: sp.Basic) -> str:
    if isinstance(e, sp.Interval):
        lo = "−∞" if e.start == -sp.oo else _txt(e.start)
        hi = "∞" if e.end == sp.oo else _txt(e.end)
        return f"{'(' if e.left_open else '['}{lo}, {hi}{')' if e.right_open else ']'}"
    if isinstance(e, sp.Union):
        return " ∪ ".join(_txt(a) for a in e.args)
    if isinstance(e, sp.FiniteSet):
        return "{" + ", ".join(_txt(a) for a in e.args) + "}"
    s = sp.sstr(e)
    s = re.sub(r"\bE\b", "e", s)  # Euler's number; the symbol E (energy) is E_rsv until the next line
    s = re.sub(r"\b([A-Za-z]+)_rsv\b", r"\1", s)
    return pretty(s)


def _num(v: float) -> float:
    return float(f"{v:.6g}")


_FN = r"(sin|cos|tan|cot|sec|csc|log|ln|exp|sinh|cosh|tanh)"


def board_functions(text: str) -> str:
    """How functions are written on a board: 'sin x', 'sinx', 'sin 2x', 'sin²x', 'sin^2 x' -> sin(x), sin(2x), sin(x)**2."""
    t = text.replace("θ", " theta ")
    t = re.sub(r"\b" + _FN + r"\s*(?:\^\s*(\d)|([²³]))\s*\(?\s*(\d*\.?\d*\s*[A-Za-z]\w*|\d+)\s*\)?",
               lambda m: f"{m.group(1)}({m.group(4)})^{m.group(2) or {'²': '2', '³': '3'}[m.group(3)]}", t)
    t = re.sub(r"\b(sin|cos|tan|cot|sec|csc)(\d*[a-z])\b(?<!sinh)(?<!cosh)(?<!tanh)", lambda m: f"{m.group(1)}({m.group(2)})"
               if m.group(2) != "h" else m.group(0), t)
    t = re.sub(r"\b" + _FN + r"\s+(\d*\.?\d*\s*[A-Za-z]\w*|\d+(?:\.\d+)?)", lambda m: f"{m.group(1)}({m.group(2)})", t)
    return t


def _sides(text: str) -> tuple[sp.Expr, sp.Expr | None]:
    """Parse 'lhs = rhs' (or a bare expression) with the board shorthand, falling back to the plain text."""
    text = board_functions(text)
    errors = []
    for candidate in (split_teacher_text(text), text.replace("^", "**")):
        try:
            if "=" in candidate:
                lhs, rhs = candidate.split("=", 1)
                if "=" in rhs:
                    raise ValueError("Write one equation at a time (only one '=')")
                return parse(lhs), parse(rhs)
            return parse(candidate), None
        except (ValueError, TypeError, SyntaxError) as e:
            errors.append(str(e))
    raise ValueError(f"The board could not read this as mathematics. Check the brackets and operators. ({errors[-1]})")


# ---------------------------------------------------------------- chemistry
_SPECIES = re.compile(r"^\d*\s*(?:[A-Z][a-z]?\d*|[(\[][A-Za-z0-9]+[)\]]\d*)+(?:\^?\d*[+-])?(?:\((?:s|l|g|aq)\))?$")


def _looks_chemical(text: str) -> bool:
    t = text.strip()
    if re.search(r"->|→|⟶|⇌|<=>|=>", t):
        return True
    if "=" not in t or "+" not in t:
        return False
    terms = [x.strip() for x in re.split(r"\s*=\s*|\s+\+\s+", t) if x.strip()]
    return all(_SPECIES.match(x) for x in terms) and any(re.search(r"\d|[A-Z][a-z]?[A-Z]", x) for x in terms)


def _chemistry(text: str) -> dict[str, Any]:
    from app.modules.chemistry.formula import element_counts, molar_mass_of, parse_equation
    from app.modules.chemistry.stoichiometry import balance_equation

    t = re.sub(r"\s*(→|⟶)\s*", " -> ", text.strip())
    t = re.sub(r"\s*\+\s*", " + ", t)
    eq = parse_equation(t)
    left = {el for _, s in eq.reactants for el in element_counts(s.formula)}
    right = {el for _, s in eq.products for el in element_counts(s.formula)}
    species = [s for _, s in eq.reactants + eq.products]
    masses = [{"species": s.text, "molar_mass_g_mol": _num(molar_mass_of(s.text))} for s in species]
    if left != right:
        only_l, only_r = sorted(left - right), sorted(right - left)
        why = []
        if only_l:
            why.append(f"{', '.join(only_l)} appear{'s' if len(only_l) == 1 else ''} only on the left")
        if only_r:
            why.append(f"{', '.join(only_r)} appear{'s' if len(only_r) == 1 else ''} only on the right")
        return {"kind": "chemical", "valid": False, "verdict": "This reaction cannot happen as written: atoms are never "
                "created or destroyed, but " + " and ".join(why) + ".", "steps": [f"Elements on the left: {', '.join(sorted(left))}",
                f"Elements on the right: {', '.join(sorted(right))}"], "species": masses}
    try:
        b = balance_equation(t)
    except ValueError as e:
        return {"kind": "chemical", "valid": False, "verdict": f"These formulas cannot be balanced: {e}.",
                "steps": [], "species": masses}
    coeffs = b["coefficients"]
    steps = [f"Elements: {', '.join(sorted(left))}",
             "For each element, atoms on the left = atoms on the right; one equation per element",
             "Solve for the smallest whole-number coefficients",
             "Coefficients: " + ", ".join(f"{k} {v}" for k, v in coeffs.items())]
    return {"kind": "chemical", "valid": True, "verdict": "Balanced by conservation of atoms" + (" and charge." if any(s.charge for s in species) else "."),
            "balanced": b["result"], "coefficients": coeffs, "steps": steps, "species": masses}


# ---------------------------------------------------------------- dimensions (M, L, T, I, Θ, N)
_BASE = ("M", "L", "T", "I", "Θ", "N")


def _d(**k: float) -> tuple[Fraction, ...]:
    return tuple(Fraction(k.get(b, 0)) for b in ("M", "L", "T", "I", "K", "N"))


NONE = _d()
LEN, TIME, MASS = _d(L=1), _d(T=1), _d(M=1)
VEL, ACC = _d(L=1, T=-1), _d(L=1, T=-2)
FORCE, ENERGY, POWER = _d(M=1, L=1, T=-2), _d(M=1, L=2, T=-2), _d(M=1, L=2, T=-3)
PRESSURE, MOMENTUM = _d(M=1, L=-1, T=-2), _d(M=1, L=1, T=-1)
CHARGE, CURRENT, VOLT = _d(I=1, T=1), _d(I=1), _d(M=1, L=2, T=-3, I=-1)
OHM, FARAD, TESLA = _d(M=1, L=2, T=-3, I=-2), _d(M=-1, L=-2, T=4, I=2), _d(M=1, T=-2, I=-1)
TEMP, AMOUNT, FREQ = _d(K=1), _d(N=1), _d(T=-1)
R_GAS, ENTROPY = _d(M=1, L=2, T=-2, K=-1, N=-1), _d(M=1, L=2, T=-2, K=-1)
EFIELD = _d(M=1, L=1, T=-3, I=-1)

# What a symbol can mean in a school formula, most likely first; ambiguous letters get every reading.
MEANINGS: dict[str, list[tuple[str, tuple]]] = {
    "m": [("mass", MASS)], "M": [("mass", MASS)], "L": [("length", LEN)], "l": [("length", LEN)], "s": [("distance", LEN)],
    "d": [("distance", LEN)], "h": [("height", LEN), ("Planck's constant", _d(M=1, L=2, T=-1))], "r": [("radius", LEN)],
    "x": [("position", LEN)], "y": [("position", LEN)], "z": [("position", LEN)], "R": [("radius", LEN), ("resistance", OHM), ("gas constant", R_GAS)],
    "lam": [("wavelength", LEN)], "lambda": [("wavelength", LEN)], "A": [("area", _d(L=2)), ("amplitude", LEN)],
    "t": [("time", TIME)], "T": [("time period", TIME), ("temperature", TEMP), ("tension", FORCE)],
    "v": [("velocity", VEL)], "u": [("initial velocity", VEL)], "c": [("speed of light", VEL)],
    "a": [("acceleration", ACC)], "g": [("gravity", ACC)], "F": [("force", FORCE)], "W": [("work", ENERGY), ("weight", FORCE)],
    "E": [("energy", ENERGY), ("electric field", EFIELD)], "K": [("kinetic energy", ENERGY)], "U": [("potential energy", ENERGY)],
    "H": [("enthalpy", ENERGY)], "G": [("gravitational constant", _d(M=-1, L=3, T=-2)), ("Gibbs energy", ENERGY)],
    "Q": [("charge", CHARGE), ("heat", ENERGY)], "q": [("charge", CHARGE)], "P": [("pressure", PRESSURE), ("power", POWER)],
    "p": [("momentum", MOMENTUM), ("pressure", PRESSURE)], "V": [("volume", _d(L=3)), ("voltage", VOLT)],
    "I": [("current", CURRENT), ("moment of inertia", _d(M=1, L=2))], "n": [("amount of substance", AMOUNT), ("number", NONE)],
    "k": [("spring constant", _d(M=1, T=-2)), ("Boltzmann constant", ENTROPY), ("wave number", _d(L=-1))],
    "f": [("frequency", FREQ)], "nu": [("frequency", FREQ)], "omega": [("angular frequency", FREQ)], "w": [("angular frequency", FREQ)],
    "theta": [("angle", NONE)], "th": [("angle", NONE)], "phi": [("angle", NONE)], "alpha": [("angle", NONE), ("angular acceleration", _d(T=-2))],
    "rho": [("density", _d(M=1, L=-3)), ("resistivity", _d(M=1, L=3, T=-3, I=-2))], "C": [("capacitance", FARAD)],
    "B": [("magnetic field", TESLA)], "mu": [("coefficient of friction", NONE)], "tau": [("torque", ENERGY), ("time constant", TIME)],
    "N": [("normal force", FORCE), ("number", NONE)], "S": [("entropy", ENTROPY)], "e": [("electron charge", CHARGE)],
    "J": [("impulse", MOMENTUM)], "Z": [("atomic number", NONE)], "eta": [("efficiency", NONE)], "mu0": [("permeability", _d(M=1, L=1, T=-2, I=-2))],
}
MATH_DEFAULTS: dict[str, float] = {"a": 1, "b": -3, "c": 2, "k": 1, "m": 1, "n": 2, "p": 1, "q": 1, "r": 2, "h": 0}
DEFAULTS: dict[str, tuple[float, float, float]] = {  # value, min, max for the formula sliders
    "g": (9.81, 1, 25), "L": (1, 0.1, 10), "l": (1, 0.1, 10), "m": (1, 0.1, 10), "M": (1, 0.1, 10), "v": (10, 0, 50), "u": (0, 0, 50),
    "a": (2, -10, 10), "t": (2, 0, 20), "T": (300, 1, 1000), "h": (10, 0, 100), "r": (1, 0.1, 10), "R": (8.314, 0.1, 100),
    "n": (1, 0.1, 10), "V": (1, 0.01, 10), "P": (101325, 1000, 300000), "F": (10, 0, 100), "k": (100, 1, 1000), "theta": (30, 0, 90),
    "th": (30, 0, 90), "c": (299792458, 1e8, 3e8), "f": (50, 1, 1000), "q": (1e-6, 1e-9, 1e-3), "Q": (1e-6, 1e-9, 1e-3),
    "I": (1, 0, 10), "s": (10, 0, 100), "d": (10, 0, 100), "x": (1, -10, 10), "omega": (2, 0, 20), "lam": (500e-9, 100e-9, 1000e-9),
}


_RARE = {"tension", "number", "Planck's constant", "Gibbs energy", "weight", "wave number", "time constant"}


def _fmt_dim(d: tuple) -> str:
    parts = []
    for b, p in zip(_BASE, d):
        if p == 0:
            continue
        parts.append(b if p == 1 else f"{b}{str(p).translate(str.maketrans('-0123456789/', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹ᐟ'))}")
    return "[" + " ".join(parts) + "]" if parts else "[dimensionless]"


class _Mismatch(Exception):
    pass


def _dim(e: sp.Basic, env: dict[str, tuple]) -> tuple:
    if e.is_Number or e in (sp.pi, sp.E):
        return NONE
    if e.is_Symbol:
        return env[sym_name(e)]
    if e.is_Add:
        ds = [_dim(a, env) for a in e.args]
        if any(d != ds[0] for d in ds):
            raise _Mismatch("terms added together have different dimensions: " + ", ".join(_fmt_dim(d) for d in ds))
        return ds[0]
    if e.is_Mul:
        out = NONE
        for a in e.args:
            out = tuple(x + y for x, y in zip(out, _dim(a, env)))
        return out
    if e.is_Pow:
        b, p = e.args
        if p.is_Rational:
            return tuple(x * Fraction(int(p.p), int(p.q)) for x in _dim(b, env))
        if _dim(b, env) != NONE or _dim(p, env) != NONE:
            raise _Mismatch("a power with a variable exponent needs dimensionless base and exponent")
        return NONE
    if isinstance(e, sp.Abs):
        return _dim(e.args[0], env)
    if isinstance(e, sp.Function):
        for a in e.args:
            if _dim(a, env) != NONE:
                raise _Mismatch(f"{type(e).__name__}() needs a dimensionless argument, got {_fmt_dim(_dim(a, env))}")
        return NONE
    raise _Mismatch(f"cannot read the dimensions of {e}")


def _dimension_check(lhs: sp.Expr, rhs: sp.Expr) -> dict[str, Any] | None:
    names = sorted({sym_name(s) for s in (lhs - rhs).free_symbols})
    if not names or any(n not in MEANINGS for n in names):
        return None
    options = [list(enumerate(MEANINGS[n])) for n in names]
    first_error, best = None, None
    for combo in itertools.product(*options):
        env = {n: d for n, (_, (_, d)) in zip(names, combo)}
        try:
            dl, dr = _dim(lhs, env), _dim(rhs, env)
        except _Mismatch as e:
            first_error = first_error or str(e)
            continue
        if dl == dr:  # several readings can fit; keep the most usual one (first-listed meanings, rare ones penalised)
            cost = sum(i + (2 if meaning in _RARE else 0) for i, (meaning, _) in combo)
            if best is None or cost < best[0]:
                best = (cost, dl, {n: meaning for n, (_, (meaning, _)) in zip(names, combo)})
            continue
        first_error = first_error or f"the left side is {_fmt_dim(dl)} but the right side is {_fmt_dim(dr)}"
    if best is not None:
        return {"consistent": True, "dimension": _fmt_dim(best[1]), "reading": best[2]}
    return {"consistent": False, "reason": first_error,
            "reading": {n: MEANINGS[n][0][0] for n in names}}


# ---------------------------------------------------------------- numerics
def _f(expr: sp.Expr, var: sp.Symbol):
    fn = sp.lambdify(var, expr, modules=["numpy"])

    def g(x):
        with np.errstate(all="ignore"):
            y = np.asarray(fn(x), dtype=complex) * np.ones_like(x)
        real = np.where(np.abs(y.imag) < 1e-9 * (1 + np.abs(y.real)), y.real, np.nan)
        return real
    return g


def _range_for(expr: sp.Expr) -> tuple[float, float]:
    return (-2 * math.pi, 2 * math.pi) if expr.has(*_TRIG) else (-10.0, 10.0)


def _clean(y: np.ndarray) -> list[float | None]:
    finite = y[np.isfinite(y)]
    if finite.size == 0:
        return [None] * len(y)
    lo, hi = np.percentile(finite, [2, 98])
    span = max(hi - lo, 1e-9)
    lo, hi = lo - 0.6 * span, hi + 0.6 * span
    out = np.where((y < lo) | (y > hi), np.nan, y)
    jumps = np.abs(np.diff(out)) > 0.5 * (hi - lo)  # break the line at asymptotes (tan x, 1/x)
    out[1:][jumps] = np.nan
    return [None if not np.isfinite(v) else _num(v) for v in out]


def _roots(g, a: float, b: float, n: int = 2000) -> list[float]:
    xs = np.linspace(a, b, n)
    ys = g(xs)
    found = []
    for i in range(n - 1):
        y0, y1 = ys[i], ys[i + 1]
        if not (np.isfinite(y0) and np.isfinite(y1)):
            continue
        if y0 == 0:
            found.append(xs[i])
        elif y0 * y1 < 0 and abs(y0) + abs(y1) < 1e6:
            lo, hi = xs[i], xs[i + 1]
            for _ in range(60):
                mid = (lo + hi) / 2
                ym = g(np.array([mid]))[0]
                if not np.isfinite(ym):
                    break
                if (ym > 0) == (y0 > 0):
                    lo = mid
                else:
                    hi = mid
            r = (lo + hi) / 2
            yr = g(np.array([r]))[0]
            if np.isfinite(yr) and abs(yr) < 1e-6 * (1 + min(abs(y0), abs(y1))):  # a real zero, not a jump across a pole
                found.append(r)
    out: list[float] = []
    for r in found:
        r = 0.0 if abs(r) < 1e-9 else r
        if not out or abs(r - out[-1]) > 1e-6:
            out.append(_num(r))
    return out


def _set_text(s: sp.Set, x: sp.Symbol) -> list[str]:
    name = _txt(x)
    if s is sp.S.EmptySet:
        return []
    if isinstance(s, sp.FiniteSet):
        return [f"{name} = {_txt(v)}" for v in s.args]
    if isinstance(s, sp.Union):
        return [t for a in s.args for t in _set_text(a, x)]
    if isinstance(s, sp.ImageSet):
        lam = s.lamda
        n = sp.Symbol("n", integer=True)
        body = lam.expr.subs(lam.variables[0], n)
        return [f"{name} = {_txt(body)},  n ∈ ℤ"]
    if isinstance(s, sp.Interval):
        return [f"{name} ∈ {_txt(s)}"]
    return [f"{name} ∈ {_txt(s)}"]


def _proof(diff: sp.Expr) -> tuple[bool, list[str]]:
    """Rewrite lhs - rhs step by step; True if it reaches 0."""
    steps = [f"Left side − right side = {_txt(diff)}"]
    cur = diff
    for label, fn in (("expand", sp.expand), ("expand the trigonometric functions", sp.expand_trig), ("use trigonometric identities", sp.trigsimp),
                      ("combine fractions", sp.together), ("cancel common factors", sp.cancel), ("expand", sp.expand),
                      ("simplify", sp.simplify)):
        try:
            new = fn(cur)
        except (TypeError, ValueError, NotImplementedError):
            continue
        if new != cur:
            steps.append(f"{label}: = {_txt(new)}")
            cur = new
        if cur == 0:
            return True, steps
    return cur == 0, steps


def _numeric_zero(diff: sp.Expr, syms: list[sp.Symbol], trials: int = 12) -> bool | None:
    """True if lhs - rhs vanishes at random points, False if it clearly does not, None if it could not be evaluated."""
    rng = np.random.default_rng(7)
    fn = sp.lambdify(syms, diff, modules=["numpy"])
    ok = 0
    for _ in range(trials * 3):
        pts = rng.uniform(0.2, 2.7, len(syms))
        with np.errstate(all="ignore"):
            try:
                v = complex(fn(*pts))
            except (ZeroDivisionError, ValueError, TypeError, OverflowError):
                continue
        if not np.isfinite(v.real) or not np.isfinite(v.imag):
            continue
        if abs(v) > 1e-8 * (1 + abs(v)):
            return False
        ok += 1
        if ok >= trials:
            return True
    return None


def _range_reason(side: sp.Expr, other: sp.Expr, x: sp.Symbol) -> str | None:
    """Why f(x) = c has no real solution: c lies outside the range of f."""
    if other.free_symbols:
        return None
    try:
        rng = sp.calculus.util.function_range(side, x, sp.S.Reals)
    except (NotImplementedError, ValueError, TypeError):
        return None
    if isinstance(rng, (sp.Interval, sp.FiniteSet, sp.Union)) and not rng.contains(other) == sp.true:
        return f"{_txt(side)} only takes values in {_txt(rng)}, and {_txt(other)} is outside that range"
    return None


def _marching(F: np.ndarray, xs: np.ndarray, ys: np.ndarray, level: float = 0.0, limit: int = 4000) -> list[list[float]]:
    """Line segments of F(x, y) = level by marching squares (F indexed [iy, ix])."""
    G = F - level
    segs: list[list[float]] = []
    ny, nx = G.shape
    for iy in range(ny - 1):
        for ix in range(nx - 1):
            c = [G[iy, ix], G[iy, ix + 1], G[iy + 1, ix + 1], G[iy + 1, ix]]
            if not all(np.isfinite(c)):
                continue
            p = [(xs[ix], ys[iy]), (xs[ix + 1], ys[iy]), (xs[ix + 1], ys[iy + 1]), (xs[ix], ys[iy + 1])]
            cross = []
            for k in range(4):
                a, b = c[k], c[(k + 1) % 4]
                if (a > 0) != (b > 0):
                    tt = a / (a - b)
                    (x0, y0), (x1, y1) = p[k], p[(k + 1) % 4]
                    cross.append((x0 + tt * (x1 - x0), y0 + tt * (y1 - y0)))
            if abs(max(c) - min(c)) > 1e6:
                continue  # a pole, not a crossing
            for k in range(0, len(cross) - 1, 2):
                segs.append([_num(cross[k][0]), _num(cross[k][1]), _num(cross[k + 1][0]), _num(cross[k + 1][1])])
                if len(segs) >= limit:
                    return segs
    return segs


def _grid(expr: sp.Expr, x: sp.Symbol, y: sp.Symbol, lim: float, n: int = 161):
    xs = np.linspace(-lim, lim, n)
    ys = np.linspace(-lim, lim, n)
    X, Y = np.meshgrid(xs, ys)
    fn = sp.lambdify((x, y), expr, modules=["numpy"])
    with np.errstate(all="ignore"):
        Z = np.asarray(fn(X, Y), dtype=complex) * np.ones_like(X)
    Z = np.where(np.abs(Z.imag) < 1e-9, Z.real, np.nan)
    return xs, ys, Z


def _conic(expr: sp.Expr, x: sp.Symbol, y: sp.Symbol) -> str | None:
    try:
        p = sp.Poly(sp.expand(expr), x, y)
    except sp.PolynomialError:
        return None
    if p.total_degree() != 2:
        return {1: "a straight line"}.get(p.total_degree())
    A, B, C = (float(p.coeff_monomial(m)) for m in (x ** 2, x * y, y ** 2))
    disc = B * B - 4 * A * C
    if abs(disc) < 1e-12:
        return "a parabola"
    if disc < 0:
        return "a circle" if abs(A - C) < 1e-12 and abs(B) < 1e-12 else "an ellipse"
    return "a hyperbola"


# ---------------------------------------------------------------- the analyses
def _function(f: sp.Expr, x: sp.Symbol, out_name: str, lo: float, hi: float) -> dict[str, Any]:
    df = sp.simplify(sp.diff(f, x))
    g, dg = _f(f, x), _f(df, x)
    xs = np.linspace(lo, hi, 600)
    steps = [f"{out_name} = {_txt(f)}", f"d{out_name}/d{_txt(x)} = {_txt(df)}"]
    zeros = _roots(g, lo, hi)
    turning = _roots(dg, lo, hi)
    extra: dict[str, Any] = {}
    try:
        per = sp.periodicity(f, x)
        if per is not None and per != 0:
            extra["period"] = _txt(per)
            steps.append(f"Repeats every {_txt(per)}")
    except (NotImplementedError, ValueError, TypeError):
        pass
    try:
        dom = sp.calculus.util.continuous_domain(f, x, sp.S.Reals)
        if dom != sp.S.Reals and isinstance(dom, (sp.Interval, sp.Union)) and not dom.has(sp.ImageSet):
            extra["domain"] = _txt(dom)
            steps.append(f"Defined for {_txt(x)} ∈ {_txt(dom)}")
    except (NotImplementedError, ValueError, TypeError):
        pass
    if zeros:
        steps.append(f"Crosses zero at {_txt(x)} ≈ " + ", ".join(f"{z:g}" for z in zeros[:8]))
    pts = [{"x": t, "y": _num(float(g(np.array([t]))[0]))} for t in turning[:8] if np.isfinite(g(np.array([t]))[0])]
    if pts:
        steps.append("Turning points: " + ", ".join(f"({p['x']:g}, {p['y']:g})" for p in pts))
    return {"plot": {"x": [_num(v) for v in xs], "x_label": _txt(x), "series": [
                {"name": f"{out_name} = {_txt(f)}", "y": _clean(g(xs))}, {"name": f"d{out_name}/d{_txt(x)}", "y": _clean(dg(xs))}]},
            "zeros": zeros[:12], "turning_points": pts, "derivative": _txt(df), "steps": steps, **extra}


@tool(domain="teach", name="explore", symbolic=True,
      description="ASM Teach Equation Lab: builds any equation the teacher writes, from the mathematics itself. Proves "
                  "identities step by step, catches equations that can never hold (and says why), solves equations exactly "
                  "(general solutions for trigonometry), studies y = f(x), draws implicit curves and z = f(x, y), checks "
                  "physics formulas for dimensional consistency and turns them into live formulas, and balances chemical "
                  "equations. values sets parameters (e.g. {'L': 2}); x_min/x_max set the plotting range.")
def teach_explore(equation: str, values: dict[str, float] | None = None, x_min: float | None = None,
                  x_max: float | None = None) -> dict:
    if not isinstance(equation, str) or not equation.strip():
        raise ValueError("Write an equation first")
    if len(equation) > 300:
        raise ValueError("That is too long for one line of the board; write one equation at a time")
    text = equation.strip()
    values = dict(values or {})
    units = {"plot": "same units as the inputs", "dimensions": "SI base dimensions M L T I Θ N"}
    assumptions = ["Worked symbolically with sympy and checked numerically; nothing is looked up"]

    def done(res: dict[str, Any]) -> dict:
        res.setdefault("steps", [])
        return {"result": {"input": equation, **res}, "units": units, "assumptions": assumptions}

    if _looks_chemical(text):
        try:
            return done(_chemistry(text))
        except ValueError as e:
            if re.search(r"->|→|⟶|⇌|<=>|=>", text):
                return done({"kind": "chemical", "valid": False, "verdict": f"This does not read as a chemical equation: {e}."})

    lhs, rhs = _sides(text)
    read = f"{_txt(lhs)} = {_txt(rhs)}" if rhs is not None else _txt(lhs)
    if rhs is None:  # a bare expression: study it as a function of its variable(s)
        syms = sorted(lhs.free_symbols, key=lambda s: sym_name(s))
        if not syms:
            v = complex(sp.N(lhs))
            return done({"kind": "value", "valid": True, "read_as": read, "verdict": f"{read} = {_num(v.real):g}",
                         "value": _num(v.real)})
        if len(syms) == 1 or (len(syms) >= 1 and "x" in [sym_name(s) for s in syms]):
            x = next((s for s in syms if sym_name(s) == "x"), syms[0])
            params = {s: values.get(sym_name(s), MATH_DEFAULTS.get(sym_name(s), 1)) for s in syms if s != x}
            f = lhs.subs(params)
            lo, hi = (x_min, x_max) if x_min is not None and x_max is not None else _range_for(f)
            res = _function(f, x, "y", lo, hi)
            return done({"kind": "function", "valid": True, "read_as": f"y = {read}", "verdict": f"A function of {_txt(x)}.",
                         "params": _params(params, maths=True), **res})
        rhs = sp.Symbol("z")
        lhs, rhs = rhs, lhs
        read = f"z = {_txt(rhs)}"

    diff = lhs - rhs
    syms = sorted(diff.free_symbols, key=lambda s: sym_name(s))
    names = [sym_name(s) for s in syms]

    # 1. no variables: arithmetic is either true or false
    if not syms:
        ok = bool(abs(complex(sp.N(diff))) < 1e-9)
        return done({"kind": "statement", "valid": ok, "read_as": read,
                     "verdict": "True." if ok else f"False: the left side is {_num(complex(sp.N(lhs)).real):g} and the right side is {_num(complex(sp.N(rhs)).real):g}.",
                     "steps": [f"Left side = {_txt(sp.nsimplify(lhs))}", f"Right side = {_txt(sp.nsimplify(rhs))}"]})

    # 2. identity or impossibility
    proved, steps = _proof(diff)
    if proved:
        res = {"kind": "identity", "valid": True, "read_as": read, "verdict": "An identity: true for every value of " +
               ", ".join(_txt(s) for s in syms) + ".", "steps": steps + ["= 0, so both sides are always equal"]}
        if len(syms) == 1:
            x = syms[0]
            lo, hi = _range_for(diff)
            xs = np.linspace(lo, hi, 600)
            res["plot"] = {"x": [_num(v) for v in xs], "x_label": _txt(x), "series": [
                {"name": "left side", "y": _clean(_f(lhs, x)(xs))}, {"name": "right side", "y": _clean(_f(rhs, x)(xs))}]}
        return done(res)
    simplified = sp.simplify(diff)
    if simplified.is_number and simplified != 0:
        return done({"kind": "contradiction", "valid": False, "read_as": read,
                     "verdict": f"This can never be true: it simplifies to {_txt(simplified)} = 0. Check what was written.",
                     "steps": steps})
    numeric = _numeric_zero(diff, syms)
    if numeric is True:
        return done({"kind": "identity", "valid": True, "read_as": read,
                     "verdict": "An identity: both sides agree at every point tested, though the algebra did not reduce it fully.",
                     "steps": steps})

    # 3. maths (x, y, z, θ) or a physics formula
    math_vars = [s for s in syms if sym_name(s) in ("x", "y", "z", "theta", "th")]
    if math_vars:
        return done(_maths(lhs, rhs, syms, math_vars, values, read, x_min, x_max))
    return done(_formula(lhs, rhs, syms, values, read))


def _params(params: dict, maths: bool = False) -> list[dict[str, Any]]:
    out = []
    for s, v in params.items():
        n = sym_name(s)
        d, lo, hi = (1, -10, 10) if maths else DEFAULTS.get(n, (1, -10, 10))
        out.append({"name": n, "label": _txt(s), "value": _num(float(v)), "min": min(lo, float(v)), "max": max(hi, float(v))})
    return out


def _maths(lhs, rhs, syms, math_vars, values, read, x_min, x_max) -> dict[str, Any]:
    names = {sym_name(s): s for s in syms}
    x = names.get("x") or names.get("theta") or names.get("th") or math_vars[0]
    y, z = names.get("y"), names.get("z")
    unknowns = [s for s in (x, y, z) if s is not None]
    params = {s: values.get(sym_name(s), MATH_DEFAULTS.get(sym_name(s), 1)) for s in syms if s not in unknowns}
    L, R = lhs.subs(params), rhs.subs(params)
    plist = _params(params, maths=True)

    if y is None and z is None:  # one unknown: solve
        steps = []
        if params:
            try:
                general = sp.solve(sp.Eq(lhs, rhs), x)
                for g in general[:4]:
                    steps.append(f"In general: {_txt(x)} = {_txt(g)}")
            except (NotImplementedError, ValueError, TypeError):
                pass
        try:
            sol = sp.solveset(sp.Eq(L, R), x, sp.S.Reals)
        except (NotImplementedError, ValueError, TypeError):
            sol = None
        lo, hi = (x_min, x_max) if x_min is not None and x_max is not None else _range_for(L - R)
        gl, gr = _f(L, x), _f(R, x)
        xs = np.linspace(lo, hi, 600)
        crossings = _roots(_f(L - R, x), lo, hi)
        plot = {"x": [_num(v) for v in xs], "x_label": _txt(x),
                "series": [{"name": f"left: {_txt(L)}", "y": _clean(gl(xs))}, {"name": f"right: {_txt(R)}", "y": _clean(gr(xs))}],
                "marks": [{"x": c, "y": _num(float(gl(np.array([c]))[0]))} for c in crossings[:24]]}
        if sol is not None and sol is sp.S.EmptySet:
            why = _range_reason(L, R, x) or _range_reason(R, L, x)
            return {"kind": "equation", "valid": False, "read_as": read, "params": plist, "plot": plot, "solutions": [],
                    "verdict": "No real value of " + _txt(x) + " satisfies this" + (f": {why}." if why else ". The two sides never meet."),
                    "steps": steps + ([why] if why else [])}
        sols = _set_text(sol, x) if sol is not None and not isinstance(sol, sp.ConditionSet) else []
        if not sols and crossings:
            sols = [f"{_txt(x)} ≈ {c:g}" for c in crossings[:8]]
            steps.append("No closed form; solved numerically where the two sides cross")
        if not sols:
            return {"kind": "equation", "valid": False, "read_as": read, "params": plist, "plot": plot, "solutions": [],
                    "verdict": f"No real solution in the range shown: the two sides never meet between {lo:g} and {hi:g}.", "steps": steps}
        steps.append("Solve over the real numbers")
        return {"kind": "equation", "valid": True, "read_as": read, "params": plist, "plot": plot, "solutions": sols,
                "verdict": "Solved: " + "; ".join(sols[:4]) + ("…" if len(sols) > 4 else ""), "steps": steps}

    lim = 2 * math.pi if (L - R).has(*_TRIG) else 10.0
    if x_min is not None and x_max is not None:
        lim = max(abs(x_min), abs(x_max))
    if z is not None:  # z = f(x, y): contour lines
        expr = sp.solve(sp.Eq(L, R), z)
        if not expr:
            raise ValueError("Could not write this as z = f(x, y)")
        f = expr[0]
        xs, ys, Z = _grid(f, x, y, lim, 101)
        finite = Z[np.isfinite(Z)]
        if finite.size == 0:
            raise ValueError("This surface has no real values in the range shown")
        levels = np.linspace(*np.percentile(finite, [5, 95]), 9)
        contours = [{"level": _num(lv), "segments": _marching(Z, xs, ys, lv, 1500)} for lv in levels]
        return {"kind": "surface", "valid": True, "read_as": read, "params": plist, "verdict": f"A surface z = {_txt(f)}, drawn as contour lines.",
                "contours": contours, "range": [-lim, lim], "steps": [f"z = {_txt(f)}", f"∂z/∂x = {_txt(sp.diff(f, x))}", f"∂z/∂y = {_txt(sp.diff(f, y))}"]}
    # y = f(x) explicitly, or an implicit relation in x and y
    if (L == y and y not in R.free_symbols) or (R == y and y not in L.free_symbols):
        f = R if L == y else L
        lo, hi = (x_min, x_max) if x_min is not None and x_max is not None else _range_for(f)
        res = _function(f, x, "y", lo, hi)
        return {"kind": "function", "valid": True, "read_as": read, "params": plist, "verdict": f"y as a function of {_txt(x)}.", **res}
    F = sp.expand(L - R)
    xs, ys, G = _grid(F, x, y, lim)
    segs = _marching(G, xs, ys)
    name = _conic(F, x, y)
    if not segs:
        return {"kind": "curve", "valid": False, "read_as": read, "params": plist, "segments": [], "range": [-lim, lim],
                "verdict": "No real points satisfy this relation in the range shown" + (f" (it would be {name}, but it is empty)" if name else "") + ".",
                "steps": [f"{_txt(F)} = 0"]}
    return {"kind": "curve", "valid": True, "read_as": read, "params": plist, "segments": segs, "range": [-lim, lim],
            "verdict": f"A curve in the x-y plane{': ' + name if name else ''}.", "conic": name,
            "steps": [f"All points where {_txt(F)} = 0"] + ([f"Second-degree terms make it {name}"] if name else [])}


def _formula(lhs, rhs, syms, values, read) -> dict[str, Any]:
    dims = _dimension_check(lhs, rhs)
    steps: list[str] = []
    if dims is not None:
        if not dims["consistent"]:
            return {"kind": "formula", "valid": False, "read_as": read, "dimensions": dims,
                    "verdict": f"This formula cannot be right: {dims['reason']}. Both sides of a physical equation must have the same dimensions.",
                    "steps": ["Reading the symbols as " + ", ".join(f"{k} = {v}" for k, v in dims["reading"].items())]}
        steps.append("Dimensions match: both sides are " + dims["dimension"] + " (" +
                     ", ".join(f"{k} = {v}" for k, v in dims["reading"].items()) + ")")
    subject = lhs if lhs.is_Symbol and lhs not in rhs.free_symbols else None
    if subject is None and rhs.is_Symbol and rhs not in lhs.free_symbols:
        subject = rhs
        lhs, rhs = rhs, lhs
    if subject is None:
        subject = syms[0]
        sols = sp.solve(sp.Eq(lhs, rhs), subject)
        if not sols:
            raise ValueError(f"Could not rearrange this for {_txt(subject)}")
        rhs = sols[0]
        steps.append(f"Rearranged: {_txt(subject)} = {_txt(rhs)}")
    inputs = sorted(rhs.free_symbols, key=lambda s: sym_name(s))
    vals = {s: float(values.get(sym_name(s), DEFAULTS.get(sym_name(s), (1, 0, 10))[0])) for s in inputs}
    value = complex(sp.N(rhs.subs(vals)))
    out: dict[str, Any] = {"kind": "formula", "valid": True, "read_as": read, "dimensions": dims, "subject": sym_name(subject),
                           "params": _params(vals), "steps": steps,
                           "value": _num(value.real) if abs(value.imag) < 1e-12 else None}
    if inputs:
        s = inputs[0]
        steps.append(f"How {_txt(subject)} changes with {_txt(s)}: ∂{_txt(subject)}/∂{_txt(s)} = {_txt(sp.simplify(sp.diff(rhs, s)))}")
    if inputs:
        s = inputs[0]
        d, lo, hi = DEFAULTS.get(sym_name(s), (vals[s], 0, max(10, 2 * vals[s])))
        xs = np.linspace(lo, hi, 300)
        g = _f(rhs.subs({o: v for o, v in vals.items() if o != s}), s)
        out["plot"] = {"x": [_num(v) for v in xs], "x_label": _txt(s), "series": [{"name": _txt(subject), "y": _clean(g(xs))}],
                       "marks": [{"x": _num(vals[s]), "y": out["value"]}] if out["value"] is not None else []}
    out["verdict"] = (f"{_txt(subject)} = {out['value']:g} for the values shown." if out["value"] is not None else
                      f"{_txt(subject)} has no real value for these inputs.")
    return out

