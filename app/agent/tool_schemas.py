"""Registry tools → OpenAI-style function schemas, plus a small keyword ranker so each request only
carries the tools that are relevant to the question."""
from __future__ import annotations

import inspect
import math
import re
import types
import typing
from collections import Counter
from functools import lru_cache
from typing import Any

from app.core.registry import Tool, get_tool, list_tools

SEPARATOR = "__"  # function names may not contain '.', so domain__name


def function_name(t: Tool) -> str:
    return f"{t.domain}{SEPARATOR}{t.name}"


def tool_for_function(name: str) -> Tool | None:
    for t in list_tools():
        if function_name(t) == name:
            return t
    return None


def _json_type(tp: Any) -> dict[str, Any]:
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin in (typing.Union, types.UnionType):
        non_null = [a for a in args if a is not type(None)]
        return _json_type(non_null[0]) if len(non_null) == 1 else {}
    if tp is bool:
        return {"type": "boolean"}
    if tp is int:
        return {"type": "integer"}
    if tp is float:
        return {"type": "number"}
    if tp is str:
        return {"type": "string"}
    if origin in (list, tuple) or tp in (list, tuple):
        return {"type": "array", "items": _json_type(args[0]) if args else {}}
    if origin is dict or tp is dict:
        return {"type": "object", "additionalProperties": _json_type(args[1]) if len(args) == 2 else {}}
    return {}


def tool_schema(t: Tool) -> dict[str, Any]:
    return _schema(t.domain, t.name)


@lru_cache(maxsize=None)
def _schema(domain: str, name: str) -> dict[str, Any]:
    t = get_tool(domain, name)
    sig = inspect.signature(t.func)
    hints = typing.get_type_hints(t.func)
    props: dict[str, Any] = {}
    required: list[str] = []
    for p in sig.parameters.values():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        spec = _json_type(hints.get(p.name, Any))
        if p.default is inspect.Parameter.empty:
            required.append(p.name)
        elif p.default is not None and isinstance(p.default, (int, float, str, bool)):
            spec = {**spec, "default": p.default}
        props[p.name] = spec
    return {
        "type": "function",
        "function": {
            "name": function_name(t),
            "description": t.description[:1000],
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


# -- relevance ranking ----------------------------------------------------------------------------
_WORD = re.compile(r"[a-z0-9]+")
_STOP = set("the and for with from what how much many does into this that are was were can you give find show get use about "
            "which when where why who will would should could our your their its has have had not all any per than then".split())


def _tokens(text: str) -> list[str]:
    out = []
    for w in _WORD.findall(text.lower().replace("_", " ").replace("-", " ")):
        if w in _STOP or len(w) < 2:
            continue
        out.append(w[:-1] if len(w) > 4 and w.endswith("s") else w)
    return out


@lru_cache(maxsize=1)
def _index() -> tuple[list[Tool], list[Counter], dict[str, float]]:
    tools = list_tools()
    docs = []
    for t in tools:
        c = Counter(_tokens(t.description))
        for w in _tokens(t.name) + _tokens(t.domain):
            c[w] += 3  # name and domain words matter most
        docs.append(c)
    df = Counter(w for d in docs for w in d)
    n = len(docs)
    idf = {w: math.log(1 + n / f) for w, f in df.items()}
    return tools, docs, idf


def select_tools(question: str, k: int = 12) -> list[Tool]:
    """The k registry tools whose names/descriptions best match the question (TF-IDF overlap)."""
    tools, docs, idf = _index()
    q = set(_tokens(question))
    scored = []
    for t, d in zip(tools, docs):
        s = sum(idf.get(w, 0) * (1 + math.log(d[w])) for w in q if d[w])
        scored.append((s, t.key, t))
    scored.sort(key=lambda x: (-x[0], x[1]))
    picked = [t for s, _, t in scored if s > 0][:k]
    return picked or [t for _, _, t in scored[:k]]
