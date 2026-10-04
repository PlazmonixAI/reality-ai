"""ASM Teach listen mode: turn what the teacher says into what the class sees.

The browser's speech recognition sends each finished sentence here. This module reads it the way a teacher speaks
("T equals 2 pi root L by g", "a pendulum of length 2 metres", "take angle 30 degrees") and decides what to show:
the matching experiment with the spoken values, or the Equation Lab for an equation the library does not have.
It is plain parsing and search over the catalogue; the AI co-teacher is a separate, optional layer.
"""
from __future__ import annotations

import re
from typing import Any

from app.core.registry import tool
from app.modules.teach import catalog  # noqa: F401  (fills CATALOG)
from app.modules.teach.core import CATALOG, equation_index

_PHRASES = [  # longest first; how teachers say mathematics aloud (Indian classroom usage included)
    (r"\bis equal to\b|\bequals to\b|\bequals\b|\bequal to\b|\bis equal\b", " = "),
    (r"\bdivided by\b|\bupon\b|\bover\b|\bby\b", " / "),
    (r"\bmultiplied by\b|\btimes\b|\binto\b", " * "),
    (r"\bplus\b", " + "), (r"\bminus\b", " - "),
    (r"\bto the power of\b|\bto the power\b|\braised to\b|\bpower\b", " ^ "),
    (r"\bsquared\b|\bsquare\b", " ^ 2 "), (r"\bcubed\b|\bcube\b", " ^ 3 "),
    (r"\bsquare root of\b|\bunder root\b|\broot of\b|\broot\b", " sqrt "),
    (r"\bsine\b", " sin "), (r"\bcosine\b", " cos "), (r"\btangent\b", " tan "),
    (r"\bhalf\b", " ( 1 / 2 ) * "), (r"\bopen bracket\b", " ( "), (r"\bclose bracket\b", " ) "),
]
_NUM_WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                         "fifteen sixteen seventeen eighteen nineteen twenty".split())}
_NUM_WORDS.update({"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100})
_FUNCS = {"sin", "cos", "tan", "cot", "sec", "csc", "log", "ln", "exp", "sqrt", "pi", "theta", "alpha", "beta", "omega", "lambda", "mu"}
_STOP = set("the a an of is are was and to in on at for with this that we us let lets see take now here there it its our your "
            "what how why when which so then some any can will be by from as into over upon equals equal plus minus times "
            "find about look today class students please okay ok right well also just".split())
_UNITS = {"degrees": "deg", "degree": "deg", "metres": "m", "meters": "m", "metre": "m", "meter": "m", "m": "m",
          "centimetres": "cm", "centimeters": "cm", "cm": "cm", "kilograms": "kg", "kilogram": "kg", "kg": "kg", "grams": "g",
          "gram": "g", "seconds": "s", "second": "s", "s": "s", "newtons": "N", "newton": "N", "volts": "V", "volt": "V",
          "ohms": "ohm", "ohm": "ohm", "kelvin": "K", "hertz": "Hz", "joules": "J", "joule": "J", "amperes": "A", "ampere": "A",
          "amps": "A"}


def _words_to_numbers(text: str) -> str:
    def repl(m: re.Match) -> str:
        parts = m.group(0).split()
        total, cur = 0, 0
        for p in parts:
            v = _NUM_WORDS[p]
            if v == 100:
                cur = max(cur, 1) * 100
            else:
                cur += v
        return str(total + cur)
    pat = r"\b(?:" + "|".join(sorted(_NUM_WORDS, key=len, reverse=True)) + r")(?:\s+(?:" + "|".join(sorted(_NUM_WORDS, key=len, reverse=True)) + r"))*\b"
    out = re.sub(pat, repl, text)
    return re.sub(r"(\d+)\s+point\s+(\d+)", r"\1.\2", out)


def spoken_to_math(text: str) -> str:
    """'T equals 2 pi root L by g' -> 'T = 2 pi sqrt( L / g )' (only the equation part of the sentence)."""
    t = _words_to_numbers(text)
    for pat, rep in _PHRASES:
        t = re.sub(pat, rep, t, flags=re.I)
    tokens = re.findall(r"\d+(?:\.\d+)?|[A-Za-z]+|[=+\-*/^()]", t)
    if "=" not in tokens:
        return ""
    def mathy(tok: str) -> bool:
        return bool(re.fullmatch(r"\d+(?:\.\d+)?|[=+\-*/^()]", tok)) or len(tok) == 1 or tok.lower() in _FUNCS
    i = tokens.index("=")
    lo, hi = i, i
    while lo > 0 and mathy(tokens[lo - 1]):
        lo -= 1
    while hi < len(tokens) - 1 and mathy(tokens[hi + 1]):
        hi += 1
    span = tokens[lo:hi + 1]
    while span and span[0] in "=+*/^)":
        span = span[1:]
    while span and span[-1] in "=+-*/^(":
        span = span[:-1]
    if "=" not in span or span.index("=") == 0 or span.index("=") == len(span) - 1:
        return ""
    out: list[str] = []  # "sqrt L / g" -> "sqrt( L / g )": a spoken root covers the rest of the term
    open_root = 0
    for tok in span:
        if tok in ("+", "-", "=") and open_root:
            out.append(")" * open_root)
            open_root = 0
        if tok.lower() == "sqrt":
            out.append("sqrt(")
            open_root += 1
            continue
        out.append(tok.lower() if tok.lower() in _FUNCS else tok)
    out.append(")" * open_root)
    return " ".join(x for x in out if x).replace("( ", "(")


def _recase(eq: str) -> str:
    """Speech arrives in lower case; give each letter the case the textbook uses (t vs T, l vs L, g)."""
    letters = set(re.findall(r"\b[A-Za-z]\b", eq))
    if not letters:
        return eq
    lowered = {c.lower() for c in letters}
    best, best_score = None, 0.0
    for _, _, names in equation_index():
        if not names:
            continue
        low = {n.lower() for n in names if len(n) == 1}
        if not low:
            continue
        score = len(lowered & low) / len(lowered | low)
        if score > best_score:
            best, best_score = names, score
    if not best or best_score < 0.5:
        return eq
    case = {n.lower(): n for n in best if len(n) == 1}
    return re.sub(r"\b([A-Za-z])\b", lambda m: case.get(m.group(1).lower(), m.group(1)), eq)


def _topic(words: list[str]) -> tuple[Any, int]:
    best, best_hits = None, 0
    for e in CATALOG.values():
        hay = f"{e.title} {e.chapter} {e.tags}".lower()
        title = e.title.lower()
        hits = sum(1 for w in set(words) if re.search(rf"\b{re.escape(w)}", hay))
        hits += sum(1 for w in set(words) if re.search(rf"\b{re.escape(w)}", title))  # title words count double
        if hits > best_hits or (hits == best_hits and best is not None and e.cls < best.cls):
            best, best_hits = e, hits
    return best, best_hits


def _values(text: str, e) -> dict[str, float]:
    """'length 2 metres', 'angle of 30 degrees', 'g is 9.8' -> parameter values, converted and clamped."""
    t = _words_to_numbers(text.lower())
    out: dict[str, float] = {}
    for m in re.finditer(r"(-?\d+(?:\.\d+)?)\s*([a-z]+)?", t):
        before = re.findall(r"[a-z]+", t[max(0, m.start() - 45): m.start()])[-5:]
        unit = _UNITS.get(m.group(2) or "", "")
        value = float(m.group(1))
        for p in e.params:
            if p.name in out:
                continue
            label = [w for w in re.findall(r"[a-z]+", p.label.lower()) if len(w) >= 4 and w not in _STOP]
            named = p.name.lower() in before[-2:] if len(p.name) <= 2 else p.name.lower() in before
            if not (named or any(w in before for w in label)):
                continue
            v = value
            if unit == "cm" and p.unit == "m":
                v /= 100
            if unit == "g" and p.unit == "kg":
                v /= 1000
            out[p.name] = v  # what the teacher said, even outside the slider range
            break
    return out


@tool(domain="teach", name="listen",
      description="ASM Teach listen mode: reads one sentence the teacher said (speech-to-text) and decides what to show. "
                  "Spoken equations ('T equals 2 pi root L by g'), topics ('a simple pendulum') and values ('length 2 "
                  "metres') become the matching experiment with those values, or the Equation Lab for any other equation.")
def teach_listen(transcript: str, current: str | None = None) -> dict:
    from app.modules.teach.lab import teach_recognize
    if not isinstance(transcript, str) or not transcript.strip():
        raise ValueError("Nothing was heard")
    heard = transcript.strip()[:400]
    equation = spoken_to_math(heard)
    if equation:
        equation = _recase(equation)
    experiment, values, matches = None, {}, []
    if equation:
        try:
            matches = teach_recognize(equation, limit=3)["result"]["matches"]
        except ValueError:
            matches = []
        if matches and matches[0]["score"] >= 1.0:
            experiment = CATALOG[matches[0]["id"]]
    if experiment is None and not equation:
        words = [w for w in re.findall(r"[a-z']+", heard.lower()) if len(w) > 2 and w not in _STOP]
        if current and current in CATALOG and _values(heard, CATALOG[current]):
            experiment = CATALOG[current]  # values for the experiment already on screen
        elif words:
            e, hits = _topic(words)
            if e is not None and hits >= 2:
                experiment = e
    if experiment is not None:
        values = _values(heard, experiment)
    if experiment is not None:
        action = "update" if current == experiment.id else "open"
        say = f"{experiment.title}" + (" with " + ", ".join(f"{k} = {v:g}" for k, v in values.items()) if values else "")
    elif equation:
        action, say = "explore", f"Equation Lab: {equation}"
    else:
        action, say = "none", "Nothing to show for that yet."
    return {"result": {"heard": heard, "action": action, "say": say, "equation": equation or None,
                       "experiment": experiment.summary() if experiment is not None else None, "values": values,
                       "matches": matches},
            "units": {"values": "SI, converted from the units spoken (cm to m, g to kg)"},
            "assumptions": ["Spoken maths: 'equals' is =, 'by'/'over' divide, 'into'/'times' multiply, 'root' covers the rest of the term",
                            "Values are matched to the experiment's parameter names and clamped to their ranges"]}
