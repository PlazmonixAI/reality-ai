"""Central tool registry. Every simulation tool registers here via @tool."""
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    domain: str
    name: str
    description: str
    func: Callable[..., dict[str, Any]]
    symbolic: bool = False  # heavy sympy work: run in a child process with a time limit

    @property
    def key(self) -> str:
        return f"{self.domain}.{self.name}"


_REGISTRY: dict[str, Tool] = {}


def tool(domain: str, name: str, description: str, symbolic: bool = False):
    """Decorator that registers a simulation function. symbolic=True marks open-ended sympy work
    (solving, integrating, limits, series) that must run under a time limit."""
    def decorator(func: Callable[..., dict[str, Any]]):
        t = Tool(domain=domain, name=name, description=description, func=func, symbolic=symbolic)
        if t.key in _REGISTRY:
            raise ValueError(f"Tool already registered: {t.key}")
        _REGISTRY[t.key] = t
        return func
    return decorator


def get_tool(domain: str, name: str) -> Tool:
    key = f"{domain}.{name}"
    if key not in _REGISTRY:
        raise KeyError(f"Unknown tool: {key}")
    return _REGISTRY[key]


def list_tools() -> list[Tool]:
    return list(_REGISTRY.values())
