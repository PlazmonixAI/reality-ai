"""ASM Teach engine tools: the curriculum library, running an experiment, practice questions with computed answers,
and reading an equation a teacher writes on the board."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import sympy as sp

from app.core.registry import tool
from app.modules.teach import catalog  # noqa: F401  (fills CATALOG)
from app.modules.teach.core import (BOARDS, CATALOG, CONSTANTS, KINDS, SUBJECTS, compute, dependencies, equation_index,
                                    nice_number, numerically_equivalent, parse, parse_eq, pretty, pretty_unit,
                                    resolve_values, split_teacher_text, sweep, sym_name)


def _get(experiment_id: str):
    e = CATALOG.get(experiment_id)
    if e is None:
        raise ValueError(f"No ASM Teach experiment called {experiment_id!r}")
    return e


def _sig(x: float, digits: int = 4) -> float:
    if x == 0 or not math.isfinite(x):
        return x
    return float(f"{x:.{digits}g}")


@tool(domain="teach", name="catalog",
      description="ASM Teach library: Class 9 to 12 physics, chemistry and maths experiments mapped to NCERT, CBSE, ICSE "
                  "and state board chapters. Filter by class (9-12), subject, board or a search phrase.")
def teach_catalog(cls: int | None = None, subject: str | None = None, board: str | None = None, query: str = "") -> dict:
    if cls is not None and cls not in (9, 10, 11, 12):
        raise ValueError("class must be 9, 10, 11 or 12")
    if subject is not None and subject not in SUBJECTS:
        raise ValueError(f"subject must be one of {', '.join(SUBJECTS)}")
    if board is not None and board not in BOARDS:
        raise ValueError(f"board must be one of {', '.join(BOARDS)}")
    words = [w for w in query.lower().split() if w]
    items = []
    for e in CATALOG.values():
        if (cls and e.cls != cls) or (subject and e.subject != subject) or (board and board not in e.boards):
            continue
        hay = f"{e.title} {e.chapter} {e.blurb} {e.tags} {' '.join(e.eqs)}".lower()
        if words and not all(w in hay for w in words):
            continue
        items.append(e.summary())
    counts: dict[str, dict[str, int]] = {}
    for e in CATALOG.values():
        counts.setdefault(str(e.cls), {s: 0 for s in SUBJECTS})[e.subject] += 1
    return {"result": {"items": items, "total": len(CATALOG), "matched": len(items), "counts": counts,
                       "boards": list(BOARDS), "kinds": KINDS},
            "units": {}, "assumptions": ["Chapters follow the NCERT textbooks, which CBSE and most state boards use.",
                                         "Topics that ICSE teaches in a different class are tagged with the board."]}


@tool(domain="teach", name="experiment",
      description="Run one ASM Teach experiment: computes every output for the given input values, the swept graph, "
                  "and returns the governing equations and derivation steps.")
def teach_experiment(experiment_id: str, values: dict[str, float] | None = None) -> dict:
    e = _get(experiment_id)
    vals = resolve_values(e, values)
    ns = compute(e, vals)
    outputs = []
    for o in e.outputs:
        v = float(np.asarray(ns[o.name], dtype=float))
        outputs.append({"name": o.name, "label": o.label, "unit": pretty_unit(o.unit), "value": _sig(v, 6) if math.isfinite(v) else None,
                        "formula": pretty(f"{o.name} = {o.expr}")})
    roles = {}
    for role, src in e.scene_roles.items():
        if src in ns:
            v = float(np.asarray(ns[src], dtype=float))
            roles[role] = v if math.isfinite(v) else None
        else:
            try:
                roles[role] = float(src)
            except ValueError:
                roles[role] = src  # a fixed setting such as a shape name
    graph = sweep(e, vals)
    return {
        "result": {**e.summary(), "params": [p.public() for p in e.params], "values": vals, "outputs": outputs, "graph": graph,
                   "equations": [{"text": q, "pretty": pretty(q)} for q in e.eqs], "steps": e.steps,
                   "scene": {"type": e.scene, "roles": roles}, "lab": e.lab or None,
                   "constants": {k: v for k, v in CONSTANTS.items() if any(k in o.expr for o in e.outputs + e.series)}},
        "units": {o.name: pretty_unit(o.unit) for o in e.outputs} | {p.name: pretty_unit(p.unit) for p in e.params},
        "assumptions": e.assumptions or ["Ideal textbook model: the conditions stated in the chapter."],
    }


def _given_text(e, vals: dict[str, float], names: list[str]) -> str:
    parts = []
    for n in names:
        p = next(q for q in e.params if q.name == n)
        unit = pretty_unit(p.unit)
        parts.append(f"{p.label.lower()} = {vals[n]:g}{'' if unit in ('', '°') else ' '}{unit}")
    if len(parts) > 1:
        return ", ".join(parts[:-1]) + " and " + parts[-1]
    return parts[0] if parts else ""


@tool(domain="teach", name="practice",
      description="Practice questions for an ASM Teach experiment: fresh input values each time, the answer computed by "
                  "the engine, four answer choices and a worked solution.")
def teach_practice(experiment_id: str, count: int = 5, seed: int = 0) -> dict:
    e = _get(experiment_id)
    if not 1 <= count <= 20:
        raise ValueError("count must be between 1 and 20")
    rng = np.random.default_rng(seed)
    targets = e.ask or [o.name for o in e.outputs]
    by_name = {o.name: o for o in e.outputs}
    questions = []
    attempts = fails = 0
    while len(questions) < count and attempts < count * 40:
        attempts += 1
        target = targets[(len(questions) + fails) % len(targets)]
        o = by_name[target]
        vals = {}
        for p in e.params:
            lo, hi = p.lo, p.hi
            if p.step is None:  # keep away from the edges, where textbook numbers are rarely chosen
                lo, hi = lo + 0.1 * (hi - lo), hi - 0.1 * (hi - lo)
            v = nice_number(float(rng.uniform(lo, hi)), rng, p.step)
            vals[p.name] = min(max(v, p.lo), p.hi)
        ns = compute(e, vals)
        ans = float(np.asarray(ns[target], dtype=float))
        if not math.isfinite(ans) or abs(ans) < 1e-300:
            fails += 1
            continue
        given = dependencies(e, target)
        text = e.question.format(**{k: f"{v:g}" for k, v in vals.items()}) if e.question and len(targets) == 1 else \
            f"{e.title}. Take {_given_text(e, vals, given)}. Find the {o.label.lower()}."
        if not given:
            text = f"{e.title}. Find the {o.label.lower()}."
        answer = _sig(ans)
        pool = [ans * f for f in (2, 0.5, 10, 0.1, -1, 1.5, 0.75, math.pi, 1 / math.pi, 4, 0.25)]
        rng.shuffle(pool)
        choices = [answer]
        for c in pool:
            c = _sig(c)
            if all(abs(c - x) > 0.02 * max(abs(x), 1e-300) for x in choices):
                choices.append(c)
            if len(choices) == 4:
                break
        rng.shuffle(choices)
        unit = pretty_unit(o.unit)
        chain = [x for x in e.outputs if x.name in _chain(e, target)]
        questions.append({
            "text": text, "values": vals, "target": target, "label": o.label, "answer": answer, "unit": unit,
            "choices": choices, "correct_index": choices.index(answer), "tolerance": 0.02,
            "solution": ([f"Given: {_given_text(e, vals, given)}."] if given else []) +
                        [f"Use {pretty(f'{x.name} = {x.expr}')}" + (f", which gives {x.label.lower()} = {_sig(float(np.asarray(ns[x.name], dtype=float))):g} {pretty_unit(x.unit)}" if x.name != target else "") + "."
                         for x in chain] +
                        [f"So the {o.label.lower()} is {answer:g} {unit}."],
        })
    if not questions:
        raise ValueError("Could not make practice questions for this experiment")
    return {"result": {"experiment_id": e.id, "title": e.title, "questions": questions},
            "units": {q["target"]: q["unit"] for q in questions},
            "assumptions": ["Answers are computed by the engine and rounded to 4 significant figures; within 2% counts as correct."]}


def _chain(e, target: str) -> list[str]:
    """Outputs needed to compute target, in catalogue order."""
    by_name = {o.name: o for o in e.outputs}
    need: set[str] = set()

    def walk(n: str) -> None:
        if n in need or n not in by_name:
            return
        need.add(n)
        for s in parse(by_name[n].expr).free_symbols:
            walk(sym_name(s))
    walk(target)
    return [o.name for o in e.outputs if o.name in need]


@tool(domain="teach", name="recognize", symbolic=True,
      description="Read an equation written on the ASM Teach whiteboard (e.g. 'v = u + at', 'PV = nRT'): finds the "
                  "matching curriculum experiments and rearranges the equation for each quantity.")
def teach_recognize(equation: str, limit: int = 6) -> dict:
    if not isinstance(equation, str) or not equation.strip():
        raise ValueError("Write an equation or a topic first")
    if len(equation) > 300:
        raise ValueError("That is too long for one line of the board; write one equation at a time")
    text = split_teacher_text(equation)
    expr = None
    try:
        expr = parse_eq(text) if "=" in text else None
    except ValueError:
        expr = None
    matches: list[dict[str, Any]] = []
    rearranged: list[dict[str, str]] = []
    if expr is not None and expr.free_symbols:
        names = frozenset(sym_name(s) for s in expr.free_symbols)
        scored: dict[str, tuple[float, str, str]] = {}
        for exp_id, eq, eq_names in equation_index():
            if not eq_names:
                continue
            overlap = len(names & eq_names) / len(names | eq_names)
            if overlap < 0.34:
                continue
            score, reason = overlap * 0.8, "uses the same quantities" if overlap == 1 else "shares quantities"
            if eq_names == names:
                try:
                    other = parse_eq(eq)
                    syms = sorted(expr.free_symbols, key=lambda s: s.name)
                    if sp.simplify(expr - other) == 0 or sp.simplify(expr + other) == 0 or numerically_equivalent(expr, other, syms):
                        score, reason = 1.0, "same equation"
                except (ValueError, TypeError, NotImplementedError):
                    pass
            if exp_id not in scored or score > scored[exp_id][0]:
                scored[exp_id] = (score, reason, eq)
        for exp_id, (score, reason, eq) in sorted(scored.items(), key=lambda kv: (-kv[1][0], CATALOG[kv[0]].cls))[:limit]:
            matches.append({**CATALOG[exp_id].summary(), "score": round(score, 3), "reason": reason, "matched": pretty(eq)})
        for s in sorted(expr.free_symbols, key=lambda s: s.name)[:8]:
            try:
                sols = sp.solve(expr, s)
            except (NotImplementedError, ValueError, TypeError):
                continue
            for sol in sols[:2]:
                rearranged.append({"for": sym_name(s), "pretty": pretty(f"{sym_name(s)} = {_to_text(sol)}")})
    if not matches:  # a topic name instead of an equation, or an equation we don't teach: search the library
        words = [w for w in equation.lower().replace("=", " ").split() if len(w) > 1]
        ranked = []
        for e in CATALOG.values():
            hay = f"{e.title} {e.chapter} {e.tags}".lower()
            hits = sum(w in hay for w in words)
            if hits:
                ranked.append((hits / len(words), e))
        for score, e in sorted(ranked, key=lambda t: (-t[0], t[1].cls))[:limit]:
            matches.append({**e.summary(), "score": round(0.5 * score, 3), "reason": "topic match", "matched": ""})
    return {"result": {"input": equation, "read_as": pretty(text) if expr is not None else None, "matches": matches,
                       "rearranged": rearranged},
            "units": {}, "assumptions": ["Symbols are matched by name, so write them the way the textbook does (v, u, a, t)."]}


def _to_text(expr: sp.Expr) -> str:
    s = sp.sstr(expr)
    for k in ("I", "E", "S", "N", "Q", "O", "beta", "gamma", "zeta"):
        s = s.replace(f"{k}_rsv", k)
    return s
