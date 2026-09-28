"""The AI representative: question → LLM picks tool(s) → engine computes → LLM explains.

The LLM never supplies numbers of its own: every figure in the answer should come from a tool result,
which is fed back to it (large arrays compacted) together with units and assumptions.
"""
from __future__ import annotations

import json
import math
from typing import Any, Protocol

from app.agent.tool_schemas import select_tools, tool_for_function, tool_schema

SYSTEM_PROMPT = """You are the AI representative of Reality ASM (Advanced Simulation Machine), Plazmonix AI's \
physics, chemistry and mathematics simulation engine.

Rules:
- Always answer quantitative questions by calling the provided tools. Never invent or estimate numbers yourself; \
every number you state must come from a tool result (or be a direct unit conversion of one).
- Tools take SI units unless their description says otherwise; convert the user's units before calling.
- If a tool returns an error, fix the arguments and try again, or explain what is missing.
- If no tool fits, say so plainly and suggest what the engine can compute instead. Biology is out of scope.
- In the final answer: give the result with units, then the key assumptions and limitations from the tool output, \
briefly. Use plain language and keep it concise."""

MAX_LIST = 12  # longer arrays are summarised before being shown to the LLM


class ChatClient(Protocol):
    model: str

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,
             tool_choice: str | None = "auto", temperature: float = 0.2, max_tokens: int = 1024) -> dict[str, Any]: ...


def compact(value: Any, depth: int = 0) -> Any:
    """Shrink a tool result for the LLM: summarise long arrays, round floats, cap nesting."""
    if isinstance(value, float):
        return value if not math.isfinite(value) or value == 0 else float(f"{value:.6g}")
    if isinstance(value, dict):
        if depth > 5:
            return "{…}"
        return {k: compact(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_LIST:
            nums = [v for v in value if isinstance(v, (int, float)) and not isinstance(v, bool)]
            if len(nums) == len(value):
                return {"n": len(value), "first": compact(value[0]), "last": compact(value[-1]),
                        "min": compact(min(nums)), "max": compact(max(nums))}
            return [compact(v, depth + 1) for v in value[:MAX_LIST]] + [f"… {len(value) - MAX_LIST} more"]
        return [compact(v, depth + 1) for v in value]
    if isinstance(value, str) and len(value) > 400:
        return value[:400] + "…"
    return value


def run_tool(name: str, raw_args: str | dict | None) -> tuple[str | None, dict[str, Any], dict[str, Any]]:
    """Execute one tool call. Returns (tool key, parsed args, result-or-error dict)."""
    t = tool_for_function(name)
    if t is None:
        return None, {}, {"error": f"unknown tool {name!r}"}
    try:
        args = raw_args if isinstance(raw_args, dict) else json.loads(raw_args or "{}")
        if not isinstance(args, dict):
            raise ValueError("arguments must be a JSON object")
    except (ValueError, TypeError) as exc:
        return t.key, {}, {"error": f"could not parse arguments: {exc}"}
    try:
        return t.key, args, t.func(**args)
    except (TypeError, ValueError, KeyError, ZeroDivisionError, OverflowError) as exc:
        return t.key, args, {"error": f"{exc.__class__.__name__}: {exc}"}


def ask(question: str, client: ChatClient, history: list[dict[str, str]] | None = None,
        max_rounds: int = 4, n_tools: int = 12) -> dict[str, Any]:
    question = question.strip()
    if not question:
        raise ValueError("question is empty")
    tools = [tool_schema(t) for t in select_tools(question, n_tools)]
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history or []:
        if h.get("role") in ("user", "assistant") and isinstance(h.get("content"), str):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": question})
    trace: list[dict[str, Any]] = []
    for round_ in range(max_rounds):
        msg = client.chat(messages, tools=tools)
        calls = msg.get("tool_calls") or []
        if not calls:
            return {"answer": (msg.get("content") or "").strip(), "tool_calls": trace, "model": client.model, "rounds": round_ + 1}
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for call in calls:
            fn = call.get("function", {})
            key, args, result = run_tool(fn.get("name", ""), fn.get("arguments"))
            small = compact(result)
            trace.append({"tool": key or fn.get("name"), "args": args, "result": small, "ok": "error" not in result})
            messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": json.dumps(small, ensure_ascii=False)})
    # Out of tool rounds: ask for the explanation without further tool use
    msg = client.chat(messages, tools=tools, tool_choice="none")
    return {"answer": (msg.get("content") or "").strip(), "tool_calls": trace, "model": client.model, "rounds": max_rounds + 1}
