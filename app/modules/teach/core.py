"""ASM Teach: the curriculum experiment format and the engine that runs it.

Every experiment is data: parameters a teacher can move, outputs defined by formulas, an optional swept graph,
the governing equations and the derivation steps. The engine parses each formula once with the shared safe
parser, compiles it with numpy, and evaluates it for the values on screen or across a sweep. Nothing is
tabulated or approximated by hand; every number a lesson shows is computed here.

Catalogue files call ``X(...)`` to add experiments. Compact string forms keep the catalogue readable:

    params = "u:Initial velocity:m/s:0:0:50; a:Acceleration:m/s^2:2:-10:10; t:Time:s:5:0:30"
             name:label:unit:default:min:max[:step]
    out    = "v:Final velocity:m/s:u + a*t; s:Displacement:m:u*t + a*t**2/2"      name:label:unit:formula
    series = "y:Height:m:v0*sin(th*pi/180)*t - g*t**2/2"                         formulas in the sweep variable
    plot   = "t: v, s"            sweep the parameter t over its range and plot outputs v and s
             "t=0..T: x ~ y"      sweep a free variable t from 0 to the output T and draw the path y against x
    eqs    = "v = u + a*t | v**2 = u**2 + 2*a*s"                                  shown and used for recognition
    steps  = "first step | second step"                                           the derivation, in order
    scene  = "pendulum: L=L, amp=theta0, T=T"                                     picture type and its inputs
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import numpy as np
import sympy as sp
from scipy import special

from app.core.parsing import parse_expression

BOARDS = ("NCERT", "CBSE", "ICSE", "State")
SUBJECTS = ("physics", "chemistry", "mathematics")
KINDS = {"derivation": "Derivation", "law": "Law", "practical": "Practical", "graph": "Graph", "concept": "Concept"}
SCENES = {"gauges", "path", "pendulum", "spring", "wave", "circuit", "lens", "mirror", "gas", "beaker", "atom", "vector",
          "incline", "graph", "shape", "decay", "field", "prism", "lever", "reaction"}

# Physical constants a formula may use by name (SI, CODATA 2018 exact or recommended values)
CONSTANTS: dict[str, float] = {
    "g0": 9.80665, "G_N": 6.67430e-11, "c0": 299_792_458.0, "h_P": 6.62607015e-34, "e_c": 1.602176634e-19,
    "k_e": 8.9875517923e9, "eps0": 8.8541878128e-12, "mu0": 1.25663706212e-6, "m_e": 9.1093837015e-31,
    "m_p": 1.67262192369e-27, "k_B": 1.380649e-23, "N_A": 6.02214076e23, "R_g": 8.314462618, "F_c": 96485.33212,
    "sigma_SB": 5.670374419e-8, "R_H": 1.0973731568e7, "a_0": 5.29177210903e-11, "eV": 1.602176634e-19,
}

# Letters sympy would read as constants (I = imaginary unit, E = Euler's number, S = singleton, N = evalf, Q = assumptions)
_RESERVED = {k: f"{k}_rsv" for k in ("I", "E", "S", "N", "Q", "O", "beta", "gamma", "zeta")}
_UNRESERVED = {v: k for k, v in _RESERVED.items()}
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_FUNCS = {"sin", "cos", "tan", "cot", "sec", "csc", "asin", "acos", "atan", "atan2", "sinh", "cosh", "tanh", "exp", "log",
          "ln", "sqrt", "cbrt", "Abs", "abs", "sign", "floor", "ceiling", "factorial", "binomial", "erf", "Min", "Max", "pi",
          "root", "Heaviside", "log10", "lim"}


def _safe_text(text: str) -> str:
    return _IDENT.sub(lambda m: _RESERVED.get(m.group(0), m.group(0)), text)


def parse(text: str) -> sp.Expr:
    """Parse a catalogue or teacher formula. Single capital letters like I (current) and E (energy) stay symbols."""
    return parse_expression(_safe_text(text))


def parse_eq(text: str) -> sp.Expr:
    """'lhs = rhs' as lhs - rhs."""
    if "=" in text:
        lhs, rhs = text.split("=", 1)
        return parse(lhs) - parse(rhs)
    return parse(text)


def sym_name(s: sp.Symbol) -> str:
    return _UNRESERVED.get(s.name, s.name)


# ---------------------------------------------------------------- pretty printing (plain Unicode, no LaTeX)
_GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "Delta": "Δ", "epsilon": "ε", "eps": "ε", "theta": "θ",
          "th": "θ", "lam": "λ", "mu": "μ", "nu": "ν", "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "phi": "φ",
          "omega": "ω", "Omega": "Ω", "eta": "η", "kappa": "κ", "psi": "ψ", "chi": "χ", "zeta": "ζ", "xi": "ξ"}
_SUB = str.maketrans("0123456789aehijklmnoprstuvx", "₀₁₂₃₄₅₆₇₈₉ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ")
_SUP = str.maketrans("0123456789-+n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺ⁿ")
_CONST_PRETTY = {"g0": "g", "G_N": "G", "c0": "c", "h_P": "h", "e_c": "e", "k_e": "k", "eps0": "ε₀", "mu0": "μ₀",
                 "m_e": "mₑ", "m_p": "mₚ", "k_B": "k_B", "N_A": "N_A", "R_g": "R", "F_c": "F", "sigma_SB": "σ",
                 "R_H": "R_H", "a_0": "a₀", "eV": "eV"}


def _pretty_ident(name: str) -> str:
    """v0 -> v₀, R1 -> R₁, theta -> θ, T_h -> Tₕ; other names are left alone."""
    if name in _CONST_PRETTY:
        return _CONST_PRETTY[name]
    if name in _GREEK:
        return _GREEK[name]
    m = re.fullmatch(r"([A-Za-z]+)(\d+)", name) or re.fullmatch(r"([A-Za-z]+)_([A-Za-z0-9]{1,3})", name)
    if m:
        base, sub = _GREEK.get(m.group(1), m.group(1)), m.group(2)
        subbed = sub.translate(_SUB)
        if all(ch in "₀₁₂₃₄₅₆₇₈₉ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ" for ch in subbed):
            return base + subbed
        return f"{base}_{sub}"
    return name


def pretty(text: str) -> str:
    """'s = u*t + a*t**2/2' -> 's = ut + at²/2'; 'T = 2*pi*sqrt(L/g)' -> 'T = 2π√(L/g)'."""
    s = text.strip()
    s = re.sub(r"\*\*\s*(?:\(\s*(-?\d+)\s*\)|(-?\d+))", lambda m: (m.group(1) or m.group(2)).translate(_SUP), s)
    s = re.sub(r"\*\*\s*\(\s*1\s*/\s*2\s*\)", "^½", s)
    s = re.sub(r"\*\*\s*([a-z])\b", lambda m: m.group(1).translate(_SUP) if m.group(1) == "n" else "^" + m.group(1), s)
    s = s.replace("**", "^")
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+\.?\d*(?:e-?\d+)?|\S", s)
    out: list[str] = []
    for i, tok in enumerate(tokens):
        if tok == "*":
            prev, nxt = tokens[i - 1] if i else "", tokens[i + 1] if i + 1 < len(tokens) else ""
            pv, nx = _pretty_ident(prev) if _IDENT.fullmatch(prev) else prev, _pretty_ident(nxt) if _IDENT.fullmatch(nxt) else nxt
            short = lambda t: len(re.sub(r"[₀-₉ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ⁰¹²³⁴⁵⁶⁷⁸⁹⁻]", "", t)) == 1  # one letter, maybe with a subscript
            joinable = (short(pv) or re.fullmatch(r"[\d.]+", prev) or prev in (")", "²", "³")) and (short(nx) or nxt in ("sqrt", "(", "pi")) \
                and not (re.fullmatch(r"[\d.]+", prev) and re.fullmatch(r"[\d.]+", nxt)) and not re.fullmatch(r"[\d.]+", nxt)
            out.append("" if joinable and nxt not in _FUNCS - {"sqrt", "pi"} else "·")
        elif tok == "sqrt":
            out.append("√")
        elif _IDENT.fullmatch(tok):
            out.append(_pretty_ident(tok) if tok not in _FUNCS or tok == "pi" else tok)
        else:
            out.append(tok)
    s = ""
    for tok in out:  # spaces around = + - but not inside exponents
        if tok in ("=", "+", "-", "<", ">") and s and not s.endswith(("(", "^", "e")):
            s = s.rstrip() + f" {tok} "
        else:
            s += tok
    s = re.sub(r"\(\s*-\s*", "(-", s).replace("= -", "= −").replace(" - ", " − ")
    return re.sub(r"^\s*-\s*", "−", s).strip()


def pretty_unit(unit: str) -> str:
    if unit.strip() in ("-", ""):
        return ""
    u = unit.replace("deg", "°").replace("ohm", "Ω").replace("*", "·")
    u = re.sub(r"(^|[/·(])u(?=[A-Za-zΩ])", r"\1µ", u)
    u = re.sub(r"\^(-?\d+)", lambda m: m.group(1).translate(_SUP), u)
    return u


# ---------------------------------------------------------------- the data model
@dataclass
class Param:
    name: str
    label: str
    unit: str
    default: float
    lo: float
    hi: float
    step: float | None = None

    def public(self) -> dict[str, Any]:
        return {"name": self.name, "label": self.label, "unit": pretty_unit(self.unit), "default": self.default, "min": self.lo,
                "max": self.hi, "step": self.step, "symbol": _pretty_ident(self.name)}


@dataclass
class Output:
    name: str
    label: str
    unit: str
    expr: str


@dataclass
class Experiment:
    id: str
    cls: int
    subject: str
    chapter: str
    title: str
    kind: str
    blurb: str
    params: list[Param]
    outputs: list[Output]
    series: list[Output] = field(default_factory=list)
    plot: str = ""
    eqs: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    scene: str = "gauges"
    scene_roles: dict[str, str] = field(default_factory=dict)
    boards: tuple[str, ...] = BOARDS
    tags: str = ""
    ask: list[str] = field(default_factory=list)
    question: str = ""
    lab: str = ""
    assumptions: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {"id": self.id, "class": self.cls, "subject": self.subject, "chapter": self.chapter, "title": self.title,
                "kind": self.kind, "kind_label": KINDS[self.kind], "blurb": self.blurb, "boards": list(self.boards),
                "scene": self.scene, "equation": pretty(self.eqs[0]) if self.eqs else ""}


CATALOG: dict[str, Experiment] = {}


def _split(text: str, sep: str = ";") -> list[str]:
    return [p.strip() for p in text.split(sep) if p.strip()]


def _num(text: str) -> float:
    return float(parse_expression(text).evalf()) if re.search(r"[a-z]", text) else float(text)


def X(id: str, cls: int, subject: str, chapter: str, title: str, kind: str, blurb: str, *, params: str, out: str,
      series: str = "", plot: str = "", eqs: str = "", steps: str = "", scene: str = "gauges", boards: tuple[str, ...] = BOARDS,
      tags: str = "", ask: str = "", question: str = "", lab: str = "", assume: str = "") -> Experiment:
    """Add an experiment to the catalogue (see the module docstring for the string formats)."""
    if id in CATALOG:
        raise ValueError(f"duplicate ASM Teach experiment id {id}")
    ps = []
    for p in _split(params):
        f = p.split(":")
        ps.append(Param(f[0], f[1], f[2], _num(f[3]), _num(f[4]), _num(f[5]), _num(f[6]) if len(f) > 6 else None))

    def outs(text: str) -> list[Output]:
        res = []
        for o in _split(text):
            name, label, unit, expr = o.split(":", 3)
            res.append(Output(name.strip(), label.strip(), unit.strip(), expr.strip()))
        return res

    sname, _, roles = scene.partition(":")
    role_map = {k.strip(): v.strip() for k, v in (r.split("=") for r in _split(roles, ","))} if roles.strip() else {}
    e = Experiment(id=id, cls=cls, subject=subject, chapter=chapter, title=title, kind=kind, blurb=blurb, params=ps,
                   outputs=outs(out), series=outs(series), plot=plot, eqs=_split(eqs, "|"), steps=_split(steps, "|"),
                   scene=sname.strip(), scene_roles=role_map, boards=boards, tags=tags, ask=_split(ask, ","),
                   question=question, lab=lab, assumptions=_split(assume, "|"))
    CATALOG[id] = e
    return e


# ---------------------------------------------------------------- evaluation
def _lambdify(expr_text: str):
    expr = parse(expr_text)
    syms = sorted(expr.free_symbols, key=lambda s: s.name)
    names = [sym_name(s) for s in syms]
    f = sp.lambdify(syms, expr, modules=[{"Heaviside": lambda x, h0=0.5: np.heaviside(x, 0.5), "factorial": lambda x: special.gamma(np.asarray(x) + 1.0),
                                          "binomial": special.binom}, "numpy"])
    return f, names


@lru_cache(maxsize=None)
def compiled(exp_id: str) -> dict[str, Any]:
    e = CATALOG[exp_id]
    return {"outputs": [(o.name, *_lambdify(o.expr)) for o in e.outputs],
            "series": [(o.name, *_lambdify(o.expr)) for o in e.series]}


def _call(f, names: list[str], ns: dict[str, Any]):
    missing = [n for n in names if n not in ns]
    if missing:
        raise ValueError(f"formula uses unknown name(s) {', '.join(missing)}")
    with np.errstate(all="ignore"):
        return f(*[ns[n] for n in names])


def resolve_values(e: Experiment, values: dict[str, float] | None) -> dict[str, float]:
    vals = {p.name: p.default for p in e.params}
    for k, v in (values or {}).items():
        p = next((p for p in e.params if p.name == k), None)
        if p is None:
            raise ValueError(f"{e.title} has no input {k!r}; inputs are {', '.join(q.name for q in e.params)}")
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            raise ValueError(f"{p.label} must be a finite number")
        span = p.hi - p.lo
        if not (p.lo - 1e-9 * abs(span) <= v <= p.hi + 1e-9 * abs(span)):
            raise ValueError(f"{p.label} must be between {p.lo:g} and {p.hi:g} {pretty_unit(p.unit)}")
        vals[k] = float(v)
    return vals


def compute(e: Experiment, vals: dict[str, Any]) -> dict[str, Any]:
    """All outputs for the given values (scalars or numpy arrays for a sweep)."""
    ns: dict[str, Any] = dict(CONSTANTS)
    ns.update({k: np.asarray(v, dtype=float) if isinstance(v, np.ndarray) else np.float64(v) for k, v in vals.items()})
    for name, f, names in compiled(e.id)["outputs"]:
        ns[name] = _call(f, names, ns)
    return ns


def _finite(x: Any) -> float | None:
    x = float(x)
    return x if math.isfinite(x) else None


def _clean(arr: Any, n: int) -> list[float | None]:
    a = np.broadcast_to(np.asarray(arr, dtype=float), (n,))
    return [round(float(v), 12) if math.isfinite(v) else None for v in a]


def parse_plot(e: Experiment) -> dict[str, Any] | None:
    if not e.plot:
        return None
    head, _, body = e.plot.partition(":")
    var, _, rng = head.partition("=")
    var = var.strip()
    lo, _, hi = rng.partition("..")
    path = "~" in body
    ys = [y.strip() for y in re.split(r"[,~]", body) if y.strip()]
    return {"var": var, "lo": lo.strip() or None, "hi": hi.strip() or None, "ys": ys, "path": path}


def sweep(e: Experiment, vals: dict[str, float], n: int = 161) -> dict[str, Any] | None:
    spec = parse_plot(e)
    if spec is None:
        return None
    var = spec["var"]
    base = compute(e, vals)
    param = next((p for p in e.params if p.name == var), None)

    def bound(text: str | None, default: float | None) -> float:
        if text is None:
            if default is None:
                raise ValueError(f"plot range for {var} is missing")
            return default
        f, names = _lambdify(text)
        return float(_call(f, names, base))

    lo = bound(spec["lo"], param.lo if param else None)
    hi = bound(spec["hi"], param.hi if param else None)
    if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo:
        raise ValueError(f"these values give an empty range for {var}")
    xs = np.linspace(lo, hi, n)
    ns = compute(e, {**vals, var: xs}) if param else {**base, var: xs}
    for name, f, names in compiled(e.id)["series"]:
        ns[name] = _call(f, names, ns)
    label_of = {o.name: (o.label, o.unit) for o in e.outputs + e.series}
    if param:
        label_of[var] = (param.label, param.unit)
    out = []
    for y in spec["ys"]:
        if y not in ns:
            raise ValueError(f"plot names unknown quantity {y}")
        lab, unit = label_of.get(y, (y, ""))
        out.append({"name": y, "label": lab, "unit": pretty_unit(unit), "values": _clean(ns[y], n)})
    xlab, xunit = label_of.get(var, ("t", "s")) if param else (next((s.label for s in e.series if s.name == var), var), "")
    if not param:
        xlab, xunit = {"t": ("Time", "s"), "x": ("x", ""), "theta": ("Angle", "rad")}.get(var, (var, ""))
    return {"x": {"name": var, "label": xlab, "unit": pretty_unit(xunit), "values": [round(float(v), 12) for v in xs]},
            "series": out, "path": spec["path"], "cursor": _finite(vals[var]) if param else None}


def dependencies(e: Experiment, name: str) -> list[str]:
    """Parameters an output depends on, directly or through other outputs."""
    by_name = {o.name: o for o in e.outputs}
    pnames = {p.name for p in e.params}
    seen: set[str] = set()
    order: list[str] = []

    def walk(n: str) -> None:
        if n in seen:
            return
        seen.add(n)
        if n in by_name:
            for s in sorted(parse(by_name[n].expr).free_symbols, key=lambda s: s.name):
                walk(sym_name(s))
        elif n in pnames:
            order.append(n)
    walk(name)
    return [p.name for p in e.params if p.name in order]


# ---------------------------------------------------------------- recognition helpers
_EQ_CACHE: dict[str, tuple[str, str, frozenset[str]]] = {}


def equation_index() -> list[tuple[str, str, frozenset[str]]]:
    """(experiment id, equation text, the set of names it uses) for every catalogue equation."""
    if not _EQ_CACHE:
        for e in CATALOG.values():
            for i, eq in enumerate(e.eqs):
                names = frozenset(n for n in _IDENT.findall(eq) if n not in _FUNCS)
                _EQ_CACHE[f"{e.id}#{i}"] = (e.id, eq, names)
    return list(_EQ_CACHE.values())


def known_names() -> set[str]:
    names: set[str] = set()
    for _, _, ns in equation_index():
        names |= ns
    return names


def split_teacher_text(text: str) -> str:
    """Board shorthand to engine syntax: 'v = u + at' -> 'v = u + a*t', '½mv²' -> '(1/2)*m*v**2', '×' and '·' -> '*'."""
    t = text.strip()
    t = t.replace("×", "*").replace("·", "*").replace("−", "-").replace("÷", "/").replace("½", "(1/2)*").replace("π", " pi ")
    t = t.replace("√", " sqrt").replace("^", "**")
    t = re.sub(r"sqrt\s*([A-Za-z0-9_]+)", r"sqrt(\1)", t)
    sup = {"²": "**2", "³": "**3", "⁴": "**4", "¹": "**1"}
    for k, v in sup.items():
        t = t.replace(k, v)
    greek_back = {v: k for k, v in _GREEK.items() if k not in ("th", "eps")}
    for g, name in greek_back.items():
        t = t.replace(g, f" {name} ")
    known = known_names() | set(CONSTANTS)

    def segment(w: str) -> list[str] | None:
        """Split a run like 'at', 'mgh' or 'P1V1' into known symbols, preferring the fewest pieces."""
        best: list[list[str] | None] = [None] * (len(w) + 1)
        best[0] = []
        for i in range(len(w)):
            if best[i] is None:
                continue
            for j in range(len(w), i, -1):
                piece = w[i:j]
                if (piece in known or len(piece) == 1 and piece.isalpha()) and \
                        (best[j] is None or len(best[i]) + 1 < len(best[j])):
                    best[j] = best[i] + [piece]
        return best[len(w)]

    def fix(m: re.Match) -> str:
        w = m.group(0)
        if w in known or w in _FUNCS or w in _GREEK or len(w) == 1:
            return w
        parts = segment(w)
        return "*".join(parts) if parts and len(parts) > 1 else w
    t = re.sub(r"[A-Za-z_][A-Za-z0-9_]*", fix, t)
    t = re.sub(r"(?<![A-Za-z_0-9.])(\d+(?:\.\d+)?)\s*(?=[A-Za-z(])", r"\1*", t)
    # juxtaposed factors written with a space: '2 pi sqrt(L/g)' -> '2*pi*sqrt(L/g)' (never between a function and its bracket)
    t = re.sub(r"([A-Za-z_][A-Za-z0-9_]*|[\d.]+|\))\s+(?=[A-Za-z_(\d])",
               lambda m: m.group(1) + ("" if m.group(1) in _FUNCS - {"pi"} else "*"), t)
    return re.sub(r"\s+", " ", t).strip()


def numerically_equivalent(a: sp.Expr, b: sp.Expr, syms: list[sp.Symbol], trials: int = 4) -> bool:
    """Do a = 0 and b = 0 describe the same relation? Solve both for a shared symbol and compare at random points."""
    rng = np.random.default_rng(12345)
    for s in syms:
        try:
            sa = sp.solve(a, s)
            sb = sp.solve(b, s)
        except (NotImplementedError, ValueError, TypeError):
            continue
        if not sa or not sb or len(sa) > 4 or len(sb) > 4:
            continue
        others = [o for o in syms if o != s]
        ok = True
        for _ in range(trials):
            point = {o: sp.Float(rng.uniform(0.6, 2.4)) for o in others}
            va = sorted(complex(sp.N(x.subs(point))).real for x in sa if abs(complex(sp.N(x.subs(point))).imag) < 1e-9)
            vb = sorted(complex(sp.N(x.subs(point))).real for x in sb if abs(complex(sp.N(x.subs(point))).imag) < 1e-9)
            if len(va) != len(vb) or any(abs(x - y) > 1e-6 * max(1.0, abs(x)) for x, y in zip(va, vb)):
                ok = False
                break
        return ok
    return False


def nice_number(x: float, rng: np.random.Generator, step: float | None) -> float:
    if step:
        return round(round(x / step) * step, 10)
    if x == 0:
        return 0.0
    mag = 10 ** math.floor(math.log10(abs(x)))
    return float(round(x / mag * 2) / 2 * mag) if rng.random() < 0.5 else float(round(x / mag) * mag)
