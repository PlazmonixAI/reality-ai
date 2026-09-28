"""Reference example tool. Copy this pattern for every new tool."""
import sympy as sp

from app.core.parsing import parse_equation, symbol
from app.core.registry import tool


@tool(
    domain="mathematics",
    name="solve_equation",
    symbolic=True,
    description="Solve an algebraic equation for a variable. Example: equation='x**2 - 4 = 0', variable='x'.",
)
def solve_equation(equation: str, variable: str = "x") -> dict:
    var = symbol(variable)
    expr = parse_equation(equation)
    solutions = sp.solve(expr, var)
    return {
        "result": [str(s) for s in solutions],
        "units": "dimensionless",
        "assumptions": ["Symbolic solution over the complex numbers (sympy.solve)"],
    }
