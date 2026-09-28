"""Run a registry tool safely: check the arguments against its signature, map failures to clear
messages, and give open-ended symbolic work a time limit (in a child process that can be killed)."""
from __future__ import annotations

import inspect
import math
import multiprocessing as mp
import types
import typing
from typing import Any

import numpy as np

from app.core.registry import Tool


class ToolInputError(ValueError):
    """The arguments (or the problem they describe) cannot be computed. Maps to HTTP 422."""


class ToolTimeout(ToolInputError):
    """The computation exceeded its time limit."""


# Exceptions that mean "this input can't be computed" rather than "the engine is broken"
INPUT_ERRORS = (ValueError, TypeError, KeyError, ArithmeticError, np.linalg.LinAlgError, NotImplementedError, RecursionError)


def _accepts(tp: Any, value: Any) -> bool:
    """Shallow type check of a JSON value against a parameter annotation."""
    if tp is Any or tp is inspect.Parameter.empty:
        return True
    origin, args = typing.get_origin(tp), typing.get_args(tp)
    if origin in (typing.Union, types.UnionType):
        return any(_accepts(a, value) for a in args)
    if tp is type(None):
        return value is None
    if tp is bool:
        return isinstance(value, bool)
    if tp is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if tp is float:  # NaN and ±inf are never meaningful physical inputs (and can stall integrators)
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if tp is str:
        return isinstance(value, str)
    if origin in (list, tuple) or tp in (list, tuple):
        if not isinstance(value, (list, tuple)):
            return False
        return not args or all(_accepts(args[0], v) for v in value)
    if origin is dict or tp is dict:
        if not isinstance(value, dict):
            return False
        return len(args) != 2 or all(_accepts(args[1], v) for v in value.values())
    return True


def _nonfinite(value: Any) -> bool:
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, (list, tuple)):
        return any(_nonfinite(v) for v in value)
    if isinstance(value, dict):
        return any(_nonfinite(v) for v in value.values())
    return False


def _describe(tp: Any) -> str:
    text = str(tp).replace("typing.", "").replace("<class '", "").replace("'>", "")
    return text.replace("NoneType", "None")


def validate_args(t: Tool, args: dict[str, Any]) -> None:
    if not isinstance(args, dict):
        raise ToolInputError("args must be a JSON object of named arguments")
    sig = inspect.signature(t.func)
    hints = typing.get_type_hints(t.func)
    params = {n: p for n, p in sig.parameters.items() if p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)}
    unknown = sorted(set(args) - set(params))
    if unknown:
        raise ToolInputError(f"unknown argument(s) {', '.join(unknown)} for {t.key}; valid arguments: {', '.join(params)}")
    missing = [n for n, p in params.items() if p.default is inspect.Parameter.empty and n not in args]
    if missing:
        raise ToolInputError(f"missing required argument(s) {', '.join(missing)} for {t.key}")
    for name, value in args.items():
        tp = hints.get(name, Any)
        if value is None and params[name].default is None:
            continue
        if not _accepts(tp, value):
            if _nonfinite(value):
                raise ToolInputError(f"argument {name!r} must contain only finite numbers (no NaN or infinity)")
            raise ToolInputError(f"argument {name!r} should be {_describe(tp)}, got {type(value).__name__} {str(value)[:60]!r}")


def _call(t: Tool, args: dict[str, Any]) -> dict[str, Any]:
    try:
        return t.func(**args)
    except INPUT_ERRORS as exc:
        msg = str(exc) or exc.__class__.__name__
        if isinstance(exc, RecursionError):
            msg = "the expression is too deeply nested to evaluate"
        elif isinstance(exc, NotImplementedError):
            msg = f"the engine cannot handle this case: {msg}"
        elif isinstance(exc, ArithmeticError) and not isinstance(exc, ValueError):
            msg = f"{exc.__class__.__name__}: {msg}"
        raise ToolInputError(msg) from exc


def _child(conn, t: Tool, args: dict[str, Any]) -> None:  # pragma: no cover - runs in the forked process
    try:
        conn.send(("ok", _call(t, args)))
    except ToolInputError as exc:
        conn.send(("input", str(exc)))
    except BaseException as exc:  # noqa: BLE001 - report anything back to the parent
        conn.send(("crash", f"{exc.__class__.__name__}: {exc}"))
    finally:
        conn.close()


def _fork_available() -> bool:
    return "fork" in mp.get_all_start_methods()


def run(t: Tool, args: dict[str, Any], timeout: float = 20.0) -> dict[str, Any]:
    """Validate and execute a tool. Raises ToolInputError (bad input, unsolvable, too slow) or RuntimeError."""
    validate_args(t, args)
    if not t.symbolic or not _fork_available() or timeout <= 0:
        return _call(t, args)
    ctx = mp.get_context("fork")
    parent, child = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_child, args=(child, t, args), daemon=True)
    proc.start()
    child.close()
    try:
        if not parent.poll(timeout):
            raise ToolTimeout(f"{t.key} took longer than {timeout:g} s; try a simpler expression or a numerical tool")
        try:
            kind, payload = parent.recv()
        except EOFError:
            raise RuntimeError(f"{t.key} stopped unexpectedly") from None
    finally:
        if proc.is_alive():
            proc.kill()
        proc.join(1)
        parent.close()
    if kind == "ok":
        return payload
    if kind == "input":
        raise ToolInputError(payload)
    raise RuntimeError(f"internal error in {t.key}: {payload}")
