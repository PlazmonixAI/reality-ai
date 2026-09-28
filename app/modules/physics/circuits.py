"""DC circuit analysis by modified nodal analysis (Kirchhoff's laws), numpy."""
from typing import Any

import numpy as np

from app.core.registry import tool

GMIN = 1e-12  # tiny conductance from every node to ground so floating parts stay solvable (as SPICE does)
_TYPES = ("resistor", "wire", "voltage_source", "current_source")


@tool(
    domain="physics",
    name="dc_circuit",
    description=(
        "Solve a DC circuit with Kirchhoff's laws (modified nodal analysis). components: list of "
        "{type, a, b, value} where type is resistor (value in ohm), wire (ideal-ish, wire_resistance), "
        "voltage_source (value V, a = + terminal, optional internal_resistance ohm) or current_source (value A "
        "pushed into node a, out of node b). Nodes are any labels. Returns node voltages and each component's "
        "current (a -> b), voltage (Va - Vb) and power. Example: components=[{type:'voltage_source',a:'1',b:'0',"
        "value:9},{type:'resistor',a:'1',b:'2',value:1000},{type:'resistor',a:'2',b:'0',value:2000}]."
    ),
)
def dc_circuit(components: list[dict[str, Any]], ground: str | None = None, wire_resistance: float = 1e-4) -> dict:
    if not components:
        raise ValueError("Give at least one component")
    if len(components) > 500:
        raise ValueError("At most 500 components")
    if wire_resistance <= 0:
        raise ValueError("wire_resistance must be positive")

    parts = []
    for i, c in enumerate(components):
        kind = c.get("type")
        if kind not in _TYPES:
            raise ValueError(f"Component {i}: type must be one of {_TYPES}")
        if "a" not in c or "b" not in c:
            raise ValueError(f"Component {i}: needs nodes a and b")
        a, b = str(c["a"]), str(c["b"])
        if a == b:
            raise ValueError(f"Component {i}: both ends on node {a}")
        value = float(c.get("value", 0.0))
        if kind == "resistor" and value <= 0:
            raise ValueError(f"Component {i}: resistance must be positive")
        r_int = float(c.get("internal_resistance", 0.0))
        if r_int < 0:
            raise ValueError(f"Component {i}: internal_resistance must be >= 0")
        parts.append({"i": i, "type": kind, "a": a, "b": b, "value": value, "r_int": r_int})

    nodes: list[str] = []
    for p in parts:
        for n in (p["a"], p["b"]):
            if n not in nodes:
                nodes.append(n)
    if ground is None:
        named = next((nd for nd in nodes if nd.lower() in ("0", "gnd", "ground")), None)
        src = next((p for p in parts if p["type"] == "voltage_source"), None)
        ground = named or (src["b"] if src else nodes[0])
    ground = str(ground)
    if ground not in nodes:
        raise ValueError(f"Ground node {ground!r} is not in the circuit")

    # Voltage sources with internal resistance get a private internal node between the ideal source and r.
    internal = {}
    for p in parts:
        if p["type"] == "voltage_source" and p["r_int"] > 0:
            internal[p["i"]] = f"__int{p['i']}"
            nodes.append(internal[p["i"]])
    idx = {n: k for k, n in enumerate(n for n in nodes if n != ground)}
    vsources = [p for p in parts if p["type"] == "voltage_source"]
    n, m = len(idx), len(vsources)
    A = np.zeros((n + m, n + m))
    z = np.zeros(n + m)

    def stamp_g(na: str, nb: str, g: float) -> None:
        ia, ib = idx.get(na), idx.get(nb)
        if ia is not None: A[ia, ia] += g
        if ib is not None: A[ib, ib] += g
        if ia is not None and ib is not None:
            A[ia, ib] -= g; A[ib, ia] -= g

    for k in range(n):
        A[k, k] += GMIN
    for p in parts:
        if p["type"] in ("resistor", "wire"):
            stamp_g(p["a"], p["b"], 1 / (p["value"] if p["type"] == "resistor" else wire_resistance))
        elif p["type"] == "current_source":
            if p["a"] in idx: z[idx[p["a"]]] += p["value"]
            if p["b"] in idx: z[idx[p["b"]]] -= p["value"]
    for j, p in enumerate(vsources):
        plus = internal.get(p["i"], p["a"])
        if p["i"] in internal:
            stamp_g(plus, p["a"], 1 / p["r_int"])
        # Ideal source between `plus` and b: V(plus) - V(b) = value; unknown current flows plus -> b inside.
        for node, sign in ((plus, 1), (p["b"], -1)):
            if node in idx:
                A[idx[node], n + j] += sign
                A[n + j, idx[node]] += sign
        z[n + j] = p["value"]

    if np.linalg.cond(A) > 1e15:
        raise ValueError("Circuit is singular: a loop made only of ideal voltage sources, or sources fighting in parallel")
    x = np.linalg.solve(A, z)
    volt = {nd: (0.0 if nd == ground else float(x[idx[nd]])) for nd in nodes}

    results, supplied, dissipated = [], 0.0, 0.0
    for p in parts:
        va, vb = volt[p["a"]], volt[p["b"]]
        if p["type"] in ("resistor", "wire"):
            r = p["value"] if p["type"] == "resistor" else wire_resistance
            cur = (va - vb) / r
            power = cur * cur * r
            dissipated += power
        elif p["type"] == "current_source":
            cur = -p["value"]            # through the component from a to b (it pushes current out of a)
            power = -(va - vb) * cur     # power delivered to the circuit
            supplied += power
        else:
            j = vsources.index(p)
            cur = float(x[n + j])        # a -> b inside the source; negative when it drives current out of +
            delivered = -cur
            loss = delivered**2 * p["r_int"]
            power = (volt[internal.get(p["i"], p["a"])] - vb) * delivered
            supplied += power
            dissipated += loss
        results.append({
            "index": p["i"], "type": p["type"], "a": p["a"], "b": p["b"],
            "current": cur, "voltage": va - vb,
            "power": power,
        })
    return {
        "result": {
            "node_voltages": {k: v for k, v in volt.items() if not k.startswith("__int")},
            "components": results,
            "power_supplied": supplied,
            "power_dissipated": dissipated,
        },
        "ground": ground,
        "units": "voltages V (relative to ground), currents A (positive from a to b), power W",
        "assumptions": [
            "Linear DC steady state, ideal sources (plus any given internal resistance)",
            f"Wires modelled as {wire_resistance} ohm resistors; {GMIN} S leakage to ground keeps floating parts solvable",
            "For sources, power is what they deliver to the circuit; for resistors, what they dissipate",
        ],
    }
